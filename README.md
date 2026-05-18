# Агент коммерческого семантического ядра

Тестовое для Appfox / AI-LLM Engineer (AI Agents).

Прототип: бизнес-контекст + сидовые услуги → агентный пайплайн → карта посадочных страниц (Кластер → URL → Действие → Приоритет) с замкнутым циклом (gap-анализ к предыдущему ядру и конкурентам) и Telegram-интерфейсом управления.

## Структура

```
core/
  collect.py    # сбор: seeds × modifiers, Yandex/Google autosuggest, scraping конкурентов
                # + stubs: Wordstat / GSC / KeyCollector CSV / SpyWords
  clean.py      # rule-фильтр (бренды/маркетплейсы/гео) ⇒ LLM intent + бизнес-релевантность
  cluster.py    # multilingual embeddings → AgglomerativeClustering + facet-split (product/geo)
  priority.py   # формула Priority Score из ТЗ + metrics provider (real|proxy|unknown)
  gap.py        # closed-loop: vs previous_state, vs конкурентам; gap_status + competitor_coverage
  output.py     # decisions.csv + decisions.md + queries.csv (per-query аудит) + briefs/{slug}.md + Google Sheets
  seo_meta.py   # title/H1/description + бриф копирайтеру (intent-aware промпты, LLM-cached)
  llm.py        # Mistral primary / Groq fallback / disk JSON-cache
bot/
  tg.py         # Telegram бот: /run /status /export csv|md|queries|state /seeds /upload_seeds
data/
  seeds.yaml    # бизнес-контекст + seeds + modifiers + конкуренты + existing_pages + brand-bans
  state/core.json  # сохранённое предыдущее ядро для gap-анализа
  output/       # decisions.csv, decisions.md, queries.csv, raw_cleaned.json
```

## Соответствие ТЗ

| Стадия ТЗ | Реализация | Файл |
|---|---|---|
| **Сбор** услуг/категорий клиента + конкурентов | `fetch_competitor_categories` (BeautifulSoup на nav/menu/category) + seeds в YAML | `collect.py:65-105` |
| **Расширение** (Wordstat/GSC/KeyCollector/SpyWords/похожие/модификаторы) | Yandex/Google autosuggest (без auth) + seeds×modifiers + stubs с явным NotImplementedError и инструкцией получения key | `collect.py` |
| **Чистка** (9 правил из ТЗ) | (1) rule-фильтр substring: brands/marketplaces/blocked_regions/freebies, (2) LLM-классификатор reason'ом | `clean.py:rule_filter` + `clean_batch` |
| **Intent классификация** (7 типов из ТЗ + irrelevant) | внутри LLM-чистки, intent в `CleanedQuery` для каждого запроса | `clean.py:INTENT_VALUES` |
| **Кластеризация** под страницы | `paraphrase-multilingual-MiniLM-L12-v2` + `AgglomerativeClustering(cosine, average)` + **facet-split** по product_type/geo/modifier (1 кластер = 1 страница) | `cluster.py` |
| **Формула приоритета** из ТЗ | точная формула `0.25·sv + 0.20·bv + 0.20·ro + 0.15·im + 0.10·tg + 0.10·cg − 0.20·kd − 0.15·cr`; каждый фактор помечен `real`/`proxy`/`unknown` | `priority.py:score_cluster` |
| **Карта посадочных** (existing/new/blog/FAQ/skip) | embedding-similarity к existing_pages (threshold 0.85) → Обновить; FAQ для problem/comparative; Создать статью для informational; Не брать для navigational | `priority.py:decide_action` |
| **Output**: Кластер→Страница→Действие | CSV + Markdown + **queries.csv** (per-query: intent+keep+reason+cluster+action) + **SEO-мета колонки** + **briefs/{slug}.md** + Google Sheets stub | `output.py` |
| **SEO meta + page brief** | для каждого «Создать»-кластера: title ≤60 / H1 ≤80 / description 140-160 + markdown-бриф 150-300 слов (audience, intent, H2-структура, тон, top-запросы); промпты intent-aware (commercial/informational/comparative/problem/local), кэш через `llm.chat(cache=True)`, опционально через `--no-seo` | `seo_meta.py` |
| **Замкнутый цикл расширения** | `gap.diff_with_previous` сравнивает текущие центроиды с сохранённым ядром (cosine ≥0.75 = existing/shifted, иначе new); `diff_with_competitors` — vs категории конкурентов | `gap.py` |
| **Каннибализация** | для каждого кластера: max(cosine) с другими центроидами (`fill_diagonal(0)`) → отрицательный вес в Priority Score | `output.py:build_decision_rows` |
| **Управление: UI или Telegram-бот** | `bot/tg.py`: `/run` (фон), `/status` (текущий шаг), `/export csv\|md\|queries\|state\|raw`, `/seeds`, `/upload_seeds` (replace через caption) | `bot/tg.py` |
| **Иерархия агентов** | LangGraph `StateGraph` с supervisor-узлами (`agents/graph.py`): collect → clean → [yield_guard] → cluster → [size_guard] → label → merge → gap → output. Гарды принимают однократное adaptive-решение (re-collect с расширенными modifiers / re-cluster с уменьшенным threshold = больше кластеров). Единственная точка входа — `agents/cli.py`. | `agents/graph.py` |

