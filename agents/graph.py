"""LangGraph StateGraph + supervisor decisions.

Flow:

    collect → clean → [yield_guard] ─┐
                              │      │
                              │      └─→ collect (1 retry с broader modifiers)
                              ▼
                          cluster → [size_guard] ─┐
                                          │       │
                                          │       └─→ cluster (1 retry с relaxed threshold)
                                          ▼
                                      label → merge → gap → output → END

Guards принимают однократное решение (см. MAX_*_RETRIES в state.py) — это не
бесконечный цикл, а одна попытка адаптации к плохим входным данным.
"""
from __future__ import annotations
from typing import Literal

from langgraph.graph import END, StateGraph

from .nodes import (
    clean_node,
    cluster_node,
    collect_node,
    gap_node,
    label_node,
    merge_node,
    output_node,
)
from .state import (
    BROADER_MODIFIERS,
    MAX_CLUSTER_RETRIES,
    MAX_COLLECT_RETRIES,
    MIN_CLUSTERS_AFTER_CLUSTER,
    PipelineState,
    THRESHOLD_RELAX_DELTA,
    YIELD_MIN_RATE,
)


def yield_guard(state: PipelineState) -> Literal["collect", "cluster"]:
    """После clean: если выживаемость ниже YIELD_MIN_RATE → re-collect (один раз)."""
    cleaned = state.get("cleaned", [])
    if not cleaned:
        return "cluster"
    kept = sum(1 for c in cleaned if c.get("keep"))
    rate = kept / len(cleaned) if cleaned else 0
    retries = state.get("collect_retries", 0)
    if rate < YIELD_MIN_RATE and retries < MAX_COLLECT_RETRIES:
        return "collect"
    return "cluster"


def yield_guard_apply(state: PipelineState) -> dict:
    """Side-effect для re-collect ветки: расширяет modifiers + инкрементит retry."""
    existing = set(state.get("modifiers", []))
    merged = sorted(existing.union(BROADER_MODIFIERS))
    decisions = list(state.get("decisions", []))
    decisions.append(
        f"supervisor: yield ниже {YIELD_MIN_RATE:.0%} → расширил modifiers до {len(merged)}"
    )
    return {
        "modifiers": merged,
        "collect_retries": state.get("collect_retries", 0) + 1,
        "decisions": decisions,
    }


def size_guard(state: PipelineState) -> Literal["cluster", "label"]:
    """После cluster: если кластеров мало → relax threshold (один раз)."""
    clusters = state.get("clusters", []) or []
    retries = state.get("cluster_retries", 0)
    if len(clusters) < MIN_CLUSTERS_AFTER_CLUSTER and retries < MAX_CLUSTER_RETRIES:
        return "cluster"
    return "label"


def size_guard_apply(state: PipelineState) -> dict:
    """Side-effect для re-cluster ветки: ослабляет distance_threshold."""
    threshold = state.get("distance_threshold", 0.20) + THRESHOLD_RELAX_DELTA
    decisions = list(state.get("decisions", []))
    decisions.append(
        f"supervisor: <{MIN_CLUSTERS_AFTER_CLUSTER} кластеров → threshold {threshold:.2f}"
    )
    return {
        "distance_threshold": threshold,
        "cluster_retries": state.get("cluster_retries", 0) + 1,
        "decisions": decisions,
    }


def build_graph():
    """Собирает и компилирует supervisor-граф. Возвращает compiled graph."""
    g = StateGraph(PipelineState)

    g.add_node("collect", collect_node)
    g.add_node("clean", clean_node)
    g.add_node("yield_decision", yield_guard_apply)  # side-effect для retry
    g.add_node("cluster", cluster_node)
    g.add_node("size_decision", size_guard_apply)
    g.add_node("label", label_node)
    g.add_node("merge", merge_node)
    g.add_node("gap", gap_node)
    g.add_node("output", output_node)

    g.set_entry_point("collect")
    g.add_edge("collect", "clean")

    # yield_guard: clean → (collect via yield_decision | cluster)
    g.add_conditional_edges(
        "clean",
        yield_guard,
        {"collect": "yield_decision", "cluster": "cluster"},
    )
    g.add_edge("yield_decision", "collect")

    # size_guard: cluster → (cluster via size_decision | label)
    g.add_conditional_edges(
        "cluster",
        size_guard,
        {"cluster": "size_decision", "label": "label"},
    )
    g.add_edge("size_decision", "cluster")

    g.add_edge("label", "merge")
    g.add_edge("merge", "gap")
    g.add_edge("gap", "output")
    g.add_edge("output", END)

    return g.compile()
