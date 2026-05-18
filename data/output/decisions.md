# Карта посадочных страниц

| # | Кластер | Интент | Страница | Действие | Priority | Mode | Q | page_sim | cannib | gap | competitors |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Угловые диваны на кухню со спальным местом | transactional | `/catalog/uglovye-divany-na-kukhnyu-so-spalnym-mestom/` | Создать | 0.689 | mixed | 23 | 0.00 | 0.90 | shifted | unknown |
| 5 | Диваны для сна с доставкой | transactional | `/catalog/divany-dlya-sna-s-dostavkoy/` | Создать | 0.676 | mixed | 10 | 0.00 | 0.98 | shifted | unknown |
| 6 | Ортопедические диваны для сна | transactional | `/catalog/ortopedicheskie-divany-dlya-sna/` | Создать | 0.653 | mixed | 9 | 0.00 | 0.97 | shifted | unknown |
| 7 | Диваны от производителя в Москве | transactional | `/catalog/divany-ot-proizvoditelya-v-moskve/` | Создать | 0.635 | mixed | 8 | 0.00 | 0.94 | shifted | unknown |
| 2 | Диваны с доставкой | transactional | `/catalog/divany-s-dostavkoj/` | Создать | 0.621 | mixed | 19 | 0.90 | 0.95 | shifted | unknown |
| 9 | Диваны для сна с акциями | transactional | `/catalog/divany-dlya-sna-s-aktsiyami/` | Создать | 0.606 | mixed | 7 | 0.00 | 0.97 | shifted | unknown |
| 10 | Диваны для сна с ортопедическим матрасом | transactional | `/catalog/divany-dlya-sna-s-ortopedicheskim-matrasom/` | Создать | 0.605 | mixed | 7 | 0.00 | 0.97 | shifted | unknown |
| 8 | Диваны для сна в Москве | transactional | `/catalog/divany-dlya-sna-v-moskve/` | Создать | 0.603 | mixed | 7 | 0.00 | 0.98 | new | unknown |
| 11 | Купить диван в Москве | transactional | `/catalog/kupit-divan-v-moskve/` | Создать | 0.535 | mixed | 4 | 0.00 | 0.95 | shifted | unknown |
| 0 | Диваны в Москве с доставкой | transactional | `/catalog/divany-v-moskve-s-dostavkoj/` | Создать | 0.473 | mixed | 31 | 0.88 | 0.95 | shifted | unknown |
| 19 | Кухонные диваны с ящиком | transactional | `/catalog/kuhonnye-divany-s-yashchikom/` | Создать | 0.470 | mixed | 1 | 0.00 | 0.90 | shifted | unknown |
| 3 | Диваны-кровати с ортопедическим матрасом | transactional | `/catalog/divany-krovati-s-ortopedicheskim-matrasom/` | Создать | 0.457 | mixed | 16 | 0.00 | 0.92 | shifted | unknown |
| 4 | Диваны для сна с независимым пружинным блоком | transactional | `/catalog/divany-dlya-sna-s-nezavisimym-pruzhinnym-blokom/` | Создать | 0.437 | mixed | 11 | 0.00 | 0.96 | new | unknown |
| 12 | Диваны-кровати трансформеры | transactional | `/catalog/divany-krovati-transformery/` | Создать | 0.410 | mixed | 4 | 0.00 | 0.85 | shifted | unknown |
| 13 | Диваны купить дешево | transactional | `/catalog/divany-kupit-deshevo/` | Создать | 0.404 | mixed | 1 | 0.00 | 0.93 | new | unknown |
| 15 | Диваны от производителя | transactional | `/catalog/divany-ot-proizvoditelya/` | Создать | 0.404 | mixed | 1 | 0.00 | 0.94 | new | unknown |
| 16 | Акции на диваны | transactional | `/catalog/aktsii-na-divany/` | Создать | 0.402 | mixed | 1 | 0.00 | 0.95 | shifted | unknown |
| 18 | Диваны Амстердам | transactional | `/catalog/divany-amsterdam/` | Создать | 0.333 | mixed | 1 | 0.00 | 0.88 | new | unknown |
| 14 | Диваны прямые | transactional | `/catalog/divany-pryamye/` | Создать | 0.321 | mixed | 1 | 0.00 | 0.95 | shifted | unknown |
| 17 | Диваны-книжки | transactional | `/catalog/divany-knizhka/` | Создать | 0.258 | mixed | 1 | 0.00 | 0.84 | new | unknown |

## Кластеры по запросам

