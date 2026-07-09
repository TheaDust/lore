# Platform mirrors reference

How `.mem-man/*` content gets mirrored to platform-specific config files. The main `SKILL.md` covers the high-level rules; this file holds the per-platform mapping and the two-section file structure.

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
| Continue.dev | `.continue/rules/mem-man.md` | — |
| LangGraph / DeepAgents | (no file — inject at runtime) | — |

For LangGraph and DeepAgents, the skill does not produce a mirror file. Read `.mem-man/*.md` directly or ingest into the system prompt at runtime — that ingestion is the user's responsibility.

## Two-section file structure

Every mirror file is split into two sections by a `---` separator. The top section is Skill-managed and rewritten on every sync. The bottom section is user-editable and preserved verbatim.

```markdown
## Mem-man (auto-managed)

# .mem-man SUMMARY (synced 2026-07-09)

> Last compressed: 2026-07-09
> Total entries: 247 across 3 scopes

## Global
- Monorepo with pnpm workspaces + Turborepo — [_global/ARCHITECTURE.md#ARCH-2026-01-15-d7a3]
...

---

## My notes (free edit)

- 回答要简洁
- 当前在重构用户认证模块
- 中文优先
```

The `---` separator is a literal Markdown horizontal rule. Both sections are plain Markdown so any agent or editor can render them normally.

### Section detection rules

When syncing a mirror file:

1. If the file contains `---` on its own line, that line is the boundary. Everything above is the Mem-man section, everything below is My notes.
2. If the file contains a `## My notes` header, the My notes section starts at that header and goes to EOF.
3. If neither marker is present, the entire file is treated as the Mem-man section (i.e. no My notes section). Subsequent sync appends a separator + empty My notes section.
4. If the file is missing the `## Mem-man` header but has `## My notes`, the entire file is treated as user notes. Skill does not write to it. User is asked to confirm before sync restructures the file.

## Sync-time behavior

**`sync` does not regenerate platform mirrors.** This is intentional — see the "Mirror update triggers" section in `SKILL.md`. The skill only writes `.mem-man/*.md` during `sync`. To update mirrors after `sync`, the user runs `mem-man mirror` (or `compress`, which calls mirror generation as a side effect).

If a project needs the old behavior (mirror updates on every `sync`), set `sync_updates_mirror: true` in `.mem-man/.config.json`.

## Mirror-time behavior (`mem-man mirror`)

This is the actual write step for platform mirrors.

1. Read the current state of `.mem-man/SUMMARY.md` and the scope-tagged index.
2. For each configured mirror target, read the existing file and detect the section boundary.
3. Compute the new Mem-man section content.
4. **Content-based dedup**: if the new Mem-man section content is byte-identical to the existing one, skip writing. Report "No changes needed: `<file>`".
5. If different, replace the Mem-man section (full rewrite, no merge with previous content). Preserve the My notes section verbatim.
6. Write the file back. Report "Mirror updated: `<file>`".

The content-based dedup step (4) is the key reason `mirror` can be run frequently without polluting `git log` — most invocations will be no-ops once the mirror is in sync.

## Init-time behavior

1. If the mirror file does not exist → create it with the full template: `## Mem-man` header + initial content + `\n---\n\n## My notes (free edit)\n\n` (empty My notes section).
2. If the mirror file exists with both sections → discard old Mem-man content, preserve My notes content, fill in new Mem-man content.
3. If the mirror file exists with only `## My notes` section (no `## Mem-man` header) → ask the user: skip this mirror / restructure file (move user content below `---`, add new Mem-man section above) / overwrite everything.
4. If the mirror file exists without any section markers → ask the user: skip / treat as My notes (add new Mem-man section above with `---` separator) / overwrite.

## What gets mirrored

By default, the mirror's Mem-man section contains:
- `SUMMARY.md` content (top-level digest)
- A scope-tagged index pointing into `.mem-man/*`

The full per-file content (every entry in every layer) is **not** mirrored by default. Mirrors are entry points, not full copies. Agents that need details should read `.mem-man/*` directly.

To mirror full content instead, set `mirror_mode: full` in `.mem-man/.config.json` (see `references/config.md`).

## Manual operations

| Command | Effect |
|---|---|
| `mem-man mirror` | Force-regenerate all configured platform mirrors from current `.mem-man/*` state. Content-based dedup: skips targets whose new Mem-man section matches the existing one. |
| `mem-man mirror reset <file>` | Archive current My notes content to `.mem-man/.archive/<file>-<date>.md`, then write a clean mirror with only the Mem-man section. User must confirm. |
| `mem-man mirror show <file>` | Print the file with the two sections clearly delimited in the output. Pure read. |
| `mem-man mirror check` | For each configured target, verify it has a `---` separator and a `## My notes` section. Report any structural problems. Read-only. |

## Trigger rules

| Trigger | Behavior |
|---|---|
| `init` confirms draft | Auto-generate mirrors for all configured targets using the init-time rules above. |
| `sync` proposal accepted | Writes to `.mem-man/*.md` only. Does **not** touch mirrors. User runs `mem-man mirror` separately to publish. (Override: set `sync_updates_mirror: true` in config to restore old behavior.) |
| `compress` completes | If `auto_mirror: true`, regenerate mirrors (with content-based dedup). Otherwise ask per target. |
| `mem-man mirror` | Force-regenerate all configured targets with content-based dedup. |
| `query` / `audit` | Never touches mirrors. |