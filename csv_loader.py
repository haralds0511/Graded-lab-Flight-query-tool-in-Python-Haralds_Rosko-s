"""Reading CSV files into flight records and error messages."""
import csv
import os

from validator import to_record, validate_row


def _single_line_text(text: str) -> str:
    """Replace control/non-printable characters so a message stays on one line."""
    return "".join(ch if ch.isprintable() else " " for ch in text)


def parse_files(paths: list[str], airports: set[str]) -> tuple[list[dict], list[str]]:
    """Process the CSV files in the order given.

    Return (records, errors):
      records - valid flight records, in input order
      errors  - one message per invalid row, in input order, formatted as
                "<file name>:<line number>: <ERROR_CODE> | <free text>"
                (base file name only, no timestamp or level, no newline)

    Also performs the DUPLICATE_FLIGHT check across all the files.
    Does not write any files and does not log anything itself.

    Raises OSError / UnicodeDecodeError if a file cannot be read.
    """
    records: list[dict] = []
    errors: list[str] = []
    seen: set[tuple[str, str]] = set()  # (flight_id, departure_datetime)

    for path in paths:
        file_name = os.path.basename(path)
        # Default newline handling turns \r\n (and \n) into \n, so both
        # Windows and Unix line endings work and line numbers stay physical.
        with open(path, encoding="utf-8") as f:
            for line_number, raw_line in enumerate(f, start=1):
                if line_number == 1:  # header: skipped without validation
                    continue

                line = raw_line.rstrip("\r\n")
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue  # blank or comment line: not logged

                try:
                    parsed = list(csv.reader([line]))
                except csv.Error:
                    parsed = []
                fields = parsed[0] if parsed else []

                code = validate_row(fields, airports)
                if code is None:
                    record = to_record(fields)
                    key = (record["flight_id"], record["departure_datetime"])
                    if key in seen:
                        code = "DUPLICATE_FLIGHT"
                    else:
                        seen.add(key)
                        records.append(record)

                if code is not None:
                    errors.append(
                        f"{file_name}:{line_number}: {code} | "
                        f"{_single_line_text(line)}"
                    )

    return records, errors