### Угловые диваны на кухню со спальным местом → Создать  (priority 0.689, mode mixed, confidence 0.38)
- intent: **transactional**, page: `/catalog/uglovye-divany-na-kukhnyu-so-spalnym-mestom/`
- факторы: {'search_volume': 0.97, 'business_value': 1.0, 'ranking_opportunity': 0.7, 'intent_match': 1.0, 'trend_growth': 0.5, 'content_gap': 1.0, 'keyword_difficulty': 0.3, 'cannibalization_risk': 0.9}
- источники: {'search_volume': 'proxy:cluster_size', 'business_value': 'config:intent_map', 'keyword_difficulty': 'proxy:label_length', 'ranking_opportunity': 'derived:1-kd', 'intent_match': 'config:intent_map', 'trend_growth': 'unknown:default_0.5', 'content_gap': 'derived:action', 'cannibalization_risk': 'computed:embedding_overlap'}
- page_similarity (matched existing): 0.000; cannibal_risk: 0.898
- gap: **shifted** vs prev `Кухонные диваны`; new 23, lost 19
- новые запросы: акция кухонный диван угловой со спальным местом, акция угловой диван на кухню со спальным местом, в москве кухонный диван со спальным местом, в москве кухонный диван угловой со спальным местом, в москве угловой диван на кухню со спальным местом, купить угловой диван на кухню со спальным местом, купить угловой диван на кухню со спальным местом в москве, кухонный диван угловой со спальным местом в москве, кухонный диван угловой со спальным местом с доставкой, кухонный угловой диван со спальным местом купить в москве
- потерянные: акция кухонный диван, в москве кухонный диван, купить кухонный диван, кухонный диван акция, кухонный диван в москве, кухонный диван купить, кухонный диван недорого, кухонный диван прямой с ящиком, кухонный диван раскладной, кухонный диван с доставкой
- запросы:
  - купить угловой диван на кухню со спальным местом
  - недорого угловой диван на кухню со спальным местом
  - угловой диван на кухню со спальным местом купить
  - угловой диван на кухню со спальным местом недорого
  - угловой диван на кухню со спальным местом цена
  - узкий угловой диван на кухню со спальным местом
  - цена угловой диван на кухню со спальным местом
  - купить угловой диван на кухню со спальным местом в москве
  - в москве угловой диван на кухню со спальным местом
  - кухонный угловой диван со спальным местом купить в москве
  - угловой диван на кухню со спальным местом в москве
  - в москве кухонный диван угловой со спальным местом
  - кухонный диван угловой со спальным местом в москве
  - акция угловой диван на кухню со спальным местом
  - распродажа угловой диван на кухню со спальным местом
  - угловой диван на кухню со спальным местом акция
  - угловой диван на кухню со спальным местом распродажа
  - акция кухонный диван угловой со спальным местом
  - с доставкой угловой диван на кухню со спальным местом
  - угловой диван на кухню со спальным местом с доставкой
  - кухонный диван угловой со спальным местом с доставкой
  - с доставкой кухонный диван угловой со спальным местом
  - в москве кухонный диван со спальным местом

### Диваны для сна с доставкой → Создать  (priority 0.676, mode mixed, confidence 0.38)
- intent: **transactional**, page: `/catalog/divany-dlya-sna-s-dostavkoy/`
- факторы: {'search_volume': 0.97, 'business_value': 1.0, 'ranking_opportunity': 0.7, 'intent_match': 1.0, 'trend_growth': 0.5, 'content_gap': 1.0, 'keyword_difficulty': 0.3, 'cannibalization_risk': 0.98}
- источники: {'search_volume': 'proxy:cluster_size', 'business_value': 'config:intent_map', 'keyword_difficulty': 'proxy:label_length', 'ranking_opportunity': 'derived:1-kd', 'intent_match': 'config:intent_map', 'trend_growth': 'unknown:default_0.5', 'content_gap': 'derived:action', 'cannibalization_risk': 'computed:embedding_overlap'}
- page_similarity (matched existing): 0.000; cannibal_risk: 0.983
- gap: **shifted** vs prev `Диваны для сна`; new 10, lost 17
- новые запросы: в москве диван для сна с доставкой, в москве с доставкой диван для сна, диван для постоянного сна с ортопедическим матрасом, диван для сна в москве с доставкой, диван для сна на каждый день с доставкой, диван для сна с доставкой в москве, диван для сна с независимым пружинным блоком с доставкой, диван кровать для ежедневного сна купить в москве, с доставкой диван для сна на каждый день, с доставкой диван для сна с независимым пружинным блоком
- потерянные: акция диван для сна, в москве диван для сна, диван для сна, диван для сна акция, диван для сна в москве, диван для сна купить, диван для сна на каждый день, диван для сна недорого, диван для сна распродажа, диван для сна с доставкой
- запросы:
  - диван для сна с независимым пружинным блоком с доставкой
  - с доставкой диван для сна с независимым пружинным блоком
  - диван для сна на каждый день с доставкой
  - с доставкой диван для сна на каждый день
  - в москве диван для сна с доставкой
  - в москве с доставкой диван для сна
  - диван для сна в москве с доставкой
  - диван для сна с доставкой в москве
  - диван для постоянного сна с ортопедическим матрасом
  - диван кровать для ежедневного сна купить в москве

