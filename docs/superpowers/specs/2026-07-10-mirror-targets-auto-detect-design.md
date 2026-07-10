# Auto-detect mirror targets — design spec

## Context

`lore` is a framework-agnostic memory skill for AI coding agents. It stores project knowledge canonically in `.lore/` and **mirrors** an agent-facing summary to platform-specific files (`CLAUDE.md`, `.cursorrules`, `.clinerules`, `AGENTS.md`, etc.) that each vendor's agent auto-loads.

Today, the list of mirror files is configured explicitly via `.lore/.config.json#mirror_targets`. The default is `["CLAUDE.md"]`. To use Cursor or Aider, the user must hand-edit the config. This is friction — most projects just want lore to "figure out which agents are in use and write the right files."

This spec replaces explicit-only configuration with **auto-detection + explicit override**: by default lore scans the repo for existing platform files and asks once at `init` time which agents the project uses. Users who want fine-grained control can still set `mirror_targets` to override.

## Goals

1. **Zero-config for common cases.** If `CLAUDE.md` / `.cursorrules` / etc. already exist in the repo, lore treats them as targets with no user action.
2. **Multi-agent friendly.** A project using Claude Code + Cursor should generate both `CLAUDE.md` and `.cursorrules` from a single `init` run.
3. **Explicit override still works.** Power users keep full control via `mirror_targets` (Replace semantics).
4. **No new config field.** All state fits in the existing `mirror_targets` field — now optional instead of implicitly required.
5. **No silent file creation.** When nothing is detected and lore has to ask, it asks — never silently writes a file based on a guess.

## Non-goals

1. **Runtime agent detection via env var.** Out of scope. Auto-detection is "existing files in repo" + "ask once at init", not "read `LORE_AGENT` at every call".
2. **A separate `primary_agent` field.** Rejected — `mirror_targets` carries all the needed information.
3. **Non-interactive fallback.** YAGNI. lore is invoked through the skill path (AI agent chat); when no detection is possible, ask. If a CLI script is added later, that script can revisit this.
4. **Auto-detection of "Also accepted" filename alternates via user prompts.** Alternates (e.g. `CONVENTIONS.md`, `.claude/CLAUDE.md`, `.cursor/rules/*.mdc`) only enter `mirror_targets` via the existing-files scan, not via the multi-select question.
5. **Backward-compatibility migration logic.** Project has not been released. Document the change in `references/platform-mirrors.md` and `references/config.md`; no automated migration needed.

## Config schema change

`.lore/.config.json` — `mirror_targets` becomes **optional**.

```jsonc
{
  "schema_version": 1,
  "auto_mirror": false,
  "sync_updates_mirror": false,
  "sync_trust": "medium",
  // mirror_targets: OPTIONAL — auto-detect fills in if absent
  // - present (any value, including []): used verbatim (Replace)
  // - absent: auto-detection runs
  "mirror_mode": "summary"
  // ...
}
```

No new fields. `schema_version` stays at `1` (the change is purely behavioral).

`references/config.md` updates: remove the "Default: `['CLAUDE.md']`" sentence; replace with "Optional. If absent, mirror targets are auto-detected (see `references/platform-mirrors.md`)."

## Resolution algorithm

A single function used by both `init` and `lore mirror`:

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

### Scan candidates (existing files)

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

Each entry's presence is checked against `repo_root`. The list matches the platform table in `references/platform-mirrors.md` (default + "Also accepted" filenames).

### Multi-select choices

When Step 3 fires, the agent presents a multi-select question to the user:

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

Note: Aider and Codex both map to `AGENTS.md` — selecting both keeps a single entry in `mirror_targets`.

Default pre-selection: every agent corresponding to a file already detected in Step 2. If none detected, all boxes start unchecked (user picks at least one or accepts empty).

Empty selection is allowed — it writes `mirror_targets: []`, which means "no mirrors" (existing opt-out path).

### When this function runs

- During `lore init` (always interactive — user is invoking init).
- During `lore mirror` when `mirror_targets` is absent in config (also interactive — invoked via skill chat).

Both paths use the same function. The "ask once, persist" semantics means after `init`, `mirror_targets` is always set, so `mirror` will hit Step 1 on subsequent runs.

## Init detailed flow

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
  For (a), auto-include in mirror_targets.

Step 4: Multi-select question — "Which agents do you use in this project?"
  Default pre-selection: every agent from Step 3 class (a).
  Allow empty selection.
  See the table above for choice ↔ file mapping.

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

## Mirror run-time flow

