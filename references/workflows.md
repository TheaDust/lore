# Workflows reference

Detailed reference for the seven lore workflows. [`SKILL.md`](../SKILL.md) gives the one-paragraph summary; this file gives the procedure, output, edge cases, and related docs for each.

## Two-tier trigger model

The skill has two distinct trigger surfaces:

**Tier 1 — Skill loading.** Controlled by the frontmatter description. The skill loads only when the user explicitly invokes `lore <cmd>` or names the skill directly ("lore", "memory bank", "project memory"). Bare "init" / "compress" / "initialize" defer to the agent's native commands.

**Tier 2 — Internal proposals.** Once the skill is loaded for this session, certain commands have internal thresholds for proactive proposals:

| Command | Implicit trigger | Output to user |
|---|---|---|
| `sync` | ≥50 lines / ≥2 dirs; or new module / dir / dep; or new convention in chat | Marker proposal (NEW / STALE / REFINED) |
| `compress` | entries > 500; or SUMMARY missing; or last compress > 30 days | `[COMPRESS NOTICE]` appended to sync proposal |
| `audit` | conflict detected during sync | `[ALERT]` markers in sync output |
| `mirror` | during `compress` if `auto_mirror: true` | Silent (or per-target ask if false) |

`init`, `query`, and `history` are **always explicit** — they need user intent.

---

## `init` — Initialize the memory bank

**Trigger**: explicit only (`lore init`)

**Used when**: starting lore on a new project, or adopting lore into a project that already has platform files (`CLAUDE.md`, `AGENTS.md`, etc.).

### Procedure

1. Check whether `.lore/` exists.
   - Absent → create `.lore/` and write initial `.config.json` with defaults.
   - Present → load existing config (use defaults if missing).
2. Scan existing platform files in repo root using the candidate list in [`platform-mirrors.md`](platform-mirrors.md).
3. Classify each detected file into one of:
   - **(a)** already a lore mirror — contains `## Lore` section → takeover, replace Lore section
   - **(b)** user-written — contains `## My notes` but no `## Lore` → preserve entirely; ask user
   - **(c)** unmarked — neither header → ask user (preserve / take over / abort)
4. If no platform files detected: multi-select agent choices (Claude Code, Cursor, Cline, Aider, OpenCode, etc.), persist `mirror_targets` to config.
5. Determine scopes: monorepo → use [`monorepo-detection.md`](monorepo-detection.md) markers; single-package → `_global/` only.
6. Create `.lore/{_global/, scopes/<scope>/}` with empty layer files.
7. Generate platform mirrors (full two-section template) for newly-created targets.

### Output

- Full `.lore/` directory tree
- Updated platform mirror files (with `## Lore` + `## My notes` sections)
- Persisted `.lore/.config.json` with `mirror_targets`, `schema_version: 1`, defaults

### Edge cases

- **Existing non-lore `CLAUDE.md`** → takeover flow; user's existing content becomes the `## My notes` section
- **Mixed platform files** (e.g., both `CLAUDE.md` and `AGENTS.md`) → each gets its own Lore section
- **No git repo** → `init` works, but `sync` and `history` later require git
- **Monorepo with overlapping scopes** (e.g., frontend AND src/) → ask user which is canonical

### Related docs

- [`monorepo-detection.md`](monorepo-detection.md) — scope detection rules
- [`platform-mirrors.md`](platform-mirrors.md) — per-platform file mapping, two-section structure
- [`config.md`](config.md) — `.config.json` schema

---

## `sync` — Update after a change

**Trigger**:
- **Explicit**: user says `lore sync`
- **Implicit proposal**: ≥50 lines / ≥2 dirs, OR new module / dir / dep, OR new convention discussed in chat

**Used when**: completed a feature, refactor, dependency change, or new convention. Always opt-in (`sync` never runs by itself without proposal or explicit invocation).

### Procedure

