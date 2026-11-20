"""Row validation: airport list loading, single-row checks, record building."""
import math
import re
from datetime import datetime

# Explicit ASCII character classes on purpose: str.isalnum(), str.isupper()
# and \d accept non-ASCII characters, which the specification forbids.
_FLIGHT_ID_RE = re.compile(r"[A-Za-z0-9]{2,8}")
_AIRPORT_SHAPE_RE = re.compile(r"[A-Z]{3}")
_DATETIME_SHAPE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}")
_DATETIME_FORMAT = "%Y-%m-%d %H:%M"


def parse_datetime(text: str) -> datetime | None:
    """Parse 'YYYY-MM-DD HH:MM' (zero-padded, 24-hour, one space).

    Return a datetime, or None if the text is not exactly in that format
    or is not a real date and time. The shape is checked with a regex first
    because strptime alone also accepts values like '2025-1-5 9:3'.
    """
    if not isinstance(text, str) or not _DATETIME_SHAPE_RE.fullmatch(text):
        return None
    try:
        return datetime.strptime(text, _DATETIME_FORMAT)
    except ValueError:
        return None


def load_airports(path: str) -> set[str]:
    """Read an airport list file and return the set of codes.

    One code per line. Strip whitespace; skip blank lines and lines
    starting with '#'.
    """
    codes = set()
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            code = line.strip()
            if not code or code.startswith("#"):
                continue
            codes.add(code)
    return codes


def _valid_airport(code: str, airports: set[str]) -> bool:
    return _AIRPORT_SHAPE_RE.fullmatch(code) is not None and code in airports


def validate_row(fields: list[str], airports: set[str]) -> str | None:
    """Check one CSV row (fields as returned by csv.reader, not yet stripped).

    Return None if the row is valid, otherwise the error code of the
    FIRST failing check (checks 1-11 in the specification, in order).
    Does not check for duplicates.
    """
    # 1. WRONG_FIELD_COUNT
    if len(fields) != 6:
        return "WRONG_FIELD_COUNT"

    flight_id, origin, destination, departure, arrival, price = (
        f.strip() for f in fields
    )

    # 2. MISSING_FIELD
    if not all((flight_id, origin, destination, departure, arrival, price)):
        return "MISSING_FIELD"

    # 3. INVALID_FLIGHT_ID
    if not _FLIGHT_ID_RE.fullmatch(flight_id):
        return "INVALID_FLIGHT_ID"

    # 4. INVALID_ORIGIN
    if not _valid_airport(origin, airports):
        return "INVALID_ORIGIN"

    # 5. INVALID_DESTINATION
    if not _valid_airport(destination, airports):
        return "INVALID_DESTINATION"

    # 6. SAME_ORIGIN_DESTINATION
    if origin == destination:
        return "SAME_ORIGIN_DESTINATION"

    # 7. INVALID_DEPARTURE
    departure_dt = parse_datetime(departure)
    if departure_dt is None:
        return "INVALID_DEPARTURE"

    # 8. INVALID_ARRIVAL
    arrival_dt = parse_datetime(arrival)
    if arrival_dt is None:
        return "INVALID_ARRIVAL"

    # 9. ARRIVAL_NOT_AFTER_DEPARTURE
    if arrival_dt <= departure_dt:
        return "ARRIVAL_NOT_AFTER_DEPARTURE"

    # 10. INVALID_PRICE
    try:
        price_value = float(price)
    except ValueError:
        return "INVALID_PRICE"
    if not math.isfinite(price_value):
        return "INVALID_PRICE"

    # 11. NON_POSITIVE_PRICE
    if price_value <= 0:
        return "NON_POSITIVE_PRICE"

    return None


def to_record(fields: list[str]) -> dict:
    """Turn a valid row into a flight record dictionary.

    Keys: flight_id, origin, destination, departure_datetime,
    arrival_datetime (stripped strings) and price (float).
    """
    flight_id, origin, destination, departure, arrival, price = (
        f.strip() for f in fields
    )
    return {
        "flight_id": flight_id,
        "origin": origin,
        "destination": destination,
        "departure_datetime": departure,
        "arrival_datetime": arrival,
        "price": float(price),
    }
