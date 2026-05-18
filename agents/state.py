"""State схема для LangGraph supervisor pipeline.

Сохраняет промежуточные артефакты и счётчики adaptive-ретраев, чтобы guards
могли принять однократное решение пересобрать/перекластеризовать.
"""
from __future__ import annotations
from typing import Any, TypedDict


class PipelineState(TypedDict, total=False):
    # Input
    business_context: dict[str, Any]
    seeds: list[str]
    modifiers: list[str]
    competitors: list[str]
    existing_pages: list[dict[str, Any]]

    # Knobs (могут быть переписаны guards)
    distance_threshold: float
    apply_split: bool
    apply_merge: bool
    max_queries: int

    # Adaptive retry counters
    collect_retries: int  # сколько раз yield_guard уже расширял modifiers
    cluster_retries: int  # сколько раз size_guard уменьшал threshold (lower → more clusters)

    # Intermediate artifacts
    raw_queries: list[str]
    comp_pages: list[str]  # competitor categories, кэшируется в collect → используется в gap (без повторного HTTP)
    cleaned: list[dict[str, Any]]  # CleanedQuery.to_dict()
    clusters: list[Any]  # list[Cluster]
    metrics_by_query: dict[str, dict[str, float]]
    metrics_by_cluster: dict[int, dict[str, float]]
    prev_diff: dict[int, dict[str, Any]]
    comp_diff: dict[int, dict[str, Any]]
    removed_clusters: list[dict[str, Any]]  # prev-кластеры без match в current → drop/архив
    rows: list[dict[str, Any]]
    state_path: str

    # Output paths
    out_dir: str
    state_file: str
    csv_path: str
    md_path: str
    queries_path: str
    raw_path: str

    # Decision log — supervisor пишет сюда каждый раз когда срабатывает guard
    decisions: list[str]


YIELD_MIN_RATE = 0.30           # <30% kept → re-collect once
MIN_CLUSTERS_AFTER_CLUSTER = 3  # <3 clusters → relax threshold once
MAX_COLLECT_RETRIES = 1
MAX_CLUSTER_RETRIES = 1
BROADER_MODIFIERS = [
    "купить", "цена", "недорого", "москва", "доставка",
    "в москве", "интернет магазин", "акция",
]
THRESHOLD_RELAX_DELTA = 0.10    # threshold уменьшается на эту дельту (0.20 → 0.10); lower → more clusters
