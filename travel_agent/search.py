"""Flight and hotel search logic, result dataclasses, and combination ranker."""
import logging
from dataclasses import dataclass
from datetime import date
from typing import List, Optional, Tuple

from amadeus import Client, ResponseError

from .amadeus_client import call_with_retry, get_client
from .config import TravelConstraints

logger = logging.getLogger(__name__)

# Maximum hotel IDs to query in a single hotel-offers request.
_MAX_HOTEL_IDS = 20


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class FlightResult:
    """Cheapest outbound + return flight pair for a given date combination."""

    airline: str
    flight_number: str  # carrier code + flight number of the outbound leg
    outbound_price: float
    return_price: float

    @property
    def total_price(self) -> float:
        return self.outbound_price + self.return_price


@dataclass
class HotelResult:
    """Cheapest hotel offer for a given stay period."""

    name: str
    stars: int
    price: float


@dataclass
class Combination:
    """A complete flight + hotel combination for a specific date pair."""

    outbound_date: date
    return_date: date
    nights: int
    flight: FlightResult
    hotel: HotelResult
    violates_constraint: bool

    @property
    def total_price(self) -> float:
        return self.flight.total_price + self.hotel.price


# ---------------------------------------------------------------------------
# Internal search helpers
# ---------------------------------------------------------------------------


def _cheapest_flight(
    client: Client,
    origin: str,
    destination: str,
    dep_date: str,
) -> Optional[Tuple[str, str, float]]:
    """Return ``(airline, flight_number, price_chf)`` for the cheapest offer.

    Returns ``None`` when no results are available or the API call fails.
    """
    try:
        response = call_with_retry(
            client.shopping.flight_offers_search.get,
            originLocationCode=origin,
            destinationLocationCode=destination,
            departureDate=dep_date,
            adults=1,
            currencyCode="CHF",
            max=5,
        )
    except ResponseError as err:
        logger.debug(
            "Flight search failed (%s→%s on %s): %s", origin, destination, dep_date, err
        )
        return None

    if not response or not response.data:
        return None

    offers = sorted(response.data, key=lambda o: float(o["price"]["grandTotal"]))
    best = offers[0]
    seg = best["itineraries"][0]["segments"][0]
    airline = seg["carrierCode"]
    number = f"{airline}{seg['number']}"
    price = float(best["price"]["grandTotal"])
    return airline, number, price


def _cheapest_hotel(
    client: Client,
    city: str,
    check_in: str,
    check_out: str,
    min_stars: int,
) -> Optional[HotelResult]:
    """Return the cheapest hotel in *city* that meets the star requirement.

    Returns ``None`` when no qualifying results are found or the API fails.
    """
    # Step 1: obtain hotel IDs for the city, filtered by minimum star rating.
    ratings = ",".join(str(s) for s in range(min_stars, 6))
    try:
        hotel_list = call_with_retry(
            client.reference_data.locations.hotels.by_city.get,
            cityCode=city,
            ratings=ratings,
        )
    except ResponseError as err:
        logger.debug("Hotel list failed (%s, ratings=%s): %s", city, ratings, err)
        return None

    if not hotel_list or not hotel_list.data:
        return None

    hotel_ids = ",".join(h["hotelId"] for h in hotel_list.data[:_MAX_HOTEL_IDS])

    # Step 2: fetch offers for those hotels.
    try:
        offers_resp = call_with_retry(
            client.shopping.hotel_offers_search.get,
            hotelIds=hotel_ids,
            checkInDate=check_in,
            checkOutDate=check_out,
            adults=1,
            roomQuantity=1,
            currencyCode="CHF",
        )
    except ResponseError as err:
        logger.debug(
            "Hotel offers failed (%s, %s–%s): %s", city, check_in, check_out, err
        )
        return None

    if not offers_resp or not offers_resp.data:
        return None

    best: Optional[HotelResult] = None
    best_price = float("inf")

    for item in offers_resp.data:
        hotel_info = item.get("hotel", {})
        offers = item.get("offers", [])
        if not offers:
            continue
        stars_raw = hotel_info.get("rating", "0") or "0"
        try:
            stars = int(stars_raw)
        except ValueError:
            stars = 0
        if stars < min_stars:
            continue
        price = float(offers[0]["price"]["total"])
        if price < best_price:
            best_price = price
            best = HotelResult(
                name=hotel_info.get("name", "Unknown Hotel"),
                stars=stars,
                price=price,
            )

    return best


# ---------------------------------------------------------------------------
# Public search entry point
# ---------------------------------------------------------------------------


def search_combinations(
    constraints: TravelConstraints,
    date_pairs,
) -> List[Combination]:
    """Search every date pair and return all combinations within budget.

    :param constraints: The travel constraints to apply.
    :param date_pairs: Iterable of ``(outbound, return, nights, violates)``
        tuples as produced by :func:`~travel_agent.date_utils.generate_date_pairs`.
    :returns: Combinations sorted by total price (ascending).
    """
    client = get_client()
    results: List[Combination] = []

    for outbound_date, return_date, nights, violates in date_pairs:
        out_str = outbound_date.strftime("%Y-%m-%d")
        ret_str = return_date.strftime("%Y-%m-%d")

        # --- Outbound flight ---
        out_flight = _cheapest_flight(
            client, constraints.origin, constraints.destination, out_str
        )
        if out_flight is None:
            logger.debug("No outbound flight found for %s.", out_str)
            continue

        # --- Return flight ---
        ret_flight = _cheapest_flight(
            client, constraints.destination, constraints.origin, ret_str
        )
        if ret_flight is None:
            logger.debug("No return flight found for %s.", ret_str)
            continue

        # --- Hotel ---
        hotel = _cheapest_hotel(
            client,
            constraints.destination,
            out_str,
            ret_str,
            constraints.min_hotel_stars,
        )
        if hotel is None:
            logger.debug("No qualifying hotel for %s–%s.", out_str, ret_str)
            continue

        flight = FlightResult(
            airline=out_flight[0],
            flight_number=out_flight[1],
            outbound_price=out_flight[2],
            return_price=ret_flight[2],
        )
        combo = Combination(
            outbound_date=outbound_date,
            return_date=return_date,
            nights=nights,
            flight=flight,
            hotel=hotel,
            violates_constraint=violates,
        )

        if combo.total_price <= constraints.max_budget_chf:
            results.append(combo)

    return sorted(results, key=lambda c: c.total_price)
