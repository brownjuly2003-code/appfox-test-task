# План работ для следующей сессии

## Состояние на 2026-05-18

Версия: **v1.2** (после двух прогонов Codex review).

Готово:
- ✅ Все 10 пунктов Codex review #1
- ✅ Все 5 critical + minor из Codex review #2
- ✅ Тесты 20/20 pass (`pytest tests/ -p no:schemathesis`)
- ✅ E2E демо на `data/seeds.yaml`: 31→16 кластеров, intent-aware matching, gap/competitor_coverage в CSV/MD
- ✅ TG-бот **@appfox_semcore_bot** создан через @BotFather (Telethon-сессией Юлии)
- ✅ Токен в `.env` (`TG_BOT_TOKEN`), ACL `TG_ALLOWED_CHAT_IDS=432751211`

## Что осталось — следующая сессия

### P0 — поднять polling бота

Бот авторизован, но `getUpdates` возвращает `409 Conflict: terminated by other getUpdates request`. Где-то в Telegram застряла прошлая polling-сессия (или паралелльно с прошлым стартом было два инстанса).

**Лечение** (по убыванию агрессивности):
1. `requests.post(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook", data={"drop_pending_updates": "true"})`
2. `requests.post(f"https://api.telegram.org/bot{TOKEN}/close")`
3. Подождать ~5 минут, Telegram сам отвалит зависший long-poll.

После любого шага запустить `python -m bot.tg` — должно сразу подняться без 409.

**Чтобы 409 не повторялся**: убедиться, что не запускаются параллельные `python -m bot.tg` процессы (проверять через `wmic process where (name='python.exe') get processid,commandline | findstr bot.tg`).

### P1 — деплой бота (если нужен 24/7)

Сейчас бот живёт только пока запущен `python -m bot.tg` на машине Юлии. Опции:
- **PythonAnywhere/Replit free** — бесплатный 24/7 polling, токен в env.
- **Render/Railway free** — webhook-режим (нужен HTTPS public endpoint).
- **systemd на VPS** — если есть.

Для демо Игнатию (single-day проверка) — достаточно ручного `python -m bot.tg` на ноутбуке.

### P2 — что ещё может всплыть на 3-м ревью

Пункты, которые Codex review #2 не назвал критичными, но могут стать ими:

1. **Иерархия агентов реально только в README**. `run.py` — flat pipeline. Если хотят строгого LangGraph — `agents/graph.py` с supervisor + router.
2. **Wordstat/GSC всё ещё stubs**. Без реальных volume `score_mode=mixed/demo` везде. Если есть тестовый OAuth — поднять `collect_wordstat`. KeyCollector CSV-импорт уже работает; можно положить пример `data/sample_keycollector.csv` и прогнать с `--keycollector-csv`.
3. **SERP-based кластеризация**. ТЗ упоминает «отличать кластер от другого по SERP» — пока не реализовано. Можно через SerpAPI или живой scraping топ-10 Я/G.
4. **Margin/inventory/seasonality** из section «Будущее». Подключаются через `business_context` extras.
5. **Title/H1/Description генератор** — отдельный `core/seo_meta.py` с LLM по `cluster.label + queries`.
6. **Post-indexing verification** — `core/verify.py` с GSC API, CTR/position через 14/30 дней.

## Структура коммитов

Сделано в одном репо `D:\appfox_test\`:

```
v1.0  baseline: collect → clean → cluster → priority → output → CSV/MD
v1.1  10 фиксов Codex #1: TG bot, gap, queries.csv, FAQ, sheets, rules
v1.2  5 critical + minor Codex #2: typed matching, gap-in-csv, confidence, dedupe, tests
```

Все три зафиксированы первым коммитом `v1.2 baseline` (git init только что).

## Команды для возобновления

```powershell
cd D:\appfox_test
# проверить что бот реально создан
curl https://api.telegram.org/bot$env:TG_BOT_TOKEN/getMe
# сбросить залипшее соединение
curl -X POST "https://api.telegram.org/bot$env:TG_BOT_TOKEN/deleteWebhook?drop_pending_updates=true"
curl -X POST "https://api.telegram.org/bot$env:TG_BOT_TOKEN/close"
# поднять бота
python -m bot.tg
# в TG: написать боту /start, потом /run
```

## Ссылки

- Бот: https://t.me/appfox_semcore_bot
- Токен и chat_id: `D:\appfox_test\.env` (НЕ коммитить в публичный)
- ТЗ Игнатия: `D:\HH_int\_appfox_task.txt`
- Артефакты прогона: `D:\appfox_test\data\output\decisions.csv` (16 кластеров), `queries.csv` (audit), `decisions.md` (читаемо)