### Ортопедические диваны для сна → Создать  (priority 0.653, mode mixed, confidence 0.38)
- intent: **transactional**, page: `/catalog/ortopedicheskie-divany-dlya-sna/`
- факторы: {'search_volume': 0.88, 'business_value': 1.0, 'ranking_opportunity': 0.7, 'intent_match': 1.0, 'trend_growth': 0.5, 'content_gap': 1.0, 'keyword_difficulty': 0.3, 'cannibalization_risk': 0.97}
- источники: {'search_volume': 'proxy:cluster_size', 'business_value': 'config:intent_map', 'keyword_difficulty': 'proxy:label_length', 'ranking_opportunity': 'derived:1-kd', 'intent_match': 'config:intent_map', 'trend_growth': 'unknown:default_0.5', 'content_gap': 'derived:action', 'cannibalization_risk': 'computed:embedding_overlap'}
- page_similarity (matched existing): 0.000; cannibal_risk: 0.973
- gap: **shifted** vs prev `Ортопедические диваны для сна`; new 9, lost 2
- новые запросы: диван для ежедневного сна с ортопедическим матрасом, диван для ежедневного сна с ортопедическим матрасом купить, диван для сна на каждый день ортопедический, диван для сна с ортопедическим матрасом купить, диван для сна с ортопедическим матрасом недорого, диван для сна с ортопедическим матрасом цена, ортопедический диван для ежедневного сна купить в москве недорого распродажа, угловой диван для ежедневного сна с ортопедическим матрасом купить, угловой диван для сна на каждый день ортопедический
- потерянные: диван для сна ортопедический, диван для сна с ортопедическим матрасом
- запросы:
  - диван для ежедневного сна с ортопедическим матрасом купить
  - диван для ежедневного сна с ортопедическим матрасом
  - диван для сна на каждый день ортопедический
  - диван для сна с ортопедическим матрасом купить
  - диван для сна с ортопедическим матрасом недорого
  - диван для сна с ортопедическим матрасом цена
  - ортопедический диван для ежедневного сна купить в москве недорого распродажа
  - угловой диван для ежедневного сна с ортопедическим матрасом купить
  - угловой диван для сна на каждый день ортопедический

### Диваны от производителя в Москве → Создать  (priority 0.635, mode mixed, confidence 0.38)
- intent: **transactional**, page: `/catalog/divany-ot-proizvoditelya-v-moskve/`
- факторы: {'search_volume': 0.78, 'business_value': 1.0, 'ranking_opportunity': 0.7, 'intent_match': 1.0, 'trend_growth': 0.5, 'content_gap': 1.0, 'keyword_difficulty': 0.3, 'cannibalization_risk': 0.94}
- источники: {'search_volume': 'proxy:cluster_size', 'business_value': 'config:intent_map', 'keyword_difficulty': 'proxy:label_length', 'ranking_opportunity': 'derived:1-kd', 'intent_match': 'config:intent_map', 'trend_growth': 'unknown:default_0.5', 'content_gap': 'derived:action', 'cannibalization_risk': 'computed:embedding_overlap'}
- page_similarity (matched existing): 0.000; cannibal_risk: 0.936
- gap: **shifted** vs prev `Диваны в Москве`; new 8, lost 16
- новые запросы: в москве диван в москве от производителя, в москве диваны в москве от производителя, в москве купить диван в москве от производителя, в москве купить диван в москве раскладной, диван в москве от производителя в москве, диваны в москве от производителя в москве, купить диван в москве от производителя в москве, купить диван еврокнижка в москве от производителя цена
- потерянные: в москве диван, в москве диван-кровать, диван в москве, диван в москве недорого, диван в москве от производителя, диван кровать в москве, диван-кровать в москве, диваны в москве, диваны в москве купить недорого с доставкой, диваны в москве от производителя
- запросы:
  - в москве купить диван в москве от производителя
  - купить диван в москве от производителя в москве
  - купить диван еврокнижка в москве от производителя цена
  - в москве диван в москве от производителя
  - в москве диваны в москве от производителя
  - в москве купить диван в москве раскладной
  - диван в москве от производителя в москве
  - диваны в москве от производителя в москве

### Диваны с доставкой → Создать  (priority 0.621, mode mixed, confidence 0.38)
- intent: **transactional**, page: `/catalog/divany-s-dostavkoj/`
- факторы: {'search_volume': 0.97, 'business_value': 1.0, 'ranking_opportunity': 0.55, 'intent_match': 1.0, 'trend_growth': 0.5, 'content_gap': 1.0, 'keyword_difficulty': 0.45, 'cannibalization_risk': 0.95}
- источники: {'search_volume': 'proxy:cluster_size', 'business_value': 'config:intent_map', 'keyword_difficulty': 'proxy:label_length', 'ranking_opportunity': 'derived:1-kd', 'intent_match': 'config:intent_map', 'trend_growth': 'unknown:default_0.5', 'content_gap': 'derived:action', 'cannibalization_risk': 'computed:embedding_overlap'}
- page_similarity (matched existing): 0.895; cannibal_risk: 0.951
- gap: **shifted** vs prev `Диваны с доставкой`; new 19, lost 11
- новые запросы: акция диваны с доставкой в день заказа, акция диваны с доставкой по всей россии, диваны с доставкой в день заказа акция, диваны с доставкой в день заказа купить, диваны с доставкой в день заказа недорого, диваны с доставкой в день заказа отзывы, диваны с доставкой в день заказа распродажа, диваны с доставкой в день заказа с доставкой, диваны с доставкой в день заказа цена, диваны с доставкой по всей россии акция
- потерянные: диван с доставкой, диван с доставкой и сборкой, диван с доставкой купить, диван с доставкой москва, диван с доставкой на дом, диван с доставкой по россии, диван с доставкой сегодня, диваны с доставкой в день заказа, диваны с доставкой по всей россии, диваны с доставкой по россии
- запросы:
  - диваны с доставкой в день заказа с доставкой
  - диваны с доставкой по всей россии с доставкой
  - с доставкой диваны с доставкой в день заказа
  - с доставкой диваны с доставкой по всей россии
  - диваны с доставкой в день заказа купить
  - диваны с доставкой в день заказа недорого
  - диваны с доставкой в день заказа отзывы
  - диваны с доставкой в день заказа цена
  - диваны с доставкой по всей россии купить
  - диваны с доставкой по всей россии недорого
  - диваны с доставкой по всей россии отзывы
  - диваны с доставкой по всей россии цена
  - диваны с доставкой по россии с доставкой
  - акция диваны с доставкой в день заказа
  - акция диваны с доставкой по всей россии
  - диваны с доставкой в день заказа акция
  - диваны с доставкой в день заказа распродажа
  - диваны с доставкой по всей россии акция
  - диваны с доставкой по всей россии распродажа

