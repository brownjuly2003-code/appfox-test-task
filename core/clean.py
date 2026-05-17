"""Clean raw queries: dedup, intent classification, business-relevance filtering.

Two stages:
1) Rule-based filter (детерминированный, до LLM): brands, marketplaces, geo, freebies
2) LLM-based classification (intent + бизнес-релевантность)
"""
from __future__ import annotations
import json
import re
from dataclasses import dataclass, field

from .llm import chat, parse_json


INTENT_VALUES = (
    "commercial",      # купить/заказать продукт
    "transactional",   # доставка/оформить заказ
    "informational",   # как выбрать/гайд
    "comparative",     # X или Y что лучше
    "navigational",    # бренд.ру
    "local",           # в москве/спб
    "problem",         # проблема/боль клиента
    "irrelevant",      # отбраковка
)

# Маркетплейсы — обычно работать с ними нельзя или нерелевантно
DEFAULT_MARKETPLACES = (
    "wildberries", "ozon", "озон", "яндекс маркет", "yandex market",
    "kufar", "куфар", "olx", "авито", "avito",
)

# Слова-триггеры «бесплатно/самовывоз/б/у» — не релевантны коммерческому магазину новинок
FREEBIE_TRIGGERS = (
    "бесплатно", "даром", "отдам",
)


@dataclass
class CleanedQuery:
    query: str
    intent: str
    keep: bool
    reason: str = ""

    def to_dict(self) -> dict:
        return {"query": self.query, "intent": self.intent, "keep": self.keep, "reason": self.reason}


def _norm(q: str) -> str:
    return re.sub(r"\s+", " ", q.strip().lower())


def dedupe_exact(queries: list[str]) -> list[str]:
    seen = set()
    out: list[str] = []
    for q in queries:
        k = _norm(q)
        if k and k not in seen:
            seen.add(k)
            out.append(q.strip().lower())
    return out


_GEO_HINT_TRIGGERS = (
    "в москве", "в санкт", "в спб", "в петербург", "в киеве", "в минске",
    "в екатеринбурге", "в новосибирске", "в челябинске", "в одессе",
    "в харькове", "в днепре", "в алматы", "в ташкенте", "в бишкеке",
    " москва", " спб", " петербург", " екатеринбург", " новосибирск",
    " челябинск", " киев", " одесса", " харьков", " днепр", " алматы",
    " ташкент", " бишкек", " минск", " россия", " рф", " мск", " мо",
)


def _looks_geo(q: str) -> bool:
    return any(t in f" {q}" for t in _GEO_HINT_TRIGGERS)


def rule_filter(queries: list[str], business_context: dict) -> tuple[list[str], list[CleanedQuery]]:
    """Rule-based drop. Returns (kept_queries, dropped_with_reason).

    business_context keys honored:
      prohibited_brands: list[str]  — бренды конкурентов
      blocked_regions:   list[str]  — города/страны вне зоны доставки
      marketplaces:      list[str]  — переопределяет DEFAULT_MARKETPLACES
      freebie_triggers:  list[str]  — переопределяет FREEBIE_TRIGGERS
      region_substrings: list[str]  — allow-list разрешённых регионов: если запрос явно
                                       привязан к гео, но ни одно из этих слов не встречается,
                                       он дропается ("геопривязка вне зоны")
    """
    prohibited = [b.lower() for b in business_context.get("prohibited_brands", [])]
    blocked_regions = [r.lower() for r in business_context.get("blocked_regions", [])]
    marketplaces = [m.lower() for m in business_context.get("marketplaces", DEFAULT_MARKETPLACES)]
    freebies = [f.lower() for f in business_context.get("freebie_triggers", FREEBIE_TRIGGERS)]
    allowed_regions = [r.lower() for r in business_context.get("region_substrings", [])]

    def _has_word(q: str, term: str) -> bool:
        term = term.strip().lower()
        if " " in term:
            return term in q
        return re.search(rf"(^|\W){re.escape(term)}($|\W)", q) is not None

    kept: list[str] = []
    dropped: list[CleanedQuery] = []
    for q in queries:
        q_norm = q.lower()

        matched_brand = next((b for b in prohibited if _has_word(q_norm, b)), None)
        if matched_brand:
            dropped.append(CleanedQuery(q_norm, "irrelevant", False, f"prohibited brand: {matched_brand}"))
            continue

        matched_mp = next((m for m in marketplaces if _has_word(q_norm, m)), None)
        if matched_mp:
            dropped.append(CleanedQuery(q_norm, "irrelevant", False, f"marketplace: {matched_mp}"))
            continue

        matched_region = next((r for r in blocked_regions if _has_word(q_norm, r)), None)
        if matched_region:
            dropped.append(CleanedQuery(q_norm, "irrelevant", False, f"blocked region: {matched_region}"))
            continue

        matched_freebie = next((f for f in freebies if _has_word(q_norm, f)), None)
        if matched_freebie:
            dropped.append(CleanedQuery(q_norm, "irrelevant", False, f"freebie trigger: {matched_freebie}"))
            continue

        # allow-list гео: если запрос явно "геопривязан" — должен матчиться на разрешённый регион.
        # Для аллоу-листа используем substring (а не word-boundary), чтобы поймать падежные формы
        # ("в москве" → есть "москв" из "москва"). Это безопасно: false-positive здесь оставляет
        # потенциально релевантный запрос, false-negative — теряет настоящий московский трафик.
        if allowed_regions and _looks_geo(q_norm):
            stems = {r.rstrip("аяыеоиую") for r in allowed_regions}
            if not any(stem and stem in q_norm for stem in stems):
                dropped.append(CleanedQuery(q_norm, "irrelevant", False, "geo outside allowed regions"))
                continue

        kept.append(q_norm)

    return kept, dropped


