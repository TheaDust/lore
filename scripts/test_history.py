#!/usr/bin/env python3
"""Unit tests for scripts/history.py."""
import json as _json
import unittest
from history import (
    COMMIT_DELIM,
    ERR_BAD_SCOPE,
    ERR_GIT_FAIL,
    ERR_NO_ENTRY,
    ERR_NO_GIT,
    ERR_NO_LORE,
    ERR_NOT_GIT,
    die,
    extract_added_date,
    extract_refs,
    fetch_commit_body,
    find_entry,
    parse_arg,
    parse_commit_line,
    resolve_code_file,
    render_json,
    render_markdown,
)


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


class TestExtractAddedDate(unittest.TestCase):
    def test_present(self):
        tags = {"added": "2026-02-03", "verified": "2026-06-15"}
        self.assertEqual(extract_added_date(tags), "2026-02-03")

    def test_missing(self):
        self.assertIsNone(extract_added_date({}))

    def test_empty(self):
        self.assertIsNone(extract_added_date({"verified": "2026-06-15"}))


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
        self.assertIn('Body: "Migration notes here."', out)
        self.assertIn("Refs: #234", out)
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


if __name__ == "__main__":
    unittest.main()