### Диваны для сна с акциями → Создать  (priority 0.606, mode mixed, confidence 0.38)
- intent: **transactional**, page: `/catalog/divany-dlya-sna-s-aktsiyami/`
- факторы: {'search_volume': 0.68, 'business_value': 1.0, 'ranking_opportunity': 0.7, 'intent_match': 1.0, 'trend_growth': 0.5, 'content_gap': 1.0, 'keyword_difficulty': 0.3, 'cannibalization_risk': 0.97}
- источники: {'search_volume': 'proxy:cluster_size', 'business_value': 'config:intent_map', 'keyword_difficulty': 'proxy:label_length', 'ranking_opportunity': 'derived:1-kd', 'intent_match': 'config:intent_map', 'trend_growth': 'unknown:default_0.5', 'content_gap': 'derived:action', 'cannibalization_risk': 'computed:embedding_overlap'}
- page_similarity (matched existing): 0.000; cannibal_risk: 0.967
- gap: **shifted** vs prev `Диваны для сна`; new 7, lost 17
- новые запросы: акция диван для сна на каждый день, акция диван для сна с независимым пружинным блоком, диван для сна на каждый день акция, диван для сна на каждый день распродажа, диван для сна с независимым пружинным блоком акция, диван для сна с независимым пружинным блоком распродажа, распродажа диван для сна с независимым пружинным блоком
- потерянные: акция диван для сна, в москве диван для сна, диван для сна, диван для сна акция, диван для сна в москве, диван для сна купить, диван для сна на каждый день, диван для сна недорого, диван для сна распродажа, диван для сна с доставкой
- запросы:
  - акция диван для сна с независимым пружинным блоком
  - диван для сна с независимым пружинным блоком акция
  - диван для сна с независимым пружинным блоком распродажа
  - распродажа диван для сна с независимым пружинным блоком
  - акция диван для сна на каждый день
  - диван для сна на каждый день акция
  - диван для сна на каждый день распродажа

### Диваны для сна с ортопедическим матрасом → Создать  (priority 0.605, mode mixed, confidence 0.38)
- intent: **transactional**, page: `/catalog/divany-dlya-sna-s-ortopedicheskim-matrasom/`
- факторы: {'search_volume': 0.68, 'business_value': 1.0, 'ranking_opportunity': 0.7, 'intent_match': 1.0, 'trend_growth': 0.5, 'content_gap': 1.0, 'keyword_difficulty': 0.3, 'cannibalization_risk': 0.97}
- источники: {'search_volume': 'proxy:cluster_size', 'business_value': 'config:intent_map', 'keyword_difficulty': 'proxy:label_length', 'ranking_opportunity': 'derived:1-kd', 'intent_match': 'config:intent_map', 'trend_growth': 'unknown:default_0.5', 'content_gap': 'derived:action', 'cannibalization_risk': 'computed:embedding_overlap'}
- page_similarity (matched existing): 0.000; cannibal_risk: 0.973
- gap: **shifted** vs prev `Ортопедические диваны для сна`; new 7, lost 2
- новые запросы: акция диван для сна с ортопедическим матрасом, в москве диван для сна с ортопедическим матрасом, диван для сна с ортопедическим матрасом акция, диван для сна с ортопедическим матрасом в москве, диван для сна с ортопедическим матрасом распродажа, диван для сна с ортопедическим матрасом с доставкой, с доставкой диван для сна с ортопедическим матрасом
- потерянные: диван для сна ортопедический, диван для сна с ортопедическим матрасом
- запросы:
  - акция диван для сна с ортопедическим матрасом
  - диван для сна с ортопедическим матрасом акция
  - диван для сна с ортопедическим матрасом распродажа
  - в москве диван для сна с ортопедическим матрасом
  - диван для сна с ортопедическим матрасом в москве
  - диван для сна с ортопедическим матрасом с доставкой
  - с доставкой диван для сна с ортопедическим матрасом