## Запуск

```powershell
python -m venv .venv
.venv\Scripts\Activate
pip install -r requirements.txt
copy .env.example .env  # вписать MISTRAL_API_KEY (+ опц. TG_BOT_TOKEN)

# Основная точка входа — LangGraph supervisor:
python -m agents.cli --config data/seeds.yaml --out data/output

# с KeyCollector (real volume → score_mode поднимается из demo в mixed):
python -m agents.cli --keycollector-csv keys.csv

# с экспортом в Google Sheet:
python -m agents.cli --google-sheet-id <ID> --service-account-json sa.json

# без скрейпа конкурентов (быстрее, без HTTP):
python -m agents.cli --skip-competitors

# Telegram-бот:
python -m bot.tg
```

## Supervisor (LangGraph)

`agents/graph.py` собирает `StateGraph` с двумя условными вершинами-гардами:

```
collect → clean → yield_guard ─┐
                          │    │
                          │    └─→ yield_decision → collect  (1 retry: расширить modifiers)
                          ▼
                      cluster → size_guard ─┐
                                    │       │
                                    │       └─→ size_decision → cluster (1 retry: relax threshold)
                                    ▼
                                  label → merge → gap → seo → output → END
```

**yield_guard** (`agents/graph.py:yield_guard`): если после `clean` выживаемость <30% (`YIELD_MIN_RATE`), супервайзер объединяет текущие modifiers с `BROADER_MODIFIERS` и пере-`collect`'ит — однократно (`MAX_COLLECT_RETRIES=1`).

**size_guard** (`agents/graph.py:size_guard`): если после `cluster` получилось <3 кластеров (`MIN_CLUSTERS_AFTER_CLUSTER`), threshold **уменьшается** на `THRESHOLD_RELAX_DELTA=0.10` (с floor 0.05) — и кластеризация повторяется. Меньше threshold = больше кластеров, что и нужно: триггер «кластеров мало». Регрессия 2026-05-18: было `+ DELTA`, теперь `- DELTA`, покрыто `test_size_guard_apply_decreases_threshold`.

Каждое решение пишется в `state["decisions"]`, виден в выводе CLI:
```
Decision log
  • collect: 200 запросов (modifiers=8)
  • clean: kept 156/200
  • cluster: 16 (threshold=0.20)
  • label: done
  • merge: 16 → 16
  • gap: 0 новых vs prev, 0 убрано
  • seo: 14 меты, 14 брифов
  • output: 16 rows → data/output/decisions.csv, briefs/=14
```

