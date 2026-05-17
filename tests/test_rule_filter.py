"""Rule-filter тесты — детерминированная чистка по бизнес-контексту."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.clean import rule_filter


BIZ = {
    "prohibited_brands": ["ами мебель", "ikea", "икеа"],
    "blocked_regions": ["минск", "спб", "бишкек"],
    "marketplaces": ["куфар", "wildberries", "авито"],
    "freebie_triggers": ["бесплатно"],
    "region_substrings": ["москва", "московская"],
}


def test_prohibited_brand_dropped():
    kept, dropped = rule_filter(["купить угловой диван", "акция на диваны в ами мебель"], BIZ)
    assert "купить угловой диван" in kept
    reasons = [d.reason for d in dropped]
    assert any("prohibited brand: ами мебель" in r for r in reasons)


def test_marketplace_dropped():
    _, dropped = rule_filter(["диван на wildberries", "диван куфар"], BIZ)
    reasons = [d.reason for d in dropped]
    assert any("marketplace: wildberries" in r for r in reasons)
    assert any("marketplace: куфар" in r for r in reasons)


def test_blocked_region_dropped():
    _, dropped = rule_filter(["диван купить минск", "диван спб", "диван бишкек"], BIZ)
    assert len(dropped) == 3
    assert all("blocked region" in d.reason for d in dropped)


def test_freebie_dropped():
    _, dropped = rule_filter(["диван бесплатно"], BIZ)
    assert any("freebie trigger" in d.reason for d in dropped)


def test_allowed_region_passes():
    kept, dropped = rule_filter(["купить диван в москве", "диван московская область"], BIZ)
    assert len(kept) == 2
    assert not dropped


def test_geo_outside_allowed_dropped():
    # запрос явно геопривязан, но не в allowed_regions → drop
    _, dropped = rule_filter(["купить диван в харькове"], BIZ)
    assert any("geo outside" in d.reason for d in dropped)


def test_pure_query_no_geo_passes():
    kept, _ = rule_filter(["купить диван", "угловой диван цена", "диван-кровать"], BIZ)
    assert len(kept) == 3


def test_word_boundary_brand():
    # "ikea" не должен матчиться внутри "ikeaplus"
    kept, dropped = rule_filter(["диван ikeaplus", "купить ikea диван"], BIZ)
    assert "диван ikeaplus" in kept
    assert any("prohibited brand: ikea" in d.reason for d in dropped)
