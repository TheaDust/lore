# Platform mirrors reference

How `.lore/*` content gets mirrored to platform-specific config files. The main `SKILL.md` covers the high-level rules; this file holds the per-platform mapping, the two-section file structure, and the algorithm that resolves which files to generate (auto-detect by default, explicit override available).

## Platform → file mapping

| Platform | File (default) | Also accepted |
|---|---|---|
| Claude Code | `CLAUDE.md` (root) | `.claude/CLAUDE.md` |
| Cursor | `.cursorrules` (root) | `.cursor/rules/*.mdc` |
| Cline | `.clinerules` (root) | — |
| Aider | `AGENTS.md` (root) | `CONVENTIONS.md` |
| OpenAI Codex | `AGENTS.md` (root) | — |
| OpenCode | `AGENTS.md` (root) | — |
| Windsurf | `.windsurfrules` (root) | — |
| GitHub Copilot | `.github/copilot-instructions.md` | — |
| Continue.dev | `.continue/rules/lore.md` | — |
| LangGraph / DeepAgents | (no file — inject at runtime) | — |

For LangGraph and DeepAgents, the skill does not produce a mirror file. Read `.lore/*.md` directly or ingest into the system prompt at runtime — that ingestion is the user's responsibility.

## Resolution: how `mirror_targets` is computed

When the skill needs to know which platform files to generate (during `init`, `mirror`, and `compress` when `auto_mirror: true`), it runs the following procedure:

```
resolve_mirror_targets(config, repo_root):

    # 1. If config has mirror_targets set, use it verbatim (auto-detect skipped)
    if "mirror_targets" in config:
        return list(config["mirror_targets"])

    # 2. Scan repo root for existing platform files (see Scan candidates)
    detected = scan_existing_platform_files(repo_root)
    if detected:
        return detected

    # 3. Nothing detected → ask user via multi-select, persist to config, return
    selected = ask_user_multi_select(AGENT_CHOICES)
    write_mirror_targets_to_config(selected)
    return selected
```

This is the core resolution used by all three commands. `init` extends it with classification and per-file takeover steps — see "Init-time behavior (full procedure)" below.

### Scan candidates

The auto-detect step checks for the following paths at `repo_root`:

```
CLAUDE.md
.claude/CLAUDE.md
.cursorrules
.clinerules
AGENTS.md
CONVENTIONS.md
.windsurfrules
.github/copilot-instructions.md
.continue/rules/lore.md
.cursor/rules/*.mdc        # glob: any .mdc file under .cursor/rules/
```

These match the platform table above (default + "Also accepted" filenames). The `.cursor/rules/*.mdc` entry is a glob — it's a hit if `.cursor/rules/` exists and contains at least one `.mdc` file.

### Multi-select agent choices

When Step 3 fires, present this question to the user:

| Choice | Primary file written |
|---|---|
| Claude Code | `CLAUDE.md` |
| Cursor | `.cursorrules` |
| Cline | `.clinerules` |
| Aider | `AGENTS.md` |
| Codex | `AGENTS.md` |
| OpenCode | `AGENTS.md` |
| Windsurf | `.windsurfrules` |
| GitHub Copilot | `.github/copilot-instructions.md` |
| Continue.dev | `.continue/rules/lore.md` |

Aider, Codex, and OpenCode all map to `AGENTS.md`. Selecting any combination produces one entry. Selecting nothing is valid — writes `mirror_targets: []` (no mirrors generated).

### When this runs

- `lore init` — always interactive.
- `lore mirror` when `mirror_targets` is absent — also interactive (skill is invoked through chat).
- `lore compress` (when `auto_mirror: true`) — also goes through this resolution if `mirror_targets` is absent.

Both paths use the same function. Once `init` has run, `mirror_targets` is set, so subsequent `mirror` calls hit Step 1 and are silent.

## Two-section file structure

Every mirror file is split into two sections by a `---` separator. The top section is Skill-managed and rewritten on every sync. The bottom section is user-editable and preserved verbatim.

```markdown
## Lore (auto-managed)

# .lore SUMMARY (synced 2026-07-09)

> Last compressed: 2026-07-09
> Total entries: 247 across 3 scopes

## Global
- Monorepo with pnpm workspaces + Turborepo — [_global/ARCHITECTURE.md#ARCH-2026-01-15-d7a3]
...

---

## My notes (free edit)

- Keep answers concise
- Currently refactoring the user auth module
- Prefer English
```