1. **Compress threshold check (silent)**:
   - entries > 500 → `[COMPRESS NOTICE]` (defer, do not block)
   - `SUMMARY.md` missing → `[COMPRESS NOTICE]`
   - last `Last compressed:` > 30 days → `[COMPRESS NOTICE]`
2. **Detect the delta** from `git diff` (committed or working tree) and re-scan any new files.
3. **Map files → scopes**: `frontend/src/...` → `scopes/frontend/`; cross-scope (root config, top-level deps) → `_global/`.
4. **Classify each change**:
   - new module / dependency / file structure → `[ARCHITECTURE.md]`
   - new "we picked X because Y" → `[DECISIONS.md]`
   - new "we don't use Z" → `[CONVENTIONS.md]`
   - existing entry contradicted → `[STALE]` (preserve, add `#stale:<today>`)
   - existing entry text needs minor update → `[REFINED]` (keep ID, update `#verified:<today>`)
5. **Emit proposal** with one section per marker type.
6. **User accepts / rejects** per marker (or globally).
7. **Apply accepted changes**: append `[NEW]`, append `#stale:` tag, or replace `[REFINED]` text.

### Output

Updated `.lore/*.md` files. If `[COMPRESS NOTICE]` was triggered, it's appended to the proposal.

### Edge cases

- **Pure typo fixes, lockfile-only changes, README rewording, sub-30-line tweaks** → do NOT propose sync (these are noise)
- **`sync` does NOT update platform mirrors** — that's a separate `mirror` command. Reason: keep `git log` of agent-facing files readable
- **Mid-sync conflicts** → emit `[ALERT]`; user resolves
- **`sync_updates_mirror: true` in config** → re-enables the old behavior (auto-update mirrors on every sync), but at the cost of `git log` noise

### Related docs

