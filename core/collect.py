"""Collect raw queries: seeds, autosuggest, modifiers, competitor categories.

Полный список источников из ТЗ:
- Yandex/Google autosuggest          → ✓ реализовано (без auth)
- Модификаторы (купить/цена/...)     → ✓ реализовано
- Категории конкурентов (scraping)   → ✓ реализовано
- Wordstat (объёмы)                  → stub (нужен OAuth Яндекс.Директ)
- Google Search Console              → stub (нужен service account + verified property)
- KeyCollector / TopVisor / Keys.so  → stub (нужен экспорт CSV из инструмента)
- SpyWords / Ahrefs / Semrush        → stub (платные API)

Каждый stub возвращает QueryCandidate с заполненным `source`. Реальные значения
volume/clicks/impressions/position идут в priority.score_cluster через metrics.
"""
from __future__ import annotations
import csv
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


@dataclass
class QueryCandidate:
    """Один кандидат-запрос с источником и метриками (если есть)."""
    query: str
    source: str  # 'yandex_autosuggest' | 'google_autosuggest' | 'modifier' | 'competitor' | 'wordstat' | 'gsc' | 'keycollector' | 'spywords'
    volume: int | None = None        # Wordstat shows
    clicks: int | None = None        # GSC clicks
    impressions: int | None = None   # GSC impressions
    position: float | None = None    # GSC avg position
    competitor_url: str | None = None
    raw: dict = field(default_factory=dict)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "ru,en;q=0.9"}


def yandex_autosuggest(query: str, *, sleep_s: float = 0.4, timeout: float = 15.0) -> list[str]:
    """Yandex's public autosuggest endpoint. Returns ~10 suggestions per call.
    No auth. Yandex intermittently rate-limits or times out — caller should fall back to Google.
    """
    url = (
        "https://suggest.yandex.ru/suggest-ya.cgi"
        f"?part={quote(query)}&v=4&srv=morda_ru_desktop"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and len(data) >= 2 and isinstance(data[1], list):
            time.sleep(sleep_s)
            return [s for s in data[1] if isinstance(s, str)]
    except Exception as e:
        print(f"[autosuggest-y:err] {query!r}: {type(e).__name__}")
    return []


def google_autosuggest(query: str, *, sleep_s: float = 0.4) -> list[str]:
    """Google's public autosuggest endpoint (Russian results)."""
    url = (
        "https://suggestqueries.google.com/complete/search"
        f"?client=firefox&hl=ru&q={quote(query)}"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list) and len(data) >= 2 and isinstance(data[1], list):
            time.sleep(sleep_s)
            return [s for s in data[1] if isinstance(s, str)]
    except Exception as e:
        print(f"[autosuggest-g:err] {query!r}: {e}")
    return []


def expand_with_modifiers(seeds: list[str], modifiers: list[str]) -> list[str]:
    """Combine seeds × modifiers in both orders, dedup."""
    out: list[str] = []
    for s in seeds:
        for m in modifiers:
            out.append(f"{m} {s}")
            out.append(f"{s} {m}")
        out.append(s)
    seen = set()
    deduped: list[str] = []
    for q in out:
        k = q.strip().lower()
        if k and k not in seen:
            seen.add(k)
            deduped.append(q.strip())
    return deduped


def fetch_competitor_categories(url: str, *, max_links: int = 60) -> list[str]:
    """Pull category names from competitor URL by reading anchors that look like menu items.

    Heuristics:
    - links inside <nav>, <header>, .menu, .catalog, [class*=category]
    - text length 2..80 chars, no digits-only, not pure URL
    """
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"[competitor:err] {url}: {e}")
        return []
    soup = BeautifulSoup(r.text, "html.parser")
    out: list[str] = []
    seen = set()
    selectors = [
        "nav a", "header a",
        "[class*=menu] a", "[class*=category] a", "[class*=catalog] a",
        "[class*=nav] a",
    ]
    for sel in selectors:
        for a in soup.select(sel):
            text = a.get_text(" ", strip=True)
            if not text:
                continue
            if not (2 <= len(text) <= 80):
                continue
            if re.fullmatch(r"[\d\W]+", text):
                continue
            if text.lower() in seen:
                continue
            # filter out boilerplate
            blocklist = {"вход", "регистрация", "корзина", "избранное", "контакты", "поиск", "о компании", "доставка"}
            if text.lower() in blocklist:
                continue
            seen.add(text.lower())
            out.append(text)
            if len(out) >= max_links:
                return out
    return out


