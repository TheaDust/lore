#!/usr/bin/env python3
"""Unit tests for scripts/history.py."""
import unittest
from history import extract_added_date, find_entry, parse_arg


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


if __name__ == "__main__":
    unittest.main()
