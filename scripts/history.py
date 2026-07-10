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
import subprocess
import sys
from pathlib import Path


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


# Match a backtick-quoted path inside an entry's text. The path must
# contain at least one slash OR start with a dot OR end with a common
# code extension, to avoid false positives like `Zustand`.
BACKTICK_PATH_RE = re.compile(
    r"`([^\s`]+\.[a-zA-Z0-9]{1,8}(?:\.[a-zA-Z0-9]{1,8})*"
    r"|[^\s`]+/[^\s`]+"
    r"|\.[a-zA-Z][^\s`]*)`"
)


def resolve_code_file(entry):
    """Decide which file path to git-log for this entry.

    Priority:
      1. First backtick-quoted path in entry.text (looks like a file).
      2. Scope directory at project root (e.g. "frontend" for scope "frontend").
      3. "." for the _global scope (project root).

    The path returned is relative to the project root. git log handles
    "." to mean the whole repo.
    """
    if entry.get("text"):
        m = BACKTICK_PATH_RE.search(entry["text"])
        if m:
            return m.group(1)
    scope = entry.get("scope", "_global")
    if scope == "_global":
        return "."
    return scope


# Single-line per commit. The trailing %s for body is multi-line content
# that we capture separately (not in the delimited format string) by
# running a second pass with a different format. For v1 we use a simple
# format and parse body via a follow-up `git show` only if needed.
#
# To keep parsing simple, we use a delimiter unlikely to appear in real
# commit metadata: ASCII Unit Separator (\x1f).
COMMIT_DELIM = "\x1f"

# git log format: hash\x1fauthor\x1fdate(iso)\x1fsubject
# We use %x1f (the same delimiter) inline so the format string is portable.
# The body is fetched separately via the second invocation below.
FORMAT_STRING = "%H%x1f%an%x1f%ai%x1f%s"


def run_git_log(project_root, since, code_file, n=None):
    """Run `git log` and return a list of commit dicts.

    Args:
        project_root: Path to the git repo root.
        since: ISO date string, or None for full history.
        code_file: Path relative to project_root to filter by.
        n: Optional int cap on number of commits.

    Returns:
        List of dicts as produced by parse_commit_line + body-fetch.

    Raises:
        RuntimeError: if git exits non-zero or is missing.
    """
    cmd = [
        "git",
        "-C", str(project_root),
        "log",
        f"--pretty=format:{FORMAT_STRING}",
    ]
    if since:
        cmd.append(f"--since={since}")
    if n is not None:
        cmd.append(f"-n{n}")
    cmd.extend(["--", code_file])

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"git executable not found on PATH: {exc}")

    if proc.returncode != 0:
        raise RuntimeError(f"git log failed: {proc.stderr.strip()}")

    commits = []
    for line in proc.stdout.splitlines():
        if not line:
            continue
        parsed = parse_commit_line(line)
        if parsed is None:
            continue
        parsed["body"] = ""  # filled in by fetch_body if requested later
        commits.append(parsed)
    return commits


def parse_commit_line(line):
    """Parse one delimited git log line. Returns dict or None on malformed input."""
    parts = line.split(COMMIT_DELIM)
    if len(parts) != 4:
        return None
    full_hash, author, date, subject = parts
    if len(full_hash) < 7:
        return None
    return {
        "hash": full_hash,
        "short": full_hash[:7],
        "author": author,
        "date": date[:10],  # take YYYY-MM-DD from full ISO timestamp
        "subject": subject,
        "body": "",  # populated by fetch_commit_body
    }


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
