"""Unit tests for travel_agent.display.render_results."""
from datetime import date
from io import StringIO

import pytest
from rich.console import Console

from travel_agent.display import render_results
from travel_agent.search import Combination, FlightResult, HotelResult


def _make_combo(
    outbound=date(2025, 5, 12),
    return_date=date(2025, 5, 20),
    nights=8,
    airline="VY",
    flight_number="VY1234",
    out_price=189.0,
    ret_price=145.0,
    hotel_name="Hotel Arts",
    hotel_stars=5,
    hotel_price=720.0,
    violates=False,
) -> Combination:
    return Combination(
        outbound_date=outbound,
        return_date=return_date,
        nights=nights,
        flight=FlightResult(airline, flight_number, out_price, ret_price),
        hotel=HotelResult(hotel_name, hotel_stars, hotel_price),
        violates_constraint=violates,
    )


def _render_to_string(combinations, top_n=10) -> str:
    buf = StringIO()
    console = Console(file=buf, highlight=False, markup=False, width=120)
    # Temporarily replace the module-level console.
    import travel_agent.display as display_mod
    original = display_mod.console
    display_mod.console = console
    try:
        render_results(combinations, top_n=top_n)
    finally:
        display_mod.console = original
    return buf.getvalue()


def test_empty_combinations_shows_message():
    output = _render_to_string([])
    assert "No combinations found" in output


def test_table_contains_expected_columns():
    combos = [_make_combo()]
    output = _render_to_string(combos)
    for header in ("Rank", "Outbound", "Return", "Nights", "Flight", "Hotel", "F-CHF", "H-CHF", "Total"):
        assert header in output, f"Column '{header}' missing from table output"


def test_table_rows_show_correct_data():
    combo = _make_combo(
        outbound=date(2025, 5, 12),
        return_date=date(2025, 5, 20),
        nights=8,
        flight_number="VY1234",
        hotel_name="Hotel Arts",
        out_price=189.0,
        ret_price=145.0,
        hotel_price=720.0,
    )
    output = _render_to_string([combo])
    assert "12.05" in output
    assert "20.05" in output
    assert "8" in output
    assert "VY1234" in output
    assert "Hotel Arts" in output


def test_top_n_limits_rows():
    combos = [_make_combo() for _ in range(15)]
    output = _render_to_string(combos, top_n=5)
    # Row "5" must appear, row "6" must not appear as a rank column.
    lines = output.splitlines()
    rank_values = []
    for line in lines:
        for token in line.split():
            try:
                rank_values.append(int(token))
            except ValueError:
                pass
    assert 5 in rank_values
    assert 6 not in rank_values


def test_violation_note_shown_when_relevant():
    violating = _make_combo(violates=True)
    output = _render_to_string([violating])
    assert "hard arrival deadline" in output or "constraint" in output.lower()


def test_no_violation_note_when_not_needed():
    clean = _make_combo(violates=False)
    output = _render_to_string([clean])
    assert "deadline" not in output
