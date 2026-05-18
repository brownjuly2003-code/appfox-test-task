"""Cluster queries by semantic similarity, then label each cluster via LLM."""
from __future__ import annotations
import json
import os
import warnings
from dataclasses import dataclass, field
from functools import lru_cache

# silence sentence-transformers / transformers progress + warnings
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TQDM_DISABLE", "1")
warnings.filterwarnings("ignore")

import numpy as np

from .llm import chat, parse_json


@dataclass
class Cluster:
    cluster_id: int
    label: str
    intent: str  # dominant intent
    queries: list[str] = field(default_factory=list)


@lru_cache(maxsize=1)
def _get_embedder():
    """Multilingual model, ~120 MB, decent quality on Russian."""
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")


def embed(texts: list[str]) -> np.ndarray:
    if not texts:
        return np.zeros((0, 384), dtype=np.float32)
    model = _get_embedder()
    return model.encode(texts, normalize_embeddings=True, show_progress_bar=False)


def _split_by_facets(
    cluster: Cluster,
    facets: dict[str, list[str]],
) -> list[Cluster]:
    """Разбить кластер на под-кластеры по фасетам (product_type, geo, modifier).

    facets: dict facet_name → list of trigger substrings. Запросы группируются по
    мульти-ключу (matched_facets). Запросы без матчей попадают в кластер 'general'.
    """
    groups: dict[tuple, list[str]] = {}
    for q in cluster.queries:
        ql = q.lower()
        key: tuple = tuple(sorted(
            facet for facet, triggers in facets.items()
            if any(t in ql for t in triggers)
        ))
        if not key:
            key = ("__general__",)
        groups.setdefault(key, []).append(q)

    # If split produced only one group → no benefit
    if len(groups) <= 1:
        return [cluster]

    new_clusters: list[Cluster] = []
    for key, qs in groups.items():
        label_hint = " + ".join(k for k in key if k != "__general__") or cluster.label
        nc = Cluster(
            cluster_id=cluster.cluster_id,
            label=f"{cluster.label} ({label_hint})" if label_hint and label_hint != cluster.label else cluster.label,
            intent=cluster.intent,
            queries=qs,
        )
        new_clusters.append(nc)
    return new_clusters


# Дефолтные фасеты для мебельного домена. Для других доменов передавайте свои в cluster_queries(facets=...).
DEFAULT_FACETS = {
    "угловой": ["угловой", "углов"],
    "прямой": ["прямой", "прямые"],
    "кухонный": ["кухонн", "для кухни", "на кухню"],
    "трансформер": ["трансформер"],
    "диван-кровать": ["диван-кров", "диван кров"],
    "для сна": ["для сна", "спальное место", "ежедневн"],
    "ортопедический": ["ортопед"],
    "доставка": ["доставк"],
    "москва": ["москв"],
    "акция": ["акция", "распродаж", "скидк"],
}


def cluster_queries(
    cleaned: list[dict],
    *,
    distance_threshold: float = 0.55,
    facets: dict[str, list[str]] | None = None,
    apply_split: bool = True,
) -> list[Cluster]:
    """Agglomerative clustering on cosine distance of multilingual embeddings.

    cleaned: list of {"query": str, "intent": str, "keep": bool, ...} (already filtered to keep=True)
    distance_threshold lower → more, smaller clusters.
    """
    from sklearn.cluster import AgglomerativeClustering

    items = [c for c in cleaned if c.get("keep")]
    if not items:
        return []

    queries = [c["query"] for c in items]
    intents = [c["intent"] for c in items]

    if len(queries) == 1:
        return [Cluster(cluster_id=0, label=queries[0], intent=intents[0], queries=queries)]

    embeddings = embed(queries)
    # normalized embeddings → euclidean distance ≈ √2·(1 − cosine), so threshold ~0.55 ≈ cos sim 0.85
    model = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=distance_threshold,
        metric="cosine",
        linkage="average",
    )
    labels = model.fit_predict(embeddings)

    by_label: dict[int, list[int]] = {}
    for i, lab in enumerate(labels):
        by_label.setdefault(int(lab), []).append(i)

    clusters: list[Cluster] = []
    for cid, idxs in sorted(by_label.items()):
        qs = [queries[i] for i in idxs]
        # dominant intent: mode
        ints = [intents[i] for i in idxs]
        dominant = max(set(ints), key=ints.count)
        clusters.append(Cluster(cluster_id=cid, label="", intent=dominant, queries=qs))

    # Facet-based splitting: 1 cluster может содержать угловые + кухонные + Москву — это разные страницы
    if apply_split:
        facets_to_use = facets or DEFAULT_FACETS
        split: list[Cluster] = []
        for c in clusters:
            split.extend(_split_by_facets(c, facets_to_use))
        clusters = split

    # sort: larger clusters first
    clusters.sort(key=lambda c: -len(c.queries))
    for new_id, c in enumerate(clusters):
        c.cluster_id = new_id

    return clusters


