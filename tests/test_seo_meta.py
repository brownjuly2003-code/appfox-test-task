"""Тесты для core/seo_meta.py — генерация SEO-меты и брифов копирайтеру.

Все «дорогие» LLM-вызовы монки-патчатся через core.seo_meta.chat, чтобы
проверять контракты функций (формат, лимиты, intent-routing) без сети.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import seo_meta as seo_mod
from core.cluster import Cluster
from core.llm import LLMError


BIZ = {
    "vertical": "Интернет-магазин мягкой мебели (диваны)",
    "region": "Москва, доставка по РФ",
    "audience": "B2C, покупатели мебели для дома",
}


def _cluster(label="Угловые диваны", intent="commercial", queries=None, slug="uglovye-divany"):
    c = Cluster(cluster_id=0, label=label, intent=intent, queries=queries or [
        "угловой диван купить",
        "угловой диван цена",
        "угловые диваны москва",
    ])
    c.slug = slug
    return c


def test_generate_meta_returns_three_fields(monkeypatch):
    """generate_seo_meta всегда возвращает dict с ключами title/h1/description."""
    monkeypatch.setattr(
        seo_mod, "chat",
        lambda system, user, **kw: (
            '{"title": "Угловые диваны в Москве с доставкой",'
            ' "h1": "Угловые диваны — каталог с ценами",'
            ' "description": "Купить угловой диван в Москве с доставкой по РФ. '
            'Подбор по размеру, материалу и наполнителю. Гарантия 18 месяцев, оплата при получении."}'
        ),
    )
    out = seo_mod.generate_seo_meta(_cluster(), BIZ)
    assert set(out.keys()) == {"title", "h1", "description"}
    assert out["title"] and out["h1"] and out["description"]


def test_meta_title_length_constraint(monkeypatch):
    """Если LLM проигнорировала лимит — post-LLM нормализация обрезает до TITLE_MAX."""
    too_long_title = "Очень длинный заголовок " * 5  # > 60
    monkeypatch.setattr(
        seo_mod, "chat",
        lambda system, user, **kw: (
            '{"title": "' + too_long_title + '",'
            ' "h1": "ок", "description": "ок описание"}'
        ),
    )
    out = seo_mod.generate_seo_meta(_cluster(), BIZ)
    assert len(out["title"]) <= seo_mod.TITLE_MAX


def test_meta_description_length_constraint(monkeypatch):
    """Description обрезается до DESC_MAX, если LLM перелила."""
    long_desc = "А" * 300
    monkeypatch.setattr(
        seo_mod, "chat",
        lambda system, user, **kw: (
            f'{{"title": "ok", "h1": "ok", "description": "{long_desc}"}}'
        ),
    )
    out = seo_mod.generate_seo_meta(_cluster(), BIZ)
    assert len(out["description"]) <= seo_mod.DESC_MAX


def test_intent_routing_problem_in_system_prompt(monkeypatch):
    """Для problem-интента в user-промпт должна попадать FAQ-подсказка
    (вопросительная форма title). Проверяем по содержимому user-сообщения,
    которое передаётся в chat."""
    captured = {}
    def fake_chat(system, user, **kw):
        captured["system"] = system
        captured["user"] = user
        return '{"title": "Как выбрать угловой диван", "h1": "ok", "description": "ok"}'
    monkeypatch.setattr(seo_mod, "chat", fake_chat)

    c = _cluster(intent="problem", queries=["как выбрать угловой диван", "какой диван лучше"])
    out = seo_mod.generate_seo_meta(c, BIZ)
    assert out["title"]
    assert "вопросительной форме" in captured["user"] or "проблемно" in captured["user"].lower()


def test_brief_structure_has_h2(monkeypatch):
    """generate_page_brief возвращает markdown с минимум одним `## ` (H2) блоком."""
    monkeypatch.setattr(
        seo_mod, "chat",
        lambda system, user, **kw: (
            "**Целевая аудитория**: B2C, покупатели мебели\n\n"
            "**Основной интент**: commercial\n\n"
            "## Каталог моделей\nПодборка угловых диванов с фильтрами.\n\n"
            "## Доставка и оплата\nУсловия доставки.\n\n"
            "## Гарантия\n18 месяцев.\n\n"
            "**Тон**: дружелюбный, без агрессии."
        ),
    )
    out = seo_mod.generate_page_brief(_cluster(), BIZ, "/catalog/uglovye-divany/")
    assert "## " in out


def test_seo_meta_handles_llm_error(monkeypatch):
    """LLMError → возвращаем пустой dict, не падаем."""
    def boom(*a, **kw):
        raise LLMError("simulated outage")
    monkeypatch.setattr(seo_mod, "chat", boom)
    out = seo_mod.generate_seo_meta(_cluster(), BIZ)
    assert out == {}


def test_brief_handles_llm_error(monkeypatch):
    """LLMError → пустая строка."""
    def boom(*a, **kw):
        raise LLMError("simulated outage")
    monkeypatch.setattr(seo_mod, "chat", boom)
    out = seo_mod.generate_page_brief(_cluster(), BIZ, "/catalog/x/")
    assert out == ""


def test_seo_meta_handles_garbage_json(monkeypatch):
    """LLM вернула не-JSON → пустой dict (через parse_json → ValueError)."""
    monkeypatch.setattr(seo_mod, "chat", lambda s, u, **kw: "не json, простой текст без скобок")
    out = seo_mod.generate_seo_meta(_cluster(), BIZ)
    assert out == {}


def test_business_vertical_in_prompt(monkeypatch):
    """business_context.vertical должен попадать в user-промпт (критично для тона)."""
    captured = {}
    monkeypatch.setattr(
        seo_mod, "chat",
        lambda s, u, **kw: (captured.setdefault("user", u), '{"title": "x", "h1": "x", "description": "x"}')[1],
    )
    seo_mod.generate_seo_meta(_cluster(), BIZ)
    assert "мягкой мебели" in captured["user"]
