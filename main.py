#!/usr/bin/env python3
"""Travel agent CLI: find optimal flight + hotel combinations via Amadeus API."""
import argparse
import logging
import sys

from rich.console import Console

from travel_agent.config import DEFAULT_CONSTRAINTS
from travel_agent.date_utils import generate_date_pairs
from travel_agent.display import render_results
from travel_agent.search import search_combinations

console = Console()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="travel-agent",
        description="Find the best flight + hotel combinations using the Amadeus API.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging (API calls, skipped results, etc.).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        metavar="N",
        help="Number of top combinations to display (default: 10).",
    )
    return parser


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    constraints = DEFAULT_CONSTRAINTS
    console.print(
        f"\n[bold]🔍  Searching {constraints.origin} → {constraints.destination}[/bold]"
    )
    console.print(
        f"Window  : {constraints.start_date} – {constraints.end_date}\n"
        f"Stay    : {constraints.min_nights}–{constraints.max_nights} nights\n"
        f"Budget  : {constraints.max_budget_chf:,.0f} CHF\n"
        f"Hotels  : minimum {constraints.min_hotel_stars}★\n"
        f"Arrive by: {constraints.must_arrive_by} (hard constraint)\n"
    )

    date_pairs = list(generate_date_pairs(constraints))
    console.print(
        f"Evaluating [bold]{len(date_pairs)}[/bold] date combinations...\n"
    )

    combinations = search_combinations(constraints, date_pairs)
    render_results(combinations, top_n=args.top)
    return 0


if __name__ == "__main__":
    sys.exit(main())
