#!/usr/bin/env python3
"""Unit tests for scripts/history.py."""
import unittest
from history import (
    COMMIT_DELIM,
    extract_added_date,
    find_entry,
    parse_arg,
    parse_commit_line,
    resolve_code_file,
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


if __name__ == "__main__":
    unittest.main()
