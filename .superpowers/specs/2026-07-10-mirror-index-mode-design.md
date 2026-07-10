# Mirror index mode — design spec

## Context

`lore` mirrors project memory into agent-facing config files (`CLAUDE.md`, `.cursorrules`, `AGENTS.md`, etc.). The current "summary" mode dumps `SUMMARY.md` content plus a scope-tagged index into the mirror. For medium and large projects this costs 5–40 KB of context tokens on every session — sometimes 15–20% of a 200K-token budget.

This conflicts with how `CLAUDE.md` and similar files are designed by their respective vendors: as small instruction files (~1–5 KB) that point agents to deeper context. CLAUDE.md is meant to be an **index**, not a knowledge dump.

This spec replaces the summary/full mirror modes with a single **index mode** — the mirror becomes a ~500-byte pointer into `.lore/`, telling the agent where to find the digest, scopes, and query commands. Agents fetch detail on demand via standard file reads or `lore query`.

## Goals

1. **Index is the only mode.** No more `summary` / `full` choice. The mirror is always an index.
2. **Per-session mirror cost stays flat.** Index is ~500 bytes regardless of project size. Project growth does not increase mirror size.
3. **`SUMMARY.md` content is not duplicated.** The mirror points to `.lore/SUMMARY.md` instead of embedding its content.
4. **Agent can locate any knowledge.** The index lists digest path, global path, all scope paths with one-line descriptions, query syntax, and skill commands.
5. **Existing field stays valid but restricted.** `mirror_mode` is preserved (forward compat) but only `"index"` is accepted; other values are rejected at config load.

## Non-goals

1. **Auto-regeneration on commit.** No git hooks. Users run `lore mirror` (or rely on `compress` to refresh) when they want the index refreshed.
2. **Forcing agent behavior.** The agent decides whether to read `.lore/SUMMARY.md` or call `lore query`. loref just provides the index.
3. **Per-cwd smart filtering.** The mirror does not include "you appear to be in scope X" hints. Generating a stale hint when cwd changes would mislead.
4. **Per-scope mirror files.** Most agents do not load from subdirectories; per-scope files would be ignored.
5. **Backward compatibility for `summary` / `full` mode.** Project is not released; users with old configs simply get a config-load warning and the new index behavior. No automatic migration.

## Config schema change

`.lore/.config.json`:

```jsonc
{
  "schema_version": 1,
  "auto_mirror": false,
  "sync_updates_mirror": false,
  "sync_trust": "medium",
  // mirror_targets: optional, auto-detected if absent
  "mirror_mode": "index"
  // ...
}
```

`mirror_mode` changes:

| Aspect | Before | After |
|---|---|---|
| Allowed values | `"summary" \| "full"` | `"index"` only |
| Default | `"summary"` | `"index"` |
| Behavior on unknown value | warn, fall back to default | **error at config load** |
| Behavior when absent | default `"summary"` | default `"index"` |
| Field removed? | — | **no** — kept for future modes |

`schema_version` stays at `1` (pure behavioral change, no structural break).

## Mirror file structure (index template)

The full index template the AI agent writes into each mirror file:

```markdown
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

- `<scope_name>` — directory name under `.lore/` (e.g., `frontend`, `backend`).
- `<scope_dir>` — project-root-relative path to the scope's source dir, derived from `.lore/.config.json#scope_paths` or auto-detection. If unknown, omit (just ` `<scope_name>``).
- `<description>` — extracted from `.lore/<scope>/SUMMARY.md` via the HTML comment `<!-- description: ... -->`. If the comment is absent, the description line is omitted entirely.

### Section visibility rules

The mirror adapts to project state. Sections appear only when they have content:

| Section | Visible when |
|---|---|
| `Digest:` line | always |
| `Global:` line | `.lore/_global/` exists and has any entry |
| `Scopes:` block | at least one scope directory exists |
| `Query:` line | always |
| `Update:` line | always |

### Scope description extraction

The agent generating the mirror scans `.lore/<scope>/SUMMARY.md` for a line matching:

```
<!-- description: <text> -->
```

Where `<text>` is everything after `description:` until the closing `-->`. Whitespace is trimmed. If found, this text appears as the scope description. If not found, the scope appears with only the path (no description).

Example `SUMMARY.md` with description:

```markdown
<!-- description: React 18 + TypeScript frontend -->
# Frontend scope

All UI code lives here. ...
```

### Adaptive renderings

**Empty project** (just initialized, no entries):

