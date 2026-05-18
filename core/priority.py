"""Priority scoring per ТЗ formula.

В проде факторы берутся из Wordstat/Ahrefs/SERP. Здесь — прокси:
- search_volume   ≈ длина кластера × intent_weight (commercial > info)
- business_value  ≈ маппинг intent → ценность
- ranking_opportunity ≈ 1 - keyword_difficulty_estimate
- intent_match    ≈ 1.0 если intent matches page type из mapping
- trend_growth    ≈ 0.5 (нейтрально, без внешних трендов)
- content_gap     ≈ 1.0 если есть recommended page Создать, 0.5 Обновить
- keyword_difficulty ≈ proxy от длины запроса (короткие = сложнее)
- cannibalization_risk ≈ 0.0 (детект ниже отдельно)
"""
from __future__ import annotations
from dataclasses import dataclass

from .cluster import DEFAULT_FACETS, Cluster


INTENT_WEIGHTS = {
    "commercial": 1.0,
    "transactional": 0.95,
    "local": 0.85,
    "comparative": 0.65,
    "problem": 0.55,
    "informational": 0.40,
    "navigational": 0.10,
    "irrelevant": 0.0,
}

INTENT_BUSINESS_VALUE = {
    "commercial": 1.0,
    "transactional": 1.0,
    "local": 0.85,
    "comparative": 0.55,
    "problem": 0.50,
    "informational": 0.35,
    "navigational": 0.05,
    "irrelevant": 0.0,
}

INTENT_PAGE_TYPE = {
    "commercial": "Категория / листинг",
    "transactional": "Категория / карточка / лендинг",
    "informational": "Статья / гайд",
    "comparative": "Сравнительная статья",
    "navigational": "Не брать",
    "local": "Гео-страница",
    "problem": "FAQ / гайд + товарная подборка",
}

# Какие интенты по умолчанию идут в FAQ (если кластер похож на «вопрос-ответ»)
FAQ_INTENT_HINTS = {"problem", "comparative"}
# Маркеры вопроса в самом запросе
FAQ_QUERY_MARKERS = (
    "как ", "почему ", "какой ", "какая ", "какое ", "какие ",
    "что лучше", "что выбрать", "сколько ", "стоит ли",
    "?", "лучше или",
)


def _difficulty_proxy(label: str) -> float:
    """Короткие 1–2 слова → 'тяжёлый' SEO. Длинные long-tail — легче."""
    words = len(label.split())
    if words <= 1:
        return 0.85
    if words == 2:
        return 0.65
    if words == 3:
        return 0.45
    return 0.30


