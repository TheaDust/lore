---
name: mem-man
description: Framework-agnostic Memory Management for AI coding agents. Use this skill ONLY when the user explicitly invokes a `mem-man` command (`mem-man init` / `mem-man sync` / `mem-man query` / `mem-man audit` / `mem-man compress`) or names the skill directly ("mem-man", "项目记忆", "记忆库"). Do NOT trigger on generic phrases like "init", "initialize project", or "compress" — those may map to the agent's native commands (Claude Code's `/init`, `/compact`, etc.). The skill manages `.mem-man/` as the canonical store and optionally mirrors to CLAUDE.md / .cursorrules / .clinerules / AGENTS.md. Supports multi-scope projects (frontend / backend / shared in monorepos) and long-term compression via SUMMARY.md.
---

# mem-man — Framework-agnostic Memory Management

## What this skill is

A long-term knowledge base for a software project, maintained by AI agents. It is **not** a dev journal or a changelog. It captures the kind of context that normally lives only in the original developer's head:

- What the project is, how it is shaped (architecture)
- Why specific choices were made over alternatives (decisions)
- How code should be written and what to avoid (conventions)

This knowledge is persisted as **plain Markdown files** in `.mem-man/` at the project root. Any agent that can read files can consume them.

## When to trigger

The skill only triggers when the user **explicitly** invokes `mem-man` or names a subcommand. Generic phrases like "init" or "compress" alone are not enough — they may map to the agent's native commands.

| User says (examples) | Command |
|---|---|
| "mem-man init" / "建 mem-man 知识库" / "初始化 mem-man" | `init` |
| "mem-man sync" / "把这个改动同步到 mem-man" / "记录这次的决策到 mem-man" | `sync` |
| "mem-man query" / "查 mem-man" / "项目里约定是什么" | `query` |
| "mem-man audit" / "检查 mem-man" / "记忆还准吗" | `audit` |
| "mem-man compress" / "压缩 mem-man" / "总结一下 mem-man" | `compress` |
| "mem-man mirror" / "更新 CLAUDE.md" / "刷新一下 mirror" | `mirror` |

If the user finishes a non-trivial change without explicitly asking for sync, the skill can still suggest running `mem-man sync` (see sync trigger threshold below).

## Reference index

Detailed specifications live in `references/`. Load these on demand.

| File | When to load |
|---|---|
| `references/entry-format.md` | Writing entries, computing IDs, cross-file references |
| `references/summary-template.md` | Running `compress` — SUMMARY.md schema and selection rules |
| `references/audit-template.md` | Running `audit` — report format and severity definitions |
| `references/monorepo-detection.md` | During `init` — detecting scope boundaries from workspace config |
| `references/stale-new-markers.md` | During `sync` — full marking convention and user reply semantics |
| `references/platform-mirrors.md` | Platform file mapping (CLAUDE.md / .cursorrules / etc.), two-section file structure |
| `references/config.md` | `.mem-man/.config.json` schema and field semantics |
| `scripts/README.md` | Helper scripts (id_hash, list_entries, find_duplicates, find_stale) — also in 中文 (`scripts/README.zh-CN.md`) |

## Memory architecture

### Directory layout

```
.mem-man/
├── SUMMARY.md              # Top-level digest. New agents read this first.
├── _global/                # Cross-scope facts (whole-project architecture, global decisions)
│   ├── ARCHITECTURE.md
│   ├── DECISIONS.md
│   └── CONVENTIONS.md
├── scopes/                 # Per-scope facts
│   ├── <scope-name>/
│   │   ├── ARCHITECTURE.md
│   │   ├── DECISIONS.md
│   │   └── CONVENTIONS.md
│   └── ...
├── draft/                  # Used only by `init`. Proposals pending user confirmation.
├── audit/                  # Used only by `audit`. Reports; never mutates main files.
└── archive/                # Old/superseded entries, kept for history
```

**Scope detection during init:** see `references/monorepo-detection.md` for marker detection across pnpm / Yarn / npm / Lerna / Nx / Rush / Cargo / Go / Bazel. Single-package projects fall back to `_global/` only.

**Decisions placement:**
- Affects ≥ 2 scopes (e.g. "use pnpm workspaces", "TypeScript strict") → `_global/DECISIONS.md`
- Affects exactly one scope → that scope's `DECISIONS.md`

There is no separate metadata file. Every status lives as inline tags on entries themselves.

### Entry format

Each entry is a Markdown bullet (≤ 2 lines), with a layer prefix, a deterministic ID, and inline status tags. See `references/entry-format.md` for the full spec (ID generation via content hash, tag semantics, cross-file reference format, splitting rules).

