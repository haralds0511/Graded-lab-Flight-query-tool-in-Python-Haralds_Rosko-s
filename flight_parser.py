"""Flight Schedule Parser and Query Tool - command-line entry point.

Run from the project folder, for example:
    python flight_parser.py -i data/db.csv -a data/airports.txt
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime

from csv_loader import parse_files
from query import run_queries
from validator import load_airports

# TODO: fill in your details: plain ASCII, no spaces or underscores.
STUDENT_ID = "251RDC034"
FIRST_NAME = "Haralds"
LAST_NAME = "Roskošs"


class RuntimeProblem(Exception):
    """An expected runtime problem; main() prints 'Error: ...' and returns 1."""


#                  arguments

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flight_parser.py",
        description="Validate flight schedule CSV files, store the valid "
                    "flights as a JSON database and answer queries.",
        allow_abbrev=False,
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("-i", dest="input_file", metavar="FILE",
                        help="parse a single CSV file")
    source.add_argument("-d", dest="input_dir", metavar="FOLDER",
                        help="parse every .csv file in the folder "
                             "(sorted by file name)")
    source.add_argument("-j", dest="json_db", metavar="FILE",
                        help="load an existing JSON database instead of "
                             "parsing CSV files")
    parser.add_argument("-a", dest="airports", metavar="FILE",
                        help="airport list file (required with -i and -d)")
    parser.add_argument("-o", dest="output", metavar="FILE",
                        help="output path of the JSON database "
                             "(default: db.json; only with -i or -d)")
    parser.add_argument("-q", dest="queries", metavar="FILE",
                        help="JSON file with queries to run")
    parser.add_argument("-r", dest="response_dir", metavar="FOLDER",
                        default=".",
                        help="folder for the query response file "
                             "(default: current directory)")
    return parser


def _parse_arguments(argv):
    """Parse and check the arguments. Usage errors exit with code 2."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if (args.input_file is not None or args.input_dir is not None) \
            and args.airports is None:
        parser.error("-a is required with -i and -d")
    if args.json_db is not None and args.output is not None:
        parser.error("-o cannot be used with -j")
    return args


#              JSON input

def _read_json(path: str, what: str):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except OSError as exc:
        raise RuntimeProblem(
            f"cannot read {what} '{path}': {exc.strerror or exc}") from None
    except (ValueError, RecursionError):
        raise RuntimeProblem(f"{what} '{path}' is not valid JSON") from None


def _load_database(path: str) -> list[dict]:
    data = _read_json(path, "database file")
    if not isinstance(data, list) or not all(isinstance(r, dict) for r in data):
        raise RuntimeProblem(
            f"database file '{path}' must be a JSON array of objects")
    return data


def _load_queries(path: str):
    data = _read_json(path, "query file")
    ok = isinstance(data, dict) or (
        isinstance(data, list) and all(isinstance(q, dict) for q in data))
    if not ok:
        raise RuntimeProblem(
            f"query file '{path}' must be a JSON object or an array of objects")
    return data


#                                 CSV input

def _collect_csv_paths(args) -> list[str]:
    if args.input_file is not None:
        if not os.path.isfile(args.input_file):
            raise RuntimeProblem(f"CSV file '{args.input_file}' does not exist or is not a file")
        return [args.input_file]

    folder = args.input_dir
    if not os.path.isdir(folder):
        raise RuntimeProblem(f"folder '{folder}' does not exist")
    try:
        names = sorted(
            name for name in os.listdir(folder)
            if name.endswith(".csv") and os.path.isfile(os.path.join(folder, name))
        )
    except OSError as exc:
        raise RuntimeProblem(
            f"cannot read folder '{folder}': {exc.strerror or exc}") from None
    if not names:
        raise RuntimeProblem(f"no .csv files found in folder '{folder}'")
    return [os.path.join(folder, name) for name in names]


def _parse_csv_input(args, logger: logging.Logger) -> tuple[list[dict], list[str]]:
    """Parse CSV input, log invalid rows, write the database."""
    paths = _collect_csv_paths(args)

    try:
        airports = load_airports(args.airports)
    except OSError as exc:
        raise RuntimeProblem(
            f"cannot read airport file '{args.airports}': "
            f"{exc.strerror or exc}") from None
    except UnicodeDecodeError:
        raise RuntimeProblem(
            f"airport file '{args.airports}' is not valid UTF-8") from None

    try:
        records, errors = parse_files(paths, airports)
    except OSError as exc:
        raise RuntimeProblem(
            f"cannot read CSV file '{exc.filename}': "
            f"{exc.strerror or exc}") from None
    except UnicodeDecodeError:
        raise RuntimeProblem("a CSV file is not valid UTF-8 text") from None

    for message in errors:
        logger.warning("%s", message)
    logger.info("%d valid rows, %d invalid rows", len(records), len(errors))
    return records, errors


#                    outputs

def _write_json(path: str, data, what: str) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError as exc:
        raise RuntimeProblem(
            f"cannot write {what} '{path}': {exc.strerror or exc}") from None


def _response_file_name() -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    return f"response_{STUDENT_ID}_{FIRST_NAME}_{LAST_NAME}_{stamp}.json"


def _build_database(args) -> list[dict]:
    """-i / -d: parse CSV files, write the database and errors.log."""
    db_path = args.output if args.output is not None else "db.json"
    log_path = os.path.join(os.path.dirname(os.path.abspath(db_path)),
                            "errors.log")

    logger = logging.getLogger("flight_parser")
    logger.setLevel(logging.INFO)
    try:
        handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    except OSError as exc:
        raise RuntimeProblem(
            f"cannot write log file '{log_path}': {exc.strerror or exc}"
        ) from None
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(handler)

    try:
        try:
            records, errors = _parse_csv_input(args, logger)
            _write_json(db_path, records, "database file")
        except RuntimeProblem as exc:
            logger.error("%s", exc)
            raise
        print(f"{len(records)} valid flights written to {db_path}; "
              f"{len(errors)} invalid rows logged to {log_path}")
        return records
    finally:
        logger.removeHandler(handler)
        handler.close()


#                              main

def _run(args) -> int:
    # Read the query file first, so that a bad one stops the run before
    queries = _load_queries(args.queries) if args.queries is not None else None

    if args.json_db is not None:
        db = _load_database(args.json_db)
    else:
        db = _build_database(args)

    if queries is not None:
        response = run_queries(db, queries)
        response_path = os.path.join(args.response_dir, _response_file_name())
        _write_json(response_path, response, "response file")
        print(f"{len(response)} query result(s) written to {response_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the whole program and return the exit code (0, 1 or 2).

    argv is the argument list without the program name.
    None means use sys.argv[1:] (argparse does this for you).
    Do not call sys.exit() inside main(); return the code instead.
    """
    try:
        args = _parse_arguments(argv)
    except SystemExit as exc:  # argparse: -h gives 0, usage errors give 2
        return exc.code if isinstance(exc.code, int) else 2

    try:
        return _run(args)
    except RuntimeProblem as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