### Диваны для сна в Москве → Создать  (priority 0.603, mode mixed, confidence 0.38)
- intent: **transactional**, page: `/catalog/divany-dlya-sna-v-moskve/`
- факторы: {'search_volume': 0.68, 'business_value': 1.0, 'ranking_opportunity': 0.7, 'intent_match': 1.0, 'trend_growth': 0.5, 'content_gap': 1.0, 'keyword_difficulty': 0.3, 'cannibalization_risk': 0.98}
- источники: {'search_volume': 'proxy:cluster_size', 'business_value': 'config:intent_map', 'keyword_difficulty': 'proxy:label_length', 'ranking_opportunity': 'derived:1-kd', 'intent_match': 'config:intent_map', 'trend_growth': 'unknown:default_0.5', 'content_gap': 'derived:action', 'cannibalization_risk': 'computed:embedding_overlap'}
- page_similarity (matched existing): 0.000; cannibal_risk: 0.983
- gap: **new**; competitors: unknown
- новые запросы: в москве диван для сна с независимым пружинным блоком, диван для сна с независимым пружинным блоком в москве, в москве диван для сна на каждый день, диван для сна на каждый день в москве, в москве в москве диван для сна, в москве диван для сна в москве, диван для сна в москве в москве
- запросы:
  - в москве диван для сна с независимым пружинным блоком
  - диван для сна с независимым пружинным блоком в москве
  - в москве диван для сна на каждый день
  - диван для сна на каждый день в москве
  - в москве в москве диван для сна
  - в москве диван для сна в москве
  - диван для сна в москве в москве

### Купить диван в Москве → Создать  (priority 0.535, mode mixed, confidence 0.38)
- intent: **transactional**, page: `/catalog/kupit-divan-v-moskve/`
- факторы: {'search_volume': 0.39, 'business_value': 1.0, 'ranking_opportunity': 0.7, 'intent_match': 1.0, 'trend_growth': 0.5, 'content_gap': 1.0, 'keyword_difficulty': 0.3, 'cannibalization_risk': 0.95}
- источники: {'search_volume': 'proxy:cluster_size', 'business_value': 'config:intent_map', 'keyword_difficulty': 'proxy:label_length', 'ranking_opportunity': 'derived:1-kd', 'intent_match': 'config:intent_map', 'trend_growth': 'unknown:default_0.5', 'content_gap': 'derived:action', 'cannibalization_risk': 'computed:embedding_overlap'}
- page_similarity (matched existing): 0.000; cannibal_risk: 0.953
- gap: **shifted** vs prev `Недорогие диваны в Москве`; new 4, lost 7
- новые запросы: в москве купить в москве диван недорого, диван купить в москве недорого от производителя, купить диван в москве от производителя с доставкой, с доставкой купить диван в москве от производителя
- потерянные: в москве угловой диван, диван купить москва, диван недорого купить москва, диван недорого москва, диваны недорого москва, диваны недорого московская область, угловой диван в москве
- запросы:
  - в москве купить в москве диван недорого
  - диван купить в москве недорого от производителя
  - купить диван в москве от производителя с доставкой
  - с доставкой купить диван в москве от производителя

### Диваны в Москве с доставкой → Создать  (priority 0.473, mode mixed, confidence 0.5)
- intent: **transactional**, page: `/catalog/divany-v-moskve-s-dostavkoj/`
- факторы: {'search_volume': 0.14, 'business_value': 1.0, 'ranking_opportunity': 0.7, 'intent_match': 1.0, 'trend_growth': 0.5, 'content_gap': 1.0, 'keyword_difficulty': 0.3, 'cannibalization_risk': 0.95}
- источники: {'search_volume': 'real', 'business_value': 'config:intent_map', 'keyword_difficulty': 'proxy:label_length', 'ranking_opportunity': 'derived:1-kd', 'intent_match': 'config:intent_map', 'trend_growth': 'unknown:default_0.5', 'content_gap': 'derived:action', 'cannibalization_risk': 'computed:embedding_overlap'}
- page_similarity (matched existing): 0.884; cannibal_risk: 0.951
- gap: **shifted** vs prev `Диваны в Москве`; new 30, lost 15
- новые запросы: акция диваны в москве купить недорого с доставкой, в москве диван с доставкой и сборкой, в москве диван с доставкой на дом, в москве диван с доставкой по россии, в москве диваны в москве купить недорого с доставкой, в москве диваны с доставкой в день заказа, в москве диваны с доставкой по всей россии, в москве диваны с доставкой по россии, в москве купить в москве диван кровать, где купить хороший диван кровать в москве
- потерянные: в москве диван, в москве диван-кровать, диван в москве, диван в москве недорого, диван в москве от производителя, диван кровать в москве, диван-кровать в москве, диваны в москве, диваны в москве от производителя, купить в москве диван
- запросы:
  - в москве диваны в москве купить недорого с доставкой
  - диваны в москве купить недорого с доставкой в москве
  - диваны в москве купить недорого с доставкой с доставкой
  - с доставкой диваны в москве купить недорого с доставкой
  - в москве диваны с доставкой в день заказа
  - в москве диваны с доставкой по всей россии
  - диваны в москве купить недорого с доставкой купить
  - диваны в москве купить недорого с доставкой недорого
  - диваны в москве купить недорого с доставкой цена
  - диваны с доставкой в день заказа в москве
  - диваны с доставкой по всей россии в москве
  - купить диваны в москве купить недорого с доставкой
  - недорого диваны в москве купить недорого с доставкой
  - цена диваны в москве купить недорого с доставкой
  - в москве диван с доставкой и сборкой
  - в москве диван с доставкой на дом
  - в москве диван с доставкой по россии
  - в москве диваны с доставкой по россии
  - диван в москве от производителя с доставкой
  - диван с доставкой и сборкой в москве
  - диван с доставкой на дом в москве
  - диван с доставкой по россии в москве
  - диваны в москве купить недорого с доставкой
  - диваны в москве от производителя с доставкой
  - диваны с доставкой по россии в москве
  - акция диваны в москве купить недорого с доставкой
  - диваны в москве купить недорого с доставкой акция
  - диваны в москве купить недорого с доставкой распродажа
  - распродажа диваны в москве купить недорого с доставкой
  - в москве купить в москве диван кровать
  - где купить хороший диван кровать в москве