The `---` separator is a literal Markdown horizontal rule. Both sections are plain Markdown so any agent or editor can render them normally.

### Section detection rules

When syncing a mirror file:

1. If the file contains `---` on its own line, that line is the boundary. Everything above is the Lore section, everything below is My notes.
2. If the file contains a `## My notes` header, the My notes section starts at that header and goes to EOF.
3. If neither marker is present, the entire file is treated as the Lore section (i.e. no My notes section). Subsequent sync appends a separator + empty My notes section.
4. If the file is missing the `## Lore` header but has `## My notes`, the entire file is treated as user notes. Skill does not write to it. User is asked to confirm before sync restructures the file.

## Sync-time behavior

**`sync` does not regenerate platform mirrors.** This is intentional — see the "Mirror update triggers" section in `SKILL.md`. The skill only writes `.lore/*.md` during `sync`. To update mirrors after `sync`, the user runs `lore mirror` (or `compress`, which calls mirror generation as a side effect).

If a project needs the old behavior (mirror updates on every `sync`), set `sync_updates_mirror: true` in `.lore/.config.json`.

## Mirror-time behavior (`lore mirror`)

This is the actual write step for platform mirrors.

1. Read the current state of `.lore/SUMMARY.md` and the scope-tagged index.
2. For each configured mirror target, read the existing file and detect the section boundary.
3. Compute the new Lore section content.
4. **Content-based dedup**: if the new Lore section content is byte-identical to the existing one, skip writing. Report "No changes needed: `<file>`".
5. If different, replace the Lore section (full rewrite, no merge with previous content). Preserve the My notes section verbatim.
6. Write the file back. Report "Mirror updated: `<file>`".

The content-based dedup step (4) is the key reason `mirror` can be run frequently without polluting `git log` — most invocations will be no-ops once the mirror is in sync.

## Init-time behavior (full procedure)

The `init` command extends the resolution algorithm above with classification and per-file takeover steps. The full procedure:

1. **Check whether `.lore/` exists.**
   - Absent → create `.lore/` and write an initial empty config.
   - Present → load existing `.lore/.config.json` (use defaults if missing).

2. **Scan existing platform files** in repo root using the same candidate list as the resolution algorithm. Result: list of paths that exist.

3. **Classify each detected file** into one of three classes:
   - **Class (a)** — already a lore mirror: contains `## Lore` section.
   - **Class (b)** — user-written: contains `## My notes` but no `## Lore`.
   - **Class (c)** — unmarked: neither header present.

   For class (b) and (c) files, present a per-file choice:
   - **Take over**: file becomes a two-section mirror; existing content is preserved as My notes.
   - **Preserve as-is**: file is left alone; NOT added to `mirror_targets`.
   - **Abort**: exit init entirely. `.lore/` may exist (from Step 1) but no `mirror_targets` is written.

   Class (a) files are auto-included in `mirror_targets`.

4. **Multi-select question.** "Which agents do you use in this project?" Default pre-selection: every agent corresponding to a class (a) file. Empty selection is allowed — but class (a) files still get included via Step 5.

5. **Compute final `mirror_targets`** by combining three sources and deduplicating:
   - All class (a) files from Step 3 (always included, regardless of Step 4 selection).
   - Files chosen via "take over" in Step 3.
   - Primary files for additional agents the user selected in Step 4 that aren't already covered.

   Dedup: Aider and Codex both map to `AGENTS.md` and collapse to one entry.

6. **Write `.lore/.config.json`** with `mirror_targets` populated.

7. **Generate initial mirror files** for each target:
   - File absent → full template (`## Lore` + `---` + empty `## My notes`).
   - File present with `## Lore` → refresh Lore section, preserve My notes verbatim.
   - File present and "take over" chosen → old content becomes My notes, new `## Lore` above.
   - File present and "preserve" chosen → no write.

For each generated mirror file, the section template is:

```
## Lore (auto-managed)

<initial or refreshed Lore content>

---

## My notes (free edit)

<preserved or empty>
```

## What gets mirrored

The mirror's Lore section is an **index** into `.lore/` — not a copy of its content. This keeps per-session token cost flat (~500 B regardless of project size) and aligns with how platform instruction files (`CLAUDE.md`, `.cursorrules`, etc.) are designed to be used: as small pointers that tell the agent where to find detail on demand.

