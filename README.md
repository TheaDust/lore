# lore

<p align="center">
  <img src="docs/lore-poster.svg" alt="lore" width="100%">
</p>

<p align="center"><em><strong>lore</strong> (noun) — a body of traditions and knowledge on a subject, passed from person to person. — Oxford English Dictionary</em></p>

<p align="right"><a href="README.zh-CN.md">简体中文</a> · English (this page)</p>

> Framework-agnostic project memory for AI coding agents.

A long-term knowledge base for software projects, maintained by AI agents. Captures the kind of context that normally lives only in the original developer's head — architecture, decisions, conventions — and persists it as plain Markdown files that any agent can consume.

> **lore is a SKILL, not a CLI tool.** It is a Markdown spec ([`skill/SKILL.md`](skill/SKILL.md)) that AI coding agents — Claude Code, Cursor, OpenCode, Cline, Aider, GitHub Copilot — read to gain long-term project memory. You do not `npm install` or `pip install` lore; you give your agent the URL and ask it to install the skill. From then on, phrases like `lore init` and `lore sync` are commands you say to your agent, **not** commands you type in a terminal. There is no `lore` binary on your `PATH`.

## Installation

The agent-facing skill lives in `skill/` — that directory is the install unit.

```bash
git clone https://github.com/TheaDust/lore.git /tmp/lore
cp -r /tmp/lore/skill <your-agent-skills-dir>/lore
# e.g. cp -r /tmp/lore/skill ~/.claude/skills/lore
```

Or, simpler — tell your agent:

> Install https://github.com/TheaDust/lore as a skill.

Each agent host loads skills from its own directory (`~/.claude/skills/` for Claude Code, `<project>/.claude/skills/` for project-scoped, etc.). Your agent knows its own skills directory and can clone the repo into the right place.