```markdown
## Lore (auto-managed)

Project memory. Read deeper on demand.

**Structure**:
- Digest: `.lore/SUMMARY.md` (top-level overview)

**Query**: `lore query <term>`
**Update**: see the `lore` skill

---
## My notes (free edit)
```

(`Global:` and `Scopes:` blocks omitted.)

**Single-scope project**:

```markdown
**Structure**:
- Digest: `.lore/SUMMARY.md`
- Global: `.lore/_global/`
- Scopes:
  - `frontend` — packages/frontend/ (React 18 + TypeScript)
```

(`Scopes:` block has one entry.)

**Monorepo with multiple scopes**:

```markdown
**Structure**:
- Digest: `.lore/SUMMARY.md`
- Global: `.lore/_global/`
- Scopes:
  - `frontend` — packages/frontend/ (React 18 + TypeScript)
  - `backend` — apps/backend/ (PostgreSQL + Prisma)
  - `shared` — packages/shared/
```

## Mirror-time behavior

The `lore mirror` command (and `compress` when `auto_mirror: true`) writes the index template above to each resolved target. The change vs the previous summary mode is purely in the rendered content — the rest of the mirror procedure is unchanged:

1. Resolve targets via the auto-detect algorithm.
2. For each target:
   - Compute new index content from current `.lore/` state.
   - If new content is byte-identical to existing → skip (content-based dedup).
   - Else → replace `## Lore (auto-managed)` section, preserve `## My notes (free edit)` verbatim.
3. Report `Mirror updated: <path>` or `No changes needed: <path>` per target.

Index content changes require mirror regeneration when:
- A new scope is added to `.lore/`
- A scope's `SUMMARY.md` `<!-- description: -->` comment changes
- `auto_mirror: true` triggers `compress` to also rewrite mirrors

Index content does **not** change when:
- Individual entries are edited
- `SUMMARY.md` content is updated (index only points to its path)
- Entry counts change

This means index regeneration is needed less often than summary regeneration, reducing `lore mirror` invocation frequency in steady state.

## Agent behavior expectations

The agent reading a mirror file sees the index and is expected to:

1. **On session start**: read the mirror (automatic — agents do this).
2. **On a generic project question**: read `.lore/SUMMARY.md` directly with the standard Read tool.
3. **On a specific question**: run `lore query <term>` or `lore query <scope>:<term>`.
4. **For scope-specific work**: read `.lore/<scope>/SUMMARY.md` then specific entries as needed.

loref does **not** enforce this behavior. The agent's training to "follow CLAUDE.md instructions and use available tools" handles it. The skill's `SKILL.md` does not need a new section for "how to use the index" — agents discover the workflow from the index text and the existing `lore query` documentation.

## Documentation updates

| File | Change |
|---|---|
| `references/platform-mirrors.md` | Replace the "What gets mirrored" section with the new index template + adaptive rendering rules. Remove discussion of `summary`/`full` modes. Add the `<!-- description: -->` extraction rule. |
| `references/config.md` | Update `mirror_mode` field description: only `"index"` accepted, default `"index"`, other values error. Remove `summary`/`full` discussion. |
| `SKILL.md` | Line 116 ("By default the Lore section contains `SUMMARY.md` plus a scope-tagged index…") updated to describe the index structure. |
| `README.md` and `README.zh-CN.md` | Config example `"mirror_mode": "summary"` → `"mirror_mode": "index"`. Add a new "Token cost" section explaining the per-session mirror cost and how index mode keeps it flat. |

## Backward compatibility

Project is not released. Existing user (if any) with `mirror_mode: "summary"` in `.lore/.config.json`:

- Config-load error: `Unsupported value for `mirror_mode`: "summary". Only "index" is accepted.`
- User must change value to `"index"` (or remove the field to use the new default).
- No automatic migration. No data loss (`.lore/` content is unchanged; only the mirror generation behavior changes).

## Testing strategy

Pure documentation change, no Python code touched. Manual verification of three scenarios:

1. **Empty project** — run `lore init`, `lore mirror`. Verify mirror file shows only Digest + Query + Update sections, no Global / Scopes blocks.
2. **Single-scope project** — populate `.lore/_global/` and `.lore/frontend/` with `<!-- description: ... -->`. Verify mirror shows one scope row with description.
3. **Monorepo** — populate multiple scopes, mix of with-description and without-description. Verify all scopes appear, descriptions only where comment is present.

Plus a content-based dedup verification: run `lore mirror` twice without changing `.lore/`. Second run reports `No changes needed` for all targets.

No automated test harness added — matches existing pattern for descriptive skill procedures.