def score_cluster(
    cluster: Cluster,
    *,
    action: str,
    metrics: dict | None = None,
    cannibalization_risk: float | None = None,
) -> dict:
    """Apply Priority Score formula from ТЗ.

    metrics keys (все опциональны; если нет — фактор помечается как proxy):
      search_volume:        реальный объём (например, Wordstat shows)
      keyword_difficulty:   реальный KD из Ahrefs/Semrush (0..1)
      trend_growth:         Google Trends slope (0..1, 0.5 = плоско)
      ranking_opportunity:  1 - kd, или из SERP-анализа
    """
    metrics = metrics or {}
    intent = cluster.intent
    cluster_size = len(cluster.queries)
    iw = INTENT_WEIGHTS.get(intent, 0.0)

    sources: dict[str, str] = {}

    if "search_volume" in metrics:
        search_volume = float(metrics["search_volume"])
        sources["search_volume"] = "real"
    else:
        search_volume = min(1.0, cluster_size / 10.0) * (0.5 + 0.5 * iw)
        sources["search_volume"] = "proxy:cluster_size"

    business_value = INTENT_BUSINESS_VALUE.get(intent, 0.0)
    sources["business_value"] = "config:intent_map"

    if "keyword_difficulty" in metrics:
        kw_difficulty = float(metrics["keyword_difficulty"])
        sources["keyword_difficulty"] = "real"
    else:
        kw_difficulty = _difficulty_proxy(cluster.label or cluster.queries[0])
        sources["keyword_difficulty"] = "proxy:label_length"

    if "ranking_opportunity" in metrics:
        ranking_opp = float(metrics["ranking_opportunity"])
        sources["ranking_opportunity"] = "real"
    else:
        ranking_opp = max(0.0, 1.0 - kw_difficulty)
        sources["ranking_opportunity"] = "derived:1-kd"

    intent_match = 1.0 if iw >= 0.5 else 0.4
    sources["intent_match"] = "config:intent_map"

    if "trend_growth" in metrics:
        trend_growth = float(metrics["trend_growth"])
        sources["trend_growth"] = "real"
    else:
        trend_growth = 0.5
        sources["trend_growth"] = "unknown:default_0.5"

    if action == "Обновить":
        content_gap = 0.6
    elif action == "Не брать":
        content_gap = 0.2
    else:  # Создать / Создать статью / Создать FAQ
        content_gap = 1.0
    sources["content_gap"] = "derived:action"

    if cannibalization_risk is None:
        cannibalization_risk = 0.0
        sources["cannibalization_risk"] = "unknown:default_0"
    else:
        cannibalization_risk = float(cannibalization_risk)
        sources["cannibalization_risk"] = "computed:embedding_overlap"

    score = (
        0.25 * search_volume
        + 0.20 * business_value
        + 0.20 * ranking_opp
        + 0.15 * intent_match
        + 0.10 * trend_growth
        + 0.10 * content_gap
        - 0.20 * kw_difficulty
        - 0.15 * cannibalization_risk
    )

    # confidence = доля факторов с реальными данными (а не proxy/unknown)
    real_count = sum(1 for v in sources.values() if v.startswith("real") or v.startswith("computed"))
    derived_count = sum(1 for v in sources.values() if v.startswith("derived") or v.startswith("config"))
    total = len(sources)
    confidence = round((real_count + 0.5 * derived_count) / total, 2) if total else 0.0
    score_mode = "production" if confidence >= 0.6 else ("demo" if confidence < 0.35 else "mixed")

    return {
        "score": round(max(0.0, score), 3),
        "confidence": confidence,
        "score_mode": score_mode,
        "factors": {
            "search_volume": round(search_volume, 2),
            "business_value": round(business_value, 2),
            "ranking_opportunity": round(ranking_opp, 2),
            "intent_match": round(intent_match, 2),
            "trend_growth": round(trend_growth, 2),
            "content_gap": round(content_gap, 2),
            "keyword_difficulty": round(kw_difficulty, 2),
            "cannibalization_risk": round(cannibalization_risk, 2),
        },
        "sources": sources,
    }


