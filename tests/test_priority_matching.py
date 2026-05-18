"""Intent-aware landing matching: commercial не уходит в /blog/, informational не в /catalog/."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np

from core.cluster import Cluster
from core.priority import decide_action, _page_type, score_cluster


def test_page_type_classification():
    assert _page_type("/catalog/uglovye-divany/") == "catalog"
    assert _page_type("/blog/kak-vybrat-divan/") == "blog"
    assert _page_type("/faq/dostavka/") == "faq"
    assert _page_type("/products/123/") == "catalog"


def test_commercial_does_not_match_blog():
    """ Угловые диваны (commercial) НЕ должны матчиться на /blog/. """
    c = Cluster(cluster_id=0, label="Угловые диваны", intent="commercial",
                queries=["угловой диван", "купить угловой диван"])
    c.slug = "uglovye-divany"
    # Существующие страницы: blog + catalog для другой темы
    pages = ["/blog/kak-vybrat-divan/", "/catalog/pryamye-divany/"]
    # embeddings нам неважны — slug-match должен fail (нет 'uglovye' в pages), embedding по eligible
    action, matched, _ = decide_action(c, pages)
    # blog не eligible для commercial → 'Создать', не 'Обновить'
    assert action == "Создать"
    assert matched is None


def test_informational_matches_blog():
    """ 'Как выбрать диван' (informational) должно матчиться на /blog/. """
    c = Cluster(cluster_id=0, label="Как выбрать диван", intent="informational",
                queries=["как выбрать диван", "какой диван купить"])
    c.slug = "kak-vybrat-divan"
    pages = ["/blog/kak-vybrat-divan/", "/catalog/uglovye-divany/"]
    action, matched, _ = decide_action(c, pages)
    assert action == "Обновить"
    assert matched == "/blog/kak-vybrat-divan/"


def test_commercial_matches_catalog():
    c = Cluster(cluster_id=0, label="Угловые диваны", intent="commercial",
                queries=["угловой диван", "купить угловой диван"])
    c.slug = "uglovye-divany"
    pages = ["/catalog/uglovye-divany/", "/blog/kak-vybrat-divan/"]
    action, matched, _ = decide_action(c, pages)
    assert action == "Обновить"
    assert matched == "/catalog/uglovye-divany/"


def test_navigational_skipped():
    c = Cluster(cluster_id=0, label="Divan.ru", intent="navigational",
                queries=["divan.ru диваны"])
    action, matched, _ = decide_action(c, ["/catalog/uglovye-divany/"])
    assert action == "Не брать"
    assert matched is None


def test_problem_creates_faq():
    c = Cluster(cluster_id=0, label="Скрипит диван", intent="problem",
                queries=["почему диван скрипит", "какой диван не скрипит"])
    c.slug = "skripit-divan"
    action, matched, _ = decide_action(c, ["/catalog/uglovye-divany/"])
    assert action == "Создать FAQ"


def test_score_confidence_with_real_metrics():
    c = Cluster(cluster_id=0, label="Угловые диваны", intent="commercial",
                queries=["угловой диван"] * 5)
    scoring = score_cluster(c, action="Создать", metrics={
        "search_volume": 0.8,
        "keyword_difficulty": 0.4,
        "trend_growth": 0.7,
        "ranking_opportunity": 0.6,
    }, cannibalization_risk=0.1)
    assert scoring["confidence"] >= 0.5
    assert scoring["score_mode"] in ("production", "mixed")


def test_facet_conflict_blocks_uglovye_to_pryamye():
    """Регрессия 2026-05-18: 'Угловые диваны в Москве' (embedding cosine высокий
    с любой страницей про диваны) НЕ должно матчиться на `/catalog/pryamye-divany/`,
    потому что фасеты `угловой` и `прямой` взаимоисключающие.
    """
    from core.cluster import embed
    c = Cluster(cluster_id=0, label="Угловые диваны в Москве", intent="commercial",
                queries=["угловой диван москва", "купить угловой диван"])
    c.slug = "uglovye-divany-moskva"  # такого slug в pages нет → slug-substring не сработает
    pages = ["/catalog/pryamye-divany/", "/catalog/kuhonnye-divany/"]
    # реальный embedding — high cosine между «угловые диваны в Москве» и «прямые диваны»
    page_emb = embed([
        "прямые диваны",
        "кухонные диваны",
    ])
    cluster_emb = embed([" ".join(c.queries)])[0]
    action, matched, sim = decide_action(
        c, pages,
        page_embeddings=page_emb,
        cluster_embedding=cluster_emb,
    )
    assert action == "Создать", (
        f"facet-guard сломан: 'Угловые диваны' матчатся на {matched} (sim={sim:.3f})"
    )
    assert matched is None


def test_facet_match_when_same_facet():
    """Negative control: facet-guard НЕ блокирует match, если facet одинаковый.
    'Угловые диваны' через slug-substring → /catalog/uglovye-divany/ должно сматчиться.
    """
    c = Cluster(cluster_id=0, label="Угловые диваны для сна", intent="commercial",
                queries=["угловой диван для сна", "угловой ортопедический диван"])
    # slug совпадает с существующей страницей — slug-substring должен пропустить
    c.slug = "uglovye-divany"
    pages = ["/catalog/uglovye-divany/", "/catalog/pryamye-divany/"]
    action, matched, _ = decide_action(c, pages)
    assert action == "Обновить"
    assert matched == "/catalog/uglovye-divany/"


def test_facet_guard_on_slug_substring():
    """slug-substring совпал, но facet-guard должен заблокировать.
    Например, кластер про угловые диваны: cluster.slug='divany-uglovye',
    page='/catalog/divany-pryamye/' — оба содержат 'divany', slug сам не
    содержится в page, всё ок. Но если бы случайный slug содержал 'divany' и
    matched через substring — facet-guard защищает.
    """
    c = Cluster(cluster_id=0, label="Угловые диваны Москва", intent="commercial",
                queries=["угловой диван москва", "купить угловой диван"])
    # slug, который случайно содержится в URL прямых диванов (синтетический сценарий)
    c.slug = "divany"
    pages = ["/catalog/pryamye-divany/"]
    action, matched, _ = decide_action(c, pages)
    # slug-substring сработал бы (divany in pryamye-divany), но facet-guard блокирует
    assert action == "Создать", f"facet-guard на slug-ветке не сработал: matched={matched}"
    assert matched is None


def test_score_confidence_without_metrics():
    c = Cluster(cluster_id=0, label="Угловые диваны", intent="commercial",
                queries=["угловой диван"] * 5)
    scoring = score_cluster(c, action="Создать")
    # proxy/unknown везде → low confidence
    assert scoring["confidence"] < 0.5
    assert scoring["score_mode"] == "demo" or scoring["score_mode"] == "mixed"