Узлы (`agents/nodes.py`) — тонкие враппера над `core/*` модулями; всё ML/LLM-наполнение там же. Тесты: `tests/test_supervisor.py` (11 кейсов: компиляция графа, оба гарда независимо, направление threshold-дельты у size_guard, threshold floor, оба end-to-end с замоканными nodes).

Параметры `agents.cli`:
- `--cluster-threshold 0.20` — мельче кластеры (дефолт)
- `--max-queries 200` — кап перед LLM-чисткой
- `--no-split` — выключить facet-split (вернуть «толстые» кластеры)
- `--no-merge` — выключить пост-merge дублей
- `--skip-competitors` — без scraping конкурентов
- `--no-seo` — без LLM-генерации SEO-меты и брифов (быстрее на ~30-60с)
- `--keycollector-csv keys.csv` — импорт CSV из KeyCollector/TopVisor с volume → `score_mode` поднимается из `demo` в `mixed`
- `--google-sheet-id <ID> --service-account-json sa.json` — экспорт результата в Google Sheet

## Демо-выход (на `data/seeds.yaml`, домен «диваны»)

Свежий прогон LangGraph supervisor: **200 запросов → 16 групп**, полный граф 263с (+SEO-мета и брифы, 14 LLM-вызовов после `gap`). Файлы под `data/output/` закоммичены как живой snapshot. Топ:

| # | Кластер | Intent | Страница | Действие | Priority | Q |
|---|---|---|---|---|---|---|
| 1 | Диваны для сна | commercial | `/catalog/divany-dlya-sna/` | Создать | 0.636 | 17 |
| 2 | Диваны в Москве | transactional | `/catalog/divany-v-moskve/` | Создать | 0.621 | 16 |
| 4 | Диваны с доставкой | transactional | `/catalog/divany-s-dostavkoj/` | Создать | 0.618 | 11 |
| 5 | Недорогие диваны в Москве | transactional | `/catalog/uglovye-divany/` | **Обновить** | 0.572 | 7 |
| 0 | Кухонные диваны | commercial | `/catalog/kuhonnye-divany/` | Создать | 0.556 | 19 |
| 3 | Угловые диваны | transactional | `/catalog/uglovye-divany/` | **Обновить** | 0.498 | 14 |

Видимое поведение:
- Rule-фильтр режет до LLM: «ами мебель», «куфар», «авито», «минск», «спб», «екатеринбург», «бишкек», «беларусь» — всё **детерминированно**, без вариативности LLM
- Существующая `/catalog/uglovye-divany/` теперь матчится с «Угловые диваны» (slug-substring) и «Недорогие диваны в Москве» (embedding ≥0.85, 2/7 запросов кластера про угловые). Регрессия «угловые → /catalog/pryamye-divany/» закрыта `_facets_conflict`-guard
- 14 «Создать»-кластеров получили `seo_title`/`seo_h1`/`seo_description` (см. колонки в `decisions.csv`) и `briefs/{slug}-{id}.md` копирайтеру
- queries.csv: каждый запрос виден с intent+keep+reason+cluster — аудитируемая классификация по ТЗ
- gap-analysis: existing/shifted/new + **removed_clusters** (prev-кластеры без match → drop/архив) + competitor_gap (у конкурентов нет страницы)
- cannibalization_risk считается как max cosine между центроидами кластеров; высокие значения снижают priority

## Что real vs proxy

Real:
- Yandex + Google autosuggest, scraping категорий конкурентов, LLM (Mistral), embeddings + clustering, gap analysis, cannibalization
- Rule-фильтр: brands/marketplaces/blocked_regions полностью детерминирован

Proxy (помечены в `sources` каждой строки CSV):
- `search_volume` — `proxy:cluster_size` если не дан real volume; **real** при `--keycollector-csv` (импорт + усреднение по кластеру)
- `keyword_difficulty` — `proxy:label_length`; **real** при `metrics_by_cluster[cid]["keyword_difficulty"]`
- `trend_growth` — `unknown:default_0.5`; **real** при наличии в metrics
- `cannibalization_risk` — `computed:embedding_overlap`

