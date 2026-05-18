"""Smoke + adaptive-retry тесты для LangGraph supervisor.

Без реальных LLM/embedding — все «дорогие» nodes (collect, clean, cluster, label, gap, output)
монки-патчатся фейками, чтобы тестировать ИМЕННО логику supervisor (guards + edges).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.graph import build_graph, size_guard, yield_guard
from agents.state import (
    MIN_CLUSTERS_AFTER_CLUSTER,
    PipelineState,
    YIELD_MIN_RATE,
)


def test_graph_compiles():
    g = build_graph()
    assert g is not None
    # У compiled graph должен быть метод invoke
    assert callable(g.invoke)


def test_yield_guard_low_yield_triggers_recollect():
    # 1 keep из 10 = 10%, ниже 30% → re-collect
    cleaned = [{"keep": i == 0} for i in range(10)]
    state: PipelineState = {"cleaned": cleaned, "collect_retries": 0}
    assert yield_guard(state) == "collect"


def test_yield_guard_acceptable_yield_proceeds():
    # 5 из 10 = 50%, выше 30% → cluster
    cleaned = [{"keep": i < 5} for i in range(10)]
    state: PipelineState = {"cleaned": cleaned, "collect_retries": 0}
    assert yield_guard(state) == "cluster"


def test_yield_guard_respects_max_retries():
    # Низкий yield, но retry уже исчерпан → proceed anyway
    cleaned = [{"keep": False} for _ in range(10)]
    state: PipelineState = {"cleaned": cleaned, "collect_retries": 1}
    assert yield_guard(state) == "cluster"


def test_size_guard_too_few_clusters_triggers_recluster():
    # 1 кластер < MIN_CLUSTERS_AFTER_CLUSTER (3)
    state: PipelineState = {
        "clusters": [object()],
        "cluster_retries": 0,
    }
    assert size_guard(state) == "cluster"


def test_size_guard_enough_clusters_proceeds():
    state: PipelineState = {
        "clusters": [object()] * MIN_CLUSTERS_AFTER_CLUSTER,
        "cluster_retries": 0,
    }
    assert size_guard(state) == "label"


def test_size_guard_respects_max_retries():
    state: PipelineState = {
        "clusters": [object()],
        "cluster_retries": 1,  # retry уже потрачен
    }
    assert size_guard(state) == "label"


def _make_cluster(cluster_id, label, intent, queries):
    """Helper to make Cluster instances without importing inside test."""
    from core.cluster import Cluster
    return Cluster(cluster_id=cluster_id, label=label, intent=intent, queries=queries)


def test_end_to_end_with_mocked_nodes(monkeypatch, tmp_path):
    """Полный прогон через граф с замоканными внешними вызовами — supervisor должен
    пройти все узлы без падений и собрать decision log."""
    from agents import nodes
    from core import gap as gap_mod

    # 1. Mock collect (15 raw queries — достаточно чтобы пройти clean yield_guard)
    monkeypatch.setattr(
        nodes.collect_mod, "collect_all",
        lambda **kw: ["диван угловой купить", "диван прямой цена", "диван кухонный москва",
                      "диван трансформер", "ортопедический диван",
                      "диван для сна", "диван доставка",
                      "диван-кровать", "диван акция", "диван недорого",
                      "купить угловой диван", "диван москва доставка", "диван для гостиной",
                      "диван для офиса", "диван бесплатно"]
    )
    monkeypatch.setattr(
        nodes.collect_mod, "fetch_competitor_categories",
        lambda url: []
    )

    # 2. Mock clean: всё keep (yield_guard сразу пропустит)
    class FakeCleaned:
        def __init__(self, q):
            self.query = q
            self.intent = "commercial"
            self.keep = True
            self.reason = ""
        def to_dict(self):
            return {"query": self.query, "intent": self.intent, "keep": True, "reason": ""}
    monkeypatch.setattr(
        nodes.clean_mod, "clean_batch",
        lambda raw, biz, batch_size=25: [FakeCleaned(q) for q in raw]
    )

    # 3. Mock cluster.cluster_queries чтобы вернуть 5 «настоящих» кластеров — size_guard пропускает
    def fake_cluster(cleaned, **kw):
        return [
            _make_cluster(i, "", "commercial", [c["query"] for c in cleaned[i*3:(i+1)*3]])
            for i in range(5)
        ]
    monkeypatch.setattr(nodes.cluster_mod, "cluster_queries", fake_cluster)

    # 4. Mock label
    def fake_label(clusters, biz, **kw):
        for c in clusters:
            c.label = f"label-{c.cluster_id}"
            c.slug = f"slug-{c.cluster_id}"
    monkeypatch.setattr(nodes.cluster_mod, "label_clusters", fake_label)

    # 5. merge — реальный (он чистый, без LLM); embed во второй pass пускаем мимо
    monkeypatch.setattr(
        nodes.cluster_mod, "merge_duplicates",
        lambda clusters: clusters
    )

    # 6. gap — реальный load_state на свежую папку отдаёт пустое
    monkeypatch.setattr(gap_mod, "diff_with_competitors", lambda c, p: {})

    out = tmp_path / "out"
    state_file = tmp_path / "state.json"

    initial = {
        "business_context": {"vertical": "мебель"},
        "seeds": ["диван"],
        "modifiers": [],
        "competitors": [],
        "existing_pages": [],
        "distance_threshold": 0.20,
        "apply_split": True,
        "apply_merge": True,
        "max_queries": 200,
        "out_dir": str(out),
        "state_file": str(state_file),
        "metrics_by_query": {},
        "collect_retries": 0,
        "cluster_retries": 0,
        "decisions": [],
    }

    graph = build_graph()
    final = graph.invoke(initial)

    # Supervisor должен пройти все стадии
    log = final["decisions"]
    assert any(d.startswith("collect:") for d in log)
    assert any(d.startswith("clean:") for d in log)
    assert any(d.startswith("cluster:") for d in log)
    assert any(d.startswith("output:") for d in log)
    # Артефакты должны быть на диске
    assert Path(final["csv_path"]).exists()
    assert Path(final["md_path"]).exists()


def test_end_to_end_yield_guard_fires(monkeypatch, tmp_path):
    """Низкий yield на первом проходе → supervisor должен расширить modifiers и пере-collect."""
    from agents import nodes
    from core import gap as gap_mod

    # collect: первый раз 10 запросов, второй раз (после расширения modifiers) 30
    collect_calls = {"n": 0}
    def fake_collect(**kw):
        collect_calls["n"] += 1
        n_modifiers = len(kw.get("modifiers", []))
        # Тривиальный сигнал: если modifiers расширены — больше данных
        if n_modifiers > 3:
            return [f"q{i}" for i in range(30)]
        return [f"q{i}" for i in range(10)]
    monkeypatch.setattr(nodes.collect_mod, "collect_all", fake_collect)
    monkeypatch.setattr(nodes.collect_mod, "fetch_competitor_categories", lambda url: [])

    # clean: первый раз 90% drop (yield=10%), второй — 80% keep
    clean_calls = {"n": 0}
    class FakeCleaned:
        def __init__(self, q, keep):
            self.query = q
            self.intent = "commercial"
            self.keep = keep
            self.reason = ""
        def to_dict(self):
            return {"query": self.query, "intent": self.intent, "keep": self.keep, "reason": ""}
    def fake_clean(raw, biz, **kw):
        clean_calls["n"] += 1
        if clean_calls["n"] == 1:
            return [FakeCleaned(q, keep=(i == 0)) for i, q in enumerate(raw)]
        return [FakeCleaned(q, keep=True) for q in raw]
    monkeypatch.setattr(nodes.clean_mod, "clean_batch", fake_clean)

    def fake_cluster(cleaned, **kw):
        return [
            _make_cluster(i, "", "commercial", [c["query"] for c in cleaned[i*5:(i+1)*5]])
            for i in range(5)
        ]
    monkeypatch.setattr(nodes.cluster_mod, "cluster_queries", fake_cluster)
    monkeypatch.setattr(
        nodes.cluster_mod, "label_clusters",
        lambda cs, biz, **kw: [setattr(c, "label", f"L{c.cluster_id}") or setattr(c, "slug", f"s{c.cluster_id}") for c in cs]
    )
    monkeypatch.setattr(nodes.cluster_mod, "merge_duplicates", lambda cs: cs)
    monkeypatch.setattr(gap_mod, "diff_with_competitors", lambda c, p: {})

    initial = {
        "business_context": {"vertical": "мебель"},
        "seeds": ["диван"],
        "modifiers": [],
        "competitors": [],
        "existing_pages": [],
        "distance_threshold": 0.20,
        "apply_split": True,
        "apply_merge": True,
        "max_queries": 200,
        "out_dir": str(tmp_path / "out"),
        "state_file": str(tmp_path / "state.json"),
        "metrics_by_query": {},
        "collect_retries": 0,
        "cluster_retries": 0,
        "decisions": [],
    }

    graph = build_graph()
    final = graph.invoke(initial)

    # collect должен быть вызван дважды (адаптивный retry)
    assert collect_calls["n"] == 2, f"expected 2 collect calls, got {collect_calls['n']}"
    assert clean_calls["n"] == 2
    # В decision-логе должен фигурировать факт расширения modifiers
    log = final["decisions"]
    assert any("расширил modifiers" in d for d in log), log
    assert final["collect_retries"] == 1
