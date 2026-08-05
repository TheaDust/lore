# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`lore` is a **Markdown skill** — a spec read by AI coding agents (Claude Code, Cursor, OpenCode, Cline, Aider, Copilot, LangGraph, DeepAgents) to give them long-term project memory. It is not an application: there is **no build, test runner, linter, type checker, or CI**. Do not look for `package.json` / `pyproject.toml` / `Cargo.toml` — none exist.

The load-bearing "code" is:
- `SKILL.md` — the loadable skill body agents consume (routing, triggers, invariants)
- `references/*.md` — detailed specs agents load on demand; `references/workflows.md` holds the step-by-step procedures for all seven commands
- `scripts/*.py` — stdlib-only Python 3.6+ helpers that the spec calls
- `README.md` + `README.zh-CN.md`, `WORKFLOWS.md` + `WORKFLOWS.zh-CN.md` — bilingual user-facing docs

`lore` is a skill, not a CLI: the seven commands (`init` / `sync` / `query` / `audit` / `compress` / `mirror` / `history`) are phrases a user says to an agent, which the agent runs by following `SKILL.md` and `references/workflows.md`. `WORKFLOWS.md` explains in plain language when each is used; `SKILL.md` routes each command to its step-by-step procedure in `references/workflows.md`.

## The compatibility contract is the central invariant

Read `references/compatibility.md` before any edit. Rules that are easy to break:

- **Add, never subtract.** New fields/files/sections use new names. Removing or renaming is a breaking change: the commit must be prefixed `BREAKING:` (not `feat:`/`fix:`/`docs:`) and name the manual migration. Run the Decision Checklist in compat.md before committing.
- **Never make an entry tag required.** The closed tag set is `#added`, `#verified`, `#stale`, `#superseded-by`; old entries may lack any tag.
- Bump `.lore/.config.json#schema_version` when changing the config schema; old readers ignore unknown fields.
- There is **no migration tool**. If you find yourself writing one, that means a breaking config change is happening — coordinate with the user first.

## Editing the spec (what "done" looks like)

There is no automated test suite; verification is script-driven and structural:

```bash
python scripts/id_hash.py "test entry"        # compute an entry ID hash
python scripts/list_entries.py --json         # enumerate entries (query/audit/compress input)
python scripts/find_duplicates.py --json      # sync step 5: candidate overlap
python scripts/find_stale.py --days=90 --json # audit: unverified / broken chains
python scripts/history.py ARCH-2026-07-10-a3f2  # git history for an entry
```

- E2E: `cd sandbox/mock-todo-app && python ../../scripts/list_entries.py --json`. The expected full flow is in `sandbox/RUN_LOG.md`.
- For spec changes, re-check `references/compatibility.md` against the edit before committing.

## Repo conventions

- **Bilingual docs.** User-facing changes update both `README.md` and `README.zh-CN.md`, and both `scripts/README.md` and `scripts/README.zh-CN.md`.
- **Edit spec + reference together.** The step-by-step procedures live in `references/workflows.md`; each other `references/*.md` backs one of those workflows. Change them and the `SKILL.md` pointers / reference index in the same commit.
- **Trigger phrase discipline.** The frontmatter `description` in `SKILL.md` governs when the skill fires. Don't tighten it so far it stops firing on legit user intent, and don't loosen it so it hijacks agent-native commands (`/init`, `/compact`).
- **Entry ID stability.** IDs are `LAYER-YYYY-MM-DD-XXXX`, `XXXX` = first 4 hex of `sha256(entry text)`. Editing the text produces a new ID; the old one survives in git history only. Compute via `python scripts/id_hash.py "<text>"` (pass the body without inline tags).
- **Mirror contract.** Every platform mirror file has `## Lore (auto-managed)` above a `---` separator and `## My notes (free edit)` below. The skill only rewrites the Lore section; My notes is preserved verbatim across every regeneration.
- **Python script style.** Stdlib only, cross-platform, `stdout` = data channel, `stderr` = warnings, `--json` everywhere it makes sense.

## Things an agent would otherwise miss

- `lore history` shells out to `git` and fails if git isn't on PATH or the project isn't a git repo — the exit codes are spec'd in `references/history-command.md`.
- `sync` trust level is `.lore/.config.json#sync_trust` (default `"medium"`). Changing a default requires updating `references/config.md` and the README config example together.
- The skill must survive cross-host translation — avoid host-specific terminology without a cross-host equivalent (e.g. explain `/init`).
- Gitignored / do not commit: `AGENTS.md` (this repo's session-scoped working guide — this `CLAUDE.md` is the committed equivalent), `sandbox/` (E2E fixture; keep its `.lore/` state in sync with `sandbox/RUN_LOG.md`), `.superpowers/` (internal design artifacts — don't reference them from user-facing docs), `.playwright-mcp/` (tooling state).
