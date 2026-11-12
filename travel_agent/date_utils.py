"""Utility functions for generating valid (outbound, return) date pairs."""
from datetime import date, timedelta
from typing import Iterator, Tuple

from .config import TravelConstraints


def generate_date_pairs(
    constraints: TravelConstraints,
) -> Iterator[Tuple[date, date, int, bool]]:
    """Yield all valid ``(outbound, return, nights, violates_constraint)`` tuples.

    A pair is valid when:
    - ``outbound`` is within ``[start_date, end_date]``
    - ``return == outbound + nights`` where ``min_nights <= nights <= max_nights``
    - ``return <= end_date``

    The ``violates_constraint`` flag is ``True`` when ``outbound`` is later than
    ``must_arrive_by`` (the hard arrival deadline).
    """
    current = constraints.start_date
    while current <= constraints.end_date:
        for nights in range(constraints.min_nights, constraints.max_nights + 1):
            return_date = current + timedelta(days=nights)
            if return_date > constraints.end_date:
                break
            violates = current > constraints.must_arrive_by
            yield current, return_date, nights, violates
        current += timedelta(days=1)
