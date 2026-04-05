"""Amadeus API client factory and retry helper."""
import logging
import os
import time

from amadeus import Client, ResponseError
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def get_client() -> Client:
    """Build and return an authenticated Amadeus ``Client``.

    Reads ``AMADEUS_CLIENT_ID`` and ``AMADEUS_CLIENT_SECRET`` from the
    environment (or from a ``.env`` file in the working directory).
    Exits with a clear message when either variable is missing.
    """
    load_dotenv()
    client_id = os.getenv("AMADEUS_CLIENT_ID")
    client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise SystemExit(
            "ERROR: AMADEUS_CLIENT_ID and/or AMADEUS_CLIENT_SECRET are not set.\n"
            "Copy .env.example to .env and fill in your Amadeus test credentials."
        )
    return Client(client_id=client_id, client_secret=client_secret)


def call_with_retry(func, *args, max_retries: int = 3, **kwargs):
    """Call *func* with exponential back-off on HTTP 429 rate-limit responses.

    Other ``ResponseError`` exceptions are re-raised immediately.

    :param func: Callable to invoke (an Amadeus SDK endpoint method).
    :param max_retries: Maximum number of attempts (default 3).
    :returns: The ``amadeus.Response`` returned by *func*, or ``None`` if
        all retries are exhausted.
    :raises amadeus.ResponseError: For any non-rate-limit API error.
    """
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except ResponseError as err:
            status = getattr(err.response, "status_code", None)
            if status == 429 and attempt < max_retries - 1:
                wait_secs = 2**attempt  # attempt 0→1 s, 1→2 s, 2→4 s
                logger.debug(
                    "Rate-limited (attempt %d/%d); retrying in %ds.",
                    attempt + 1,
                    max_retries,
                    wait_secs,
                )
                time.sleep(wait_secs)
                continue
            raise
    return None  # all retries exhausted without success
