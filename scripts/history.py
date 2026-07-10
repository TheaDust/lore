#!/usr/bin/env python3
"""`lore history` — list git commits related to an entry, file, or scope.

Usage:
    lore history <entry-id>
    lore history <file-path>
    lore history --scope=<name>
    lore history --since=<YYYY-MM-DD>
    lore history --json

See references/history-command.md for the full specification.
"""
import re
import sys


# Entry ID pattern: LAYER-YYYY-MM-DD-xxxx (4 hex chars)
ENTRY_ID_RE = re.compile(r"^[A-Z]+-\d{4}-\d{2}-\d{2}-[a-f0-9]{4}$")


def parse_arg(arg: str):
    """Dispatch the first positional argument to entry / file / scope form.

    Returns a dict {"form": "entry"|"file"|"scope", "value": str}, or None
    if the argument matches none of the recognized patterns.
    """
    if not arg:
        return None
    if arg.startswith("--scope="):
        return {"form": "scope", "value": arg.split("=", 1)[1]}
    if ENTRY_ID_RE.match(arg):
        return {"form": "entry", "value": arg}
    if "/" in arg or arg.startswith("."):
        return {"form": "file", "value": arg}
    return None


def find_entry(entries, entry_id):
    """Look up an entry by ID in the list from list_entries.py --json.

    Returns the entry dict, or None if not found.
    """
    for e in entries:
        if e.get("id") == entry_id:
            return e
    return None


def extract_added_date(tags):
    """Return the value of the 'added' tag, or None if absent.

    The entry dict's `tags` field is {name: value, ...} as produced
    by list_entries.py.
    """
    if not tags:
        return None
    return tags.get("added")


if __name__ == "__main__":
    # Placeholder; real CLI wiring comes in later tasks.
    if len(sys.argv) < 2:
        print("usage: lore history <entry-id|file-path|--scope=NAME>", file=sys.stderr)
        sys.exit(2)
    parsed = parse_arg(sys.argv[1])
    if parsed is None:
        print(f"error: unrecognized argument: {sys.argv[1]}", file=sys.stderr)
        sys.exit(2)
    print(parsed)