> Looking for a specific doc? Jump to: [Quick start](#quick-start) · [What it looks like](#what-this-looks-like) · [What lives in `.lore/`](#what-lives-in-lore) · [Seven workflows](#seven-workflows) · [Platform mirrors](#platform-mirrors) · [Configuration](#configuration) · [Upgrading](#upgrading) · [FAQ](#faq). Full reference docs live in [`skill/references/`](skill/references/). **Want plain-language "when to use each workflow"?** See [`WORKFLOWS.md`](WORKFLOWS.md) (also in [中文](WORKFLOWS.zh-CN.md)).

## What it solves

When you work on a project across multiple AI tools (Claude Code, Cursor, Cline, GitHub Copilot, Aider, LangGraph agents, DeepAgents) and across many sessions, context gets lost:

- **Every new session re-explains the project.** "We're using Next.js App Router, not Pages. Use Zustand, not Redux. Don't commit secrets."
- **Decisions are forgotten.** "Why did we pick X over Y?" → "I don't remember, let me ask the team."
- **Agents disagree with each other.** Cursor follows `.cursorrules`, Claude Code follows `CLAUDE.md`, but the two files drift apart.
- **Onboarding takes weeks.** New members / new agents need to learn the conventions from scratch.

lore maintains a single source of truth (`.lore/`) and projects it into whatever config files your agents already read. It tracks *why* decisions were made, not just *what* the code does, and keeps that history across sessions and tools.

## Quick start

The commands below are **phrases you say to your agent** — there is no `lore` binary. With this skill loaded, your agent runs each phrase through the workflows defined in [`skill/SKILL.md`](skill/SKILL.md) and [`skill/references/workflows.md`](skill/references/workflows.md). Anything you'd normally type into a terminal goes to the agent instead.

```bash
# 1. Initialize (run once per project)
lore init
# Walks the project, drafts entries, asks for confirmation, creates .lore/

# 2. After a non-trivial change
lore sync
# Spans commits + uncommitted changes; flags contradictions as ALERT; proposes [NEW]/[STALE]/[REFINED]; waits for your call

# 3. After many changes, refresh the agent-facing summary
lore compress
# Regenerates SUMMARY.md; mirror update depends on `auto_mirror` (default: asks per target)

# 4. Force a mirror refresh (e.g. after hand-editing .lore/)
lore mirror
# Rewrites CLAUDE.md and other platform files from current state
```

Three read-only commands round out the toolkit:

```bash
lore query                          # Answer a question from memory, cite entry IDs
lore audit                          # Check memory vs. reality, write report to .lore/audit/
lore history DEC-2026-02-03-7c19    # Show git commits that touched an entry's code
lore history frontend/src/store.ts  # ...or a file
lore history --scope=frontend       # ...or every lore file in a scope
lore history --json                 # machine-readable
```

## What this looks like

### Querying memory

> You: "How does this project authenticate API requests?"
> Agent (uses `lore query auth`):

```
Found 6 entries matching 'auth':

  [_global/DECISIONS.md#DEC-2026-07-10-6d9c]
    Opaque base64 tokens over JWT; reason: simpler revocation, no library dep.

  [scopes/backend/ARCHITECTURE.md#ARCH-2026-07-10-59ac]
    Auth helpers in backend/app/auth.py:
    hash_password, issue_token, login_required decorator.

  [scopes/backend/CONVENTIONS.md#CONV-2026-07-10-84e3]
    Missing/invalid token returns 401; resource not found returns 404.

  [scopes/frontend/ARCHITECTURE.md#ARCH-2026-07-10-6de2]
    Auth token stored in localStorage under todo.auth.token key.

  [scopes/frontend/DECISIONS.md#DEC-2026-07-10-c1ea]
    Axios over raw fetch; reason: interceptors for auth header injection.
```

Every answer cites the exact `[file#ID]` so you can `cat` the entry or run `lore history <ID>` to see why the decision exists.

### What `CLAUDE.md` looks like

`lore` keeps per-session cost flat by emitting a small index, not the full memory:

```markdown
<!-- LORE:START -->
## Lore (auto-managed)

Project memory at `.lore/`. Before project-specific questions, read `.lore/SUMMARY.md` as the digest, then open the referenced entries (`.lore/_global/`, `.lore/scopes/`) for the full text before answering or deciding; cite entry IDs (e.g. `_global/ARCHITECTURE.md#ARCH-2026-01-15-d7a3`) when using memory.

**Structure**:
- Digest: `.lore/SUMMARY.md` (top-level overview)
- Global: `.lore/_global/` (architecture, decisions, conventions)
- Scopes: `.lore/scopes/`
  - `.lore/scopes/backend/` (Flask 3 + SQLAlchemy 2 + pytest; Python 3.11+)
  - `.lore/scopes/frontend/` (React 18 + TypeScript + Vite + Zustand + Axios)
  - `.lore/scopes/shared/` (TypeScript types mirrored as Python dataclasses)

**Query**: `lore query <term>` or `lore query <scope>:<term>`
**Update**: see the `lore` skill (init / sync / query / audit / compress / mirror / history)
<!-- LORE:END -->

---
## My notes (free edit)

- Anything you write here is preserved verbatim across every sync.
```

The mirror file opens with an imperative sentence (e.g. "Project memory at `.lore/`. Before project-specific questions, read `.lore/SUMMARY.md` as the digest, then open the referenced entries for the full text before answering or deciding.") so the consuming agent has a clear trigger to load memory. The line lives in `## Lore (auto-managed)` and is rewritten on every `compress` or `lore mirror` regeneration.

### Git traceability with `lore history`

> `lore history DEC-2026-07-10-e45d` (asking "why did we choose bcrypt?")

```
# history: [DEC-2026-07-10-e45d]

> Entry: scopes/backend/DECISIONS.md
> Since: 2026-07-10T00:00:00 (entry #added date)
> File: backend
> Commits: 2 (showing all)

## 9f264f4 (2026-07-10, Lore Tester)
feat(backend): add alembic migrations and switch password hashing to bcrypt

## ed2b288 (2026-07-10, Lore Tester)
feat(backend): password hashing and JWT-style auth tokens
```

The agent reads the commit messages and tells you *why* — without you having to manually dig through `git log`.

## What lives in `.lore/`

```
.lore/
├── SUMMARY.md                    # Top-level digest; new agents read this first
├── .config.json                  # Optional config (auto_mirror, sync_trust, ...)
├── _global/                      # Cross-scope facts
│   ├── ARCHITECTURE.md
│   ├── DECISIONS.md
│   └── CONVENTIONS.md
├── scopes/                       # Per-scope facts (frontend / backend / shared)
│   └── <scope>/
│       ├── ARCHITECTURE.md
│       ├── DECISIONS.md
│       └── CONVENTIONS.md
├── draft/                        # Used by `init` for proposals pending confirmation
└── audit/                        # Used by `audit` for reports
```

Each entry is a single Markdown bullet (≤ 2 lines) with a deterministic ID and inline status tags:

```markdown
- [ARCH-2026-07-09-a3f2] Use Next.js App Router; reason: streaming + RSC. #added:2026-07-09
- [DEC-2026-02-03-7c19] Chose Zustand over Redux; reason: 60% less boilerplate. #added:2026-02-03 #verified:2026-06-15
- [CONV-2026-01-20-b1e8] Never commit secrets; use `dotenv` + `.env.local` (gitignored). #added:2026-01-20
```

Entries can also carry `#superseded-by:LAYER-YYYY-MM-DD-xxxx`, which points to the entry that replaced this one — letting `find_stale`, `history`, and `compress` walk the replacement chain instead of inferring it from prose.

For the full format spec (ID generation, tags, splitting rules), see [`skill/references/entry-format.md`](skill/references/entry-format.md).

## Seven workflows

| Command | What it does | Writes | Reference |
|---|---|---|---|
| `init` | First-time project scan; drafts entries; user confirms | `.lore/*` + platform mirrors | [workflows](skill/references/workflows.md#init--initialize-the-memory-bank) |
| `sync` | Detects code changes; proposes updates; user approves | `.lore/*` only (not mirrors) | [workflows](skill/references/workflows.md#sync--update-after-a-change) |
| `query` | Read-only; answers from memory with entry IDs | nothing | [workflows](skill/references/workflows.md#query--answer-from-memory) |
| `audit` | Read-only; checks memory vs. current code; writes report | `.lore/audit/*` only | [workflows](skill/references/workflows.md#audit--check-memory-vs-reality) |
| `compress` | Generates `SUMMARY.md` from current entries | `SUMMARY.md` + platform mirrors | [workflows](skill/references/workflows.md#compress--build-the-top-level-summary) |
| `mirror` | Force-regenerate platform mirrors (with content dedup) | `CLAUDE.md`, `.cursorrules`, etc. | [workflows](skill/references/workflows.md#mirror--regenerate-platform-mirrors) |
| `history` | Read-only; lists git commits related to an entry / file / scope | nothing | [workflows](skill/references/workflows.md#history--show-git-commits-related-to-a-memory-entry) |

For a plain-language explanation of each workflow (when you'd actually use each one, with real scenarios), see [`WORKFLOWS.md`](WORKFLOWS.md) (中文版: [`WORKFLOWS.zh-CN.md`](WORKFLOWS.zh-CN.md)).

`sync` never updates mirrors — run `lore mirror` (or `compress`) to publish changes. To restore mirror updates on every `sync`, set `"sync_updates_mirror": true` in `.lore/.config.json`.

## Sync trust levels

`sync` can auto-apply or require confirmation depending on the change type and the configured trust level:

| Change type | `high` | `medium` (default) | `low` |
|---|---|---|---|
| De-duplicate hit | auto | auto | confirm |
| REFINED, tags only (body unchanged) | auto | auto | confirm |
| REFINED, body changed (new ID + supersede link) | auto | confirm | confirm |
| `NEW` entry | auto | confirm | confirm |
| `STALE` mark | auto | confirm | confirm |
| `ALERT` | confirm | confirm | confirm |

The default `medium` is a balance: low-risk changes apply silently, real additions or contradictions still get your sign-off. Switch to `high` for high-confidence projects (you trust the agent fully) or `low` if you want to review every change.

## Platform mirrors

lore's canonical store is `.lore/*`, but it projects into the config files agents already read. Targets are resolved by scanning the repo root for existing platform files (auto-detect). When none are present, `lore init` asks via multi-select which agents to write for. Setting `mirror_targets` in `.lore/.config.json` overrides this with an explicit list (Replace semantics).

| Platform | File | Auto-detected? |
|---|---|---|
| Claude Code | `CLAUDE.md` | ✅ |
| Cursor | `.cursorrules` (or `.cursor/rules/*.mdc`) | ✅ |
| Cline | `.clinerules` | ✅ |
| Aider / Codex / OpenCode | `AGENTS.md` (or `CONVENTIONS.md`) | ✅ |
| Windsurf | `.windsurfrules` | ✅ |
| GitHub Copilot | `.github/copilot-instructions.md` | ✅ |
| Continue.dev | `.continue/rules/lore.md` | ✅ |
| LangGraph / DeepAgents | (no file — read `.lore/*.md` directly) | n/a |

Each mirror file is split by a `---` separator into a `## Lore (auto-managed)` section (bounded by `<!-- LORE:START -->` / `<!-- LORE:END -->`) and a `## My notes (free edit)` section. Lore only writes inside the Lore section; My notes is preserved verbatim. (See the full example under "What `CLAUDE.md` looks like" above.)

## Token cost

lore's token model has six components. Only the mirror file is per-session; everything else is on-demand or per-invocation.

| Component | Loaded when | Typical size | Per-session? |
|---|---|---|---|
| **Mirror file** (CLAUDE.md, AGENTS.md, etc.) | Every session start | ~600 bytes (index mode, worst case) | yes |
| **skill/SKILL.md** (the lore spec itself) | Every `lore <cmd>` invocation | ~19 KB | no, per-invocation |
| **`skill/references/workflows.md`** (the seven procedures) | Every `lore <cmd>` invocation (only the routed section) | ~17 KB | no, per-invocation |
| **`.lore/SUMMARY.md`** | Agent reads on demand as the table of contents | 1–30 KB | no, on demand |
| **`scopes/<scope>/{ARCH,DEC,CONV}.md`** | Agent reads only the relevant scope | 1–5 KB each | no, on demand |
| **`lore query <term>`** result | Agent runs a query | bounded by matches | no, per query |

The mirror is the only ambient piece — the agent sees it every session — and it stays ~600 bytes because it's an index, not the memory. Mirror size scales with scope count and descriptions, not entry count: a 30-entry and a 250-entry project with the same scope shape have identical mirrors. Everything under `.lore/` is on-demand: the agent reads `SUMMARY.md` as a table of contents, then opens only the entries it needs. `skill/SKILL.md` and the routed `workflows.md` section load only when you invoke a lore command, and `lore query` returns only matched lines. Dumping the full `SUMMARY.md` into `CLAUDE.md` works but trades session-start cost for zero fetch — not recommended.

## Scripts

Helper scripts in `skill/scripts/` reduce repetitive mechanical work:

```bash
python skill/scripts/id_hash.py "Use Next.js App Router"        # → 409a (4-char ID hash)
python skill/scripts/list_entries.py                            # List all entries (text)
python skill/scripts/list_entries.py --scope=frontend --json    # Filtered JSON
python skill/scripts/find_duplicates.py                          # Find potential duplicates
python skill/scripts/find_stale.py --days=90                    # Find stale entries
python skill/scripts/history.py DEC-2026-02-03-7c19             # Show git history for an entry
python skill/scripts/history.py --follow-superseded DEC-2026-02-03-7c19   # Walk the replacement chain
```

All scripts are cross-platform Python 3.6+ with no third-party dependencies. Regression tests live in `tests/` and run with `python -m unittest discover -s tests -v` from the repo root. See [`skill/scripts/README.md`](skill/scripts/README.md) (English) or [`skill/scripts/README.zh-CN.md`](skill/scripts/README.zh-CN.md) (Chinese) for details.

## Configuration

`.lore/.config.json` is optional. The defaults work for most projects.

```json
{
  "schema_version": 1,
  "auto_mirror": false,
  "sync_updates_mirror": false,
  "sync_trust": "medium",
  "mirror_targets": ["CLAUDE.md"], // optional — auto-detected if absent
  "mirror_mode": "index",
  "compress_thresholds": { "max_entries": 500, "max_days_since_compress": 30 },
  "sync_thresholds": { "min_lines_changed": 50, "min_directories_changed": 2 }
}
```

Field semantics: see [`skill/references/config.md`](skill/references/config.md). New configs include `schema_version: 1`; old configs without it still work but trigger a warning. See [`skill/references/compatibility.md`](skill/references/compatibility.md) for the compatibility policy.

## Upgrading

`git pull` (or re-clone) is the normal upgrade path; your `.lore/` is preserved verbatim across upgrades. If a commit ships a breaking change, the commit message is prefixed `BREAKING:` and names what you need to edit by hand. Run `git log --grep=^BREAKING` after pulling to see any since your last sync. The current schema is `schema_version: 1`; no migration tool has shipped, so today there is nothing to run after pulling. See [`skill/references/compatibility.md`](skill/references/compatibility.md) for the versioning policy.

## When NOT to use lore

lore is built for long-term projects. It's overkill for:

- **Short-lived scripts / one-off demos.** The maintenance overhead exceeds the value.
- **Rapid prototyping** where decisions change weekly. The decision-tracking machinery gets in the way.
- **Tiny single-file projects.** Just use a `README.md`.
- **Projects where you never want AI to make decisions.** If you want a pure read-only agent, lore adds no value.
- **Massive monorepos with 50+ packages.** The scope tree becomes unwieldy; consider splitting per-package or using a sub-skill per cluster.

## FAQ

**Q: Does lore work without git?**
A: Partially. Most of lore is **agent workflow** described in [`skill/references/workflows.md`](skill/references/workflows.md) (routed from `skill/SKILL.md`) — the agent reads your files, drafts entries, edits `.lore/*.md`, and (when asked) regenerates mirrors. Without git, the agent can still do `init` / `query` / `audit` / `compress` / `mirror` by reading files directly. What you lose: `sync` uses `git diff` to detect changes (no diff → the agent asks you what changed), and `lore history` requires a git repo (it runs `git log`). The helper scripts (`list_entries.py`, `find_stale.py`, etc.) work either way.

**Q: Can I hand-edit `.lore/*.md` directly?**
A: Yes. The files are plain Markdown. Use `id_hash.py` if you're adding new entries (to keep IDs deterministic). After hand-editing, run `lore mirror` to update agent-facing files.

**Q: What if I don't want a mirror file at all (just `.lore/`)?**
A: Set `mirror_targets: []` in `.config.json`. The `compress` and `mirror` commands will be no-ops on the file system; only `SUMMARY.md` and the entry files matter.

**Q: How is this different from Cursor's `.cursorrules` or Aider's `AGENTS.md`?**
A: Those are flat lists of rules. lore is structured (architecture / decisions / conventions), atomic (one fact per entry), and historical (every entry has `#added` and `#verified` tags). It also produces those files for you.

**Q: Does lore talk to the agent's API?**
A: No. lore is pure file I/O. The agent invoking lore does the semantic work (scanning code, deciding what to extract, classifying changes); lore provides the file layout, the ID scheme, the markers, and the verification scripts.

**Q: What about the agent's native `/init` or `/compact` commands?**
A: They serve different purposes — `/init` is a one-shot project scan, `/compact` compresses conversation context, and lore manages long-term project knowledge. All three coexist.

**Q: I already generated a root `AGENTS.md` (via `/init` or a bootstrapping tool). Can I still use lore?**
A: Yes — that's the designed flow. Run `lore init` and choose **take over** when it detects the existing `AGENTS.md`: the file becomes a two-section mirror, your original content is preserved verbatim as `## My notes (free edit)`, and lore's `## Lore (auto-managed)` section is added above it. Lore only rewrites its own section, so the bootstrapped commands and conventions stay untouched. The same applies to `CLAUDE.md`, `.cursorrules`, etc. In reverse — if lore created the file first — run the bootstrap tool and choose **skip**, then paste its generated content into `## My notes`.

**Q: I added a new scope (e.g. a new package) after `lore init`. Do I re-run init?**
A: No — run `lore sync`. It detects the new scope from the changed file paths, creates `scopes/<name>/` automatically, and routes entries there. Then run `lore mirror` so the new scope appears in the agent-facing files. `init` is only for first-time setup or an explicit start-over.

**Q: What's the difference between `sync` and `mirror`?**
A: `sync` updates `.lore/` from code changes (run after a feature or refactor). `mirror` updates agent-facing files (`CLAUDE.md`, `.cursorrules`, etc.) from current `.lore/`. `sync` deliberately does **not** update mirrors — mirror files should be human-merged, not regenerated on every commit, so `git log` stays readable. Run `mirror` (or `compress`) explicitly when you want agent-facing files to catch up.

**Q: How is lore different from ADRs (Architecture Decision Records)?**
A: ADRs are documents — one markdown file per decision. lore is structured project memory: one fact per entry, with a stable ID and `#added` / `#verified` / `#stale` markers. The `DEC` layer can replace `docs/adr/` (one DEC entry per decision), but lore also covers `ARCH` (architecture) and `CONV` (conventions) in the same store, plus generates agent-facing summaries via `compress` / `mirror`. Use lore **instead of** ADRs, or **alongside** them (one DEC entry pointing to the existing ADR document).

**Q: What if I disagree with an entry the agent wrote?**
A: Edit `.lore/*.md` directly — it's plain Markdown. The next `mirror` / `compress` will reflect your edit, and the helper scripts keep the ID stable as long as the entry text is unchanged. To revert to pre-AI state, `git checkout .lore/` like any tracked file.

**Q: Can I sync `.lore/` across multiple machines without git?**
A: Git is the recommended transport (`.lore/` is plain text in your repo; `git push` / `git pull` carry it). Other transports (Dropbox, OneDrive, Syncthing) work as long as you trust their text-file conflict resolution — they won't understand lore's ID scheme or `#added` markers. **Don't run two agents on the same `.lore/` simultaneously**; last-writer-wins, and IDs aren't protected by a remote lock.

## License

[MIT](./LICENSE) — use, modify, redistribute, sublicense, and sell, including commercially. No warranty.

---

<p align="center">
  <a href="skill/SKILL.md">skill/SKILL.md</a> ·
  <a href="skill/references/workflows.md">workflows</a> ·
  <a href="skill/references/entry-format.md">entry-format</a> ·
  <a href="skill/references/summary-template.md">summary-template</a> ·
  <a href="skill/references/audit-template.md">audit-template</a> ·
  <a href="skill/references/monorepo-detection.md">monorepo-detection</a> ·
  <a href="skill/references/stale-new-markers.md">stale-new-markers</a> ·
  <a href="skill/references/platform-mirrors.md">platform-mirrors</a> ·
  <a href="skill/references/config.md">config</a> ·
  <a href="skill/references/history-command.md">history-command</a> ·
  <a href="skill/references/compatibility.md">compatibility</a> ·
  <a href="skill/scripts/README.md">scripts</a>
</p>
