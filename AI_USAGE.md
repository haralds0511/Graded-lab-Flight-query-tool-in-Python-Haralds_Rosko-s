# AI Usage Disclosure

## Tools used

-  Gemini

## Conversation links

- Link 1: https://gemini.google.com/app/98c737cf122ae5ba?pli=1

## What I used them for

- understand some parts of the code, and trying to understand some errors along the way

## Which parts of the code were AI-generated or substantially AI-assisted

- Some of flight_parser.py was assisted by ai.

## Key prompts



## Tricky details the code handles (and that were checked)

- Airport codes and flight IDs are checked with explicit ASCII patterns
  ([A-Z]{3}, [A-Za-z0-9]{2,8}), because str.isalnum() and str.isupper() accept
  non-ASCII letters such as "A" with a macron.
- Dates are checked with a strict YYYY-MM-DD HH:MM pattern before strptime,
  because strptime alone accepts values like "2025-1-5 9:3".
- Checks run in the specified order and only the first failing code is
  reported; DUPLICATE_FLIGHT is checked only in parse_files, only against
  earlier valid rows, using (flight_id, departure_datetime).
- Line numbers are physical 1-based line numbers, counting the header, blank
  lines and comment lines; Windows (\r\n) line endings are handled.
- Prices: float() must succeed and the result must be finite (nan/inf are
  INVALID_PRICE); zero or negative is NON_POSITIVE_PRICE.
- Booleans are rejected as numbers in queries; limit must be an integer >= 0;
  order without sort_by is an invalid query; sorting is stable in both
  directions.
- errors.log is written with the logging module (FileHandler, no basicConfig),
  and the handler is removed and closed in a finally block, so calling main()
  several times in one process does not duplicate log lines.
- Runtime problems print "Error: ..." to stderr and return 1; usage errors
  return 2 (argparse or parser.error); main() returns the code and never
  calls sys.exit().

## What I changed or verified myself

- Set my own STUDENT_ID, FIRST_NAME and LAST_NAME in flight_parser.py.
- Written most of the code with trial and error.
- Ran `python tests/run_public_tests.py` in my own repository and checked that
  all tests pass.

