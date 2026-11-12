# travel-agent

CLI agent to find optimal **flight + hotel** combinations via the [Amadeus API](https://developers.amadeus.com).

## Features

- Generates all valid outbound/return date pairs within a configurable travel window
- Calls the Amadeus API for flight offers (ZRH → BCN outbound, BCN → ZRH return)
- Fetches hotel offers in the destination city, filtered by minimum star rating
- Ranks combinations by **total price** (flight + hotel)
- Displays a Rich-formatted comparison table in the terminal
- Flags combinations that violate the hard arrival constraint in **red**
- Retries automatically on Amadeus API rate-limit (HTTP 429) errors

## Requirements

- Python 3.11+
- Amadeus test API credentials ([register for free](https://developers.amadeus.com/self-service))

## Quick start

```bash
# 1. Clone and enter the project
git clone https://github.com/staehep/travel-agent.git
cd travel-agent

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up credentials
cp .env.example .env
# Edit .env and fill in AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET

# 4. Run
python main.py
```

## Configuration

Travel constraints are hardcoded in `travel_agent/config.py` via the `TravelConstraints` dataclass:

| Parameter         | Default        | Description                            |
|-------------------|----------------|----------------------------------------|
| `origin`          | `ZRH`          | Departure airport IATA code            |
| `destination`     | `BCN`          | Destination airport IATA code          |
| `start_date`      | `2025-05-10`   | Earliest outbound departure date       |
| `end_date`        | `2025-05-25`   | Latest return date                     |
| `must_arrive_by`  | `2025-05-15`   | Hard arrival deadline (violations shown in red) |
| `min_nights`      | `5`            | Minimum nights in destination          |
| `max_nights`      | `10`           | Maximum nights in destination          |
| `max_budget_chf`  | `2000`         | Maximum total budget (CHF)             |
| `min_hotel_stars` | `3`            | Minimum hotel star rating              |

## CLI options

```
python main.py [--debug] [--top N]

  --debug   Enable debug logging (API calls, skipped results, etc.)
  --top N   Show top N combinations (default: 10)
```

## Example output

```
✈️  Top Flight + Hotel Combinations
╭──────┬──────────┬────────┬────────┬────────┬───────────┬───────┬───────┬───────┬───────────╮
│ Rank │ Outbound │ Return │ Nights │ Flight │ Hotel     │ Stars │ F-CHF │ H-CHF │ Total CHF │
├──────┼──────────┼────────┼────────┼────────┼───────────┼───────┼───────┼───────┼───────────┤
│    1 │  12.05   │ 20.05  │      8 │ VY1234 │ Hotel Arts│ ★★★★★ │   334 │   720 │      1054 │
╰──────┴──────────┴────────┴────────┴────────┴───────────┴───────┴───────┴───────┴───────────╯
```

## Running tests

```bash
pip install pytest
pytest tests/ -v
```

## Project structure

```
travel-agent/
├── travel_agent/
│   ├── config.py          # TravelConstraints dataclass (hardcoded defaults)
│   ├── date_utils.py      # Date-pair generator
│   ├── amadeus_client.py  # Amadeus client factory + retry helper
│   ├── search.py          # Flight/hotel search + combination ranker
│   └── display.py         # Rich table renderer
├── tests/
│   ├── test_date_utils.py
│   ├── test_search.py
│   └── test_display.py
├── main.py                # CLI entry point
├── requirements.txt
└── .env.example
```
