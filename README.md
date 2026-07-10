# mem-man

> Framework-agnostic project memory for AI coding agents.

A long-term knowledge base for software projects, maintained by AI agents. Captures the kind of context that normally lives only in the original developer's head — architecture, decisions, conventions — and persists it as plain Markdown files that any agent can consume.

## What it solves

When you work on a project across multiple AI tools (Claude Code, Cursor, Cline, GitHub Copilot, Aider, LangGraph agents, DeepAgents) and across many sessions, context gets lost:

- **Every new session re-explains the project.** "We're using Next.js App Router, not Pages. Use Zustand, not Redux. Don't commit secrets."
- **Decisions are forgotten.** "Why did we pick X over Y?" → "I don't remember, let me ask the team."
- **Agents disagree with each other.** Cursor follows `.cursorrules`, Claude Code follows `CLAUDE.md`, but the two files drift apart.
- **Onboarding takes weeks.** New members / new agents need to learn the conventions from scratch.

mem-man maintains a single source of truth (`.mem-man/`) and projects it into whatever config files your agents already read. It tracks *why* decisions were made, not just *what* the code does, and keeps that history across sessions and tools.

## Quick start

```bash
# 1. Initialize (run once per project)
mem-man init
# Walks the project, drafts entries, asks for confirmation, creates .mem-man/

# 2. After a non-trivial change
mem-man sync
# Detects code diffs, proposes [NEW]/[STALE]/[REFINED] entries, waits for your call

# 3. After many changes, refresh the agent-facing summary
mem-man compress
# Regenerates SUMMARY.md and updates CLAUDE.md / .cursorrules / etc.

# 4. Force a mirror refresh (e.g. after hand-editing .mem-man/)
mem-man mirror
# Rewrites CLAUDE.md and other platform files from current state
```

A sixth read-only command surfaces the git history behind a memory entry:

```bash
lore history                    # List commits for an entry / file / scope
lore history DEC-2026-02-03-7c19
lore history frontend/src/store/index.ts
lore history --scope=frontend   # all .md files in that scope
lore history --json             # machine-readable
```

Three read-only commands round out the toolkit:

```bash
mem-man query    # Answer a question from memory, cite entry IDs
mem-man audit    # Check memory vs. reality, write report to .mem-man/audit/
```

## What lives in `.mem-man/`

```
.mem-man/
├── SUMMARY.md                    # Top-level digest; new agents read this first
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
├── audit/                        # Used by `audit` for reports
└── archive/                      # Old/superseded entries
```

Each entry is a single Markdown bullet (≤ 2 lines) with a deterministic ID and inline status tags:

```markdown
- [ARCH-2026-07-09-a3f2] Use Next.js App Router; reason: streaming + RSC. #added:2026-07-09
- [DEC-2026-02-03-7c19] Chose Zustand over Redux; reason: 60% less boilerplate. #added:2026-02-03 #verified:2026-06-15
- [CONV-2026-01-20-b1e8] Never commit secrets; use `dotenv` + `.env.local`. #added:2026-01-20
```

## Six workflows

| Command | What it does | Writes |
|---|---|---|
| `init` | First-time project scan; drafts entries; user confirms | `.mem-man/*` + platform mirrors |
| `sync` | Detects code changes; proposes updates; user approves | `.mem-man/*` only (not mirrors) |
| `query` | Read-only; answers from memory with entry IDs | nothing |
| `audit` | Read-only; checks memory vs. current code; writes report | `.mem-man/audit/*` only |
| `compress` | Generates `SUMMARY.md` from current entries | `SUMMARY.md` + platform mirrors |
| `mirror` | Force-regenerate platform mirrors (with content dedup) | `CLAUDE.md`, `.cursorrules`, etc. |
| `history` | Read-only; lists git commits related to an entry / file / scope | nothing |

`sync` deliberately does **not** update platform mirrors. Mirror files are agent-facing entry points, not per-change logs. Regenerating them on every `sync` would clutter `git log` and dilute the "human-merged" signal they're supposed to provide. Run `mem-man mirror` (or `compress`) when you want the agent-facing view to catch up.

To restore old behavior (mirror updates on every `sync`), set `"sync_updates_mirror": true` in `.mem-man/.config.json`.

## Sync trust levels

`sync` can auto-apply or require confirmation depending on the change type and the configured trust level:

| Change type | `high` | `medium` (default) | `low` |
|---|---|---|---|
| De-duplicate hit | auto | auto | confirm |
| Equivalent REFINED | auto | auto | confirm |
| `NEW` entry | auto | confirm | confirm |
| `STALE` mark | auto | confirm | confirm |
| `ALERT` | confirm | confirm | confirm |

