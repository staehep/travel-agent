"""Rich-based table renderer for flight + hotel combinations."""
from typing import List

from rich import box
from rich.console import Console
from rich.table import Table

from .search import Combination

console = Console()


def render_results(combinations: List[Combination], top_n: int = 10) -> None:
    """Print a ranked comparison table of *combinations* to the terminal.

    :param combinations: Sorted list of :class:`~travel_agent.search.Combination`
        objects (cheapest first).
    :param top_n: Maximum number of rows to display (default 10).
    """
    if not combinations:
        console.print(
            "[bold yellow]No combinations found within the budget. "
            "Try relaxing the constraints.[/bold yellow]"
        )
        return

    table = Table(
        title="✈️  Top Flight + Hotel Combinations",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        highlight=True,
    )
    table.add_column("Rank", style="bold", justify="right", no_wrap=True)
    table.add_column("Outbound", justify="center", no_wrap=True)
    table.add_column("Return", justify="center", no_wrap=True)
    table.add_column("Nights", justify="right", no_wrap=True)
    table.add_column("Flight", justify="center", no_wrap=True)
    table.add_column("Hotel", justify="left")
    table.add_column("Stars", justify="center", no_wrap=True)
    table.add_column("F-CHF", justify="right", no_wrap=True)
    table.add_column("H-CHF", justify="right", no_wrap=True)
    table.add_column("Total CHF", justify="right", style="bold green", no_wrap=True)

    shown = combinations[:top_n]
    has_violations = any(c.violates_constraint for c in shown)

    for rank, combo in enumerate(shown, start=1):
        row_style = "bold red" if combo.violates_constraint else ""
        stars_str = "★" * combo.hotel.stars
        table.add_row(
            str(rank),
            combo.outbound_date.strftime("%d.%m"),
            combo.return_date.strftime("%d.%m"),
            str(combo.nights),
            combo.flight.flight_number,
            combo.hotel.name,
            stars_str,
            f"{combo.flight.total_price:.0f}",
            f"{combo.hotel.price:.0f}",
            f"{combo.total_price:.0f}",
            style=row_style,
        )

    console.print(table)

    if has_violations:
        console.print(
            "[bold red]⚠  Red rows violate the hard arrival constraint "
            "(outbound date is after must-arrive-by deadline).[/bold red]"
        )
