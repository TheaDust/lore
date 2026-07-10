# lore `history` command — design

> Date: 2026-07-10
> Status: proposed
> Scope: new command `lore history` + supporting script + reference

## Summary

Add a read-only command `lore history` that, given an existing `.lore/`
entry, a file path, or a scope, lists the git commits that touched the
relevant files since the entry was added. Output is plain Markdown to
stdout (or JSON with `--json`). No writes to `.lore/*`.

The command fills the gap that `lore sync` only inspects `git diff`
(uncommitted/working-tree deltas) and never reads commit history. With
`history`, agents can answer "why does this decision exist?" by pointing
at the commits that introduced or evolved the relevant code.

## Goals

- Provide a way to enumerate commits related to a memory entry or file,
  with the entry's `#added` date as the natural lower bound.
- Stay within lore's "pure file I/O" contract: no network calls, no
  GitHub/GitLab API, no LLM invocation. The agent invoking lore does the
  semantic work.
- Output to stdout only. No writes to `.lore/`, `.lore/audit/`, or any
  mirror file.
- Cross-platform: Python 3.6+, standard library only, no third-party
  dependencies. Behaves identically on Windows / Linux / macOS.
- Reuse the existing scripts/ patterns (`list_entries.py` style,
  `--json` flag, `walk-up` to find `.lore/`).

## Non-goals

- Reading GitHub / GitLab PRs, issues, or comments. The data source is
  the local git CLI only.
- Persisting commit history to disk. `history` is a query, not a sync.
- Semantic matching between commit messages and entry text. The command
  reports commits; the agent decides relevance.
- Modifying `.lore/*` entries to inline commit refs (this would break
  the atomic ≤2-line entry format and is rejected by spec).
- Detecting rewritten history (rebase / squash). The command reads what
  `git log` returns today; it does not track rewritten refs.

## Trigger

The command is **explicit-only**. It does not auto-fire on any
conversation pattern. The user invokes it by name, e.g.:

| User says | Command |
|---|---|
| "lore history DEC-2026-02-03-7c19" | `lore history DEC-2026-02-03-7c19` |
| "lore history frontend/src/store/index.ts" | `lore history frontend/src/store/index.ts` |
| "lore history --scope=frontend" | `lore history --scope=frontend` |
| "查这个 entry 的 git 历史" | `lore history <id>` |
| "this is from before, why did we change it" | does not trigger — needs an explicit id/file |

This matches the existing lore pattern where every command is named and
called explicitly (see SKILL.md "When to trigger" table).

## Command signature

```
lore history <entry-id>            # entry form
lore history <file-path>           # file form
lore history --scope=<name>        # scope form
lore history --since=<YYYY-MM-DD>  # override the default #added window
lore history --json                # JSON output
lore history --help                # usage
```

### Argument dispatch rules

The CLI dispatches based on the first non-flag argument:

1. **Entry form**: the argument matches the regex
   `^[A-Z]+-\d{4}-\d{2}-\d{2}-[a-f0-9]{4}$` (e.g. `DEC-2026-02-03-7c19`).
2. **File form**: the argument contains `/` or starts with `.` (covers
   both `frontend/src/store/index.ts` and `.cursorrules`).
3. **Scope form**: only the `--scope=<name>` flag is given (no positional
   argument). `<name>` must match an existing `scopes/<name>/` directory;
   otherwise error.
4. **No argument**: print usage and exit non-zero.

If the first non-flag argument matches both patterns (e.g. a hypothetical
file named `DEC-2026-02-03-7c19.md`), the entry pattern wins because
it's more specific.

## Architecture

### Components

```
scripts/
  history.py            # new — the command
  list_entries.py       # existing — reused to find entry → file mapping
  ...
references/
  history-command.md    # new — full spec for the command
  ...
SKILL.md                # modified — adds "history" workflow section
README.md               # modified — adds the command to the quick-start
                        #   and the quick-reference table
```

The new script imports nothing from `list_entries.py`; it shells out to
`python scripts/list_entries.py --json` via subprocess, matching the
existing `find_duplicates.py` and `find_stale.py` pattern. One source
of truth for entry parsing.

### Entry → file resolution