The default `medium` is a balance: low-risk changes apply silently, real additions or contradictions still get your sign-off. Switch to `high` for high-confidence projects (you trust the agent fully) or `low` if you want to review every change.

## Platform mirrors

mem-man's canonical store is `.mem-man/*`, but it projects into the config files agents already read:

| Platform | File | Default? |
|---|---|---|
| Claude Code | `CLAUDE.md` | ✅ yes |
| Cursor | `.cursorrules` | ❌ opt-in via `mirror_targets` |
| Cline | `.clinerules` | ❌ opt-in |
| Aider / Codex | `AGENTS.md` | ❌ opt-in |
| Windsurf | `.windsurfrules` | ❌ opt-in |
| GitHub Copilot | `.github/copilot-instructions.md` | ❌ opt-in |
| LangGraph / DeepAgents | (no file — read `.mem-man/*.md` directly) | n/a |

Each mirror file is split into two sections by a `---` separator:

```markdown
## Mem-man (auto-managed)
... Skill-managed content from .mem-man/ ...

---

## My notes (free edit)
... your hand-written notes, preserved verbatim across syncs ...
```

The Skill only writes inside the `## Mem-man` section. Everything under `## My notes` is yours to edit freely. The Skill preserves it verbatim across every `sync` and `compress`.

## Scripts

Helper scripts in `scripts/` reduce repetitive mechanical work:

```bash
python scripts/id_hash.py "Use Next.js App Router"        # → a3f2 (4-char ID hash)
python scripts/list_entries.py                            # List all entries (text)
python scripts/list_entries.py --scope=frontend --json    # Filtered JSON
python scripts/find_duplicates.py                          # Find potential duplicates
python scripts/find_stale.py --days=90                    # Find stale entries
```

All scripts are cross-platform Python 3.6+ with no third-party dependencies. See `scripts/README.md` (English) or `scripts/README.zh-CN.md` (中文) for details.

## Configuration

`.mem-man/.config.json` is optional. The defaults work for most projects.

```json
{
  "auto_mirror": false,
  "sync_updates_mirror": false,
  "sync_trust": "medium",
  "mirror_targets": ["CLAUDE.md"],
  "mirror_mode": "summary",
  "compress_thresholds": { "max_entries": 500, "max_days_since_compress": 30 },
  "sync_thresholds": { "min_lines_changed": 50, "min_directories_changed": 2 }
}
```

Field semantics: see `references/config.md`.

## When NOT to use mem-man

mem-man is built for long-term projects. It's overkill for:

- **Short-lived scripts / one-off demos.** The maintenance overhead exceeds the value.
- **Rapid prototyping** where decisions change weekly. The decision-tracking machinery gets in the way.
- **Tiny single-file projects.** Just use a `README.md`.
- **Projects where you never want AI to make decisions.** If you want a pure read-only agent, mem-man adds no value.
- **Massive monorepos with 50+ packages.** The scope tree becomes unwieldy; consider splitting per-package or using a sub-skill per cluster.

## FAQ

**Q: Does mem-man work without git?**
A: Partially. `sync` uses `git diff` to detect changes. Without git, you can still use `init` / `query` / `audit` / `compress` / `mirror`, but `sync` will need you to tell it what changed.

**Q: Can I hand-edit `.mem-man/*.md` directly?**
A: Yes. The files are plain Markdown. Use `id_hash.py` if you're adding new entries (to keep IDs deterministic). After hand-editing, run `mem-man mirror` to update agent-facing files.

**Q: What if I don't want a mirror file at all (just `.mem-man/`)?**
A: Set `mirror_targets: []` in `.config.json`. The `compress` and `mirror` commands will be no-ops on the file system; only `SUMMARY.md` and the entry files matter.

**Q: How is this different from Cursor's `.cursorrules` or Aider's `AGENTS.md`?**
A: Those are flat lists of rules. mem-man is structured (architecture / decisions / conventions), atomic (one fact per entry), and historical (every entry has `#added` and `#verified` tags). It also produces those files for you.

**Q: Does mem-man talk to the agent's API?**
A: No. mem-man is pure file I/O. The agent invoking mem-man does the semantic work (scanning code, deciding what to extract, classifying changes); mem-man provides the file layout, the ID scheme, the markers, and the verification scripts.

**Q: What about the agent's native `/init` or `/compact` commands?**
A: They serve different purposes. `/init` is a one-shot project scan → `CLAUDE.md`. `/compact` compresses conversation context. mem-man `init` and `compress` manage long-term project knowledge, not session context. If you run `mem-man init` on a project that already has a non-mem-man `CLAUDE.md`, the takeover check (init step 0) handles integration.

## License

This skill is provided as-is. Use it, fork it, modify it for your project's needs.