### Кухонные диваны с ящиком → Создать  (priority 0.470, mode mixed, confidence 0.38)
- intent: **transactional**, page: `/catalog/kuhonnye-divany-s-yashchikom/`
- факторы: {'search_volume': 0.1, 'business_value': 1.0, 'ranking_opportunity': 0.7, 'intent_match': 1.0, 'trend_growth': 0.5, 'content_gap': 1.0, 'keyword_difficulty': 0.3, 'cannibalization_risk': 0.9}
- источники: {'search_volume': 'proxy:cluster_size', 'business_value': 'config:intent_map', 'keyword_difficulty': 'proxy:label_length', 'ranking_opportunity': 'derived:1-kd', 'intent_match': 'config:intent_map', 'trend_growth': 'unknown:default_0.5', 'content_gap': 'derived:action', 'cannibalization_risk': 'computed:embedding_overlap'}
- page_similarity (matched existing): 0.000; cannibal_risk: 0.898
- gap: **shifted** vs prev `Кухонные диваны`; new 1, lost 19
- новые запросы: в москве кухонный диван прямой с ящиком
- потерянные: акция кухонный диван, в москве кухонный диван, купить кухонный диван, кухонный диван акция, кухонный диван в москве, кухонный диван купить, кухонный диван недорого, кухонный диван прямой с ящиком, кухонный диван раскладной, кухонный диван с доставкой
- запросы:
  - в москве кухонный диван прямой с ящиком

### Диваны-кровати с ортопедическим матрасом → Создать  (priority 0.457, mode mixed, confidence 0.5)
- intent: **transactional**, page: `/catalog/divany-krovati-s-ortopedicheskim-matrasom/`
- факторы: {'search_volume': 0.06, 'business_value': 1.0, 'ranking_opportunity': 0.7, 'intent_match': 1.0, 'trend_growth': 0.5, 'content_gap': 1.0, 'keyword_difficulty': 0.3, 'cannibalization_risk': 0.92}
- источники: {'search_volume': 'real', 'business_value': 'config:intent_map', 'keyword_difficulty': 'proxy:label_length', 'ranking_opportunity': 'derived:1-kd', 'intent_match': 'config:intent_map', 'trend_growth': 'unknown:default_0.5', 'content_gap': 'derived:action', 'cannibalization_risk': 'computed:embedding_overlap'}
- page_similarity (matched existing): 0.000; cannibal_risk: 0.920
- gap: **shifted** vs prev `Диваны-кровати ортопедические`; new 15, lost 1
- новые запросы: акция диван-кровать с ортопедическим матрасом для ежедневного использования, в москве диван-кровать с ортопедическим матрасом для ежедневного использования, диван кровать с ортопедическим матрасом для ежедневного использования купить, диван-кровать с ортопедическим матрасом для ежедневного использования акция, диван-кровать с ортопедическим матрасом для ежедневного использования в москве, диван-кровать с ортопедическим матрасом для ежедневного использования купить, диван-кровать с ортопедическим матрасом для ежедневного использования недорого, диван-кровать с ортопедическим матрасом для ежедневного использования распродажа, диван-кровать с ортопедическим матрасом для ежедневного использования с доставкой, диван-кровать с ортопедическим матрасом для ежедневного использования цена
- потерянные: диван-кровать с ортопедическим матрасом
- запросы:
  - диван кровать с ортопедическим матрасом для ежедневного использования купить
  - диван-кровать с ортопедическим матрасом для ежедневного использования купить
  - диван-кровать с ортопедическим матрасом для ежедневного использования недорого
  - диван-кровать с ортопедическим матрасом для ежедневного использования цена
  - купить диван-кровать с ортопедическим матрасом для ежедневного использования
  - недорого диван-кровать с ортопедическим матрасом для ежедневного использования
  - цена диван-кровать с ортопедическим матрасом для ежедневного использования
  - диван-кровать с ортопедическим матрасом для ежедневного использования
  - акция диван-кровать с ортопедическим матрасом для ежедневного использования
  - диван-кровать с ортопедическим матрасом для ежедневного использования акция
  - диван-кровать с ортопедическим матрасом для ежедневного использования распродажа
  - распродажа диван-кровать с ортопедическим матрасом для ежедневного использования
  - в москве диван-кровать с ортопедическим матрасом для ежедневного использования
  - диван-кровать с ортопедическим матрасом для ежедневного использования в москве
  - диван-кровать с ортопедическим матрасом для ежедневного использования с доставкой
  - с доставкой диван-кровать с ортопедическим матрасом для ежедневного использования

