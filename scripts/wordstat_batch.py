"""Batch-парсинг volume из живого Wordstat через Opera (или Chrome) CDP.

Преcondition:
1. Залогиниться в wordstat.yandex.ru в Opera/Chrome
2. Закрыть браузер (taskkill /F /IM opera.exe)
3. Запустить с debug-портом:
     "C:\\Users\\<user>\\AppData\\Local\\Programs\\Opera\\opera.exe" --remote-debugging-port=9222 --restore-last-session
4. Убедиться что вкладка с wordstat.yandex.ru восстановилась (sessoin)
5. Запустить этот скрипт: python scripts/wordstat_batch.py [limit]

Источник запросов: data/output/queries.csv (уже cleaned список после rule-filter+LLM).
Output: data/wordstat_volumes.csv (формат для --keycollector-csv: query,volume).
После — pipeline c флагом `--keycollector-csv data/wordstat_volumes.csv` поднимет
score_mode из demo в mixed (real search_volume).

Парсинг: открываем https://wordstat.yandex.ru/?words=<phrase>, ждём AJAX,
читаем число рядом с «за <date_range>: NNN NNN». Регексп по inner_text.
"""
from __future__ import annotations
import csv
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path("D:/appfox_test")
QUERIES_CSV = ROOT / "data" / "output" / "queries.csv"
OUT_CSV = ROOT / "data" / "wordstat_volumes.csv"
PROGRESS = ROOT / "_wordstat_progress.txt"

# Регулярка под формат «за DD.MM.YYYY – DD.MM.YYYY: 197 703»
VOLUME_RE = re.compile(r"за\s+\d{2}\.\d{2}\.\d{4}\s*[–-]\s*\d{2}\.\d{2}\.\d{4}\s*:\s*([\d\s  ]+)")


def parse_volume(text: str) -> int | None:
    m = VOLUME_RE.search(text)
    if not m:
        return None
    digits = re.sub(r"\D", "", m.group(1))
    return int(digits) if digits else None


def load_queries() -> list[str]:
    """Уникальные запросы из queries.csv где keep=True."""
    seen, out = set(), []
    with QUERIES_CSV.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("keep", "").lower() != "true":
                continue
            q = (r.get("query") or "").strip().lower()
            if q and q not in seen:
                seen.add(q)
                out.append(q)
    return out


def write_progress(msg: str):
    print(msg, flush=True)
    PROGRESS.write_text(msg, encoding="utf-8")


def main():
    queries = load_queries()
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else len(queries)
    queries = queries[:limit]
    write_progress(f"start: {len(queries)} queries")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    # Если CSV уже есть — продолжим (skip уже спарсенные)
    done: dict[str, int | None] = {}
    if OUT_CSV.exists():
        with OUT_CSV.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                done[r["query"]] = int(r["volume"]) if r.get("volume") else None

    todo = [q for q in queries if q not in done]
    write_progress(f"todo: {len(todo)} (already done: {len(done)})")

    with sync_playwright() as pw:
        browser = pw.chromium.connect_over_cdp("http://localhost:9222")
        ctx = browser.contexts[0]
        # Используем существующую wordstat-вкладку или открываем
        page = None
        for p in ctx.pages:
            if "wordstat.yandex.ru" in p.url:
                page = p
                break
        if not page:
            page = ctx.new_page()

        for i, q in enumerate(todo, start=1):
            try:
                url = f"https://wordstat.yandex.ru/?words={q}"
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                # AJAX ~ 2-4 секунды
                time.sleep(3.5)
                text = page.locator("body").inner_text()
                vol = parse_volume(text)
                done[q] = vol
                # Append to CSV сразу (чтобы не потерять при сбое)
                exists = OUT_CSV.exists()
                with OUT_CSV.open("a", encoding="utf-8", newline="") as f:
                    w = csv.writer(f)
                    if not exists:
                        w.writerow(["query", "volume"])
                    w.writerow([q, vol if vol is not None else ""])
                write_progress(f"[{i}/{len(todo)}] {q!r}: {vol}")
            except Exception as e:
                write_progress(f"[{i}/{len(todo)}] {q!r}: ERR {type(e).__name__}: {e}")
                time.sleep(5)

        browser.close()
    write_progress(f"done: {sum(1 for v in done.values() if v is not None)}/{len(done)} с volume")


if __name__ == "__main__":
    main()