1. Run `python scripts/list_entries.py --json`.
2. Filter the JSON list to the matching `id`.
3. From the matching entry, extract:
   - `file` (relative to `.lore/`) — used to find the actual code file
     under the project root
   - `text` — used by the output's "Suggested next step" callout
   - `tags` — extract `#added:<date>` if present (this is the default
     `--since` window)

The code-file mapping is scope-aware and priority-ordered:
- **Backtick path** (highest priority): if the entry text contains a
  backtick-quoted file path (e.g. `see src/store/index.ts`), use it.
- **Scope directory** (fallback): `_global/...` → project root;
  `scopes/<scope>/...` → `<scope>/` directory at the project root
  (e.g. `scopes/frontend/...` → `frontend/`).
- **No match**: error with a clear message including the entry text,
  so the user can pick a file manually and use the file form.

The exact regex used to extract backtick paths and the resolution
algorithm are documented in `references/history-command.md`.

### Git invocation

```
git -C <project_root> log \
    --since=<date> \
    --pretty=format:<format_string> \
    -- <file_path>
```

The `--pretty=format:` is a single delimited line per commit so the
Python script can parse it deterministically. See the data flow section
for the exact format string.

The script invokes git via `subprocess.run` with `check=False`, captures
stdout/stderr, and maps non-zero exit codes to one of the documented
error modes.

## Data flow

For entry form, given `<entry-id>`:

1. **Resolve project root** — walk up from CWD looking for `.lore/`.
   If not found, error: "`.lore/` not found. Run `lore init` first."
2. **Load entry index** — subprocess
   `python scripts/list_entries.py --json`. Parse JSON. If the entry is
   not found, error with the list of available IDs (truncated to 20).
3. **Extract `since` date** — read the entry's tags. If `#added:` is
   present, use it. If not, set `since = "1970-01-01"` and print a
   warning to stderr: "Entry has no `#added` tag; using full history."
4. **Extract code file path** — see "Entry → file resolution" above.
   Priority: backtick-quoted path in entry text → scope directory
   → error.
5. **Invoke git log** — see "Git invocation" above. Capture stdout.
6. **Parse commits** — split by the delimiter, extract:
   - `hash` (full 40-char SHA, displayed as 7-char short)
   - `author` (name only; email dropped)
   - `date` (ISO `YYYY-MM-DD`)
   - `subject` (first line of message)
   - `body` (lines 2+ of message, up to 3 lines, trimmed)
   - `refs` — grep the full message for `(#\d+)`, `Closes #\d+`,
     `Refs #\d+`, `Fixes #\d+`. Stored as a list of strings
     (e.g. `["#234", "Closes #456"]`).
7. **Render output** — Markdown by default, JSON if `--json`.
8. **Exit** — no files written.

For file form, the flow is identical but skips step 2 and 3
(no entry to look up; the file path is the argument; the `--since`
default becomes "1 year ago" or `1970-01-01` depending on whether
`--since` is given).

For scope form, the flow iterates over every `*.md` file in
`scopes/<scope>/` and runs the file form on each, then concatenates
the results under a single Markdown header per layer
(`## Architecture`, `## Decisions`, `## Conventions`).

## Output format

### Default (Markdown)

```markdown
# history: [DEC-2026-02-03-7c19]

> Entry: scopes/frontend/DECISIONS.md
> Since: 2026-02-03 (entry #added date)
> File: frontend/src/store/index.ts
> Commits: 7 (showing all)

## abc1234 (2026-04-12, alice)
Use Zustand v4 with slices pattern
  Refs: #234

## def5678 (2026-06-15, bob)
Migrate to TanStack Query for server state
  Body: "Deprecates the legacy useFetch hook. See RFC-2026-05."

## ... (5 more, use --json to see all)

## Suggested next step
Run `lore sync` to check whether any of these commits
introduce a [REFINED] candidate for this entry.
```

