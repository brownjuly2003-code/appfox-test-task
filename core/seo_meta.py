"""SEO-мета + бриф копирайтера для «Создать»-кластеров.

Две LLM-driven функции с явными контрактами:
- generate_seo_meta(cluster, business_context) → {title, h1, description}
- generate_page_brief(cluster, business_context, recommended_url) → markdown

Промпты — intent-aware (commercial/transactional vs informational vs problem/FAQ
vs comparative vs local). Используем `core.llm.chat(cache=True)` — повторные
прогоны на тех же кластерах бесплатные.

Pipeline-friendly:
- На LLMError / JSON-parse-fail возвращаем пустой dict / пустую строку — НЕ
  роняем граф, фича опциональная (см. seo_node в agents/nodes.py).
- Post-LLM нормализация длин (title ≤60, description 140-160) — если LLM
  проигнорировала constraint, обрезаем сами.
"""
from __future__ import annotations

from .cluster import Cluster
from .llm import LLMError, chat, parse_json


TITLE_MAX = 60
H1_MAX = 80
DESC_MIN = 140
DESC_MAX = 160


def _intent_guidance(intent: str, business_context: dict) -> str:
    """Подсказка LLM по интенту: что именно подчеркнуть в title/description."""
    region = (business_context.get("region") or "").strip()
    if intent in ("commercial", "transactional"):
        return (
            "Интент коммерческий/транзакционный: упор на «купить», «заказать», цена/доставка/гарантия. "
            "В description — призыв к действию."
        )
    if intent == "informational":
        return (
            "Интент информационный: тон гайда/обзора («как выбрать», «отличия», «руководство»). "
            "В description — обещание полезной информации без агрессивной продажи."
        )
    if intent == "comparative":
        return (
            "Интент сравнительный: формулировки «vs», «или», «что лучше», pros/cons. "
            "В description — обещание разобрать различия."
        )
    if intent == "problem":
        return (
            "Интент проблемно-FAQ: title в вопросительной форме («Как…», «Почему…», «Что лучше…»), "
            "description — прямой короткий ответ + обещание развернуть на странице."
        )
    if intent == "local":
        region_hint = f"; гео-маркер «{region}»" if region else ""
        return f"Интент локальный: упомянуть регион/город в title и description{region_hint}."
    return "Интент общий: нейтральный тон, без агрессивной продажи."


_SEO_SYSTEM = (
    "Ты SEO-редактор. По кластеру поисковых запросов сгенерируй три поля для страницы:\n"
    "  title — кликабельный, ≤60 символов, на русском;\n"
    "  h1    — близкий к title заголовок страницы, ≤80 символов;\n"
    "  description — мета-описание 140-160 символов, на русском.\n\n"
    "Отвечай СТРОГО JSON-объектом без markdown:\n"
    '{"title":"...", "h1":"...", "description":"..."}'
)


_BRIEF_SYSTEM = (
    "Ты SEO-редактор. Подготовь короткий бриф для копирайтера: что писать на странице.\n"
    "Формат — markdown 150–300 слов, на русском, со следующими секциями:\n"
    "- **Целевая аудитория** (1 строка)\n"
    "- **Основной интент** (commercial / informational / comparative / problem / local)\n"
    "- **Структура страницы** — 3–5 H2-блоков с короткой пометкой что раскрыть\n"
    "- **Тон и стиль** (1 строка)\n"
    "- **Ключевые запросы для покрытия** — список 3–5 самых частотных из кластера\n\n"
    "В каждом H2-пункте используй markdown-заголовок `## ...`. Не оборачивай ответ в код-блоки."
)


def _truncate(text: str, limit: int) -> str:
    text = (text or "").strip().strip('"').strip("'")
    if len(text) <= limit:
        return text
    # Truncate on word boundary if possible
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut if len(cut) >= int(limit * 0.6) else text[:limit]


def _normalize_meta(raw: dict) -> dict[str, str]:
    """Подрезаем длины + страхуем формат. Описание уплотняем до DESC_MAX."""
    title = _truncate(str(raw.get("title", "")), TITLE_MAX)
    h1 = _truncate(str(raw.get("h1", "")), H1_MAX)
    description = (raw.get("description") or "").strip().strip('"').strip("'")
    if len(description) > DESC_MAX:
        description = _truncate(description, DESC_MAX)
    return {"title": title, "h1": h1, "description": description}


def generate_seo_meta(cluster: Cluster, business_context: dict) -> dict[str, str]:
    """Сгенерировать {title, h1, description} для кластера.

    Возвращает пустой dict если LLM упала / вернула мусор — caller не должен
    падать. Длины title/description проверяются и обрезаются post-LLM.
    """
    if not cluster.queries:
        return {}

    vertical = (business_context.get("vertical") or "").strip()
    region = (business_context.get("region") or "").strip()
    guidance = _intent_guidance(cluster.intent, business_context)
    sample = cluster.queries[:8]

    user = (
        f"Бизнес: {vertical or '—'}.\n"
        f"Регион: {region or '—'}.\n"
        f"Кластер: {cluster.label or cluster.queries[0]} (slug: {getattr(cluster, 'slug', '')}).\n"
        f"Доминирующий интент: {cluster.intent}.\n"
        f"{guidance}\n"
        f"Жёсткие лимиты: title ≤{TITLE_MAX} символов, h1 ≤{H1_MAX} символов, "
        f"description {DESC_MIN}–{DESC_MAX} символов.\n"
        f"Запросы кластера:\n" + "\n".join(f"- {q}" for q in sample)
    )

    try:
        raw = chat(_SEO_SYSTEM, user, temperature=0.3, max_tokens=400, cache=True)
        parsed = parse_json(raw)
        if not isinstance(parsed, dict):
            return {}
        return _normalize_meta(parsed)
    except (LLMError, ValueError, KeyError):
        return {}


def generate_page_brief(
    cluster: Cluster,
    business_context: dict,
    recommended_url: str,
) -> str:
    """Сгенерировать markdown-бриф для копирайтера. Пустая строка при ошибке."""
    if not cluster.queries:
        return ""

    vertical = (business_context.get("vertical") or "").strip()
    region = (business_context.get("region") or "").strip()
    audience = (business_context.get("audience") or "").strip()
    guidance = _intent_guidance(cluster.intent, business_context)
    # Топ-5 «частотных» — у нас нет volume, берём первые из кластера (cluster_queries
    # уже отсортирован по длине запросов, частотные обычно короче — но это прокси).
    top_queries = cluster.queries[:5]

    user = (
        f"Бизнес: {vertical or '—'}.\n"
        f"Регион: {region or '—'}.\n"
        f"Аудитория: {audience or '—'}.\n"
        f"Кластер: {cluster.label or cluster.queries[0]}.\n"
        f"Доминирующий интент: {cluster.intent}.\n"
        f"Рекомендованный URL: {recommended_url or '—'}.\n"
        f"{guidance}\n"
        f"Топ запросы для покрытия:\n" + "\n".join(f"- {q}" for q in top_queries) + "\n\n"
        f"Сделай markdown-бриф 150–300 слов по структуре из system-промпта."
    )

    try:
        raw = chat(_BRIEF_SYSTEM, user, temperature=0.4, max_tokens=900, cache=True)
        text = (raw or "").strip()
        if text.startswith("```"):
            lines = [l for l in text.split("\n") if not l.startswith("```")]
            text = "\n".join(lines).strip()
        return text
    except LLMError:
        return ""
