#!/usr/bin/env python3
"""Black-box regression tests for the lore helper scripts.

Run from the repo root:

    python -m unittest discover -s tests -v

Every test builds an isolated `.lore/` fixture in a temporary directory
and runs the real script via subprocess, exactly as the lore workflows
do. Stdlib only (unittest), Python 3.6+, cross-platform.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"


def run_script(name, args, cwd):
    """Run a lore script as a black box; returns CompletedProcess."""
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def hash_of(text):
    """Compute the 4-char ID hash via the real id_hash.py script."""
    r = run_script("id_hash.py", [text], cwd=REPO_ROOT)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def days_ago(n):
    return (date.today() - timedelta(days=n)).isoformat()


def write(path, content, bom=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = content.encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    path.write_bytes(data)


def make_project(tmp, scopes=("frontend",)):
    """Create a temp project with an empty .lore/ layout."""
    root = Path(tmp) / "proj"
    lore = root / ".lore"
    (lore / "_global").mkdir(parents=True)
    for scope in scopes:
        (lore / "scopes" / scope).mkdir(parents=True)
    return root, lore


class TestIdHash(unittest.TestCase):
    def test_deterministic(self):
        text = "Use Next.js App Router; reason: streaming + RSC"
        r1 = run_script("id_hash.py", [text], cwd=REPO_ROOT)
        r2 = run_script("id_hash.py", [text], cwd=REPO_ROOT)
        self.assertEqual(r1.returncode, 0)
        self.assertEqual(r1.stdout.strip(), r2.stdout.strip())

    def test_different_text_different_hash(self):
        a = run_script("id_hash.py", ["aaa"], cwd=REPO_ROOT).stdout.strip()
        b = run_script("id_hash.py", ["bbb"], cwd=REPO_ROOT).stdout.strip()
        self.assertNotEqual(a, b)

    def test_output_is_4_hex_chars(self):
        r = run_script("id_hash.py", ["hello world"], cwd=REPO_ROOT)
        out = r.stdout.strip()
        self.assertRegex(out, r"^[a-f0-9]{4}$")
        self.assertTrue(r.stdout.isascii())

    def test_help_exits_zero(self):
        r = run_script("id_hash.py", ["--help"], cwd=REPO_ROOT)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout, "")


class TestListEntries(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root, self.lore = make_project(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _entries_json(self, args=()):
        r = run_script("list_entries.py", ["--json", *args], cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_basic_parse_and_fields(self):
        write(
            self.lore / "_global" / "ARCHITECTURE.md",
            "# Global Architecture\n"
            "- [ARCH-2026-07-09-a3f2] Use Next.js App Router. #added:2026-07-09 #verified:2026-07-15\n",
        )
        write(
            self.lore / "scopes" / "frontend" / "DECISIONS.md",
            "# Frontend Decisions\n"
            "- [DEC-2026-02-03-7c19] Chose Zustand over Redux; reason: less boilerplate. #added:2026-02-03\n",
        )
        entries = self._entries_json()
        self.assertEqual(len(entries), 2)
        by_id = {e["id"]: e for e in entries}
        arch = by_id["ARCH-2026-07-09-a3f2"]
        self.assertEqual(arch["layer"], "ARCH")
        self.assertEqual(arch["scope"], "_global")
        self.assertEqual(arch["layer_file"], "ARCHITECTURE")
        self.assertEqual(arch["file"], "_global/ARCHITECTURE.md")
        self.assertEqual(arch["text"], "Use Next.js App Router.")
        self.assertEqual(arch["tags"], {"added": "2026-07-09", "verified": "2026-07-15"})
        self.assertEqual(arch["last_verified"], "2026-07-15")
        self.assertIsNone(arch["replaced_by"])
        dec = by_id["DEC-2026-02-03-7c19"]
        self.assertEqual(dec["scope"], "frontend")
        self.assertEqual(dec["file"], "scopes/frontend/DECISIONS.md")

    def test_bom_stripped_from_first_line(self):
        write(
            self.lore / "_global" / "CONVENTIONS.md",
            "# Conventions\n"
            "- [CONV-2026-01-20-b1e8] Never commit secrets. #added:2026-01-20\n",
            bom=True,
        )
        entries = self._entries_json()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["id"], "CONV-2026-01-20-b1e8")

    def test_continuation_lines_merged(self):
        write(
            self.lore / "_global" / "ARCHITECTURE.md",
            "- [ARCH-2026-07-09-a3f2] Use Next.js App Router; reason: streaming\n"
            "    plus RSC and fast refresh. #added:2026-07-09\n",
        )
        entries = self._entries_json()
        self.assertEqual(len(entries), 1)
        self.assertEqual(
            entries[0]["text"],
            "Use Next.js App Router; reason: streaming plus RSC and fast refresh.",
        )

    def test_duplicate_superseded_by_warns_and_keeps_first(self):
        write(
            self.lore / "scopes" / "frontend" / "ARCHITECTURE.md",
            "- [ARCH-2026-01-15-d7a3] Old form approach. #added:2026-01-15 "
            "#superseded-by:ARCH-2026-07-09-b4d2 #superseded-by:ARCH-2026-07-10-c5e3\n",
        )
        write(
            self.lore / "scopes" / "frontend" / "DECISIONS.md",
            "- [ARCH-2026-07-09-b4d2] New form approach. #added:2026-07-09\n"
            "- [ARCH-2026-07-10-c5e3] Newer form approach. #added:2026-07-10\n",
        )
        r = run_script("list_entries.py", ["--json"], cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("multiple #superseded-by", r.stderr)
        entries = json.loads(r.stdout)
        old = next(e for e in entries if e["id"] == "ARCH-2026-01-15-d7a3")
        self.assertEqual(old["replaced_by"], "ARCH-2026-07-09-b4d2")
        self.assertNotIn("superseded-by", old["text"])

    def test_malformed_superseded_by_warns(self):
        # A non-hex hash (zzzz) is not a valid entry ID; the script must
        # not drop it silently. The tag stays in the text, replaced_by
        # stays None, and a WARN explains why the chain is unresolved.
        write(
            self.lore / "scopes" / "frontend" / "ARCHITECTURE.md",
            "- [ARCH-2026-01-15-d7a3] Old form approach. #added:2026-01-15 "
            "#superseded-by:ARCH-2026-07-09-zzzz\n",
        )
        r = run_script("list_entries.py", ["--json"], cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("malformed #superseded-by", r.stderr)
        entries = json.loads(r.stdout)
        old = next(e for e in entries if e["id"] == "ARCH-2026-01-15-d7a3")
        self.assertIsNone(old["replaced_by"])
        self.assertIn("#superseded-by:ARCH-2026-07-09-zzzz", old["text"])

    def test_scope_and_layer_filters(self):
        write(
            self.lore / "_global" / "ARCHITECTURE.md",
            "- [ARCH-2026-07-09-a3f2] Global fact. #added:2026-07-09\n",
        )
        write(
            self.lore / "scopes" / "frontend" / "DECISIONS.md",
            "- [DEC-2026-02-03-7c19] Frontend fact. #added:2026-02-03\n",
        )
        scoped = self._entries_json(["--scope=frontend"])
        self.assertEqual([e["id"] for e in scoped], ["DEC-2026-02-03-7c19"])
        layered = self._entries_json(["--layer=ARCH"])
        self.assertEqual([e["id"] for e in layered], ["ARCH-2026-07-09-a3f2"])

    def test_human_output(self):
        write(
            self.lore / "_global" / "ARCHITECTURE.md",
            "- [ARCH-2026-07-09-a3f2] Use Next.js App Router. #added:2026-07-09 #verified:2026-07-15\n",
        )
        r = run_script("list_entries.py", [], cwd=self.root)
        self.assertEqual(r.returncode, 0)
        self.assertIn("_global/ARCHITECTURE.md", r.stdout)
        self.assertIn("ARCH-2026-07-09-a3f2", r.stdout)
        self.assertIn("[verified:2026-07-15]", r.stdout)

    def test_no_lore_dir_exits_1(self):
        empty = Path(self._tmp.name) / "empty"
        empty.mkdir()
        r = run_script("list_entries.py", ["--json"], cwd=empty)
        self.assertEqual(r.returncode, 1)
        self.assertIn(".lore/ not found", r.stderr)
        self.assertEqual(r.stdout, "")

    def test_walks_up_from_subdirectory(self):
        write(
            self.lore / "_global" / "ARCHITECTURE.md",
            "- [ARCH-2026-07-09-a3f2] Fact. #added:2026-07-09\n",
        )
        sub = self.root / "src" / "deep" / "nest"
        sub.mkdir(parents=True)
        r = run_script("list_entries.py", ["--json"], cwd=sub)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(json.loads(r.stdout)), 1)

    def test_config_schema_warnings(self):
        write(self.lore / ".config.json", "{}")
        r = run_script("list_entries.py", ["--json"], cwd=self.root)
        self.assertIn("no schema_version", r.stderr)
        write(self.lore / ".config.json", '{"schema_version": 2}')
        r = run_script("list_entries.py", ["--json"], cwd=self.root)
        self.assertIn("schema_version=2 is newer", r.stderr)
        write(self.lore / ".config.json", '{"schema_version": 1}')
        r = run_script("list_entries.py", ["--json"], cwd=self.root)
        self.assertEqual(r.stderr, "")

    def test_non_ascii_entry_round_trips(self):
        write(
            self.lore / "_global" / "CONVENTIONS.md",
            "- [CONV-2026-01-20-b1e8] \u6c38\u4e0d\u63d0\u4ea4\u79d8\u5bc6. #added:2026-01-20\n",
        )
        r = run_script("list_entries.py", ["--json"], cwd=self.root)
        entries = json.loads(r.stdout)
        self.assertEqual(entries[0]["text"], "\u6c38\u4e0d\u63d0\u4ea4\u79d8\u5bc6.")

    def test_ascii_output_when_input_ascii(self):
        write(
            self.lore / "_global" / "ARCHITECTURE.md",
            "- [ARCH-2026-07-09-a3f2] Use Next.js App Router. #added:2026-07-09 #stale:2026-07-15 #superseded-by:ARCH-2026-07-09-b4d2\n",
        )
        r = run_script("list_entries.py", ["--json"], cwd=self.root)
        self.assertTrue(r.stdout.isascii(), r.stdout)


class TestFindStale(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root, self.lore = make_project(self._tmp.name)
        write(
            self.lore / "_global" / "CONVENTIONS.md",
            "# Conventions\n"
            "- [CONV-2026-01-20-b1e8] Old fact never verified. #added:%s\n"
            "- [CONV-2026-08-01-ab12] Recent fact. #added:%s #verified:%s\n"
            "- [CONV-2026-05-01-cd34] Old added, freshly verified. #added:%s #verified:%s\n"
            "- [CONV-2026-07-01-ef56] No date tags at all.\n"
            % (
                days_ago(200),
                days_ago(5),
                days_ago(5),
                days_ago(200),
                days_ago(5),
            ),
        )
        write(
            self.lore / "scopes" / "frontend" / "ARCHITECTURE.md",
            "# Frontend Architecture\n"
            "- [ARCH-2026-01-15-d7a3] Replaced with successor. #added:%s #stale:%s #superseded-by:ARCH-2026-07-09-b4d2\n"
            "- [ARCH-2026-07-09-b4d2] The successor. #added:%s\n"
            "- [ARCH-2026-02-10-ff00] Broken chain. #added:%s #superseded-by:ARCH-2026-07-09-cafe\n"
            "- [ARCH-2026-06-01-1111] Deprecated with no successor. #added:%s #stale:%s\n"
            % (
                days_ago(200),
                days_ago(30),
                days_ago(5),
                days_ago(200),
                days_ago(30),
                days_ago(30),
            ),
        )

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, args=()):
        r = run_script("find_stale.py", ["--json", *args], cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_default_90_day_threshold(self):
        out = self._run()
        self.assertEqual(out["threshold_days"], 90)
        stale_ids = {e["id"] for e in out["stale"]}
        self.assertIn("CONV-2026-01-20-b1e8", stale_ids)
        self.assertNotIn("CONV-2026-08-01-ab12", stale_ids)
        self.assertNotIn("CONV-2026-05-01-cd34", stale_ids)
        self.assertNotIn("CONV-2026-07-01-ef56", stale_ids)

    def test_custom_days_threshold(self):
        out = self._run(["--days=30"])
        self.assertEqual(out["threshold_days"], 30)
        stale_ids = {e["id"] for e in out["stale"]}
        # CONV-2026-05-01-cd34 was added 200 days ago but verified 5 days
        # ago; with a 30-day window it is still fresh.
        self.assertIn("CONV-2026-01-20-b1e8", stale_ids)

    def test_pending_review_and_chains(self):
        out = self._run()
        pending_ids = {e["id"] for e in out["pending_review"]}
        self.assertIn("ARCH-2026-01-15-d7a3", pending_ids)
        self.assertIn("ARCH-2026-02-10-ff00", pending_ids)
        self.assertIn("ARCH-2026-06-01-1111", pending_ids)
        # The replacement itself is current, not pending.
        self.assertNotIn("ARCH-2026-07-09-b4d2", pending_ids)
        # Valid chain is listed; the no-successor sentinel is excluded.
        self.assertIn(
            "ARCH-2026-01-15-d7a3",
            out["chains"]["ARCH-2026-07-09-b4d2"],
        )
        self.assertNotIn(None, out["chains"])

    def test_broken_chain_reported(self):
        out = self._run()
        broken = {b["id"]: b["missing_target"] for b in out["broken_chains"]}
        self.assertIn("ARCH-2026-02-10-ff00", broken)
        self.assertEqual(broken["ARCH-2026-02-10-ff00"], "ARCH-2026-07-09-cafe")

    def test_human_output_ascii(self):
        r = run_script("find_stale.py", [], cwd=self.root)
        self.assertEqual(r.returncode, 0)
        self.assertIn("=== Stale", r.stdout)
        self.assertIn("=== Broken chains", r.stdout)
        self.assertTrue(r.stdout.isascii(), r.stdout)


class TestFindDuplicates(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root, self.lore = make_project(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, args=()):
        r = run_script("find_duplicates.py", ["--json", *args], cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_identical_hash_across_layers_reported(self):
        text = "Use Zustand for state management"
        h = hash_of(text)
        write(
            self.lore / "_global" / "ARCHITECTURE.md",
            "- [ARCH-2026-07-09-%s] %s #added:2026-07-09\n" % (h, text),
        )
        write(
            self.lore / "scopes" / "frontend" / "DECISIONS.md",
            "- [DEC-2026-02-03-%s] %s #added:2026-02-03\n" % (h, text),
        )
        out = self._run()
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["reason"], "identical hash")
        self.assertEqual(out[0]["similarity"], 1.0)
        ids = {out[0]["a"]["id"], out[0]["b"]["id"]}
        self.assertEqual(ids, {"ARCH-2026-07-09-%s" % h, "DEC-2026-02-03-%s" % h})

    def test_similar_text_same_layer(self):
        write(
            self.lore / "scopes" / "frontend" / "CONVENTIONS.md",
            "- [CONV-2026-07-09-ab12] Use Zustand for state management. #added:2026-07-09\n"
            "- [CONV-2026-07-10-cd34] Use Zustand for state management everywhere. #added:2026-07-10\n",
        )
        out = self._run()
        self.assertEqual(len(out), 1)
        self.assertIn("similar text", out[0]["reason"])
        self.assertGreaterEqual(out[0]["similarity"], 0.7)

    def test_high_threshold_drops_similar_but_keeps_identical(self):
        text = "Use Zustand for state management"
        h = hash_of(text)
        write(
            self.lore / "scopes" / "frontend" / "CONVENTIONS.md",
            "- [CONV-2026-07-09-%s] %s #added:2026-07-09\n" % (h, text)
            + "- [CONV-2026-07-10-cd34] We use Zustand for state. #added:2026-07-10\n",
        )
        write(
            self.lore / "_global" / "ARCHITECTURE.md",
            "- [ARCH-2026-07-09-%s] %s #added:2026-07-09\n" % (h, text),
        )
        out = self._run(["--threshold=0.99"])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["reason"], "identical hash")

    def test_candidate_comparison(self):
        write(
            self.lore / "scopes" / "frontend" / "CONVENTIONS.md",
            "- [CONV-2026-07-09-ab12] Use Zustand for state management. #added:2026-07-09\n",
        )
        out = self._run(["--candidate=Use Zustand for state management"])
        self.assertEqual(len(out), 1)
        self.assertIn("candidate similar", out[0]["reason"])
        self.assertEqual(out[0]["a"]["id"], "CANDIDATE-unsaved")

    def test_no_duplicates(self):
        write(
            self.lore / "_global" / "ARCHITECTURE.md",
            "- [ARCH-2026-07-09-ab12] Something unique. #added:2026-07-09\n",
        )
        out = self._run()
        self.assertEqual(out, [])
        r = run_script("find_duplicates.py", [], cwd=self.root)
        self.assertIn("No potential duplicates found.", r.stdout)


class TestHistory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if shutil.which("git") is None:
            raise unittest.SkipTest("git not available on PATH")

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "proj"
        self.lore = self.root / ".lore"
        (self.lore / "_global").mkdir(parents=True)
        (self.lore / "scopes" / "frontend").mkdir(parents=True)
        subprocess.run(
            ["git", "init", "-q", str(self.root)],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "config", "user.email", "test@example.com"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "config", "user.name", "Tester"],
            check=True, capture_output=True,
        )

    def tearDown(self):
        self._tmp.cleanup()

    def _commit_all(self, message):
        subprocess.run(
            ["git", "-C", str(self.root), "add", "-A"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "commit", "-q", "-m", message],
            check=True, capture_output=True,
        )

    def _run(self, args, cwd=None):
        return run_script("history.py", args, cwd or self.root)

    def _entry_fixture(self):
        write(
            self.lore / "scopes" / "frontend" / "ARCHITECTURE.md",
            "# Frontend Architecture\n"
            "- [ARCH-2026-07-09-b4d2] Use react-hook-form for all forms. #added:%s\n"
            % days_ago(10),
        )
        write(
            self.root / "frontend" / "src" / "index.ts",
            "// forms\n",
        )
        self._commit_all("feat(frontend): use react-hook-form")

    def test_entry_form_json(self):
        self._entry_fixture()
        r = self._run(["ARCH-2026-07-09-b4d2", "--json"])
        self.assertEqual(r.returncode, 0, r.stderr)
        payload = json.loads(r.stdout)
        self.assertEqual(payload["entry_id"], "ARCH-2026-07-09-b4d2")
        self.assertEqual(payload["lore_file"], "scopes/frontend/ARCHITECTURE.md")
        self.assertEqual(payload["code_file"], "frontend")
        self.assertEqual(payload["since"], days_ago(10) + "T00:00:00")
        self.assertEqual(payload["since_source"], "entry_added")
        self.assertEqual(len(payload["commits"]), 1)
        c = payload["commits"][0]
        self.assertEqual(c["subject"], "feat(frontend): use react-hook-form")
        self.assertEqual(len(c["short"]), 7)
        self.assertIn("refs", c)

    def test_since_override_source_is_user_arg(self):
        self._entry_fixture()
        r = self._run(["ARCH-2026-07-09-b4d2", "--since=2026-01-01", "--json"])
        payload = json.loads(r.stdout)
        self.assertEqual(payload["since"], "2026-01-01T00:00:00")
        self.assertEqual(payload["since_source"], "user_arg")

    def test_entry_without_added_tag_warns_and_uses_full_history(self):
        write(
            self.lore / "scopes" / "frontend" / "ARCHITECTURE.md",
            "- [ARCH-2026-07-09-b4d2] No date tags here.\n",
        )
        write(self.root / "frontend" / "src" / "index.ts", "// x\n")
        self._commit_all("feat(frontend): scaffold")
        r = self._run(["ARCH-2026-07-09-b4d2", "--json"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("no #added tag", r.stderr)
        payload = json.loads(r.stdout)
        self.assertEqual(payload["since"], "1970-01-01T00:00:00")
        self.assertEqual(payload["since_source"], "entry_added")

    def test_no_lore_dir_exit_2(self):
        empty = Path(self._tmp.name) / "empty"
        empty.mkdir()
        r = self._run(["ARCH-2026-07-09-b4d2"], cwd=empty)
        self.assertEqual(r.returncode, 2)
        self.assertIn(".lore/ not found", r.stderr)

    def test_not_git_repo_exit_4(self):
        nogit = Path(self._tmp.name) / "nogit"
        (nogit / ".lore" / "_global").mkdir(parents=True)
        r = self._run(["ARCH-2026-07-09-b4d2"], cwd=nogit)
        self.assertEqual(r.returncode, 4)
        self.assertIn("Not a git repository", r.stderr)

    def test_unknown_entry_exit_3(self):
        self._entry_fixture()
        r = self._run(["ARCH-1999-01-01-0000"])
        self.assertEqual(r.returncode, 3)
        self.assertIn("not found", r.stderr)

    def test_bad_scope_exit_6(self):
        self._entry_fixture()
        r = self._run(["--scope=nope"])
        self.assertEqual(r.returncode, 6)
        self.assertIn("Scope 'nope' not found", r.stderr)

    def test_follow_superseded_chain(self):
        write(
            self.lore / "scopes" / "frontend" / "ARCHITECTURE.md",
            "- [ARCH-2026-01-15-d7a3] Old forms approach. #added:%s "
            "#stale:%s #superseded-by:ARCH-2026-07-09-b4d2\n"
            "- [ARCH-2026-07-09-b4d2] Use react-hook-form. #added:%s\n"
            % (days_ago(200), days_ago(30), days_ago(10)),
        )
        write(self.root / "frontend" / "src" / "index.ts", "// forms\n")
        self._commit_all("feat(frontend): switch to react-hook-form")
        r = self._run(["ARCH-2026-01-15-d7a3", "--follow-superseded", "--json"])
        self.assertEqual(r.returncode, 0, r.stderr)
        payload = json.loads(r.stdout)
        self.assertEqual(
            [c["entry_id"] for c in payload["chain"]],
            ["ARCH-2026-01-15-d7a3", "ARCH-2026-07-09-b4d2"],
        )
        md = self._run(["ARCH-2026-01-15-d7a3", "--follow-superseded"]).stdout
        self.assertIn("## Chain", md)
        self.assertTrue(md.isascii(), md)

    def test_follow_superseded_on_file_form_warns_and_ignores(self):
        self._entry_fixture()
        r = self._run(["frontend/src/index.ts", "--follow-superseded", "--json"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("[WARN] --follow-superseded only applies", r.stderr)
        payload = json.loads(r.stdout)
        self.assertIsNone(payload.get("chain"))

    def test_scope_form_json(self):
        self._entry_fixture()
        r = self._run(["--scope=frontend", "--json"])
        self.assertEqual(r.returncode, 0, r.stderr)
        payload = json.loads(r.stdout)
        self.assertEqual(payload["form"], "scope")
        self.assertEqual(payload["scope"], "frontend")
        self.assertIn("ARCHITECTURE", payload["layers"])
        result = next(
            item for item in payload["results"] if item["layer"] == "ARCHITECTURE"
        )
        self.assertGreaterEqual(len(result["payload"]["commits"]), 1)

    def test_unrecognized_arg_exit_2(self):
        self._entry_fixture()
        r = self._run(["not-an-entry-or-path"])
        self.assertEqual(r.returncode, 2)
        self.assertIn("unrecognized argument", r.stderr)


if __name__ == "__main__":
    unittest.main()