The "Suggested next step" footer is a static, rule-based string. It is
**not** LLM-generated. It exists to remind the agent of the natural
follow-up action. If 0 commits are found, the footer is omitted.

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
      "hash": "abc1234...",
      "short": "abc1234",
      "author": "alice",
      "date": "2026-04-12",
      "subject": "Use Zustand v4 with slices pattern",
      "body": "",
      "refs": ["#234"]
    }
  ]
}
```

## Error handling

All error paths print to stderr and exit with a non-zero code. The
agent caller should treat any non-zero exit as "no result".

| Condition | Stderr message | Exit code |
|---|---|---|
| `.lore/` not found | `.lore/ not found. Run 'lore init' first.` | 2 |
| Entry ID not in index | `Entry <id> not found. Use 'python scripts/list_entries.py' to list IDs.` | 3 |
| Not a git repo | `Not a git repository. 'lore history' requires git; run inside a git repo or use 'lore query' for in-memory answers.` | 4 |
| `git` CLI missing | `git executable not found on PATH.` | 5 |
| Entry has no `#added` | Warning: `Entry <id> has no #added tag; using full history. Output may be long.` (continues with `1970-01-01`) | 0 |
| Scope name invalid | `Scope '<name>' not found. Available: global, frontend, backend, shared` | 6 |
| 0 commits in window | (no error; Markdown shows `> Commits: 0`, JSON has `commits: []`) | 0 |
| `git log` exit non-zero (other) | `git log failed: <stderr>` | 7 |

## Testing strategy

### Manual smoke tests (in a fixture repo)

After implementation, manually verify with a temporary project:

1. `lore history <existing-id>` on a project with a known `.lore/`
   → expect a non-empty Markdown list.
2. `lore history <existing-id> --json` → expect valid JSON parseable
   by `python -c "import json,sys; json.load(sys.stdin)"`.
3. `lore history NONEXISTENT-ID` → expect exit 3 and the "not found"
   stderr message.
4. `lore history` with no args → expect usage and exit 2.
5. `lore history --scope=frontend` in a fixture with 3 entries → expect
   three sections (ARCH / DEC / CONV).
6. `lore history frontend/src/foo.ts` → expect file-form output even
   if no `.lore/` entry mentions the file.
7. Run inside a non-git directory (e.g. `/tmp`) → expect exit 4.

### Unit tests (optional but recommended)

`scripts/test_history.py`, pure standard library:

- `test_parse_format_line` — verify the delimiter-based parser handles
  empty body, multi-line body, and unusual characters in author names.
- `test_extract_refs` — verify the regex catches `(#123)`, `#123`,
  `Closes #456`, `Refs #789`, `Fixes #012`, and ignores email-like
  substrings (e.g. `user@example.com`).
- `test_dispatch` — verify the regex correctly distinguishes entry
  form from file form.

Test fixtures live under `scripts/tests/fixtures/`. Run with:

```
python -m unittest scripts.test_history
```

(Add this to `scripts/README.md` "Testing" section.)

## File changes

| File | Change | Lines (est.) |
|---|---|---|
| `scripts/history.py` | new | +180 |
| `references/history-command.md` | new | +120 |
| `SKILL.md` | modify — add `### history` workflow section + Quick reference row | +50 |
| `README.md` | modify — add `lore history` to quick-start and FAQ | +15 |
| `scripts/README.md` | modify — add `history.py` row to script table + testing notes | +10 |
| `README.zh-CN.md` | modify — mirror the README change in Chinese | +15 |

Total: ~390 lines added, 0 removed, 0 files deleted.

## Migration / compatibility

- No changes to existing commands.
- No changes to `.lore/.config.json` schema.
- No changes to mirror file format.
- The new `history.py` is invoked only by the new `lore history`
  command. Existing scripts are unchanged.
- Users who don't want `history` available can simply not invoke it.
  There is no "feature flag" needed because the command is opt-in.

## Relationship to existing commands

| Command | Writes `.lore/` | Calls git | Output |
|---|---|---|---|
| init | yes | no | summary |
| sync | yes | yes (`diff`) | diff proposal |
| query | no | no | stdout |
| audit | yes (audit/ only) | no | report file |
| compress | yes (SUMMARY) | no | summary |
| mirror | yes (mirror files) | no | report |
| **history (new)** | **no** | **yes (`log`)** | **stdout** |

`history` fills the previously-empty cell "read-only, calls git log".
It does not overlap with any existing command's output or write paths.

## Open questions

None at design time. Resolved during brainstorming:

- ✅ Form: standalone command (not part of `sync`).
- ✅ Data source: git CLI only, no remote API.
- ✅ Output destination: stdout only, no writes.
- ✅ Command signature: must pass an argument; smart dispatch.
- ✅ Relevance filter: time window (entry's `#added`) + file path.
- ✅ Default format: Markdown with `--json` opt-in.