Stubs для платных API (`NotImplementedError` с инструкцией auth):
- `collect_wordstat(oauth_token=...)` — Яндекс.Директ OAuth
- `collect_gsc(service_account_json=...)` — Google Search Console
- `collect_spywords(api_key=...)` — SpyWords/Ahrefs/Semrush
- `write_google_sheet(spreadsheet_id, service_account_json=...)` — Google Sheets API

## Telegram-бот

**Бот**: [@appfox_semcore_bot](https://t.me/appfox_semcore_bot) (создан через @BotFather 2026-05-18). Токен — в `.env` (`TG_BOT_TOKEN`).

```
/start          справка
/run            запустить пайплайн (фон, через subprocess)
/status         текущий шаг + хвост лога
/export csv     decisions.csv
/export md      decisions.md
/export queries queries.csv (per-query audit)
/export state   data/state/core.json (текущее ядро)
/seeds          текущий seeds.yaml
/upload_seeds   (caption: `confirm`) — заменить seeds.yaml после YAML-валидации
```

**ACL**: deny-by-default. Без `TG_ALLOWED_CHAT_IDS=12345,67890` в `.env` все запросы игнорируются — никаких info-leaks для случайных пользователей.

**Стек**: чистый `requests` long-polling, не python-telegram-bot. На Win11 httpx-default IPv6-first вешает `bot.initialize()` на `get_me` (`telegram.error.TimedOut` через 5 минут). С requests тайм-аут предсказуемый, IPv4-резолв стабильный, кода меньше.

**Запуск**:
```powershell
python -m bot.tg
# или фоном:
Start-Process pythonw -ArgumentList "-m","bot.tg" -WorkingDirectory "D:\appfox_test"
```

**Известная проблема (next session)**: при стартe `getUpdates` возвращает `409 Conflict: terminated by other getUpdates request`. Бот авторизован (`getMe` ok, `live as @appfox_semcore_bot`), но Telegram держит зависшую polling-сессию от предыдущего инстанса. Лечится:
1. `POST https://api.telegram.org/bot<TOKEN>/deleteWebhook?drop_pending_updates=true`
2. `POST https://api.telegram.org/bot<TOKEN>/close`
3. Или подождать ~5 минут — TG сам отвалит зависший long-poll.

После любого из шагов polling должен подняться чисто.

## Архитектурные решения

1. **Rule-filter ДО LLM** — детерминирует чистку для критичных правил (бренды, гео, маркетплейсы). LLM-чистка тогда работает только на «серой зоне», где правил недостаточно — например, «слишком общий запрос».
2. **Facet-split после embedding-кластеризации** — embedding группирует похожее, но «угловой диван в москве» и «прямой диван в москве» под одну страницу не пойдут. Сплит по triggers (`угловой`, `кухонный`, `доставка`, `москва`) разделяет.
3. **Metrics-провайдер вместо констант** — `score_cluster(metrics=...)` принимает реальные значения с пометкой `real`. Если нет — фактор `proxy:...` или `unknown:default_X` (видно в каждой строке выхода).
4. **Embedding-matching существующих страниц** — slug-substring был неустойчив (страница `/catalog/divany-krovati/` теряла кластер «диваны-кровати трансформеры»). Cosine с translit-pretty имени страницы при threshold 0.85 даёт стабильный матч.
5. **Cannibalization как max-cosine между центроидами** — формула из ТЗ требует учитывать. Высокие значения (>0.95) означают, что кластеры пересекаются по запросам и конкурируют за одну страницу — это сигнал смерджить или явно развести.
6. **State в JSON** — `data/state/core.json` хранит предыдущее ядро. Следующий прогон сравнивает центроиды, размечает `existing/shifted/new`. Это минимальный замкнутый цикл без БД.
7. **TG-бот как тонкий враппер** — основная логика в `agents/cli.py` (LangGraph supervisor), бот через `subprocess.Popen` запускает её. Никакой дубликат-логики, есть watchdog с таймаутом и атомарные обновления `STATE` под `STATE_LOCK`.

## Roadmap для production

| Future-фича из ТЗ | Где встроить |
|---|---|
| **SERP-проверка различия кластеров** | `core/serp.py`: top-10 Я/G через scraper или SerpAPI; jaccard URL → merge/split |
| **Маржинальность** | `business_context.margin_map: {product_type: weight}` → множитель `business_value` |
| **Наличие товаров** | join `cluster.slug ↔ catalog_feed.csv` (формат YML/feed) |
| **Сезонность** | Google Trends API или Wordstat history → `trend_growth` |
| **Post-indexing verify** | `core/verify.py`: GSC API → CTR/position 14/30 дней после публикации → ratchet |
| **Иерархия агентов через LangGraph** | `agents/graph.py`: каждый core-модуль = node; supervisor с router'ом |

## История ревью

### Codex review #1 (10 пунктов) — закрыты в v1.1

1. ~~Нет TG-бота~~ → `bot/tg.py` с 6 командами
2. ~~Нет замкнутого цикла~~ → `core/gap.py` + state в JSON
3. ~~Источники semantic — только autosuggest~~ → +stubs Wordstat/GSC/KeyCollector с инструкциями auth; работающий импорт KeyCollector CSV
4. ~~Priority Score на заглушках~~ → metrics provider с пометкой real/proxy/unknown
5. ~~Per-query intent не виден в output~~ → `queries.csv`
6. ~~Чистка LLM-only недетерминирована~~ → rule-фильтр **до** LLM
7. ~~Кластеры мешают продукты+гео~~ → facet-split (32 кластера вместо 9 «толстых»)
8. ~~slug-matching примитивно~~ → embedding-similarity + threshold
9. ~~Нет FAQ-action~~ → action=«Создать FAQ» для problem/вопросительных кластеров
10. ~~Нет Google Sheets~~ → `write_google_sheet()` с service account stub

### Codex review #2 (5 critical + minor) — закрыты в v1.2

1. ~~Landing-matcher маппит commercial в /blog/~~ → intent-aware matching через `_INTENT_TO_ALLOWED_PAGE_TYPES`: commercial/transactional ходят только в catalog, informational/comparative — только в blog/faq
2. ~~Gap analysis считается, но не пишется в CSV/MD~~ → `write_csv`/`write_markdown` теперь несут `gap_status`, `competitor_coverage`, `matched_prev_label`, `new_queries_count`, `lost_queries_count`
3. ~~Priority Score = proxy-only~~ → `score_cluster` возвращает `confidence` (real-ratio) и `score_mode` (production/mixed/demo); пометки видны в каждой строке CSV
4. ~~Wordstat/GSC/Sheets не подключены к CLI~~ → флаги `--google-sheet-id` / `--service-account-json` / `--keycollector-csv` в `agents/cli.py`
5. ~~Дубли кластеров~~ → `cluster.merge_duplicates`: 31 → 16 кластеров после merge

Minor:
- `region_substrings` теперь применяется в `rule_filter` как allow-list для гео-привязанных запросов
- TG-бот: deny-by-default ACL, шаг-парсер до «Шаг 6», `/upload_seeds` требует caption `confirm` + YAML-валидация
- Typo `cannibalization_risk` → `cannibal_risk`
- 20 unit-тестов: `tests/test_rule_filter.py`, `tests/test_priority_matching.py`, `tests/test_cluster_merge.py`

### Audit #3 (manual, 2026-05-18) — закрыт в HEAD f1ea9f4

Critical:
1. ~~`size_guard` двигал threshold в WRONG direction~~ → `+ DELTA` → `- DELTA` с floor 0.05. Покрыто `test_size_guard_apply_decreases_threshold`
2. ~~TG `/run` запускал flat `run.py`, не LangGraph~~ → бот теперь зовёт `python -m agents.cli`
3. ~~Hero numbers в PRESENTATION не совпадали с актуальными artifacts~~ → синхронизировано: 200 → 16, 252с

High / Medium:
4. ~~`score_mode` tooltip говорил `real/proxy/derived`, код выдаёт `production/mixed/demo`~~ → копия приведена к лейблам кода
5. ~~«Stubs swap by config» overclaim~~ → честно: нужны OAuth и credentials
6. ~~`requests.RequestException` не оборачивался в `LLMError`~~ → fallback теперь срабатывает на сетевые ошибки
7. ~~TG bot без child-process timeout~~ → `threading.Timer` watchdog + `STATE_LOCK` для атомарных обновлений
8. ~~Competitor pages скрейпились дважды (collect + gap)~~ → `comp_pages` кэшируется в state, gap читает оттуда
9. ~~`gap.py` docstring обещал «удалённые → drop/архив», не возвращал~~ → `find_removed_clusters(current, prev)`, печатается в CLI
10. ~~`run.py` дублировал orchestration с `agents/nodes.py`~~ → УДАЛЁН, все фичи перенесены в `agents/cli.py`

Tests: 20 → 31 pass (+ 11 supervisor tests).

### v1.3 — SEO meta + page brief (2026-05-18)

Закрыты 2 пункта из «Будущее» в исходном ТЗ:
1. **Title / H1 / Description** — `core/seo_meta.py:generate_seo_meta`, intent-aware промпты на русском (commercial vs informational vs problem-FAQ vs comparative vs local). Лимиты `title ≤60`, `h1 ≤80`, `description 140-160` контролируются post-LLM, кэш через `llm.chat(cache=True)`.
2. **Бриф копирайтеру** — `core/seo_meta.py:generate_page_brief`, markdown 150-300 слов: аудитория / интент / 3-5 H2-блоков / тон / top-5 запросов. Артефакт — `data/output/briefs/{slug}-{id}.md` на каждый «Создать»-кластер.

В графе: новый узел `seo` между `gap` и `output`. `output_node` инжектит `seo_title`/`seo_h1`/`seo_description` в строки CSV/MD. CLI флаг `--no-seo` отключает шаг (быстрее на ~30-60с). На LLMError pipeline не падает — пустые поля.

Tests: 31 → 42 pass (+9 в `test_seo_meta.py`, +2 в `test_supervisor.py`).

### v1.4 — facet-guard и UI-фиксы (2026-05-18)

Закрыты замечания внешнего ревью 7.5/10:

1. **Landing matching: facet-guard** — `decide_action` теперь блокирует match если cluster и page несут взаимоисключающие фасеты из `DEFAULT_FACETS` (угловой vs прямой, кухонный vs для-сна, и т.д.). Регрессия «Угловые диваны в Москве» → `/catalog/pryamye-divany/` закрыта. Сам threshold вернули к 0.85 — для русского multilingual MiniLM cosine 0.81–0.83 одинаково низкий и для «своих» и для «чужих»; реальная защита — фасеты, не cutoff. `core/priority.py:_facets_conflict`, +2 теста в `test_priority_matching.py`.
2. **Mobile overflow 390→455px** — таблица решений раздувалась на mono-URL и невидимые `.term::after` tooltip'ы держали layout-width. На `max-width:520px` таблица переключается в `table-layout:fixed`, mono-ячейки получают `word-break:break-all`, tooltip-pseudo скрываются. Проверено через Playwright на 360px и 390px viewports.
3. **Demo-артефакты синхронизированы** — `data/output/decisions.csv` (с SEO-колонками), `decisions.md` и `briefs/*.md` теперь закоммичены как демо-snapshot, чтобы презентация и репо не расходились. `raw_cleaned.json` остался в `.gitignore`.

Tests: 42 → 45 pass.
