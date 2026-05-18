"""Closed-loop gap analysis: сравнивает текущий прогон с предыдущим ядром и конкурентами.

Хранит previous_core в data/state/core.json. На повторном прогоне:
- новые кластеры → gap=missing
- кластеры, которых больше нет → дроп / архив
- кластеры, у которых упал/вырос запрос → traffic_status
- gap vs competitor pages → competitor_coverage
"""
from __future__ import annotations
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .cluster import Cluster, embed


STATE_FILE_DEFAULT = Path("data/state/core.json")


def load_state(path: Path | str = STATE_FILE_DEFAULT) -> dict:
    path = Path(path)
    if not path.exists():
        return {"clusters": [], "version": 0}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(state: dict, path: Path | str = STATE_FILE_DEFAULT) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _cluster_signature(c: Cluster) -> dict:
    return {
        "cluster_id": c.cluster_id,
        "label": c.label,
        "slug": getattr(c, "slug", ""),
        "intent": c.intent,
        "queries": list(c.queries),
    }


def diff_with_previous(
    current: list[Cluster],
    previous_state: dict,
    *,
    similarity_threshold: float = 0.75,
) -> dict[int, dict]:
    """Match current clusters к prev по centroid similarity. Return per cluster diff.

    diff entry: {
       "gap_status": "new" | "existing" | "shifted",
       "matched_prev_label": str | None,
       "matched_prev_sim": float,
       "new_queries":     [q...] not in previous cluster,
       "lost_queries":    [q...] in previous cluster but not in current,
    }
    """
    prev_clusters = previous_state.get("clusters", [])
    if not prev_clusters or not current:
        return {c.cluster_id: {"gap_status": "new", "matched_prev_label": None, "matched_prev_sim": 0.0,
                                "new_queries": list(c.queries), "lost_queries": []} for c in current}

    # Embed labels of current and previous
    curr_texts = [c.label or " ".join(c.queries[:3]) for c in current]
    prev_texts = [p.get("label") or " ".join(p.get("queries", [])[:3]) for p in prev_clusters]
    curr_emb = embed(curr_texts)
    prev_emb = embed(prev_texts)
    sims = curr_emb @ prev_emb.T  # cosine (normalized)

    out: dict[int, dict] = {}
    for i, c in enumerate(current):
        j = int(np.argmax(sims[i])) if len(prev_emb) else -1
        best_sim = float(sims[i, j]) if j >= 0 else 0.0
        if best_sim >= similarity_threshold and j >= 0:
            prev = prev_clusters[j]
            prev_set = set(q.lower() for q in prev.get("queries", []))
            curr_set = set(q.lower() for q in c.queries)
            new_q = sorted(curr_set - prev_set)
            lost_q = sorted(prev_set - curr_set)
            status = "shifted" if (new_q or lost_q) else "existing"
            out[c.cluster_id] = {
                "gap_status": status,
                "matched_prev_label": prev.get("label"),
                "matched_prev_sim": round(best_sim, 3),
                "new_queries": new_q,
                "lost_queries": lost_q,
            }
        else:
            out[c.cluster_id] = {
                "gap_status": "new",
                "matched_prev_label": None,
                "matched_prev_sim": round(best_sim, 3),
                "new_queries": list(c.queries),
                "lost_queries": [],
            }
    return out


def find_removed_clusters(
    current: list[Cluster],
    previous_state: dict,
    *,
    similarity_threshold: float = 0.75,
) -> list[dict]:
    """Кластеры из previous_state, которым в current не нашлось пары → кандидаты на дроп/архив.

    Возвращает список prev-кластеров с полями `label`, `intent`, `queries`, `closest_curr_sim`.
    """
    prev_clusters = previous_state.get("clusters", [])
    if not prev_clusters or not current:
        return []

    curr_texts = [c.label or " ".join(c.queries[:3]) for c in current]
    prev_texts = [p.get("label") or " ".join(p.get("queries", [])[:3]) for p in prev_clusters]
    curr_emb = embed(curr_texts)
    prev_emb = embed(prev_texts)
    sims = prev_emb @ curr_emb.T  # prev × curr

    removed: list[dict] = []
    for i, prev in enumerate(prev_clusters):
        best_sim = float(np.max(sims[i])) if len(curr_emb) else 0.0
        if best_sim < similarity_threshold:
            removed.append({
                "label": prev.get("label", ""),
                "intent": prev.get("intent", ""),
                "queries": list(prev.get("queries", [])),
                "closest_curr_sim": round(best_sim, 3),
            })
    return removed


def diff_with_competitors(
    current: list[Cluster],
    competitor_page_titles: list[str],
    *,
    similarity_threshold: float = 0.55,
) -> dict[int, dict]:
    """Кластер vs категории конкурентов: где у конкурентов есть страница, а у нас кластер новый — competitor_pressure.

    competitor_page_titles: список названий категорий, собранных collect.fetch_competitor_categories.
    """
    if not competitor_page_titles or not current:
        return {c.cluster_id: {"competitor_coverage": "unknown", "competitor_match": None, "competitor_sim": 0.0}
                for c in current}

    curr_emb = embed([c.label or " ".join(c.queries[:3]) for c in current])
    comp_emb = embed(competitor_page_titles)
    sims = curr_emb @ comp_emb.T

    out: dict[int, dict] = {}
    for i, c in enumerate(current):
        j = int(np.argmax(sims[i]))
        best_sim = float(sims[i, j])
        if best_sim >= similarity_threshold:
            out[c.cluster_id] = {
                "competitor_coverage": "covered_by_competitor",
                "competitor_match": competitor_page_titles[j],
                "competitor_sim": round(best_sim, 3),
            }
        else:
            out[c.cluster_id] = {
                "competitor_coverage": "competitor_gap",
                "competitor_match": None,
                "competitor_sim": round(best_sim, 3),
            }
    return out


def build_state_from_clusters(clusters: list[Cluster], version: int) -> dict:
    return {
        "version": version,
        "clusters": [_cluster_signature(c) for c in clusters],
    }
