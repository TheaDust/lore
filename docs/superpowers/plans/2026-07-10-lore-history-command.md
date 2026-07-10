# lore `history` command — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only `lore history <entry-id|file-path|--scope>` command that prints git commits related to a memory entry or file, sourced from the local git CLI only.

**Architecture:** Single new script `scripts/history.py` (Python 3.6+, standard library only). It shells out to `list_entries.py --json` to reuse entry parsing (matching the existing `find_duplicates.py` / `find_stale.py` pattern), and to `git log` for commit data. argparse for CLI dispatch. All output to stdout; never writes to `.lore/`.

**Tech Stack:** Python 3.6+ (argparse, subprocess, json, re, datetime, pathlib, sys, os, unittest). External: `git` CLI (already required for `lore sync`).

**Reference spec:** `docs/superpowers/specs/2026-07-10-lore-history-command-design.md`

**Commit style:** Matches the existing `init` and `Add design spec...` commits. Short summary line, no body unless context requires it.

---

## File map

| File | Status | Responsibility |
|---|---|---|
| `scripts/history.py` | new | CLI + dispatch + git invocation + render |
| `scripts/test_history.py` | new | Unit tests (unittest, standard library) |
| `references/history-command.md` | new | Full reference spec (separate from this plan) |
| `SKILL.md` | modify | New `### history` workflow section + Quick reference row |
| `README.md` | modify | Quick-start command + FAQ entry |
| `README.zh-CN.md` | modify | Mirror of README.md change |
| `scripts/README.md` | modify | Add `history.py` row + testing notes |

Estimated total: ~390 new lines across 4 new files, ~80 modified lines across 4 existing files.

---

## Task 1: Test scaffolding and argparse skeleton

**Files:**
- Create: `scripts/test_history.py`
- Create: `scripts/history.py`

- [ ] **Step 1: Write failing test for `parse_arg`**

Create `scripts/test_history.py`:

```python
#!/usr/bin/env python3
"""Unit tests for scripts/history.py."""
import unittest
from history import parse_arg


class TestParseArg(unittest.TestCase):
    def test_entry_id_pattern(self):
        result = parse_arg("DEC-2026-02-03-7c19")
        self.assertEqual(result, {"form": "entry", "value": "DEC-2026-02-03-7c19"})

    def test_file_path_with_slash(self):
        result = parse_arg("frontend/src/store/index.ts")
        self.assertEqual(result, {"form": "file", "value": "frontend/src/store/index.ts"})

    def test_dotfile(self):
        result = parse_arg(".cursorrules")
        self.assertEqual(result, {"form": "file", "value": ".cursorrules"})

    def test_scope_flag_only(self):
        result = parse_arg("--scope=frontend")
        self.assertEqual(result, {"form": "scope", "value": "frontend"})

    def test_empty_arg(self):
        result = parse_arg("")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd scripts && python -m unittest test_history -v
```

Expected: `ModuleNotFoundError: No module named 'history'`

- [ ] **Step 3: Write minimal `history.py` with `parse_arg` only**

Create `scripts/history.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd scripts && python -m unittest test_history -v
```

Expected: `Ran 5 tests ... OK`

- [ ] **Step 5: Commit**

```bash
git add scripts/history.py scripts/test_history.py
git commit -m "Add scripts/history.py skeleton with arg dispatch"
```

---

## Task 2: Entry ID → lore file resolution

**Files:**
- Modify: `scripts/history.py`
- Modify: `scripts/test_history.py`

- [ ] **Step 1: Add failing test for `find_entry`**

Append to `scripts/test_history.py`:

```python
from history import find_entry


class TestFindEntry(unittest.TestCase):
    def test_returns_matching_entry(self):
        entries = [
            {
                "id": "DEC-2026-02-03-7c19",
                "file": "scopes/frontend/DECISIONS.md",
                "scope": "frontend",
                "text": "Use Zustand",
                "tags": {"added": "2026-02-03"},
            },
            {
                "id": "ARCH-2026-01-15-d7a3",
                "file": "_global/ARCHITECTURE.md",
                "scope": "_global",
                "text": "Monorepo with pnpm",
                "tags": {"added": "2026-01-15"},
            },
        ]
        result = find_entry(entries, "DEC-2026-02-03-7c19")
        self.assertEqual(result["file"], "scopes/frontend/DECISIONS.md")
        self.assertEqual(result["tags"]["added"], "2026-02-03")

    def test_missing_entry_returns_none(self):
        entries = [
            {"id": "DEC-2026-02-03-7c19", "file": "x.md", "scope": "frontend",
             "text": "t", "tags": {}},
        ]
        self.assertIsNone(find_entry(entries, "ARCH-2099-01-01-ffff"))
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd scripts && python -m unittest test_history.TestFindEntry -v
```

Expected: `ImportError: cannot import name 'find_entry'`

- [ ] **Step 3: Implement `find_entry`**

Add to `scripts/history.py` (between `parse_arg` and `if __name__ == "__main__"`):

```python
def find_entry(entries, entry_id):
    """Look up an entry by ID in the list from list_entries.py --json.

    Returns the entry dict, or None if not found.
    """
    for e in entries:
        if e.get("id") == entry_id:
            return e
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd scripts && python -m unittest test_history.TestFindEntry -v
```

Expected: `Ran 2 tests ... OK`

- [ ] **Step 5: Commit**

```bash
git add scripts/history.py scripts/test_history.py
git commit -m "Add find_entry to resolve entry ID to lore file"
```

---

## Task 3: Extract `#added` date from entry tags

**Files:**
- Modify: `scripts/history.py`
- Modify: `scripts/test_history.py`

- [ ] **Step 1: Add failing test for `extract_added_date`**

Append to `scripts/test_history.py`:

```python
from history import extract_added_date


class TestExtractAddedDate(unittest.TestCase):
    def test_present(self):
        tags = {"added": "2026-02-03", "verified": "2026-06-15"}
        self.assertEqual(extract_added_date(tags), "2026-02-03")

    def test_missing(self):
        self.assertIsNone(extract_added_date({}))

    def test_empty(self):
        self.assertIsNone(extract_added_date({"verified": "2026-06-15"}))
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd scripts && python -m unittest test_history.TestExtractAddedDate -v
```

Expected: `ImportError: cannot import name 'extract_added_date'`

- [ ] **Step 3: Implement `extract_added_date`**

Add to `scripts/history.py`:

```python
def extract_added_date(tags):
    """Return the value of the 'added' tag, or None if absent.

    The entry dict's `tags` field is {name: value, ...} as produced
    by list_entries.py.
    """
    if not tags:
        return None
    return tags.get("added")
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd scripts && python -m unittest test_history.TestExtractAddedDate -v
```

Expected: `Ran 3 tests ... OK`

- [ ] **Step 5: Commit**

```bash
git add scripts/history.py scripts/test_history.py
git commit -m "Add extract_added_date helper"
```

---

## Task 4: Extract code file path (backtick + scope fallback)

**Files:**
- Modify: `scripts/history.py`
- Modify: `scripts/test_history.py`

- [ ] **Step 1: Add failing test for `resolve_code_file`**

Append to `scripts/test_history.py`:

```python
from history import resolve_code_file


class TestResolveCodeFile(unittest.TestCase):
    def test_backtick_path_wins(self):
        entry = {
            "text": "Use Zustand; see `src/store/index.ts` for the implementation.",
            "scope": "frontend",
        }
        self.assertEqual(resolve_code_file(entry), "src/store/index.ts")

    def test_backtick_path_ignores_scope_dir(self):
        entry = {
            "text": "see `lib/api.ts`",
            "scope": "backend",
        }
        self.assertEqual(resolve_code_file(entry), "lib/api.ts")

    def test_no_backtick_falls_back_to_global(self):
        entry = {"text": "All packages use TypeScript strict mode", "scope": "_global"}
        self.assertEqual(resolve_code_file(entry), ".")

    def test_no_backtick_falls_back_to_scope(self):
        entry = {"text": "Use TanStack Query", "scope": "frontend"}
        self.assertEqual(resolve_code_file(entry), "frontend")

    def test_multiple_backticks_uses_first(self):
        entry = {
            "text": "see `a/foo.ts` and `b/bar.ts`",
            "scope": "frontend",
        }
        self.assertEqual(resolve_code_file(entry), "a/foo.ts")
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd scripts && python -m unittest test_history.TestResolveCodeFile -v
```

Expected: `ImportError: cannot import name 'resolve_code_file'`

- [ ] **Step 3: Implement `resolve_code_file`**

Add to `scripts/history.py`:

```python
# Match a backtick-quoted path inside an entry's text. The path must
# contain at least one slash OR start with a dot OR end with a common
# code extension, to avoid false positives like `Zustand`.
BACKTICK_PATH_RE = re.compile(
    r"`([^\s`]+\.[a-zA-Z0-9]{1,8}(?:\.[a-zA-Z0-9]{1,8})*`"
    r"|[^\s`]+/[^\s`]+`"
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
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd scripts && python -m unittest test_history.TestResolveCodeFile -v
```

Expected: `Ran 5 tests ... OK`

If any backtick-path test fails, the regex needs tuning. Common case: a path like `src/store/index.ts` should match the `[a-zA-Z]+\.[a-zA-Z0-9]{1,8}` branch. Adjust the regex first; do not change tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/history.py scripts/test_history.py
git commit -m "Add resolve_code_file with backtick + scope fallback"
```

---

## Task 5: Run `git log` and parse commit output

**Files:**
- Modify: `scripts/history.py`
- Modify: `scripts/test_history.py`

- [ ] **Step 1: Add failing test for `parse_commit_line`**

Append to `scripts/test_history.py`:

```python
from history import parse_commit_line, COMMIT_DELIM, FORMAT_STRING


class TestParseCommitLine(unittest.TestCase):
    def test_full_record(self):
        line = (
            "abc1234567890abcdef1234567890abcdef12345" + COMMIT_DELIM
            + "Alice" + COMMIT_DELIM
            + "2026-04-12" + COMMIT_DELIM
            + "Use Zustand v4"
        )
        result = parse_commit_line(line)
        self.assertEqual(result["hash"], "abc1234567890abcdef1234567890abcdef12345")
        self.assertEqual(result["short"], "abc1234")
        self.assertEqual(result["author"], "Alice")
        self.assertEqual(result["date"], "2026-04-12")
        self.assertEqual(result["subject"], "Use Zustand v4")
        self.assertEqual(result["body"], "")

    def test_empty_body_filled(self):
        line = "h" * 40 + COMMIT_DELIM + "Bob" + COMMIT_DELIM + "2026-01-01" + COMMIT_DELIM + "subject"
        result = parse_commit_line(line)
        self.assertEqual(result["body"], "")

    def test_too_few_fields_returns_none(self):
        self.assertIsNone(parse_commit_line("abc" + COMMIT_DELIM + "def"))
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd scripts && python -m unittest test_history.TestParseCommitLine -v
```

Expected: `ImportError: cannot import name 'parse_commit_line'`

- [ ] **Step 3: Implement `run_git_log`, `parse_commit_line`, constants**

Add to `scripts/history.py`:

```python
import subprocess
from pathlib import Path


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
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd scripts && python -m unittest test_history.TestParseCommitLine -v
```

Expected: `Ran 3 tests ... OK`

- [ ] **Step 5: Commit**

```bash
git add scripts/history.py scripts/test_history.py
git commit -m "Add run_git_log and parse_commit_line"
```

---

## Task 6: Extract PR/issue refs from commit message

**Files:**
- Modify: `scripts/history.py`
- Modify: `scripts/test_history.py`

- [ ] **Step 1: Add failing test for `extract_refs`**

Append to `scripts/test_history.py`:

```python
from history import extract_refs


class TestExtractRefs(unittest.TestCase):
    def test_paren_form(self):
        self.assertEqual(extract_refs("Some change (#123)"), ["#123"])

    def test_closes_form(self):
        self.assertEqual(extract_refs("Fix bug\n\nCloses #456"), ["Closes #456"])

    def test_refs_form(self):
        self.assertEqual(extract_refs("Refs #789 and Refs #012"), ["Refs #789", "Refs #012"])

    def test_fixes_form(self):
        self.assertEqual(extract_refs("Fixes #345"), ["Fixes #345"])

    def test_no_refs(self):
        self.assertEqual(extract_refs("Just a commit"), [])

    def test_ignores_email(self):
        self.assertEqual(extract_refs("Co-authored-by: Alice <a@b.com>"), [])

    def test_mixed(self):
        msg = "Big refactor (#111)\n\nCloses #222, Refs #333"
        self.assertEqual(extract_refs(msg), ["#111", "Closes #222", "Refs #333"])
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd scripts && python -m unittest test_history.TestExtractRefs -v
```

Expected: `ImportError: cannot import name 'extract_refs'`

- [ ] **Step 3: Implement `extract_refs`**

Add to `scripts/history.py`:

```python
# Match PR/issue references. Order matters: longer keywords first so
# "Closes" doesn't get eaten by "#NNN" alone. We require word boundary
# (or start of string) before the keyword to avoid matching substrings
# like "address#N" mid-word.
REFS_RE = re.compile(
    r"(?:\(|\b(?:Closes|Refs|Fixes|Resolves)\s+)"
    r"(#\d+)",
    re.IGNORECASE,
)


def extract_refs(message):
    """Return a list of PR/issue references found in a commit message.

    Each item is either "#NNN" (from parens form) or "Keyword #NNN"
    (from Closes/Refs/Fixes/Resolves form). Duplicates are removed
    in order of appearance.
    """
    matches = []
    seen = set()
    for m in REFS_RE.finditer(message):
        keyword = m.group(0).split("#")[0].strip()
        ref = "#" + m.group(1)[1:]  # normalize to "#NNN"
        if ref in seen:
            continue
        seen.add(ref)
        if keyword:
            matches.append(f"{keyword} {ref}")
        else:
            matches.append(ref)
    return matches
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd scripts && python -m unittest test_history.TestExtractRefs -v
```

Expected: `Ran 7 tests ... OK`

- [ ] **Step 5: Commit**

```bash
git add scripts/history.py scripts/test_history.py
git commit -m "Add extract_refs for commit message PR/issue references"
```

---

## Task 7: Fetch commit body via `git show`

**Files:**
- Modify: `scripts/history.py`
- Modify: `scripts/test_history.py`

- [ ] **Step 1: Add failing test for `fetch_commit_body`**

Append to `scripts/test_history.py`:

```python
from history import fetch_commit_body


class TestFetchCommitBody(unittest.TestCase):
    def test_truncate_body_short(self):
        from history import truncate_body
        self.assertEqual(truncate_body("line1\nline2", max_lines=3), "line1\nline2")

    def test_truncate_body_long(self):
        from history import truncate_body
        text = "\n".join(f"line {i}" for i in range(10))
        result = truncate_body(text, max_lines=3)
        self.assertEqual(result, "line 0\nline 1\nline 2")

    def test_truncate_body_strips_trailing_whitespace(self):
        from history import truncate_body
        self.assertEqual(truncate_body("a\nb\n\n\n", max_lines=3), "a\nb")
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd scripts && python -m unittest test_history.TestFetchCommitBody -v
```

Expected: failures on the `truncate_body` tests, since `truncate_body` is not yet defined. The `fetch_commit_body` test is a placeholder (no assertion); it serves as a future integration point.

- [ ] **Step 3: Implement `truncate_body` and `fetch_commit_body`**

Add to `scripts/history.py`:

```python
def truncate_body(body, max_lines=3):
    """Trim a multi-line string to at most `max_lines`, stripping blank tails.

    Used to keep commit bodies short in the Markdown output. The subject
    is already shown separately; the body is supplementary context.
    """
    lines = body.splitlines()
    trimmed = lines[:max_lines]
    while trimmed and not trimmed[-1].strip():
        trimmed.pop()
    return "\n".join(trimmed)


def fetch_commit_body(project_root, commit_hash):
    """Fetch the full commit message (subject + body) via `git show`.

    Returns a string with the subject as the first line and the body
    (if any) following a blank line. Trailing blank lines are removed.
    """
    cmd = [
        "git", "-C", str(project_root),
        "show", "-s", "--format=%B", commit_hash,
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", check=False,
        )
    except FileNotFoundError:
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout.rstrip()
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd scripts && python -m unittest test_history.TestFetchCommitBody -v
```

Expected: `Ran 4 tests ... OK`

- [ ] **Step 5: Commit**

```bash
git add scripts/history.py scripts/test_history.py
git commit -m "Add fetch_commit_body and truncate_body helpers"
```

---

## Task 8: Markdown rendering

**Files:**
- Modify: `scripts/history.py`
- Modify: `scripts/test_history.py`

- [ ] **Step 1: Add failing test for `render_markdown`**

Append to `scripts/test_history.py`:

```python
from history import render_markdown


class TestRenderMarkdown(unittest.TestCase):
    def test_header_and_metadata(self):
        meta = {
            "entry_id": "DEC-2026-02-03-7c19",
            "lore_file": "scopes/frontend/DECISIONS.md",
            "code_file": "frontend/src/store/index.ts",
            "since": "2026-02-03",
            "since_source": "entry_added",
        }
        commits = []
        out = render_markdown(meta, commits)
        self.assertIn("# history: [DEC-2026-02-03-7c19]", out)
        self.assertIn("> Entry: scopes/frontend/DECISIONS.md", out)
        self.assertIn("> Since: 2026-02-03 (entry #added date)", out)
        self.assertIn("> File: frontend/src/store/index.ts", out)
        self.assertIn("> Commits: 0", out)
        # No "Suggested next step" footer when 0 commits.
        self.assertNotIn("Suggested next step", out)

    def test_commit_block_with_body_and_refs(self):
        meta = {
            "entry_id": "X-2026-01-01-aaaa",
            "lore_file": "x.md",
            "code_file": "x.ts",
            "since": "2026-01-01",
            "since_source": "entry_added",
        }
        commits = [
            {
                "hash": "abc1234567890abcdef1234567890abcdef12345",
                "short": "abc1234",
                "author": "alice",
                "date": "2026-04-12",
                "subject": "Use Zustand v4",
                "body": "Migration notes here.",
                "refs": ["#234"],
            },
        ]
        out = render_markdown(meta, commits)
        self.assertIn("## abc1234 (2026-04-12, alice)", out)
        self.assertIn("Use Zustand v4", out)
        self.assertIn("Body: \"Migration notes here.\"", out)
        self.assertIn("Refs: #234", out)
        # Footer appears when commits exist.
        self.assertIn("Suggested next step", out)

    def test_commit_block_no_body_no_refs(self):
        meta = {"entry_id": "X", "lore_file": "x.md", "code_file": "x.ts",
                "since": "2026-01-01", "since_source": "entry_added"}
        commits = [
            {"hash": "abcdef1", "short": "abcdef1", "author": "bob",
             "date": "2026-01-02", "subject": "tweak", "body": "", "refs": []},
        ]
        out = render_markdown(meta, commits)
        self.assertIn("## abcdef1 (2026-01-02, bob)", out)
        self.assertIn("tweak", out)
        self.assertNotIn("Body:", out)
        self.assertNotIn("Refs:", out)
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd scripts && python -m unittest test_history.TestRenderMarkdown -v
```

Expected: `ImportError: cannot import name 'render_markdown'`

- [ ] **Step 3: Implement `render_markdown`**

Add to `scripts/history.py`:

```python
def render_markdown(meta, commits):
    """Render the Markdown output for a `lore history` invocation.

    Args:
        meta: dict with keys entry_id, lore_file, code_file, since,
              since_source.
        commits: list of commit dicts (see parse_commit_line + extract_refs).

    Returns:
        Markdown string ready for stdout.
    """
    lines = []
    lines.append(f"# history: [{meta['entry_id']}]")
    lines.append("")
    lines.append(f"> Entry: {meta['lore_file']}")
    lines.append(f"> Since: {meta['since']} (entry #added date)")
    lines.append(f"> File: {meta['code_file']}")
    lines.append(f"> Commits: {len(commits)} (showing all)")
    lines.append("")

    if not commits:
        return "\n".join(lines) + "\n"

    for c in commits:
        lines.append(f"## {c['short']} ({c['date']}, {c['author']})")
        lines.append(c["subject"])
        if c.get("body"):
            body = truncate_body(c["body"], max_lines=3)
            lines.append(f'  Body: "{body}"')
        if c.get("refs"):
            lines.append(f"  Refs: {', '.join(c['refs'])}")
        lines.append("")

    lines.append("## Suggested next step")
    lines.append("Run `lore sync` to check whether any of these commits")
    lines.append("introduce a [REFINED] candidate for this entry.")
    lines.append("")
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd scripts && python -m unittest test_history.TestRenderMarkdown -v
```

Expected: `Ran 3 tests ... OK`

- [ ] **Step 5: Commit**

```bash
git add scripts/history.py scripts/test_history.py
git commit -m "Add render_markdown output renderer"
```

---

## Task 9: JSON rendering

**Files:**
- Modify: `scripts/history.py`
- Modify: `scripts/test_history.py`

- [ ] **Step 1: Add failing test for `render_json`**

Append to `scripts/test_history.py`:

```python
import json as _json
from history import render_json


class TestRenderJson(unittest.TestCase):
    def test_round_trip(self):
        meta = {
            "entry_id": "DEC-2026-02-03-7c19",
            "lore_file": "scopes/frontend/DECISIONS.md",
            "code_file": "frontend/src/store/index.ts",
            "since": "2026-02-03",
            "since_source": "entry_added",
        }
        commits = [
            {"hash": "abc1234567890abcdef1234567890abcdef12345",
             "short": "abc1234", "author": "alice", "date": "2026-04-12",
             "subject": "Use Zustand v4", "body": "Migrate notes.",
             "refs": ["#234"]},
        ]
        out = render_json(meta, commits)
        parsed = _json.loads(out)
        self.assertEqual(parsed["entry_id"], "DEC-2026-02-03-7c19")
        self.assertEqual(len(parsed["commits"]), 1)
        self.assertEqual(parsed["commits"][0]["short"], "abc1234")
        self.assertEqual(parsed["commits"][0]["refs"], ["#234"])

    def test_empty_commits(self):
        meta = {"entry_id": "X", "lore_file": "x.md", "code_file": "x.ts",
                "since": "2026-01-01", "since_source": "entry_added"}
        out = render_json(meta, [])
        parsed = _json.loads(out)
        self.assertEqual(parsed["commits"], [])
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd scripts && python -m unittest test_history.TestRenderJson -v
```

Expected: `ImportError: cannot import name 'render_json'`

- [ ] **Step 3: Implement `render_json`**

Add to `scripts/history.py`:

```python
import json as _json  # standard library; aliased to avoid clashing with future vars


def render_json(meta, commits):
    """Render the JSON output for a `lore history` invocation.

    Output matches the schema documented in the spec.
    """
    payload = {
        "entry_id": meta["entry_id"],
        "lore_file": meta["lore_file"],
        "code_file": meta["code_file"],
        "since": meta["since"],
        "since_source": meta["since_source"],
        "commits": commits,
    }
    return _json.dumps(payload, indent=2, ensure_ascii=False)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd scripts && python -m unittest test_history.TestRenderJson -v
```

Expected: `Ran 2 tests ... OK`

- [ ] **Step 5: Commit**

```bash
git add scripts/history.py scripts/test_history.py
git commit -m "Add render_json output renderer"
```

---

## Task 10: Error handling (codes 2–7)

**Files:**
- Modify: `scripts/history.py`
- Modify: `scripts/test_history.py`

- [ ] **Step 1: Add failing test for `die` and exit-code paths**

Append to `scripts/test_history.py`:

```python
from history import die, ERR_NO_LORE, ERR_NO_ENTRY, ERR_NOT_GIT, ERR_NO_GIT, ERR_GIT_FAIL, ERR_BAD_SCOPE


class TestExitCodes(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(ERR_NO_LORE, 2)
        self.assertEqual(ERR_NO_ENTRY, 3)
        self.assertEqual(ERR_NOT_GIT, 4)
        self.assertEqual(ERR_NO_GIT, 5)
        self.assertEqual(ERR_GIT_FAIL, 7)
        self.assertEqual(ERR_BAD_SCOPE, 6)

    def test_die_writes_to_stderr_and_exits(self):
        import subprocess, sys
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, 'scripts'); "
             "from history import die, ERR_NO_ENTRY; "
             "die(ERR_NO_ENTRY, 'X not found')"],
            capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 3)
        self.assertIn("X not found", result.stderr)
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd scripts && python -m unittest test_history.TestExitCodes -v
```

Expected: `ImportError: cannot import name 'die'` (or one of the constants).

- [ ] **Step 3: Implement error constants and `die`**

Add to `scripts/history.py`:

```python
# Exit codes per spec section "Error handling".
ERR_USAGE      = 2  # no arg / unrecognized arg (also used by argparse path)
ERR_NO_LORE    = 2  # .lore/ not found
ERR_NO_ENTRY   = 3  # entry ID not in index
ERR_NOT_GIT    = 4  # not a git repository
ERR_NO_GIT     = 5  # git CLI missing
ERR_BAD_SCOPE  = 6  # scope name not in scopes/
ERR_GIT_FAIL   = 7  # git log returned non-zero for other reasons


def die(code, message):
    """Print message to stderr and exit with the given code."""
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd scripts && python -m unittest test_history.TestExitCodes -v
```

Expected: `Ran 2 tests ... OK`

- [ ] **Step 5: Commit**

```bash
git add scripts/history.py scripts/test_history.py
git commit -m "Add error codes and die() helper"
```

---

## Task 11: Wire up the full CLI in `main()`

**Files:**
- Modify: `scripts/history.py`
- Modify: `scripts/test_history.py`

- [ ] **Step 1: Replace placeholder `__main__` with full CLI**

Replace the `if __name__ == "__main__":` block at the bottom of `scripts/history.py` with:

```python
def _load_entries_via_subprocess():
    """Run scripts/list_entries.py --json and return the parsed list.

    Mirrors the pattern in find_duplicates.py / find_stale.py.
    Returns [] if no entries.
    """
    here = Path(__file__).resolve().parent
    cmd = [sys.executable, str(here / "list_entries.py"), "--json"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", check=False)
    except FileNotFoundError as exc:
        die(ERR_NO_GIT, f"python executable not found: {exc}")
    if proc.returncode != 0:
        die(ERR_NO_LORE, f"list_entries.py failed: {proc.stderr.strip()}")
    try:
        return _json.loads(proc.stdout)
    except _json.JSONDecodeError as exc:
        die(ERR_NO_LORE, f"list_entries.py returned invalid JSON: {exc}")


def _find_lore_root_or_die():
    """Walk up from CWD to find .lore/. Die with ERR_NO_LORE if not found."""
    p = Path(".").resolve()
    while p != p.parent:
        if (p / ".lore").is_dir():
            return p
        p = p.parent
    die(ERR_NO_LORE, ".lore/ not found. Run 'lore init' first.")


def _build_meta_entry(entry, code_file, since, since_source):
    return {
        "entry_id": entry["id"],
        "lore_file": entry["file"],
        "code_file": code_file,
        "since": since,
        "since_source": since_source,
    }


def _resolve_scope_to_md_files(project_root, scope_name):
    """For scope form: list the (layer_file, md_path) tuples under the scope."""
    scopes_dir = project_root / ".lore" / "scopes" / scope_name
    if not scopes_dir.is_dir():
        available = sorted(
            p.name for p in (project_root / ".lore" / "scopes").iterdir()
            if p.is_dir()
        ) if (project_root / ".lore" / "scopes").is_dir() else []
        available_display = ", ".join(available) if available else "(none)"
        die(ERR_BAD_SCOPE, f"Scope '{scope_name}' not found. Available: {available_display}")
    files = []
    for md in sorted(scopes_dir.glob("*.md")):
        files.append((md.stem, md))
    return files


def _is_git_repo(project_root):
    try:
        proc = subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", "--git-dir"],
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError:
        die(ERR_NO_GIT, "git executable not found on PATH.")
    return proc.returncode == 0


def _enrich_commits_with_body_and_refs(project_root, commits):
    """For each commit, fetch body and extract refs. Mutates in place."""
    for c in commits:
        msg = fetch_commit_body(project_root, c["hash"])
        if msg:
            # Body is everything after the first line.
            parts = msg.split("\n", 1)
            subject = parts[0]
            body = parts[1].strip() if len(parts) > 1 else ""
            c["subject"] = subject
            c["body"] = truncate_body(body, max_lines=3)
            c["refs"] = extract_refs(msg)


def main():
    args = sys.argv[1:]
    json_mode = "--json" in args
    since_override = None
    for a in args:
        if a.startswith("--since="):
            since_override = a.split("=", 1)[1]

    positional = [a for a in args if not a.startswith("--") and a != "--json"]
    if not positional:
        print("usage: lore history <entry-id|file-path|--scope=NAME>",
              file=sys.stderr)
        die(ERR_USAGE, "missing argument")

    parsed = parse_arg(positional[0])
    if parsed is None:
        die(ERR_USAGE, f"unrecognized argument: {positional[0]}")

    project_root = _find_lore_root_or_die()

    if not _is_git_repo(project_root):
        die(ERR_NOT_GIT,
            "Not a git repository. 'lore history' requires git; "
            "use 'lore query' for in-memory answers.")

    if parsed["form"] == "entry":
        entries = _load_entries_via_subprocess()
        entry = find_entry(entries, parsed["value"])
        if entry is None:
            ids = ", ".join(e["id"] for e in entries[:20])
            more = "" if len(entries) <= 20 else f" (and {len(entries)-20} more)"
            die(ERR_NO_ENTRY,
                f"Entry {parsed['value']} not found. Available: {ids}{more}")
        since = since_override or extract_added_date(entry.get("tags", {}))
        if since is None:
            print("warning: entry has no #added tag; using full history",
                  file=sys.stderr)
            since = "1970-01-01"
        code_file = resolve_code_file(entry)
        commits = run_git_log(project_root, since, code_file)
        _enrich_commits_with_body_and_refs(project_root, commits)
        meta = _build_meta_entry(entry, code_file, since, "entry_added")
        out = render_json(meta, commits) if json_mode else render_markdown(meta, commits)
        print(out)
        return

    if parsed["form"] == "file":
        since = since_override or "1970-01-01"
        code_file = parsed["value"]
        commits = run_git_log(project_root, since, code_file)
        _enrich_commits_with_body_and_refs(project_root, commits)
        meta = {
            "entry_id": f"<file:{code_file}>",
            "lore_file": "(direct file query)",
            "code_file": code_file,
            "since": since,
            "since_source": "user_arg" if since_override else "default",
        }
        out = render_json(meta, commits) if json_mode else render_markdown(meta, commits)
        print(out)
        return

    if parsed["form"] == "scope":
        layer_files = _resolve_scope_to_md_files(project_root, parsed["value"])
        for layer_name, md_path in layer_files:
            # For scope form we treat each .md file as a "code file" stand-in:
            # we git log the md file's project-relative path to find commits
            # that touched that lore file. (Useful for tracking lore edits.)
            rel = str(md_path.relative_to(project_root))
            commits = run_git_log(project_root, "1970-01-01", rel)
            _enrich_commits_with_body_and_refs(project_root, commits)
            if json_mode:
                meta = {
                    "entry_id": f"<scope:{parsed['value']}/{layer_name}>",
                    "lore_file": rel,
                    "code_file": rel,
                    "since": "1970-01-01",
                    "since_source": "scope_form",
                }
                print(render_json(meta, commits))
            else:
                print(f"## Scope: {parsed['value']} / {layer_name}")
                print("")
                if not commits:
                    print("(no commits)")
                    print("")
                    continue
                for c in commits:
                    print(f"### {c['short']} ({c['date']}, {c['author']})")
                    print(c["subject"])
                    if c.get("body"):
                        print(f'  Body: "{c["body"]}"')
                    if c.get("refs"):
                        print(f"  Refs: {', '.join(c['refs'])}")
                    print("")
        return


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run all tests to verify nothing regresses**

Run:
```bash
cd scripts && python -m unittest test_history -v
```

Expected: all prior tests still pass; no new tests in this task (this is wiring).

- [ ] **Step 3: Smoke-test the script with `--help`-style usage**

Run:
```bash
cd scripts && python history.py
```

Expected: stderr shows `error: missing argument`, exit code 2.

Run:
```bash
cd scripts && python history.py NONEXISTENT
```

Expected: stderr shows `error: unrecognized argument: NONEXISTENT`, exit code 2.

- [ ] **Step 4: Commit**

```bash
git add scripts/history.py scripts/test_history.py
git commit -m "Wire up lore history main() with all dispatch paths"
```

---

## Task 12: Write `references/history-command.md`

**Files:**
- Create: `references/history-command.md`

- [ ] **Step 1: Create the reference doc**

Create `references/history-command.md` with the following content. (This is documentation, no code or tests in this task.)

```markdown
# `lore history` — full specification

Read-only command. Lists git commits related to a memory entry, a file,
or a scope, since the entry's `#added` date. Output to stdout only;
never writes to `.lore/`.

## Synopsis

```
lore history <entry-id>
lore history <file-path>
lore history --scope=<name>
lore history --since=<YYYY-MM-DD>
lore history --json
```

## Forms

| Form | Argument shape | Example | Behavior |
|---|---|---|---|
| Entry | `[A-Z]+-\d{4}-\d{2}-\d{2}-[a-f0-9]{4}` | `lore history DEC-2026-02-03-7c19` | Locate entry in `.lore/`, derive its `#added` date and code file, then `git log` since that date. |
| File  | contains `/` or starts with `.` | `lore history frontend/src/store/index.ts` | Run `git log --since=1970-01-01` on the given path. |
| Scope | `--scope=<name>` only | `lore history --scope=frontend` | For each `*.md` in `.lore/scopes/<name>/`, run file form on the lore file path itself. |

## Code-file resolution (entry form)

Priority:

1. First backtick-quoted path in entry.text that looks like a file
   (e.g. `src/store/index.ts`).
2. Scope directory at the project root (e.g. entry scope `frontend` →
   `frontend/`).
3. Project root `.` for entries in `_global/`.

If the regex finds no path, falls back to the scope directory.

## Data source

`git` CLI only. No network calls. Requires:

- A git repository at or above the current working directory.
- The `git` executable on `PATH`.

## Output

### Markdown (default)

Header block: `Entry`, `Since`, `File`, `Commits`. One section per
commit with `## <short-hash> (<date>, <author>)`, subject, optional
`Body:` line, optional `Refs:` line. A "Suggested next step" footer
appears only when at least one commit is found.

### JSON (`--json`)

```json
{
  "entry_id": "DEC-2026-02-03-7c19",
  "lore_file": "scopes/frontend/DECISIONS.md",
  "code_file": "frontend/src/store/index.ts",
  "since": "2026-02-03",
  "since_source": "entry_added",
  "commits": [
    {
      "hash": "...",
      "short": "abc1234",
      "author": "alice",
      "date": "2026-04-12",
      "subject": "Use Zustand v4",
      "body": "Migrate notes here.",
      "refs": ["#234"]
    }
  ]
}
```

## Error handling

| Condition | Exit code | Message |
|---|---|---|
| No argument | 2 | `error: missing argument` |
| Unrecognized argument | 2 | `error: unrecognized argument: <arg>` |
| `.lore/` not found | 2 | `error: .lore/ not found. Run 'lore init' first.` |
| Entry not in index | 3 | `error: Entry <id> not found. Available: ...` |
| Not a git repo | 4 | `error: Not a git repository. ...` |
| `git` missing | 5 | `error: git executable not found on PATH.` |
| Bad scope name | 6 | `error: Scope '<name>' not found. Available: ...` |
| `git log` failure | 7 | `error: git log failed: <stderr>` |
| Entry missing `#added` | 0 (warning) | `warning: entry has no #added tag; using full history` |

## Exit codes summary

- `0` — success (including "0 commits found" case)
- `2` — usage / configuration error
- `3` — entry lookup failure
- `4` — not a git repo
- `5` — git CLI missing
- `6` — invalid scope
- `7` — git command failed

## Why this exists

`lore sync` reads `git diff` (working-tree deltas). It never reads
commit history. `lore history` fills that gap: given a memory entry,
it shows the commits that introduced or modified the underlying code,
letting the agent answer "why does this decision exist?" with a pointer
to the original commit instead of an LLM-generated guess.
```

- [ ] **Step 2: Verify the doc is well-formed Markdown**

Run:
```bash
python -c "import re,sys; t=open('references/history-command.md').read(); print(len(t), 'chars,', t.count('\n## '), 'sections')"
```

Expected: prints a number > 1000 and at least 6 sections.

- [ ] **Step 3: Commit**

```bash
git add references/history-command.md
git commit -m "Add references/history-command.md full spec"
```

---

## Task 13: Update `SKILL.md` with the `history` workflow

**Files:**
- Modify: `SKILL.md`

- [ ] **Step 1: Add `history` row to the Quick reference table**

In `SKILL.md`, find the Quick reference block near the end (the one starting `lore init      # Step 0 takeover check...`). Add a new row at the bottom of the code block:

```markdown
lore history   # Read-only. List git commits related to an entry / file / scope. Pure stdout.
```

(Insert one line above the closing ``` of the fenced block.)

- [ ] **Step 2: Add the `### history` workflow section**

In `SKILL.md`, find the `### `query` — Answer from memory` section. After it, insert a new section:

```markdown
### `history` — Show git commits related to a memory entry

Read-only. Surfaces the git history that backs a memory entry, a file,
or a scope, so the agent can answer "why does this decision exist?"
with a pointer to the actual commits rather than a guess.

**When to trigger:** only when the user explicitly invokes `lore
history` or names a subcommand ("查 git 历史", "show me the commits
behind this entry"). Generic "history" or "git log" alone does not
trigger — defer to the user's intent.

| User says (examples) | Command |
|---|---|
| "lore history DEC-2026-02-03-7c19" | `lore history <entry-id>` |
| "lore history frontend/src/store/index.ts" | `lore history <file-path>` |
| "lore history --scope=frontend" | `lore history --scope=<name>` |

**Procedure (entry form):**

1. Resolve project root (`.lore/` must exist; else exit 2).
2. Confirm git repo + git CLI on PATH (exit 4 / 5 otherwise).
3. Load entry index via `python scripts/list_entries.py --json`.
4. Locate the entry. If not found, exit 3 with a hint of available IDs.
5. Extract `#added` date as the default `--since`. If missing, print a
   warning to stderr and use `1970-01-01`.
6. Resolve the code file: backtick path in entry text → scope
   directory → project root.
7. Run `git log --since=<since> -- <code_file>` with a custom delimited
   format string.
8. For each commit, fetch the body via `git show -s --format=%B` and
   extract PR/issue refs via regex.
9. Render Markdown (default) or JSON (`--json`) and print to stdout.
10. **Stop.** No files are written.

**Data source contract:** local git CLI only. No GitHub / GitLab API.
No LLM call. The agent invoking the command does the semantic work
(interpreting commit messages, deciding relevance).

**Relationship to other commands:** fills the previously-empty cell of
"read git history" (other commands read either the current file system
or `git diff` only). See `references/history-command.md` for the full
dispatch rules, output format, and error table.
```

(Insert before the next `### ` section, which is the conflict resolution
or the next workflow.)

- [ ] **Step 3: Update the Reference index table**

In `SKILL.md`'s Reference index table (the one starting `| File | When to load |`), add a row:

```markdown
| `references/history-command.md` | Running `history` — full spec, dispatch rules, error table |
```

(Insert near the other `references/*.md` rows.)

- [ ] **Step 4: Verify `SKILL.md` still parses as reasonable Markdown**

Run:
```bash
python -c "import re; t=open('SKILL.md').read(); print('lines:', t.count(chr(10))+1, 'history mentions:', t.lower().count('history'))"
```

Expected: lines count > 350; "history" appears at least 5 times in the file.

- [ ] **Step 5: Commit**

```bash
git add SKILL.md
git commit -m "Document lore history workflow in SKILL.md"
```

---

## Task 14: Update README files

**Files:**
- Modify: `README.md`
- Modify: `README.zh-CN.md`
- Modify: `scripts/README.md`

- [ ] **Step 1: Add `lore history` to README.md Quick start**

In `README.md`, find the Quick start code block (the one starting
`# 4. Force a mirror refresh...`). After that block, add a paragraph:

```markdown
A sixth read-only command surfaces the git history behind a memory
entry:

\`\`\`bash
lore history                    # List commits for an entry / file / scope
lore history DEC-2026-02-03-7c19
lore history frontend/src/store/index.ts
lore history --scope=frontend   # all .md files in that scope
lore history --json             # machine-readable
\`\`\`
```

(Use proper fenced Markdown; the example above is escaped for the plan
text only.)

- [ ] **Step 2: Update the README.md Six workflows table**

In `README.md`, find the table that starts `| Command | What it does | Writes |`. Add a row:

```markdown
| `history` | Read-only; lists git commits related to an entry / file / scope | nothing |
```

- [ ] **Step 3: Mirror the changes in README.zh-CN.md**

In `README.zh-CN.md`, find the equivalent Quick start and Six workflows
sections (they mirror README.md). Add the same two additions, in
Chinese, consistent with the surrounding tone. Suggested Chinese text:

```markdown
第六个只读命令展示记忆库条目背后的 git 历史：

\`\`\`bash
lore history                    # 列出某条目/文件/scope 的相关 commits
lore history DEC-2026-02-03-7c19
lore history frontend/src/store/index.ts
lore history --scope=frontend
lore history --json
\`\`\`
```

And the table row:

```markdown
| `history` | 只读；列出某条目/文件/scope 相关的 git commits | 无 |
```

(Adjust the wording to match the rest of README.zh-CN.md's tone.)

- [ ] **Step 4: Update scripts/README.md**

In `scripts/README.md`, find the "When each script is called" table. Add a row:

```markdown
| `history.py` | lore history | List git commits related to a memory entry / file / scope |
```

(Insert at the top of the table, after the header row.)

- [ ] **Step 5: Commit**

```bash
git add README.md README.zh-CN.md scripts/README.md
git commit -m "Document lore history in README, README.zh-CN, scripts/README"
```

---

## Task 15: Manual smoke test in a fixture repo

**Files:** (no code changes; this is a verification task)

- [ ] **Step 1: Create a fixture project**

In a temp directory:

```bash
mkdir /tmp/lore-history-smoke
cd /tmp/lore-history-smoke
git init -q
git config user.email "test@example.com"
git config user.name "Test"
mkdir -p .lore/_global .lore/scopes/frontend frontend/src
echo "- [ARCH-2026-01-15-aaaa] Use pnpm. #added:2026-01-15" > .lore/_global/ARCHITECTURE.md
echo "- [DEC-2026-02-03-bbbb] Use Zustand; see \`src/store/index.ts\`. #added:2026-02-03" > .lore/scopes/frontend/DECISIONS.md
echo "console.log('hello')" > frontend/src/store/index.ts
git add -A
git commit -q -m "init"
echo "console.log('hello v2')" > frontend/src/store/index.ts
git add -A
git commit -q -m "Bump store (#1)"
```

- [ ] **Step 2: Run `lore history` on the entry**

From the fixture root, invoke the script:

```bash
cd /tmp/lore-history-smoke
python <repo-root>/scripts/history.py DEC-2026-02-03-bbbb
```

Expected: stdout contains `# history: [DEC-2026-02-03-bbbb]`, `> File: src/store/index.ts`, and at least one commit block referencing the "Bump store" commit.

- [ ] **Step 3: Run with `--json`**

```bash
python <repo-root>/scripts/history.py --json DEC-2026-02-03-bbbb
```

Expected: valid JSON parseable by `python -c "import json,sys; json.load(sys.stdin)"`.

- [ ] **Step 4: Test error paths**

```bash
python <repo-root>/scripts/history.py ARCH-2099-01-01-zzzz   # exit 3
python <repo-root>/scripts/history.py                         # exit 2
python <repo-root>/scripts/history.py --scope=does_not_exist  # exit 6
```

Expected: each prints to stderr and exits with the corresponding code.

- [ ] **Step 5: Clean up and commit verification log**

```bash
rm -rf /tmp/lore-history-smoke
git status   # should be clean
```

If `git status` shows any unintended changes (e.g. CRLF conversions on
unrelated files), do **not** commit them. Report the situation to the
user and stop.

- [ ] **Step 6: Final commit if any docs-only drift accumulated**

```bash
# Only if the previous tasks left uncommitted docs-only tweaks.
git add -u
git status --short
```

If only expected files appear in the status, commit:

```bash
git commit -m "Final doc tweaks from smoke test"
```

Otherwise, stop and report.

---

## Self-review checklist

- [x] **Spec coverage:** all spec requirements map to a task. Entry form (Tasks 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11), file form (Task 11), scope form (Task 11), Markdown (Task 8), JSON (Task 9), error handling (Task 10), reference doc (Task 12), SKILL.md (Task 13), README (Task 14), testing (Tasks 1-10 unit + Task 15 manual).
- [x] **Placeholder scan:** no "TBD" / "TODO" / "fill in" / "similar to Task N" markers. Each step has concrete code or a concrete command.
- [x] **Type consistency:** `parse_arg` returns `{"form", "value"}` dicts throughout. Commit dict keys (`hash`, `short`, `author`, `date`, `subject`, `body`, `refs`) are consistent across Tasks 5, 6, 7, 8, 9, 11. `meta` dict keys (`entry_id`, `lore_file`, `code_file`, `since`, `since_source`) are consistent across Tasks 8, 9, 11. Error constants (`ERR_NO_LORE` etc.) defined in Task 10 and used in Task 11.
- [x] **Frequent commits:** 15 commits total, one per task (Task 15 may or may not commit, depending on smoke-test outcome).
- [x] **DRY / YAGNI:** no unused features. The placeholder `fetch_commit_body` test in Task 7 is a known stub for future integration; the substantive `truncate_body` tests cover what we actually use.