_SYSTEM = """Ты SEO-аналитик. По каждому поисковому запросу:
1) определи интент: commercial | transactional | informational | comparative | navigational | local | problem | irrelevant
2) реши, оставить ли его в коммерческом семантическом ядре для указанного бизнеса (keep=true/false)

Удаляй (keep=false):
- запросы вне бизнес-модели (например, "X бесплатно" для магазина)
- слишком общие фразы без интента
- бренды конкурентов, с которыми работать запрещено
- запросы с юридическими/репутационными рисками
- информационные запросы, если проекту нужны ТОЛЬКО коммерческие страницы (см. business_context.commercial_only)

Verно отвечай СТРОГО JSON-массивом без обёрток markdown. Schema:
[{"query":"...", "intent":"commercial", "keep":true, "reason":"..." }, ...]
reason — короткая (до 80 символов), на русском."""


def _build_prompt(batch: list[str], business_context: dict) -> str:
    ctx = json.dumps(business_context, ensure_ascii=False, indent=2)
    qs = "\n".join(f"- {q}" for q in batch)
    return f"Бизнес-контекст:\n{ctx}\n\nЗапросы:\n{qs}"


def clean_batch(
    queries: list[str],
    business_context: dict,
    *,
    batch_size: int = 25,
    model: str | None = None,
) -> list[CleanedQuery]:
    """Rule-filter ⇒ LLM-классификация. Батчами для экономии токенов."""
    queries = dedupe_exact(queries)
    after_rules, rule_dropped = rule_filter(queries, business_context)
    results: list[CleanedQuery] = list(rule_dropped)
    queries = after_rules

    for i in range(0, len(queries), batch_size):
        batch = queries[i : i + batch_size]
        user = _build_prompt(batch, business_context)
        raw = chat(_SYSTEM, user, temperature=0.1, max_tokens=2500, model=model)
        try:
            parsed = parse_json(raw)
        except Exception as e:
            print(f"[clean:parse_err] batch {i//batch_size}: {e}; raw[:200]={raw[:200]!r}")
            # fallback: keep all queries with unknown intent
            for q in batch:
                results.append(CleanedQuery(q, "irrelevant", False, "parse error"))
            continue

        seen_in_batch = set()
        for entry in parsed:
            q = (entry.get("query") or "").strip().lower()
            if not q or q in seen_in_batch:
                continue
            seen_in_batch.add(q)
            intent = entry.get("intent", "irrelevant")
            if intent not in INTENT_VALUES:
                intent = "irrelevant"
            keep = bool(entry.get("keep", False))
            reason = (entry.get("reason") or "").strip()
            results.append(CleanedQuery(q, intent, keep, reason))

        # ensure every query has a result; queries the LLM dropped silently → mark
        returned = {r.query for r in results[-len(batch) :]}
        for q in batch:
            if q.lower() not in returned:
                results.append(CleanedQuery(q.lower(), "irrelevant", False, "no LLM verdict"))

    return results