- [`stale-new-markers.md`](stale-new-markers.md) — full marker spec and reply semantics
- [`entry-format.md`](entry-format.md) — `#added`, `#verified`, `#stale` tag semantics
- [`config.md`](config.md#sync_trust) — `sync_trust: low | medium | high` controls automatic vs prompted acceptance

---

## `query` — Answer from memory

**Trigger**: explicit only (`lore query <term>` or `lore query <scope>:<term>`)

**Used when**: starting a session, debugging, onboarding, asking "why" questions, writing code that might conflict with existing entries.

### Procedure

1. Read `.lore/SUMMARY.md` as the table of contents.
2. Fuzzy match the query term against entry text and IDs.
3. Optionally drill into specific scope files for fuller context.
4. Return matched entries with stable `[file#ID]` references and one-line summaries.

### Output

Bounded list of matched entries:

```
[_global/DECISIONS.md#DEC-2026-07-11-6137] Picked OpenAI-compatible LLM API
[scopes/backend/CONVENTIONS.md#CONV-2026-07-11-9b89] Embedding has two backends
```

The `[file#ID]` reference lets the agent `cat` the file at that line for full text.

### Edge cases

- **No `SUMMARY.md`** → fall back to scanning all `.lore/*.md` directly
- **Empty term** → return `SUMMARY.md` verbatim (acts as a directory listing)
- **Very broad term** → may return many entries; consider scoping (`<scope>:<term>`) for narrower results
- **Query hits `[STALE]` entries** → still returned, with `[STALE]` flag visible in the agent's reading context

### Related docs

- [`entry-format.md`](entry-format.md) — ID format, scope convention
- [`summary-template.md`](summary-template.md) — what `SUMMARY.md` contains

---

## `audit` — Check memory vs reality

**Trigger**:
- **Implicit**: `[ALERT]` emitted during sync when conflicts detected (see Conflict Resolution in SKILL.md)
- **Explicit**: `lore audit` for periodic health check

**Used when**: quarterly review, before big refactor, when suspecting stale entries, before sharing lore with a new contributor.

### Procedure

1. Run `python scripts/find_stale.py --days=90 --json` to find entries with `#added` > 90 days and no `#verified`.
2. Run `python scripts/find_duplicates.py --json` to find content conflicts.
3. Cross-check entry-referenced code paths (paths inside `[file#ID]` references) against current filesystem.
4. Emit `[ALERT]` report grouped by issue type.

### Output

```
[ALERT] 5 entries may be stale (no #verified in >90 days):
  - ARCH-2026-01-15-d7a3  last verified 2026-04-12
  ...

[ALERT] 2 entries contradict current code:
  - CONV-2026-03-01-1f8c  says "use webpack"; project now uses Vite
```

### Edge cases

- **First-time audit on a fresh `init`** → many old entries will appear stale; expected
- **Large projects** (500+ entries) → report can be long; consider scoping
- **`audit` does NOT modify files** — purely observational. To act on findings, run `sync` with proposal-driven updates

### Related docs

- [`stale-new-markers.md`](stale-new-markers.md) — how stale entries are marked
- [`compatibility.md`](compatibility.md) — when old entries should be archived

---

## `compress` — Build the top-level summary

**Trigger**:
- **Implicit**: `[COMPRESS NOTICE]` during sync (entries > 500 / SUMMARY missing / >30 days since last compress)
- **Explicit**: `lore compress`

**Used when**: `SUMMARY.md` grows stale, want a fresh table of contents, after a batch of syncs, before sharing lore.

### Procedure

1. Run `python scripts/list_entries.py --json` to enumerate every entry.
2. Optionally run `python scripts/find_stale.py --json` to identify entries that shouldn't anchor the summary (recently-stale or long-unverified).
3. For each `(scope, layer)` pair, pick 3–5 most important entries using the selection rule in [`summary-template.md`](summary-template.md).
4. Write `SUMMARY.md` per template.
5. **Stop.** `SUMMARY.md` is the only file written by compress itself. Underlying ARCHITECTURE / DECISIONS / CONVENTIONS files are untouched.
6. **Mirror regeneration** (if `auto_mirror: true` in config): for each `mirror_targets` entry, write to that platform file with content-based dedup. If `auto_mirror: false`, ask per target.

### Output

- Updated `.lore/SUMMARY.md`
- (Optional) updated platform mirror files

### Idempotency

Compress is idempotent: running it twice produces the same `SUMMARY.md` content (modulo the date stamp). Re-running after new `sync`s picks up new entries automatically.

### Edge cases

- **Auto-mirror writes** are content-dedup'd — no-op if byte-identical to existing
- **My notes section** is always preserved in mirror writes
- **Compress never deletes entries** — only writes `SUMMARY.md`
- **No entries** → writes an empty `SUMMARY.md` with `Total entries: 0`

### Related docs

- [`summary-template.md`](summary-template.md) — selection rule, template
- [`platform-mirrors.md`](platform-mirrors.md) — mirror write semantics

---

## `mirror` — Regenerate platform mirrors

**Trigger**:
- **Implicit**: during `compress` if `auto_mirror: true`
- **Explicit**: `lore mirror`

**Used when**: batch of syncs done, want agent-facing files updated, hand-edited `.lore/*.md` and want to sync to mirrors, verify a mirror hasn't drifted.

### Procedure

1. Read the current state of `.lore/SUMMARY.md` and the scope-tagged index.
2. For each configured `mirror_targets` entry, read the existing file and detect the section boundary (`## Lore` / `---` / `## My notes`).
3. Compute the new Lore section content (~500 bytes in index mode).
4. **Content-based dedup**: if the new Lore section content is byte-identical to the existing one, skip writing. Report "No changes needed: `<file>`".
5. Replace the Lore section (full rewrite, no merge with previous content). Preserve the My notes section verbatim.
6. Write the file back. Report "Mirror updated: `<file>`".

### Output

Updated `CLAUDE.md` / `AGENTS.md` / `.cursorrules` / `.clinerules` / etc., or no-op reports if nothing changed.

### Edge cases

- **File has `## Lore` and `---` and `## My notes`** → standard takeover, replace Lore only
- **File has `## My notes` but no `## Lore`** → entire file is treated as user notes; skill does NOT write. User asked to confirm before sync restructures
- **File has neither header** → entire file treated as Lore (no My notes section yet). Subsequent mirror appends `---` + empty My notes section
- **File missing** → create with full two-section template
- **Content-dedup is per-target** — one target may skip while another writes

### Related docs

- [`platform-mirrors.md`](platform-mirrors.md) — full per-platform rules, two-section structure, My notes semantics
- [`stale-new-markers.md`](stale-new-markers.md) — when sync proposes mirror changes

---

## `history` — Show git commits related to a memory entry

**Trigger**: explicit only (`lore history <entry-id>|<file-path>|--scope=<name>`)

**Used when**: investigating "why does this entry exist", debugging, onboarding, finding when a file changed.

### Procedure

Three forms (dispatched by argument type):

| Form | Trigger | Behavior |
|---|---|---|
| Entry | `[LAYER-DATE-HASH]` | Locate entry in `.lore/`, derive its `#added` date and referenced code file, then `git log --since=<date>` |
| File | contains `/` or starts with `.` | Run `git log --since=1970-01-01` on the given path |
| Scope | `--scope=<name>` only | For each `*.md` in `.lore/scopes/<name>/`, run file form on the lore file path itself |

Optional `--since=YYYY-MM-DD` overrides the date filter. Optional `--json` switches to machine-readable output.

### Output

Markdown (default) or JSON:

```markdown
# history: [DEC-2026-02-03-7c19]

  abc1234  2026-05-12  refactor: extract chat agent_loop (#87)
  def5678  2026-03-08  feat: switch chat chain to chat_fast (#74)
```

### Edge cases

- **Not a git repo** → error: `lore history requires git; not a git repository`
- **Entry without `#added` tag** → warning to stderr, uses full history (`--since=1970`)
- **`--since=YYYY-MM-DD` in +0800 timezone with same-day commits** → may return 0 (git filters by UTC); workaround: use `--since=YYYY-MM-DD T00:00:00` or pick the prior day
- **Entry references a file that no longer exists** → entry still found; file's `git log` may be empty

### Related docs

- [`history-command.md`](history-command.md) — full spec, dispatch rules, error codes

---

## Cross-workflow notes

### Typical sequence

```
init
  ↓
[sync ⇄ query ⇄ audit]   ← these three are interchangeable; the agent picks based on context
  ↓
compress                 ← when SUMMARY.md grows stale
  ↓
mirror (or auto via compress if auto_mirror: true)
```

### What writes what

| File | Written by |
|---|---|
| `.lore/SUMMARY.md` | `compress` |
| `.lore/{_global,scopes/<scope>}/<LAYER>.md` | `sync`, manual edits |
| `.lore/.config.json` | `init`, manual edits |
| `<project-root>/<platform files>` | `init`, `mirror`, `compress` (if `auto_mirror: true`) |

### What never happens silently

- File mutation — `sync` proposes, user accepts/rejects
- Platform mirror rewrite on every `sync` (deliberate; separate command)
- `compress` deleting entries (only writes SUMMARY.md)
- Entry marked as `[STALE]` without proposal
- `init` overwriting user-written `CLAUDE.md` without explicit takeover

### Where the helpers live

All Python helpers are in `scripts/`:

| Script | Used by |
|---|---|
| `id_hash.py` | `init`, `sync`, manual entry creation |
| `list_entries.py` | `compress`, `audit` |
| `find_stale.py` | `audit`, `compress` |
| `find_duplicates.py` | `audit` |
| `history.py` | `history` |
| `migrate.py` (planned, v1 not shipped) | schema_version bumps |