def _is_faq_cluster(cluster: Cluster) -> bool:
    """Кластер похож на FAQ, если интент problem/comparative ИЛИ запросы содержат вопросительные маркеры."""
    if cluster.intent in FAQ_INTENT_HINTS:
        return True
    markers_hit = sum(
        1 for q in cluster.queries
        if any(m in q.lower() for m in FAQ_QUERY_MARKERS)
    )
    return markers_hit >= max(1, len(cluster.queries) // 3)


def _page_type(url: str) -> str:
    """Classify existing page by URL pattern → page-type для intent-guarded matching."""
    u = url.lower()
    if "/blog/" in u or "/article" in u or "/post" in u or "/news/" in u:
        return "blog"
    if "/faq" in u or "/help" in u or "/q-and-a" in u:
        return "faq"
    if "/catalog/" in u or "/category/" in u or "/products/" in u or "/c/" in u or u.startswith("/"):
        return "catalog"
    return "other"


def _slug_to_ru(slug_or_url: str) -> str:
    """Translit `/catalog/uglovye-divany/` → «угловые диваны» для facet-конфликта.

    Грубая обратная транслитерация — для проверки взаимоисключающих фасетов
    («угловой» vs «прямой») этого достаточно; точное соответствие не нужно.
    """
    last = slug_or_url.strip("/").split("/")[-1]
    text = last.lower().replace("-", " ")
    lat_to_ru = {
        "sh": "ш", "ch": "ч", "yu": "ю", "ya": "я", "zh": "ж", "yo": "ё",
        "a": "а", "b": "б", "v": "в", "g": "г", "d": "д", "e": "е", "z": "з",
        "i": "и", "y": "ы", "k": "к", "l": "л", "m": "м", "n": "н", "o": "о",
        "p": "п", "r": "р", "s": "с", "t": "т", "u": "у", "f": "ф", "h": "х",
        "c": "ц",
    }
    for src, dst in sorted(lat_to_ru.items(), key=lambda kv: -len(kv[0])):
        text = text.replace(src, dst)
    return text


def _detect_facets(text: str) -> set[str]:
    """Какие facet-теги из DEFAULT_FACETS присутствуют в тексте."""
    text_l = text.lower()
    return {
        name for name, triggers in DEFAULT_FACETS.items()
        if any(t in text_l for t in triggers)
    }


def _facets_conflict(cluster_text: str, page_url: str) -> bool:
    """True если cluster и page несут взаимоисключающие фасеты.

    Закрывает регрессию «Угловые диваны в Москве» → `/catalog/pryamye-divany/`:
    embedding sim ловит «диваны», но «угловой» и «прямой» — несовместимые
    facet-теги (даже при cosine ≥0.90 такой match вреден).
    """
    cf = _detect_facets(cluster_text)
    pf = _detect_facets(_slug_to_ru(page_url))
    return bool(cf and pf and not (cf & pf))


_INTENT_TO_ALLOWED_PAGE_TYPES = {
    "commercial":    {"catalog"},
    "transactional": {"catalog"},
    "local":         {"catalog"},
    "comparative":   {"blog", "faq"},
    "informational": {"blog", "faq"},
    "problem":       {"faq", "blog"},
    "navigational":  set(),
    "irrelevant":    set(),
}


def decide_action(
    cluster: Cluster,
    existing_pages: list[str],
    *,
    page_embeddings: "np.ndarray | None" = None,
    cluster_embedding: "np.ndarray | None" = None,
    similarity_threshold: float = 0.85,
) -> tuple[str, str | None, float]:
    """Return (action, matched_existing_url_or_none, page_similarity).

    Matching cascade — INTENT-AWARE + FACET-GUARDED:
      Сначала фильтруем `existing_pages` по допустимым page_type для intent кластера
      (commercial/transactional → только /catalog/; informational/comparative → только blog/faq).
      Внутри допустимого подмножества:
        1) exact slug-substring match (+ facet-guard)
        2) embedding similarity ≥0.85 (если есть embeddings) + facet-guard
      Facet-guard важнее threshold: для русского multilingual MiniLM cosine
      между «угловые диваны» и «прямые диваны» ≈0.82, а между «угловые в Москве»
      и «угловые» тоже ≈0.82 — embedding не отличает антоним-фасеты. Защита —
      `DEFAULT_FACETS`: если facet-tag кластера ({"угловой"}) не пересекается
      с facet-tag страницы ({"прямой"}) — match блокируется. Закрывает
      регрессию «Угловые диваны в Москве» → `/catalog/pryamye-divany/`.
    """
    slug = getattr(cluster, "slug", "") or ""
    intent = cluster.intent

    if intent in ("navigational", "irrelevant"):
        return "Не брать", None, 0.0

    allowed_types = _INTENT_TO_ALLOWED_PAGE_TYPES.get(intent, {"catalog"})
    eligible: list[tuple[int, str]] = [
        (i, url) for i, url in enumerate(existing_pages)
        if _page_type(url) in allowed_types
    ]

    cluster_text = (cluster.label or "") + " " + " ".join(cluster.queries[:10])

    matched: str | None = None
    best_sim: float = 0.0

    # 1) slug-substring внутри eligible (с facet-guard — slug может совпасть, но фасет
    # не должен противоречить — для надёжности проверяем и здесь)
    if slug:
        for _, url in eligible:
            if slug in url.lower() and not _facets_conflict(cluster_text, url):
                matched = url
                break

    # 2) embedding sim внутри eligible + facet-guard
    if matched is None and page_embeddings is not None and cluster_embedding is not None and eligible:
        import numpy as np
        idxs = [i for i, _ in eligible]
        sub_emb = page_embeddings[idxs]
        sims = sub_emb @ cluster_embedding
        # сортируем по убыванию sim — берём первый кандидат, прошедший facet-guard
        order = np.argsort(-sims)
        for local_idx in order:
            sim_val = float(sims[local_idx])
            if sim_val < similarity_threshold:
                break  # дальше будет только хуже
            candidate = existing_pages[idxs[int(local_idx)]]
            if not _facets_conflict(cluster_text, candidate):
                matched = candidate
                best_sim = sim_val
                break
            best_sim = max(best_sim, sim_val)  # храним для отчёта, но не матчим

    if matched:
        return "Обновить", matched, best_sim

    if _is_faq_cluster(cluster):
        return "Создать FAQ", None, best_sim
    if intent == "informational":
        return "Создать статью", None, best_sim
    if intent == "comparative":
        return "Создать статью", None, best_sim
    return "Создать", None, best_sim