```markdown
- [ARCH-2026-07-09-a3f2] Use Next.js App Router; reason: streaming + RSC. #added:2026-07-09
- [DEC-2026-02-03-7c19] Chose Zustand over Redux; reason: 60% less boilerplate. #added:2026-02-03
- [CONV-2026-01-20-b1e8] Never commit secrets; use `dotenv` + `.env.local` (gitignored). #added:2026-01-20
```

## Platform mirror

The canonical store is `.mem-man/*`. Agents that expect a single config file at the project root (`CLAUDE.md` for Claude Code, `.cursorrules` for Cursor, `.clinerules` for Cline, `AGENTS.md` for Aider, etc.) read a synced projection of that store.

**A mirror is a synced projection, not a strict derivative.** It contains two sections: a Skill-managed `## Mem-man` section (rewritten on every sync) and a user-editable `## My notes` section (preserved verbatim). Both sections are legitimate mirror content. The user can write personal preferences, temporary instructions, or any project-specific note in the My notes section; the Skill never touches it.

```markdown
## Mem-man (auto-managed)

# .mem-man SUMMARY (synced 2026-07-09)

...auto-generated content from .mem-man/*...

---

## My notes (free edit)

- 回答要简洁
- 中文优先
- 当前在重构用户认证模块
```

**Default behavior:**

- **Init**: missing mirror file → auto-create with both sections. Existing mirror with both sections → refresh Mem-man section, preserve My notes. Existing mirror with only My notes (no Mem-man header) → ask user how to handle. File with no section markers → ask user.
- **Sync / Compress**: controlled by `.mem-man/.config.json#auto_mirror`. Default is `false` (ask per target). When `true`, mirrors update automatically. My notes section is **always** preserved.

By default the Mem-man section contains `SUMMARY.md` plus a scope-tagged index — not the full content. Full-content mirroring is opt-in via `mirror_mode: full`.

See `references/platform-mirrors.md` for the per-platform file mapping and the full two-section structure rules, and `references/config.md` for `.config.json` schema.

LangGraph / DeepAgents typically don't need a mirror file — they read `.mem-man/*.md` directly or ingest into the system prompt at runtime (the user's responsibility).

## Relationship to agent native commands

Several agents have built-in commands with similar names. mem-man does **not** replace them; it manages a different concern (long-term project knowledge vs. session context). The two coexist.

| Agent command | What it does | mem-man equivalent |
|---|---|---|
| Claude Code `/init` | One-shot project scan → generates `CLAUDE.md` | `mem-man init` (creates `.mem-man/` + mirror files) |
| Claude Code `/compact` | Compresses the current conversation context | `mem-man compress` (regenerates `SUMMARY.md` from entries) |
| Cursor `/init` (if present) | Project bootstrap | Same as Claude Code `/init` |

**How they interact:**

- If the user runs `mem-man init` and a non-mem-man `CLAUDE.md` exists, the init takeover check (step 0 in `init`) handles integration.
- If the user runs the agent's native `/init` on a project that already has `.mem-man/`, the skill should ask whether the user wants to take over the existing `CLAUDE.md` or leave it alone.
- If both `mem-man sync` and `/compact` are available, they do unrelated work — run them independently.
- If the user's intent is ambiguous (e.g. they say "init" without "mem-man"), defer to the agent's native `/init`. Do not silently invoke `mem-man init`.

To disable Claude Code's automatic `/init` on a project where `mem-man` is in use, set `"initHintShown": true` in `.claude/settings.json` (see Claude Code docs for current options).

## Workflows

### `init` — Initialize the memory bank

Runs once per project (or to start over).