The agent generating the mirror walks `.lore/` and emits the structure below. Sections appear only when their content exists (adaptive rendering).

### Index template

```
## Lore (auto-managed)

Project memory. Read deeper on demand.

**Structure**:
- Digest: `.lore/SUMMARY.md` (top-level overview)
- Global: `.lore/_global/` (architecture, decisions, conventions)
- Scopes:
  - `<scope_name>` — <scope_dir> (<description>)
  - `<scope_name>` — <scope_dir>
  ...

**Query**: `lore query <term>` or `lore query <scope>:<term>`
**Update**: see the `lore` skill (init / sync / query / audit / compress / mirror)

---
## My notes (free edit)
```

### Field sources

- `<scope_name>` — directory name under `.lore/`.
- `<scope_dir>` — project-root-relative path from `.lore/.config.json#scope_paths` or auto-detection. Omit if unknown.
- `<description>` — extracted from `.lore/<scope>/SUMMARY.md` via the HTML comment `<!-- description: ... -->`. See "Scope description extraction" below. If absent, the description is omitted (scope row still appears, just without parenthetical).

### Section visibility rules

| Section | Visible when |
|---|---|
| `Digest:` line | always |
| `Global:` line | `.lore/_global/` exists and has any entry |
| `Scopes:` block | at least one scope directory exists under `.lore/` |
| `Query:` line | always |
| `Update:` line | always |

### Adaptive renderings

**Empty project** (just initialized, no entries yet):

```
## Lore (auto-managed)

Project memory. Read deeper on demand.

**Structure**:
- Digest: `.lore/SUMMARY.md` (top-level overview)

**Query**: `lore query <term>`
**Update**: see the `lore` skill

---
## My notes (free edit)
```

`Global:` and `Scopes:` blocks omitted.

**Single-scope project**:

```
**Structure**:
- Digest: `.lore/SUMMARY.md`
- Global: `.lore/_global/`
- Scopes:
  - `frontend` — packages/frontend/ (React 18 + TypeScript)
```

`Scopes:` block has one entry.

**Monorepo with multiple scopes**:

```
**Structure**:
- Digest: `.lore/SUMMARY.md`
- Global: `.lore/_global/`
- Scopes:
  - `frontend` — packages/frontend/ (React 18 + TypeScript)
  - `backend` — apps/backend/ (PostgreSQL + Prisma)
  - `shared` — packages/shared/
```

### Scope description extraction

The agent scans `.lore/<scope>/SUMMARY.md` for a line matching `<!-- description: <text> -->`. `<text>` is everything after `description:` until the closing `-->`, trimmed. If found, it appears as the scope description. If not, the scope row is rendered without a parenthetical.

Example `SUMMARY.md` with description:

```
<!-- description: React 18 + TypeScript frontend -->
# Frontend scope

All UI code lives here. ...
```

### What does NOT trigger mirror regeneration

Index content does not change when:
- Individual entries are edited
- `SUMMARY.md` content is updated (the index only points to its path)
- Entry counts change

Index content changes require regeneration when:
- A new scope is added to `.lore/`
- A scope's `SUMMARY.md` `<!-- description: -->` comment changes
- `.lore/_global/` gains or loses its first entry (Global section visibility flips)

## Manual operations

| Command | Effect |
|---|---|
| `lore mirror` | Force-regenerate all configured platform mirrors from current `.lore/*` state. Content-based dedup: skips targets whose new Lore section matches the existing one. |
| `lore mirror reset <file>` | Archive current My notes content to `.lore/.archive/<file>-<date>.md`, then write a clean mirror with only the Lore section. User must confirm. |
| `lore mirror show <file>` | Print the file with the two sections clearly delimited in the output. Pure read. |
| `lore mirror check` | For each configured target, verify it has a `---` separator and a `## My notes` section. Report any structural problems. Read-only. |

## Trigger rules

| Trigger | Behavior |
|---|---|
| `init` confirms draft | Auto-generate mirrors for all configured targets using the init-time rules above. |
| `sync` proposal accepted | Writes to `.lore/*.md` only. Does **not** touch mirrors. User runs `lore mirror` separately to publish. (Override: set `sync_updates_mirror: true` in config to restore old behavior.) |
| `compress` completes | If `auto_mirror: true`, regenerate mirrors (with content-based dedup). Otherwise ask per target. |
| `lore mirror` | Force-regenerate all configured targets with content-based dedup. |
| `query` / `audit` | Never touches mirrors. |