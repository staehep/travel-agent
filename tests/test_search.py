"""Unit tests for search dataclasses and combination-building logic."""
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from travel_agent.config import TravelConstraints
from travel_agent.search import (
    Combination,
    FlightResult,
    HotelResult,
    _cheapest_flight,
    _cheapest_hotel,
    search_combinations,
)


# ---------------------------------------------------------------------------
# FlightResult
# ---------------------------------------------------------------------------


def test_flight_result_total_price():
    f = FlightResult(
        airline="VY",
        flight_number="VY1234",
        outbound_price=189.0,
        return_price=145.0,
    )
    assert f.total_price == pytest.approx(334.0)


# ---------------------------------------------------------------------------
# Combination
# ---------------------------------------------------------------------------


def test_combination_total_price():
    flight = FlightResult("VY", "VY1234", outbound_price=189.0, return_price=145.0)
    hotel = HotelResult(name="Hotel Arts", stars=5, price=720.0)
    combo = Combination(
        outbound_date=date(2025, 5, 12),
        return_date=date(2025, 5, 20),
        nights=8,
        flight=flight,
        hotel=hotel,
        violates_constraint=False,
    )
    assert combo.total_price == pytest.approx(1054.0)


# ---------------------------------------------------------------------------
# _cheapest_flight (mocked)
# ---------------------------------------------------------------------------


def _make_flight_response(carrier="VY", number="1234", price="189.00"):
    return MagicMock(
        data=[
            {
                "itineraries": [
                    {"segments": [{"carrierCode": carrier, "number": number}]}
                ],
                "price": {"grandTotal": price},
            }
        ]
    )


def test_cheapest_flight_happy_path():
    client = MagicMock()
    client.shopping.flight_offers_search.get.return_value = _make_flight_response()

    with patch("travel_agent.search.call_with_retry", side_effect=lambda f, *a, **kw: f(*a, **kw)):
        result = _cheapest_flight(client, "ZRH", "BCN", "2025-05-12")

    assert result is not None
    airline, number, price = result
    assert airline == "VY"
    assert number == "VY1234"
    assert price == pytest.approx(189.0)


def test_cheapest_flight_no_data():
    client = MagicMock()
    client.shopping.flight_offers_search.get.return_value = MagicMock(data=[])

    with patch("travel_agent.search.call_with_retry", side_effect=lambda f, *a, **kw: f(*a, **kw)):
        result = _cheapest_flight(client, "ZRH", "BCN", "2025-05-12")

    assert result is None


def test_cheapest_flight_api_error():
    from amadeus import ResponseError

    client = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.parsed = False
    err = ResponseError(mock_response)

    with patch("travel_agent.search.call_with_retry", side_effect=err):
        result = _cheapest_flight(client, "ZRH", "BCN", "2025-05-12")

    assert result is None


# ---------------------------------------------------------------------------
# _cheapest_hotel (mocked)
# ---------------------------------------------------------------------------


def _make_hotel_list_response(hotel_ids=("BCNHOTEL1",)):
    return MagicMock(data=[{"hotelId": hid} for hid in hotel_ids])


def _make_hotel_offers_response(name="Hotel Arts", rating="5", price="720.00"):
    return MagicMock(
        data=[
            {
                "hotel": {"name": name, "rating": rating},
                "offers": [{"price": {"total": price}}],
            }
        ]
    )


def test_cheapest_hotel_happy_path():
    client = MagicMock()

    responses = iter(
        [_make_hotel_list_response(), _make_hotel_offers_response()]
    )

    with patch(
        "travel_agent.search.call_with_retry",
        side_effect=lambda f, *a, **kw: next(responses),
    ):
        hotel = _cheapest_hotel(client, "BCN", "2025-05-12", "2025-05-20", min_stars=3)

    assert hotel is not None
    assert hotel.name == "Hotel Arts"
    assert hotel.stars == 5
    assert hotel.price == pytest.approx(720.0)