0. **Takeover check.** For each configured mirror target (e.g. `CLAUDE.md`, `.cursorrules`):
   - If the file does not exist → no action; it will be created later in step 7.
   - If the file exists AND contains a `## Mem-man` section → it's already a mem-man mirror; note it and continue (its My notes will be processed as seed in step 5).
   - If the file exists AND does NOT contain a `## Mem-man` section → it's likely from the agent's native `/init` or hand-written. Show the user:
     - (a) **Take over** — rewrite the file as a two-section mirror. The existing content becomes the My notes section (preserved verbatim, treated as seed knowledge in step 5).
     - (b) **Preserve as-is** — leave the file alone. Remove it from `mirror_targets` for this project (mem-man won't write to it). `.mem-man/` is still generated normally; the user can read `SUMMARY.md` directly or merge manually later.
     - (c) **Abort** — exit init. Nothing is created. The user can decide later.
   - Repeat for each configured mirror target before proceeding.
1. Check if `.mem-man/` already exists. If yes, warn and ask: archive the current one and re-init, or abort?
2. Detect monorepo structure (per `references/monorepo-detection.md`). Propose scope list to the user; let them rename / merge / split before proceeding. No monorepo → `_global/` only.
3. Scan the project (per scope if applicable):
   - Top-level structure, entry points, package manager, language version
   - Config files: `package.json`, `pyproject.toml`, `Cargo.toml`, `tsconfig.json`, `Dockerfile`, `Makefile`, CI
   - `README*`, `CONTRIBUTING*`, existing docs
   - Key dependencies from lockfiles
4. Write proposals to `.mem-man/draft/` mirroring the target layout (`_global/` and per-scope subdirs). Every entry gets `#added:<today>` and a deterministic hash-based ID (see `references/entry-format.md`).
5. For any mirror file that already has a `## Mem-man` section (from step 0), read its My notes section as user-supplied seed knowledge. Parse as atomic bullets into the right layer/scope.
6. **Stop and show the user a summary**: which scopes, how many entries per layer per scope, sample of 5–10 entries, and what mirror files will be (re)generated (or skipped per step 0).
7. On user confirmation: `mv .mem-man/draft/* .mem-man/`, run an initial `compress` to generate `SUMMARY.md`, then (re)generate platform mirrors per the two-section structure — auto-create missing files, refresh Mem-man sections, leave My notes sections intact. Skip any target the user chose "preserve as-is" in step 0.
8. On user rejection: `rm -rf .mem-man/draft/`. Nothing persists.

The `draft/` directory gives a clean rollback path: nothing in `.mem-man/` is real until the user approves.

### `sync` — Update after a change

Runs after the user completes a feature, refactor, or bug fix.

**Trigger threshold — only propose sync when at least one is true:**
- `git diff --stat HEAD` shows ≥ 50 changed lines across ≥ 2 directories
- A new top-level module / directory / dependency was added or removed
- A new convention was explicitly discussed (e.g. user said "from now on we use X")
- The user explicitly invokes `sync` regardless of diff size

Pure typo fixes, lockfile-only changes, README rewording, or sub-30-line tweaks do **not** warrant `sync`.

**Compress threshold check (silent, runs before sync proposal):**
- Total entry count across all files > 500, **or**
- `SUMMARY.md` is missing, **or**
- `SUMMARY.md` last `Last compressed:` date is > 30 days ago

If any of these are true, the skill appends a `[COMPRESS NOTICE]` to the sync proposal. It does not block the sync — the user can defer.

**Procedure:**

1. **Detect the delta** from `git diff` (committed or working tree) and re-scan any new files.
2. **Determine target scope(s)** for each change. Use `git diff --name-only` paths to map files → scopes (e.g. `frontend/src/...` → `scopes/frontend/`). Cross-scope changes (root config files) → `_global/`.
3. **Classify each change** into one layer:
   - New module, new dependency, new file structure → `ARCHITECTURE.md`
   - "We picked X over Y because Z" → `DECISIONS.md`
   - New lint rule, new naming pattern, new "we never do X" → `CONVENTIONS.md`
4. **For each candidate entry**:
   - **Contradicts an existing entry** in the same scope/layer → mark the old one `#stale:<today>`. Emit an `ALERT`.
   - **Refines an existing entry** → update the text in place, bump `#verified:<today>`.
   - **Genuinely new** → append with `#added:<today>` and a new hash ID.
5. **De-duplicate**: before appending, run `python scripts/find_duplicates.py --json` to identify any candidate entry that overlaps with existing entries (same hash, or Jaccard ≥ `--threshold`). For each match, skip the new entry and bump `#verified` on the existing one. If the new entry is genuinely different in meaning (the script flags but doesn't decide), keep both.
6. **Apply trust level** (controlled by `.mem-man/.config.json#sync_trust`, default `"medium"`):

   | Change type | `high` | `medium` (default) | `low` |
   |---|---|---|---|
   | De-duplicate hit (same fact already present) | auto-apply | auto-apply | confirm |
   | Equivalent REFINED (text rewrite, same meaning) | auto-apply | auto-apply | confirm |
   | `NEW` entry | auto-apply | confirm | confirm |
   | `STALE` mark | auto-apply | confirm | confirm |
   | `ALERT` | confirm | confirm | confirm |

   Auto-applied changes are written silently and reported at the end. Confirmation-required changes are bundled into a single diff proposal and shown together.
7. **Generate the proposed diff** (for any confirmation-required changes) using the `[NEW]/[STALE]/[REFINED]/[ALERT]/[COMPRESS NOTICE]` markers. See `references/stale-new-markers.md` for the full convention and user reply semantics.
8. **Stop and wait for user confirmation** for any pending changes. Auto-applied changes need no confirmation.
9. After the user accepts, write to `.mem-man/*` only. **Do not** regenerate platform mirrors from `sync` — this is intentional. See "Mirror update triggers" below for the rationale and the dedicated `mem-man mirror` command.

**Source priority** (when sources disagree):

1. Git diff of changed code (most reliable — shows what actually happened)
2. Static scan of new files (reliable for facts, not for intent)
3. Conversation context (lowest priority — see below)
4. Test/build output (auxiliary — only consulted if 1–3 are ambiguous)

**Conversation context is opt-in.** The skill does **not** automatically mine chat messages for memory updates. It only extracts from conversation when the user explicitly says things like "记录一下" / "remember this" / "this is important". Reason: chat context is high-noise, and silent extraction creates false entries.

**Mirror update triggers.** Platform mirrors (`CLAUDE.md`, `.cursorrules`, etc.) are regenerated on only three occasions, not on every `sync`:

1. `init` completion — first time the mirror is created or restructured
2. `compress` completion — `SUMMARY.md` changed, so mirrors reflect the new digest
3. Explicit `mem-man mirror` command — user forces a regeneration

`sync` only updates `.mem-man/*` files. This is deliberate: mirror files are agent-facing entry points, not a per-change log. Regenerating them on every `sync` would clutter `git log` and dilute the "human-merged" signal that mirror files are supposed to provide. Use `mem-man mirror` after a batch of changes when you want the agent-facing view to catch up.

If a project needs old behavior (mirror updates on every `sync`), set `sync_updates_mirror: true` in `.mem-man/.config.json` (see `references/config.md`).

### `mirror` — Regenerate platform mirrors

Force-regenerate all configured platform mirrors from the current state of `.mem-man/*`.

1. Read current `.mem-man/SUMMARY.md` and the scope-tagged index.
2. For each configured mirror target (per `references/platform-mirrors.md`), read the existing file and detect the section boundary.
3. For each target, compare the new Mem-man section content against the existing one. **Skip writing if content is identical** (content-based dedup; avoids empty `git diff`).
4. If different, replace the Mem-man section; preserve the My notes section verbatim.
5. **Stop.** Report: "Mirror updated: `<file>`" or "No changes needed: `<file>`" per target.

This command exists because most users want `sync` to be fast and unobtrusive, but occasionally need the agent-facing files to reflect recent knowledge. `mirror` is that explicit "publish to agent view" step.

### `query` — Answer from memory

Read-only.

1. Determine which scope(s) the question targets:
   - "this project" / "the whole codebase" / unspecified → `_global/` first, then SUMMARY.md
   - "frontend" / "in the web app" / "the React side" → `scopes/frontend/`
   - "backend" / "the API" → `scopes/backend/`
   - If ambiguous, search SUMMARY.md for clues.
2. Grep the target files for relevant entries. If multi-layer or multi-scope, check all relevant ones.
3. If found: answer concisely, citing fully-qualified entry IDs (e.g. `[scopes/frontend/DECISIONS.md#DEC-2026-02-03-7c19]`). Mention `#verified` date.
4. If not found but inferable from the code: say so explicitly ("Not in memory, but inferable from `frontend/src/store/index.ts`..."). Offer to add it.
5. Never fabricate an entry. If memory doesn't have it, say it doesn't have it.

### `audit` — Check memory vs. reality

Read-only diagnostic. Reports drift; does not fix and does not mutate `.mem-man/*.md` or `SUMMARY.md`.

1. For each entry in `_global/*` and `scopes/*/*`, find the code/config it claims to describe (scoped to the relevant scope's source tree) and compare against current state.
2. Also flag: entries with `#verified` older than 90 days. Run `python scripts/find_stale.py --days=90 --json` to enumerate them mechanically.
3. Write the report to `.mem-man/audit/audit-YYYY-MM-DD.md`, organized by scope. **Do not** mark anything as stale in the main files. **Do not** emit ALERT blocks. See `references/audit-template.md` for the full report format and severity definitions.
4. **Stop.** User reviews the report and decides what to do. To act on findings, the user runs `sync`.

This separation keeps `audit` honest: it observes, it does not edit. ALERT noise is contained to `sync` and `query`, where the agent is about to act on the memory.

### `compress` — Build the top-level summary

Long-term compression. Generates `SUMMARY.md` without modifying any underlying entry file.

1. Run `python scripts/list_entries.py --json` to enumerate every entry. Use the JSON output as the input for the selection step.
2. Optionally run `python scripts/find_stale.py --json` to identify entries that shouldn't anchor the summary (recently-stale or long-unverified).
3. For each (scope, layer) pair, pick 3–5 most important entries using the selection rule in `references/summary-template.md`.
4. Write `SUMMARY.md` per the template in `references/summary-template.md`.
5. **Stop.** `SUMMARY.md` is the only file written. Underlying ARCHITECTURE / DECISIONS / CONVENTIONS files are untouched.
6. Regenerate platform mirrors (this is one of the three mirror update triggers — see "Mirror update triggers" in the `sync` section). If `auto_mirror: true` in config, write automatically. Otherwise ask per target. Content-based dedup: if the new Mem-man section equals the current one, skip the write. My notes section is always preserved.

**Compress is idempotent.** Running it twice produces the same `SUMMARY.md` content (modulo the date stamp). Re-running after new `sync`s picks up new entries automatically.

## Conflict resolution

When the agent's current understanding contradicts a memory entry, **memory wins by default** — but ALERT is emitted only at moments of action, not on every observation.

**Trigger ALERT when**:
- The agent is about to write code that would violate an active (non-stale) memory entry
- The user asks the agent to do something that contradicts memory, and the agent is deciding whether to comply
- `sync` is processing a candidate change that touches a conflicting entry

**Do NOT trigger ALERT for**:
- Temporary debug code or one-off experiments (unless the user asks to keep them)
- Code in `archive/` examples
- `audit` findings (those go in the audit report, not as ALERT)
- Files that look like they violate memory but are gitignored, in `node_modules/`, or in a different scope

```
[ALERT] Conflict detected:
  Memory [_global/CONVENTIONS.md#CONV-2026-01-20-b1e8]: "All API calls go through lib/api.ts"
  Current code: backend/src/api/users.ts:1 imports fetch directly
  Action: Memory is source of truth. Do NOT proceed with the bypass pattern
  unless the user explicitly overrides [CONV-2026-01-20-b1e8].
```

The user then either: (a) confirms memory is wrong and runs `sync` to update it, or (b) explicitly overrides for this case.

## Anti-patterns

- **Don't make this a changelog.** Changelogs list every commit. Memory lists only what future agents need to know to work correctly.
- **Don't store code snippets.** Memory is for facts, not source. Link to files instead (`see src/store/index.ts`).
- **Don't silently overwrite user-edited mirror content.** The My notes section of each mirror file is always preserved verbatim. Sync only rewrites the Mem-man section. Files without proper section structure require explicit user choice before sync restructures them.
- **Don't delete silently.** Stale entries get marked, then archived to `archive/`, never lost.
- **Don't trust the agent's word over its own audit.** If an entry claims `react@18` and the code says `react@16`, the code wins for the audit, but the entry needs an update, not a silent fix.
- **Don't mine conversation for memory unless explicitly asked.** Chat is high-noise; silent extraction corrupts the memory bank.
- **Don't compress without preserving detail.** `compress` writes `SUMMARY.md` but never deletes or edits the underlying entry files.
- **Don't trigger on the agent's native `/init` or `/compact` calls.** mem-man only fires when the user explicitly says `mem-man <command>`. Bare "init" / "compress" / "initialize" is the agent's native command — defer to it. If the user later wants to integrate a native-init `CLAUDE.md` with mem-man, point them at `mem-man init` step 0.

## Quick reference

```
mem-man init      # Step 0 takeover check → scan → draft into .mem-man/draft/ → user confirms → move to .mem-man/.
mem-man sync      # After a non-trivial change, update .mem-man/*.md. Does NOT touch platform mirrors. Trust level controls what auto-applies.
mem-man query     # Read-only. Answer from memory, cite entry IDs with file paths.
mem-man audit     # Read-only. Write .mem-man/audit/audit-<date>.md. No entry file is modified.
mem-man compress  # Generate/refresh SUMMARY.md from existing entries, then update platform mirrors.
mem-man mirror    # Force-regenerate all platform mirrors from current .mem-man/* state. Skips targets whose content is unchanged.
```

Of the six, only `init`, `sync`, `compress`, and `mirror` write files. `init` and `sync` mutate `.mem-man/*.md`. `compress` writes `SUMMARY.md`. `mirror` writes platform mirror files (with content-based dedup). Each requires explicit user confirmation before any file is written unless `auto_mirror: true` is set in `.mem-man/.config.json`. `query` and `audit` are pure read.