```
lore mirror:
    1. Load .lore/.config.json (defaults if missing).
    2. targets = resolve_mirror_targets(config, repo_root)
    3. For each target in targets:
         - read existing file (if any)
         - detect section boundary (## Lore / --- / ## My notes)
         - compute new Lore section from .lore/SUMMARY.md + scope index
         - if new Lore byte-identical to existing → skip (content-based dedup)
         - else → replace Lore section, preserve My notes verbatim
         - report "Mirror updated: <path>" or "No changes: <path>"
    4. Targets list is empty (e.g., user picked nothing in init) → report
       "No mirror targets configured. Set mirror_targets in .lore/.config.json
       or run lore init again."
```

The existing content-based dedup (already implemented in the mirror procedure) is preserved. The change here is solely in **how `targets` is computed**.

## Edge cases

1. **Repo has `CLAUDE.md` only, user never ran init.** Auto-detect picks up `CLAUDE.md`. Mirror uses it.
2. **Repo has no platform files, user never ran init.** First `init` or `mirror` call asks multi-select, persists.
3. **User selects zero agents in init, no existing files.** `mirror_targets = []`. Mirrors are not generated. User can edit config later to add targets.
4. **User selects Aider + Codex.** Both map to `AGENTS.md`. One entry written.
5. **User picks Claude Code + `CONVENTIONS.md` already exists with `## Lore` section.** Claude Code → `CLAUDE.md` (added by selection); `CONVENTIONS.md` is class (a) so force-included by Step 5. Result: `["CLAUDE.md", "CONVENTIONS.md"]`. If `CONVENTIONS.md` lacks `## Lore`, the user is prompted take over / preserve; preserve removes it from `mirror_targets`.
6. **User selects "preserve" for an existing `.cursorrules`.** File is left alone, `.cursorrules` NOT in `mirror_targets`. User can hand-write content; lore will not touch it.
7. **User edits `.lore/.config.json` to remove `mirror_targets` after init.** Next `mirror` call re-runs auto-detect (Step 2). If nothing detected, asks again (Step 3).
8. **Project contains a `.cursorrules` with `## Lore` that the user did NOT select.** Step 5 force-includes it (class (a) rule). User must hand-remove from `mirror_targets` post-init if they don't want it managed. If `.cursorrules` lacks `## Lore`, the user is prompted; only "take over" adds it to `mirror_targets`.

## Backward compatibility

Project has not been released; no migration step. Behavior change for users with `.lore/.config.json` that **does not** set `mirror_targets`:

- Before: implicit default `["CLAUDE.md"]`. `CLAUDE.md` always generated.
- After: scan + ask. If `CLAUDE.md` exists, still generated. If not, user is asked.

Users who relied on the implicit `["CLAUDE.md"]` default should set it explicitly in `.config.json` if they want the old behavior preserved.

Users who already set `mirror_targets` explicitly are unaffected (Replace semantics).

## Documentation updates

1. **`references/platform-mirrors.md`** — replace the "Platform → file mapping" section's surrounding prose with:
   - Document that `mirror_targets` is now optional.
   - Describe the resolution algorithm (Replace → scan → ask).
   - Document the multi-select agent choices.
   - Update init flow to Steps 1–7 above.
   - Update the manual operations table if needed (no semantic change to `lore mirror`/`lore mirror reset`/`lore mirror show`/`lore mirror check` — they all keep their behavior).
2. **`references/config.md`** — update `mirror_targets` field description:
   - Remove "Default: `['CLAUDE.md']`".
   - Add: "Optional. If absent, mirror targets are auto-detected (see `references/platform-mirrors.md`). When present, used verbatim (Replace semantics)."
3. **`SKILL.md`** — Section "Mirror update triggers" and the `init` procedure reference the new behavior. The reference index entry for `references/platform-mirrors.md` may need a one-line update noting the auto-detection capability.

## Testing strategy

Pure documentation + manual verification, no new code. Three scenarios:

1. **Fresh project, no platform files.** Run `lore init`, verify multi-select question appears with no pre-selection, verify `mirror_targets` is written.
2. **Project with `CLAUDE.md` and `.cursorrules` already present.** Run `lore init`, verify both are pre-selected, verify per-file take-over/preserve question fires for any file lacking `## Lore`, verify `mirror_targets` is written with both.
3. **Project with `mirror_targets` set explicitly in `.config.json`.** Run `lore mirror`, verify the explicit list is used and auto-detect does not run.

Verify manually with a temp repo for each. No automated test harness needed for the procedural mirror logic (which is already the case for `lore init` itself).