def collect_all(
    seeds: list[str],
    modifiers: list[str],
    competitor_urls: list[str],
    *,
    autosuggest_per_seed: bool = True,
    use_google: bool = False,
) -> list[str]:
    """Full collection: seeds + seeds×modifiers + autosuggest(seed,modified) + competitor cats."""
    bag: set[str] = set()
    bag.update(s.strip().lower() for s in seeds if s.strip())

    expanded = expand_with_modifiers(seeds, modifiers)
    bag.update(q.lower() for q in expanded)

    if autosuggest_per_seed:
        probe_targets = seeds + expanded[: max(len(seeds) * 3, 10)]
        for q in probe_targets:
            y = yandex_autosuggest(q)
            for s in y:
                bag.add(s.lower())
            # If Yandex returned nothing (rate-limited / timeout), fall back to Google
            if (use_google or not y):
                for s in google_autosuggest(q):
                    bag.add(s.lower())

    for url in competitor_urls:
        for cat in fetch_competitor_categories(url):
            bag.add(cat.lower())

    return sorted(bag)


# ---------------- Stubs for real-volume sources ----------------

def collect_wordstat(seeds: list[str], *, oauth_token: str | None = None) -> list[QueryCandidate]:
    """Wordstat запросы + объёмы. Нужен OAuth токен Яндекс.Директ API.

    Endpoint: https://api.direct.yandex.com/v4/json/ method=KeywordsResearch (или Reports).
    OAuth получать через https://oauth.yandex.ru/ для приложения с правом on agency.
    Реализация: после получения токена, POST `{"method":"GetReportList", "param":{...}}`
    с `Bearer {oauth_token}`. Парсить shows из ответа.
    """
    if not oauth_token:
        raise NotImplementedError(
            "Wordstat требует OAuth токен Яндекс.Директ. Получить: oauth.yandex.ru, "
            "scope=direct:api. Передать в collect_wordstat(seeds, oauth_token=...). "
            "Альтернатива — ручной экспорт CSV из wordstat.yandex.ru и вызов import_keycollector_csv."
        )
    raise NotImplementedError("Wordstat client не реализован — добавьте requests-обвязку под токен")


def collect_gsc(
    site_url: str,
    *,
    service_account_json: str | None = None,
    start_date: str = "2025-01-01",
    end_date: str | None = None,
) -> list[QueryCandidate]:
    """Google Search Console: запросы, по которым сайт уже получает показы/клики.

    Нужно: service account JSON + домен подтверждён в GSC + service account добавлен в Users.
    Endpoint: searchanalytics.googleapis.com/v1/sites/{siteUrl}/searchAnalytics/query
    """
    if not service_account_json:
        raise NotImplementedError(
            "GSC требует service account credentials. Создать в Google Cloud Console, "
            "скачать JSON, добавить email сервис-аккаунта в Search Console > Settings > Users > Add. "
            "Передать путь к JSON в collect_gsc(site_url, service_account_json=...)."
        )
    raise NotImplementedError("GSC client не реализован — добавьте google-api-python-client под JWT")


def import_keycollector_csv(csv_path: str | Path) -> list[QueryCandidate]:
    """Импорт ручного экспорта из KeyCollector / TopVisor / Keys.so.

    Универсальный CSV-парсер: ожидает колонки `query` (или `keyword`/`phrase`/`фраза`),
    опционально `volume`/`shows`/`частотность`. Остальные колонки кладутся в raw.
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)
    out: list[QueryCandidate] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        # sniff delimiter
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        # column aliases
        QUERY_COLS = ("query", "keyword", "phrase", "фраза", "запрос", "ключ")
        VOLUME_COLS = ("volume", "shows", "shows_yandex", "частотность", "частота", "wordstat", "ws", "search_volume")
        for row in reader:
            q = None
            for col in QUERY_COLS:
                for k in row:
                    if k and k.strip().lower() == col:
                        q = (row[k] or "").strip()
                        break
                if q:
                    break
            if not q:
                continue
            vol: int | None = None
            for col in VOLUME_COLS:
                for k in row:
                    if k and k.strip().lower() == col:
                        try:
                            vol = int(re.sub(r"[^\d]", "", row[k] or "0") or "0")
                        except ValueError:
                            vol = None
                        break
                if vol is not None:
                    break
            out.append(QueryCandidate(query=q.lower(), source="keycollector", volume=vol, raw=dict(row)))
    return out


def collect_spywords(seeds: list[str], *, api_key: str | None = None) -> list[QueryCandidate]:
    """SpyWords / Ahrefs / Semrush — запросы конкурентов с метриками.

    Платный API, ключ передаётся в `api_key`. Endpoint конкретного провайдера.
    """
    if not api_key:
        raise NotImplementedError(
            "SpyWords/Ahrefs/Semrush требуют платного API ключа. "
            "Получить в личном кабинете провайдера, передать в api_key=. "
            "Альтернатива — экспорт CSV и вызов import_keycollector_csv (формат совместим)."
        )
    raise NotImplementedError("SpyWords client не реализован")
