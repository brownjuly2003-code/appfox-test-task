"""Post-merge дублирующихся кластеров."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.cluster import Cluster, merge_duplicates


def test_merge_by_identical_label():
    c1 = Cluster(cluster_id=0, label="Диваны для сна", intent="commercial",
                 queries=["диван для сна купить", "диван для сна цена"])
    c2 = Cluster(cluster_id=1, label="Диваны для сна", intent="commercial",
                 queries=["диван для сна недорого"])
    merged = merge_duplicates([c1, c2], centroid_threshold=2.0)  # отключить centroid pass
    assert len(merged) == 1
    assert set(merged[0].queries) == {"диван для сна купить", "диван для сна цена", "диван для сна недорого"}


def test_dedupe_queries_in_merge():
    c1 = Cluster(cluster_id=0, label="Диваны для сна", intent="commercial",
                 queries=["диван для сна"])
    c2 = Cluster(cluster_id=1, label="Диваны для сна", intent="commercial",
                 queries=["диван для сна", "диван для сна купить"])
    merged = merge_duplicates([c1, c2], centroid_threshold=2.0)
    assert len(merged) == 1
    assert len(merged[0].queries) == 2  # dedup


def test_keep_distinct_labels():
    c1 = Cluster(cluster_id=0, label="Угловые диваны", intent="commercial",
                 queries=["угловой диван"])
    c2 = Cluster(cluster_id=1, label="Кухонные диваны", intent="commercial",
                 queries=["кухонный диван"])
    merged = merge_duplicates([c1, c2], centroid_threshold=2.0)
    assert len(merged) == 2


def test_dominant_intent_after_merge():
    c1 = Cluster(cluster_id=0, label="Диваны для сна", intent="commercial",
                 queries=["диван для сна", "диван для сна купить"])
    c2 = Cluster(cluster_id=1, label="Диваны для сна", intent="transactional",
                 queries=["диван для сна с доставкой"])
    merged = merge_duplicates([c1, c2], centroid_threshold=2.0)
    assert len(merged) == 1
    assert merged[0].intent == "commercial"  # majority by query count