### Диваны для сна с независимым пружинным блоком → Создать  (priority 0.437, mode mixed, confidence 0.5)
- intent: **transactional**, page: `/catalog/divany-dlya-sna-s-nezavisimym-pruzhinnym-blokom/`
- факторы: {'search_volume': 0.0, 'business_value': 1.0, 'ranking_opportunity': 0.7, 'intent_match': 1.0, 'trend_growth': 0.5, 'content_gap': 1.0, 'keyword_difficulty': 0.3, 'cannibalization_risk': 0.96}
- источники: {'search_volume': 'real', 'business_value': 'config:intent_map', 'keyword_difficulty': 'proxy:label_length', 'ranking_opportunity': 'derived:1-kd', 'intent_match': 'config:intent_map', 'trend_growth': 'unknown:default_0.5', 'content_gap': 'derived:action', 'cannibalization_risk': 'computed:embedding_overlap'}
- page_similarity (matched existing): 0.000; cannibal_risk: 0.964
- gap: **new**; competitors: unknown
- новые запросы: диван для сна с независимым пружинным блоком купить, диван для сна с независимым пружинным блоком недорого, диван для сна с независимым пружинным блоком цена, купить диван для сна с независимым пружинным блоком, недорого диван для сна с независимым пружинным блоком, самый удобный диван для сна на каждый день, цена диван для сна с независимым пружинным блоком, диван для сна на каждый день купить, диван для сна на каждый день недорого, диван для сна на каждый день цена
- запросы:
  - диван для сна с независимым пружинным блоком купить
  - диван для сна с независимым пружинным блоком недорого
  - диван для сна с независимым пружинным блоком цена
  - купить диван для сна с независимым пружинным блоком
  - недорого диван для сна с независимым пружинным блоком
  - самый удобный диван для сна на каждый день
  - цена диван для сна с независимым пружинным блоком
  - диван для сна на каждый день купить
  - диван для сна на каждый день недорого
  - диван для сна на каждый день цена
  - диван для сна с независимым пружинным блоком

### Диваны-кровати трансформеры → Создать  (priority 0.410, mode mixed, confidence 0.38)
- intent: **transactional**, page: `/catalog/divany-krovati-transformery/`
- факторы: {'search_volume': 0.39, 'business_value': 1.0, 'ranking_opportunity': 0.35, 'intent_match': 1.0, 'trend_growth': 0.5, 'content_gap': 1.0, 'keyword_difficulty': 0.65, 'cannibalization_risk': 0.85}
- источники: {'search_volume': 'proxy:cluster_size', 'business_value': 'config:intent_map', 'keyword_difficulty': 'proxy:label_length', 'ranking_opportunity': 'derived:1-kd', 'intent_match': 'config:intent_map', 'trend_growth': 'unknown:default_0.5', 'content_gap': 'derived:action', 'cannibalization_risk': 'computed:embedding_overlap'}
- page_similarity (matched existing): 0.000; cannibal_risk: 0.853
- gap: **shifted** vs prev `Диваны-кровати трансформеры`; new 4, lost 2
- новые запросы: в москве диван-кровать трансформер с ортопедическим матрасом, диван кровать трансформер с ортопедическим матрасом купить, диван-кровать трансформер с ортопедическим матрасом в москве, диван-кровать трансформер с ортопедическим матрасом с доставкой
- потерянные: диван-кровать трансформер с ортопедическим матрасом, цена диван кровать трансформер
- запросы:
  - в москве диван-кровать трансформер с ортопедическим матрасом
  - диван-кровать трансформер с ортопедическим матрасом в москве
  - диван кровать трансформер с ортопедическим матрасом купить
  - диван-кровать трансформер с ортопедическим матрасом с доставкой

### Диваны купить дешево → Создать  (priority 0.404, mode mixed, confidence 0.38)
- intent: **transactional**, page: `/catalog/divany-kupit-deshevo/`
- факторы: {'search_volume': 0.1, 'business_value': 1.0, 'ranking_opportunity': 0.55, 'intent_match': 1.0, 'trend_growth': 0.5, 'content_gap': 1.0, 'keyword_difficulty': 0.45, 'cannibalization_risk': 0.93}
- источники: {'search_volume': 'proxy:cluster_size', 'business_value': 'config:intent_map', 'keyword_difficulty': 'proxy:label_length', 'ranking_opportunity': 'derived:1-kd', 'intent_match': 'config:intent_map', 'trend_growth': 'unknown:default_0.5', 'content_gap': 'derived:action', 'cannibalization_risk': 'computed:embedding_overlap'}
- page_similarity (matched existing): 0.000; cannibal_risk: 0.934
- gap: **new**; competitors: unknown
- новые запросы: диван купить в москве дешево от производителя распродажа
- запросы:
  - диван купить в москве дешево от производителя распродажа

