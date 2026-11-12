"""Unit tests for travel_agent.date_utils.generate_date_pairs."""
from datetime import date

import pytest

from travel_agent.config import TravelConstraints
from travel_agent.date_utils import generate_date_pairs


def _constraints(**overrides) -> TravelConstraints:
    defaults = dict(
        origin="ZRH",
        destination="BCN",
        start_date=date(2025, 5, 10),
        end_date=date(2025, 5, 25),
        must_arrive_by=date(2025, 5, 15),
        min_nights=5,
        max_nights=10,
        max_budget_chf=2000.0,
        min_hotel_stars=3,
    )
    defaults.update(overrides)
    return TravelConstraints(**defaults)


def test_pairs_are_within_window():
    c = _constraints()
    for out, ret, nights, _ in generate_date_pairs(c):
        assert c.start_date <= out <= c.end_date
        assert ret <= c.end_date
        assert c.min_nights <= nights <= c.max_nights


def test_nights_is_correct():
    c = _constraints()
    for out, ret, nights, _ in generate_date_pairs(c):
        assert (ret - out).days == nights


def test_violates_constraint_flag():
    c = _constraints(must_arrive_by=date(2025, 5, 12))
    for out, ret, nights, violates in generate_date_pairs(c):
        expected = out > date(2025, 5, 12)
        assert violates == expected, f"Wrong flag for outbound {out}"


def test_no_pairs_when_window_too_small():
    # A 3-day window with min_nights=5 yields nothing.
    c = _constraints(
        start_date=date(2025, 5, 10),
        end_date=date(2025, 5, 12),
        min_nights=5,
        max_nights=10,
    )
    pairs = list(generate_date_pairs(c))
    assert pairs == []


def test_exact_single_pair():
    # start_date=10, end_date=15, min=max=5 => exactly one pair: (10, 15)
    c = _constraints(
        start_date=date(2025, 5, 10),
        end_date=date(2025, 5, 15),
        min_nights=5,
        max_nights=5,
    )
    pairs = list(generate_date_pairs(c))
    assert len(pairs) == 1
    out, ret, nights, _ = pairs[0]
    assert out == date(2025, 5, 10)
    assert ret == date(2025, 5, 15)
    assert nights == 5


def test_all_pairs_count():
    # Window: 10–20 (11 days), nights: 5–7
    # Outbound can be 10..15 (max: 20 - 5 = 15).
    # 10: nights 5,6,7 -> returns 15,16,17 (all <=20) => 3
    # 11: nights 5,6,7 -> 16,17,18 => 3
    # 12: nights 5,6,7 -> 17,18,19 => 3
    # 13: nights 5,6,7 -> 18,19,20 => 3
    # 14: nights 5,6 -> 19,20; nights 7 -> 21 > 20 => 2
    # 15: nights 5 -> 20; nights 6 -> 21 > 20 => 1
    # 16..20: nights 5 -> 21 > 20 => 0
    # total = 3+3+3+3+2+1 = 15
    c = _constraints(
        start_date=date(2025, 5, 10),
        end_date=date(2025, 5, 20),
        min_nights=5,
        max_nights=7,
    )
    pairs = list(generate_date_pairs(c))
    assert len(pairs) == 15