def test_cheapest_hotel_below_min_stars_filtered():
    client = MagicMock()

    # Hotel has only 2 stars; min_stars=3 should discard it.
    responses = iter(
        [
            _make_hotel_list_response(),
            _make_hotel_offers_response(rating="2", price="100.00"),
        ]
    )

    with patch(
        "travel_agent.search.call_with_retry",
        side_effect=lambda f, *a, **kw: next(responses),
    ):
        hotel = _cheapest_hotel(client, "BCN", "2025-05-12", "2025-05-20", min_stars=3)

    assert hotel is None


def test_cheapest_hotel_no_list_data():
    client = MagicMock()

    with patch(
        "travel_agent.search.call_with_retry",
        return_value=MagicMock(data=[]),
    ):
        hotel = _cheapest_hotel(client, "BCN", "2025-05-12", "2025-05-20", min_stars=3)

    assert hotel is None


# ---------------------------------------------------------------------------
# search_combinations (mocked end-to-end)
# ---------------------------------------------------------------------------


def test_search_combinations_budget_filter():
    """Combinations above the budget ceiling must be excluded."""
    from datetime import date

    constraints = TravelConstraints(
        start_date=date(2025, 5, 10),
        end_date=date(2025, 5, 16),
        must_arrive_by=date(2025, 5, 15),
        min_nights=5,
        max_nights=6,
        max_budget_chf=500.0,  # very tight budget
        min_hotel_stars=3,
    )

    # Flight: 200 out + 200 return = 400; hotel: 200 => total 600 > 500 CHF => excluded.
    def fake_cheapest_flight(client, origin, dest, dep_date):
        return ("VY", "VY1234", 200.0)

    def fake_cheapest_hotel(client, city, check_in, check_out, min_stars):
        return HotelResult(name="Pricey Hotel", stars=4, price=200.0)

    with (
        patch("travel_agent.search.get_client", return_value=MagicMock()),
        patch("travel_agent.search._cheapest_flight", side_effect=fake_cheapest_flight),
        patch("travel_agent.search._cheapest_hotel", side_effect=fake_cheapest_hotel),
    ):
        results = search_combinations(
            constraints,
            [(date(2025, 5, 10), date(2025, 5, 15), 5, False)],
        )

    assert results == []


def test_search_combinations_sorted_by_price():
    """Results must be sorted cheapest first."""
    from datetime import date, timedelta

    constraints = TravelConstraints(
        start_date=date(2025, 5, 10),
        end_date=date(2025, 5, 25),
        must_arrive_by=date(2025, 5, 20),
        min_nights=5,
        max_nights=5,
        max_budget_chf=5000.0,
        min_hotel_stars=3,
    )

    # Two date pairs: first is more expensive, second is cheaper.
    pair1 = (date(2025, 5, 10), date(2025, 5, 15), 5, False)
    pair2 = (date(2025, 5, 11), date(2025, 5, 16), 5, False)

    def fake_flight(client, origin, dest, dep_date):
        if dep_date == "2025-05-10" or dep_date == "2025-05-15":
            return ("IB", "IB1111", 300.0)
        return ("VY", "VY2222", 100.0)

    def fake_hotel(client, city, check_in, check_out, min_stars):
        if check_in == "2025-05-10":
            return HotelResult("Expensive Hotel", 4, 800.0)
        return HotelResult("Cheap Hotel", 3, 200.0)

    with (
        patch("travel_agent.search.get_client", return_value=MagicMock()),
        patch("travel_agent.search._cheapest_flight", side_effect=fake_flight),
        patch("travel_agent.search._cheapest_hotel", side_effect=fake_hotel),
    ):
        results = search_combinations(constraints, [pair1, pair2])

    assert len(results) == 2
    assert results[0].total_price <= results[1].total_price
    assert results[0].hotel.name == "Cheap Hotel"
