"""Running queries against the flight database."""
from validator import parse_datetime

_RECORD_KEYS = (
    "flight_id",
    "origin",
    "destination",
    "departure_datetime",
    "arrival_datetime",
    "price",
)
_STRING_KEYS = ("flight_id", "origin", "destination")
_DATETIME_KEYS = ("departure_datetime", "arrival_datetime")
_NUMBER_KEYS = ("price", "min_price")


def _is_number(value) -> bool:
    """A JSON number: int or float, but never a bool."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_valid_query(query) -> bool:
    if not isinstance(query, dict):
        return False

    for key, value in query.items():
        if key in _STRING_KEYS:
            if not isinstance(value, str):
                return False
        elif key in _DATETIME_KEYS:
            if parse_datetime(value) is None:
                return False
        elif key in _NUMBER_KEYS:
            if not _is_number(value):
                return False
        elif key == "sort_by":
            if not isinstance(value, str) or value not in _RECORD_KEYS:
                return False
        elif key == "order":
            if not isinstance(value, str) or value not in ("asc", "desc"):
                return False
        elif key == "limit":
            if (not isinstance(value, int) or isinstance(value, bool)
                    or value < 0):
                return False
        else:  # unknown key
            return False

    # order requires sort_by
    if "order" in query and "sort_by" not in query:
        return False
    return True


def _record_matches(record: dict, query: dict) -> bool:
    for key in _STRING_KEYS:
        if key in query and record.get(key) != query[key]:
            return False

    # Datetimes are zero-padded 'YYYY-MM-DD HH:MM', so comparing the strings
    # is the same as comparing the moments in time.
    if "departure_datetime" in query:
        departure = record.get("departure_datetime")
        if not isinstance(departure, str) or departure < query["departure_datetime"]:
            return False
    if "arrival_datetime" in query:
        arrival = record.get("arrival_datetime")
        if not isinstance(arrival, str) or arrival > query["arrival_datetime"]:
            return False

    if "price" in query or "min_price" in query:
        price = record.get("price")
        if not _is_number(price):
            return False
        if "price" in query and not price <= query["price"]:
            return False
        if "min_price" in query and not price >= query["min_price"]:
            return False

    return True


def run_query(db: list[dict], query: dict) -> dict:
    """Return one response entry for one query object.

    Valid query:   {"query": query, "matches": [...]}
    Invalid query: {"query": query, "error": "INVALID_QUERY", "matches": []}
    """
    if not _is_valid_query(query):
        return {"query": query, "error": "INVALID_QUERY", "matches": []}

    matches = [record for record in db if _record_matches(record, query)]

    if "sort_by" in query:
        # sorted() is stable, also with reverse=True, so equal values keep
        # database order in both directions.
        matches = sorted(
            matches,
            key=lambda record: record[query["sort_by"]],
            reverse=query.get("order", "asc") == "desc",
        )

    if "limit" in query:
        matches = matches[:query["limit"]]

    return {"query": query, "matches": matches}


def run_queries(db: list[dict], queries: dict | list) -> list[dict]:
    """Accept one query object or a list of them; always return a list."""
    if isinstance(queries, list):
        return [run_query(db, query) for query in queries]
    return [run_query(db, queries)]
