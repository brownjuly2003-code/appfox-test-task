"""Nodes для LangGraph supervisor — каждый делает один шаг flat-pipeline из run.py.

Каждый node принимает PipelineState и возвращает partial-state с новыми ключами.
Никаких side-effects кроме записи финальных артефактов в output_node.
"""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any

from core import clean as clean_mod
from core import cluster as cluster_mod
from core import collect as collect_mod
from core import gap as gap_mod
from core import output as output_mod

from .state import PipelineState


def collect_node(state: PipelineState) -> dict[str, Any]:
    """Сбор raw запросов из seeds + modifiers + competitors. Optional retry с расширенными modifiers.

    Кэширует competitor pages в state["comp_pages"], чтобы gap_node не скрейпил повторно.
    """
    seeds = state["seeds"]
    modifiers = state.get("modifiers", [])
    competitors = state.get("competitors", [])
    max_q = state.get("max_queries", 200)
    cached = state.get("comp_pages")  # переиспользуем при re-collect через yield_guard

    raw, comp_pages = collect_mod.collect_all(
        seeds=seeds,
        modifiers=modifiers,
        competitor_urls=competitors,
        autosuggest_per_seed=True,
        use_google=False,
        cached_comp_pages=cached,
    )
    raw = sorted(set(raw))
    if len(raw) > max_q:
        raw = sorted(raw, key=lambda q: (-len(q.split()), q))[:max_q]

    decisions = list(state.get("decisions", []))
    decisions.append(f"collect: {len(raw)} запросов (modifiers={len(modifiers)})")
    return {"raw_queries": raw, "comp_pages": comp_pages, "decisions": decisions}


def clean_node(state: PipelineState) -> dict[str, Any]:
    """Rule-фильтр + LLM intent. Возвращает обновлённый cleaned + decisions log."""
    raw = state["raw_queries"]
    biz = state["business_context"]
    cleaned = clean_mod.clean_batch(raw, biz, batch_size=25)
    cleaned_dicts = [c.to_dict() for c in cleaned]
    kept = sum(1 for c in cleaned_dicts if c.get("keep"))

    decisions = list(state.get("decisions", []))
    decisions.append(f"clean: kept {kept}/{len(cleaned_dicts)}")
    return {"cleaned": cleaned_dicts, "decisions": decisions}


def cluster_node(state: PipelineState) -> dict[str, Any]:
    """Agglomerative + facet-split. Может вызываться повторно с relaxed threshold."""
    cleaned = state["cleaned"]
    threshold = state.get("distance_threshold", 0.20)
    apply_split = state.get("apply_split", True)

    clusters = cluster_mod.cluster_queries(
        cleaned,
        distance_threshold=threshold,
        apply_split=apply_split,
    )
    decisions = list(state.get("decisions", []))
    decisions.append(f"cluster: {len(clusters)} (threshold={threshold:.2f})")
    return {"clusters": clusters, "decisions": decisions}


def label_node(state: PipelineState) -> dict[str, Any]:
    """LLM проставляет label+slug на каждый кластер in-place."""
    clusters = state["clusters"]
    biz = state["business_context"]
    cluster_mod.label_clusters(clusters, biz)
    decisions = list(state.get("decisions", []))
    decisions.append("label: done")
    return {"clusters": clusters, "decisions": decisions}


def merge_node(state: PipelineState) -> dict[str, Any]:
    """Post-merge дублей по label + centroid."""
    if not state.get("apply_merge", True):
        return {}
    clusters = state["clusters"]
    before = len(clusters)
    merged = cluster_mod.merge_duplicates(clusters)
    decisions = list(state.get("decisions", []))
    decisions.append(f"merge: {before} → {len(merged)}")
    return {"clusters": merged, "decisions": decisions}


def gap_node(state: PipelineState) -> dict[str, Any]:
    """Diff vs previous state + competitor SERP."""
    clusters = state["clusters"]
    state_file = state.get("state_file", "data/state/core.json")
    competitors = state.get("competitors", [])

    prev = gap_mod.load_state(state_file)
    prev_diff = gap_mod.diff_with_previous(clusters, prev)
    removed = gap_mod.find_removed_clusters(clusters, prev)

    # Переиспользуем comp_pages из collect_node — без повторного HTTP-скрейпа
    comp_pages: list[str] = state.get("comp_pages", []) or []
    comp_diff = gap_mod.diff_with_competitors(clusters, comp_pages)

    new_count = sum(1 for v in prev_diff.values() if v["gap_status"] == "new")
    decisions = list(state.get("decisions", []))
    decisions.append(
        f"gap: {new_count} новых vs prev, {len(removed)} убрано, {len(comp_pages)} competitor pages"
    )
    return {
        "prev_diff": prev_diff,
        "comp_diff": comp_diff,
        "removed_clusters": removed,
        "decisions": decisions,
    }


def output_node(state: PipelineState) -> dict[str, Any]:
    """Финальная сборка decision rows + запись артефактов."""
    clusters = state["clusters"]
    cleaned = state["cleaned"]
    existing_pages = state.get("existing_pages", [])
    metrics_by_query = state.get("metrics_by_query", {})
    prev_diff = state.get("prev_diff", {})
    comp_diff = state.get("comp_diff", {})

    metrics_by_cluster: dict[int, dict[str, float]] = {}
    for c in clusters:
        vols = [metrics_by_query[q.lower()]["search_volume"]
                for q in c.queries if q.lower() in metrics_by_query]
        if vols:
            metrics_by_cluster[c.cluster_id] = {"search_volume": sum(vols) / len(vols)}

    rows = output_mod.build_decision_rows(
        clusters,
        existing_pages,
        metrics_by_cluster=metrics_by_cluster,
    )
    for r in rows:
        gi = prev_diff.get(r["cluster_id"], {})
        ci = comp_diff.get(r["cluster_id"], {})
        r["gap_status"] = gi.get("gap_status", "new")
        r["competitor_coverage"] = ci.get("competitor_coverage", "unknown")
        r["matched_prev_label"] = gi.get("matched_prev_label", "") or ""
        r["new_queries"] = gi.get("new_queries", []) or []
        r["lost_queries"] = gi.get("lost_queries", []) or []

    out_dir = Path(state.get("out_dir", "data/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_mod.write_csv(rows, out_dir / "decisions.csv")
    md_path = output_mod.write_markdown(rows, out_dir / "decisions.md")
    queries_path = output_mod.write_queries_csv(cleaned, rows, out_dir / "queries.csv")
    raw_path = out_dir / "raw_cleaned.json"
    raw_path.write_text(
        json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    state_file = state.get("state_file", "data/state/core.json")
    prev = gap_mod.load_state(state_file)
    sp = gap_mod.save_state(
        gap_mod.build_state_from_clusters(clusters, version=prev.get("version", 0) + 1),
        state_file,
    )

    decisions = list(state.get("decisions", []))
    decisions.append(f"output: {len(rows)} rows → {csv_path}")
    return {
        "rows": rows,
        "metrics_by_cluster": metrics_by_cluster,
        "csv_path": str(csv_path),
        "md_path": str(md_path),
        "queries_path": str(queries_path),
        "raw_path": str(raw_path),
        "state_path": str(sp),
        "decisions": decisions,
    }