def merge_duplicates(clusters: list[Cluster], *, label_match: bool = True, centroid_threshold: float = 0.93) -> list[Cluster]:
    """Post-merge кластеров с одинаковым label (после labelling) или очень близкими центроидами.

    Запускать ПОСЛЕ label_clusters: одна и та же тема может попасть в 2-3 кластера
    (если facet-split разнёс по разным веткам, но смысл один).
    """
    if not clusters:
        return clusters

    # Group by exact label (case-insensitive)
    groups: dict[str, list[Cluster]] = {}
    leftover: list[Cluster] = []
    for c in clusters:
        if label_match and c.label:
            key = c.label.strip().lower()
            groups.setdefault(key, []).append(c)
        else:
            leftover.append(c)

    merged_by_label: list[Cluster] = []
    for key, group in groups.items():
        if len(group) == 1:
            merged_by_label.append(group[0])
            continue
        # merge: union queries, dominant intent
        all_q: list[str] = []
        for g in group:
            all_q.extend(g.queries)
        # dedupe preserving order
        seen = set()
        dedup_q = [q for q in all_q if not (q in seen or seen.add(q))]
        # weight intent by query count, не по числу кластеров (см. test_dominant_intent_after_merge)
        intents: list[str] = []
        for g in group:
            intents.extend([g.intent] * len(g.queries))
        dominant = max(set(intents), key=intents.count)
        first = group[0]
        merged = Cluster(
            cluster_id=first.cluster_id,
            label=first.label,
            intent=dominant,
            queries=dedup_q,
        )
        if hasattr(first, "slug"):
            merged.slug = getattr(first, "slug", "")
        merged_by_label.append(merged)

    pool = merged_by_label + leftover

    # Second pass: merge by centroid cosine if >= threshold
    if centroid_threshold < 1.0 and len(pool) > 1:
        texts = [c.label or " ".join(c.queries[:3]) for c in pool]
        embs = embed(texts)
        used = set()
        result: list[Cluster] = []
        for i, ci in enumerate(pool):
            if i in used:
                continue
            sim = embs[i] @ embs.T
            sim[i] = -1.0
            mates = [j for j, s in enumerate(sim) if s >= centroid_threshold and j not in used]
            if not mates:
                result.append(ci)
                used.add(i)
                continue
            # merge ci + mates
            all_q: list[str] = list(ci.queries)
            intents: list[str] = [ci.intent] * len(ci.queries)
            for j in mates:
                cj = pool[j]
                all_q.extend(cj.queries)
                intents.extend([cj.intent] * len(cj.queries))
            seen_q = set()
            dedup_q = [q for q in all_q if not (q in seen_q or seen_q.add(q))]
            dominant = max(set(intents), key=intents.count) if intents else ci.intent
            merged = Cluster(
                cluster_id=ci.cluster_id,
                label=ci.label,
                intent=dominant,
                queries=dedup_q,
            )
            if hasattr(ci, "slug"):
                merged.slug = getattr(ci, "slug", "")
            result.append(merged)
            used.add(i)
            used.update(mates)
        pool = result

    pool.sort(key=lambda c: -len(c.queries))
    for new_id, c in enumerate(pool):
        c.cluster_id = new_id
    return pool


_LABEL_SYSTEM = """Ты SEO-редактор. По списку похожих запросов в кластере определи:
1) короткое название кластера (2–5 слов, в именительном падеже, по-русски)
2) канонический URL-slug на латинице (kebab-case, без префикса /)

Отвечай СТРОГО JSON-объектом без markdown:
{"label":"Угловые диваны", "slug":"uglovye-divany"}"""


def label_clusters(clusters: list[Cluster], business_context: dict, *, max_queries_in_prompt: int = 12) -> None:
    """Mutates clusters in-place: adds .label and .slug."""
    for c in clusters:
        sample = c.queries[:max_queries_in_prompt]
        user = (
            f"Бизнес: {business_context.get('vertical', '')}.\n"
            f"Доминирующий интент: {c.intent}.\n"
            f"Запросы:\n" + "\n".join(f"- {q}" for q in sample)
        )
        try:
            raw = chat(_LABEL_SYSTEM, user, temperature=0.2, max_tokens=200)
            parsed = parse_json(raw)
            c.label = parsed.get("label", c.queries[0]) or c.queries[0]
            c.slug = parsed.get("slug") or _fallback_slug(c.label)
        except Exception as e:
            print(f"[label:err] cluster {c.cluster_id}: {e}")
            c.label = c.queries[0]
            c.slug = _fallback_slug(c.label)


def _fallback_slug(text: str) -> str:
    import re
    ru_to_lat = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "zh", "з": "z", "и": "i", "й": "i", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    }
    s = "".join(ru_to_lat.get(ch, ch) for ch in text.lower())
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")[:60] or "cluster"
