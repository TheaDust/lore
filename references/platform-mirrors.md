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
| Windsurf | `.windsurfrules` (root) | — |
| GitHub Copilot | `.github/copilot-instructions.md` | — |
| Continue.dev | `.continue/rules/lore.md` | — |
| LangGraph / DeepAgents | (no file — inject at runtime) | — |

For LangGraph and DeepAgents, the skill does not produce a mirror file. Read `.lore/*.md` directly or ingest into the system prompt at runtime — that ingestion is the user's responsibility.

## Resolution: how `mirror_targets` is computed

When the skill needs to know which platform files to generate (during `init` and `mirror`), it runs the following procedure:

```
resolve_mirror_targets(config, repo_root):

    # 1. Explicit override (Replace semantics)
    if "mirror_targets" in config:
        return list(config["mirror_targets"])

    # 2. Auto-detect existing platform files
    detected = scan_existing_platform_files(repo_root)
    if detected:
        return detected

    # 3. Nothing detected → ask user once, persist, return
    selected = ask_user_multi_select(AGENT_CHOICES)
    write_mirror_targets_to_config(selected)
    return selected
```

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
```

These match the platform table above (default + "Also accepted" filenames).

### Multi-select agent choices

When Step 3 fires, present this question to the user:

| Choice | Primary file written |
|---|---|
| Claude Code | `CLAUDE.md` |
| Cursor | `.cursorrules` |
| Cline | `.clinerules` |
| Aider | `AGENTS.md` |
| Codex | `AGENTS.md` |
| Windsurf | `.windsurfrules` |
| GitHub Copilot | `.github/copilot-instructions.md` |
| Continue.dev | `.continue/rules/lore.md` |

Aider and Codex both map to `AGENTS.md`. Selecting both produces one entry. Selecting nothing is valid — writes `mirror_targets: []` (no mirrors generated).

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

The skill's `init` flow uses the resolution algorithm above to determine targets, then walks the following steps.

```
Step 1: Check whether .lore/ exists
  - absent → create .lore/ + initial empty config
  - present → load existing .lore/.config.json (defaults if missing)

Step 2: Scan existing platform files in repo root
  Returns: list of paths from the candidate set that exist.

Step 3: Classify each detected file
  Three classes:
  a. Already a lore mirror — contains `## Lore` section
  b. User-written — contains `## My notes` but no `## Lore`
  c. Unmarked — neither header present

  For (b) and (c), present per-file choice:
    - Take over: file becomes a two-section mirror; existing content is preserved as My notes.
    - Preserve as-is: file is left alone; NOT added to mirror_targets.
    - Abort: exit init entirely. .lore/ may exist (from Step 1) but no mirror_targets is written.
  For (a), auto-include in mirror_targets.

Step 4: Multi-select question — "Which agents do you use in this project?"
  Default pre-selection: every agent from Step 3 class (a).
  Allow empty selection.
  See "Multi-select agent choices" above.

Step 5: Compute final mirror_targets
  = [primary file for each selected agent]
  + Step 3 class (a) files (force-include — prevents orphans)
  + Step 3 "take over" files
  − duplicates (Aider+Codex → one AGENTS.md)

Step 6: Write .lore/.config.json with mirror_targets populated.

Step 7: Generate initial mirror files
  For each target:
    - absent → full template (## Lore + --- + empty ## My notes)
    - present, has ## Lore → refresh Lore section, preserve My notes verbatim
    - present, take over chosen → old content as My notes, new ## Lore above
    - present, preserve chosen → no write
```

For each generated mirror file, the section template is:

```
## Lore (auto-managed)

<initial or refreshed Lore content>

---

## My notes (free edit)

<preserved or empty>
```

## What gets mirrored

By default, the mirror's Lore section contains:
- `SUMMARY.md` content (top-level digest)
- A scope-tagged index pointing into `.lore/*`

The full per-file content (every entry in every layer) is **not** mirrored by default. Mirrors are entry points, not full copies. Agents that need details should read `.lore/*` directly.

To mirror full content instead, set `mirror_mode: full` in `.lore/.config.json` (see `references/config.md`).

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