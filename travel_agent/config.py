"""Travel constraints configuration.

Constraints are hardcoded here for now; a CLI prompt can replace them later.
"""
from dataclasses import dataclass, field
from datetime import date


@dataclass
class TravelConstraints:
    """All parameters that govern the search."""

    # Route
    origin: str = "ZRH"
    destination: str = "BCN"

    # Travel window
    start_date: date = field(default_factory=lambda: date(2025, 5, 10))
    end_date: date = field(default_factory=lambda: date(2025, 5, 25))

    # Hard constraint: must have arrived by this date
    must_arrive_by: date = field(default_factory=lambda: date(2025, 5, 15))

    # Stay length
    min_nights: int = 5
    max_nights: int = 10

    # Budget (flight + hotel combined)
    max_budget_chf: float = 2000.0

    # Hotel quality
    min_hotel_stars: int = 3


# Default instance used by the CLI
DEFAULT_CONSTRAINTS = TravelConstraints()