### Диваны от производителя → Создать  (priority 0.404, mode mixed, confidence 0.38)
- intent: **transactional**, page: `/catalog/divany-ot-proizvoditelya/`
- факторы: {'search_volume': 0.1, 'business_value': 1.0, 'ranking_opportunity': 0.55, 'intent_match': 1.0, 'trend_growth': 0.5, 'content_gap': 1.0, 'keyword_difficulty': 0.45, 'cannibalization_risk': 0.94}
- источники: {'search_volume': 'proxy:cluster_size', 'business_value': 'config:intent_map', 'keyword_difficulty': 'proxy:label_length', 'ranking_opportunity': 'derived:1-kd', 'intent_match': 'config:intent_map', 'trend_growth': 'unknown:default_0.5', 'content_gap': 'derived:action', 'cannibalization_risk': 'computed:embedding_overlap'}
- page_similarity (matched existing): 0.000; cannibal_risk: 0.937
- gap: **new**; competitors: unknown
- новые запросы: купить диван от производителя с доставкой по россии
- запросы:
  - купить диван от производителя с доставкой по россии

### Акции на диваны → Создать  (priority 0.402, mode mixed, confidence 0.38)
- intent: **transactional**, page: `/catalog/aktsii-na-divany/`
- факторы: {'search_volume': 0.1, 'business_value': 1.0, 'ranking_opportunity': 0.55, 'intent_match': 1.0, 'trend_growth': 0.5, 'content_gap': 1.0, 'keyword_difficulty': 0.45, 'cannibalization_risk': 0.95}
- источники: {'search_volume': 'proxy:cluster_size', 'business_value': 'config:intent_map', 'keyword_difficulty': 'proxy:label_length', 'ranking_opportunity': 'derived:1-kd', 'intent_match': 'config:intent_map', 'trend_growth': 'unknown:default_0.5', 'content_gap': 'derived:action', 'cannibalization_risk': 'computed:embedding_overlap'}
- page_similarity (matched existing): 0.000; cannibal_risk: 0.950
- gap: **shifted** vs prev `Акции на диваны`; new 1, lost 2
- новые запросы: акция купить диван в москве от производителя
- потерянные: акция диваны со скидкой, купить диван акция
- запросы:
  - акция купить диван в москве от производителя

### Диваны Амстердам → Создать  (priority 0.333, mode mixed, confidence 0.38)
- intent: **transactional**, page: `/catalog/divany-amsterdam/`
- факторы: {'search_volume': 0.1, 'business_value': 1.0, 'ranking_opportunity': 0.35, 'intent_match': 1.0, 'trend_growth': 0.5, 'content_gap': 1.0, 'keyword_difficulty': 0.65, 'cannibalization_risk': 0.88}
- источники: {'search_volume': 'proxy:cluster_size', 'business_value': 'config:intent_map', 'keyword_difficulty': 'proxy:label_length', 'ranking_opportunity': 'derived:1-kd', 'intent_match': 'config:intent_map', 'trend_growth': 'unknown:default_0.5', 'content_gap': 'derived:action', 'cannibalization_risk': 'computed:embedding_overlap'}
- page_similarity (matched existing): 0.000; cannibal_risk: 0.876
- gap: **new**; competitors: unknown
- новые запросы: диван амстердам купить в москве дешево от производителя
- запросы:
  - диван амстердам купить в москве дешево от производителя

### Диваны прямые → Создать  (priority 0.321, mode mixed, confidence 0.38)
- intent: **transactional**, page: `/catalog/divany-pryamye/`
- факторы: {'search_volume': 0.1, 'business_value': 1.0, 'ranking_opportunity': 0.35, 'intent_match': 1.0, 'trend_growth': 0.5, 'content_gap': 1.0, 'keyword_difficulty': 0.65, 'cannibalization_risk': 0.95}
- источники: {'search_volume': 'proxy:cluster_size', 'business_value': 'config:intent_map', 'keyword_difficulty': 'proxy:label_length', 'ranking_opportunity': 'derived:1-kd', 'intent_match': 'config:intent_map', 'trend_growth': 'unknown:default_0.5', 'content_gap': 'derived:action', 'cannibalization_risk': 'computed:embedding_overlap'}
- page_similarity (matched existing): 0.000; cannibal_risk: 0.953
- gap: **shifted** vs prev `Диваны-кровати`; new 1, lost 1
- новые запросы: купить диван прямой в москве от производителя хорошего качества
- потерянные: купить диван кровать
- запросы:
  - купить диван прямой в москве от производителя хорошего качества

### Диваны-книжки → Создать  (priority 0.258, mode mixed, confidence 0.38)
- intent: **transactional**, page: `/catalog/divany-knizhka/`
- факторы: {'search_volume': 0.1, 'business_value': 1.0, 'ranking_opportunity': 0.15, 'intent_match': 1.0, 'trend_growth': 0.5, 'content_gap': 1.0, 'keyword_difficulty': 0.85, 'cannibalization_risk': 0.84}
- источники: {'search_volume': 'proxy:cluster_size', 'business_value': 'config:intent_map', 'keyword_difficulty': 'proxy:label_length', 'ranking_opportunity': 'derived:1-kd', 'intent_match': 'config:intent_map', 'trend_growth': 'unknown:default_0.5', 'content_gap': 'derived:action', 'cannibalization_risk': 'computed:embedding_overlap'}
- page_similarity (matched existing): 0.000; cannibal_risk: 0.842
- gap: **new**; competitors: unknown
- новые запросы: купить диван книжка недорого в москве от производителя распродажа
- запросы:
  - купить диван книжка недорого в москве от производителя распродажа
