# lore

<p align="center">
  <img src="docs/lore-poster.svg" alt="lore" width="640">
</p>

<p align="center">
  <a href="https://github.com/TheaDust/lore"><img src="https://img.shields.io/github/stars/TheaDust/lore?style=flat&label=stars" alt="stars"></a>
  <a href="https://github.com/TheaDust/lore/commits/main"><img src="https://img.shields.io/github/last-commit/TheaDust/lore?style=flat&label=last%20commit" alt="last commit"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="license"></a>
  <img src="https://img.shields.io/badge/python-3.6%2B-blue.svg" alt="python">
</p>

<p align="center"><em><strong>lore</strong> (noun) — a body of traditions and knowledge on a subject, passed from person to person. — Oxford English Dictionary</em></p>

<p align="right"><a href="README.zh-CN.md">简体中文</a> · English</p>

> Framework-agnostic project memory for AI coding agents. A long-term knowledge base that persists architecture, decisions, and conventions as plain Markdown any agent can read.

> **lore is a SKILL, not a CLI.** It is a Markdown spec ([`skill/SKILL.md`](skill/SKILL.md)) for Claude Code, Cursor, OpenCode, Cline, Aider, Copilot and others. There is no `lore` binary — phrases like `lore init` and `lore sync` are spoken to your agent.

| Structured | Searchable | Portable |
|---|---|---|
| Architecture / Decisions / Conventions in `.lore/` with stable IDs and lifecycle tags | `lore query` answers with `[file#ID]` citations; `lore history` traces commits | Single source `.lore/` projected to `CLAUDE.md` / `.cursorrules` / `AGENTS.md` via mirrors |

> After `/init`, platform memory files are rarely updated by hand — stale knowledge pollutes memory. Claude reads `CLAUDE.md`, Codex reads `AGENTS.md`, they drift. lore keeps one source `.lore/` and projects it everywhere.

> Contents: [Installation](#installation) · [Quick start](#quick-start) · [What it looks like](#what-it-looks-like) · [How it works](#how-it-works) · [Workflows](#workflows) · [Platform mirrors](#platform-mirrors) · [FAQ](#faq)

## Installation

The install unit is `skill/`:

```bash
git clone https://github.com/TheaDust/lore.git /tmp/lore
cp -r /tmp/lore/skill <your-agent-skills-dir>/lore
# e.g. cp -r /tmp/lore/skill ~/.claude/skills/lore
```

Or tell your agent:

> Install https://github.com/TheaDust/lore as a skill (skill is in `skill/`).

Full reference docs: [`skill/references/`](skill/references/) · Plain-language workflow guide: [`WORKFLOWS.md`](WORKFLOWS.md)

## Quick start

Phrases you say to your agent (no binary):

```bash
lore init      # One-time: scan project, draft entries, confirm, create .lore/
lore sync      # After a feature/refactor: detect changes, propose [NEW]/[STALE]/[REFINED]/[ALERT]
lore compress  # Refresh SUMMARY.md when stale; optionally regenerate mirrors
lore mirror    # Force-regenerate CLAUDE.md and other mirrors from current .lore/
```

```bash
lore query <term>                  # Answer from memory with entry IDs
lore audit                         # Check memory vs. code, report to .lore/audit/
lore history <entry-id|path|--scope> [--json]  # Git commits behind an entry
```

## What it looks like

### Query

> You: "How does this project authenticate API requests?" — Agent runs `lore query auth`:

```
[_global/DECISIONS.md#DEC-2026-07-10-6d9c] Opaque base64 tokens over JWT; simpler revocation.
[scopes/backend/ARCHITECTURE.md#ARCH-2026-07-10-59ac] Auth helpers in backend/app/auth.py
[scopes/backend/CONVENTIONS.md#CONV-2026-07-10-84e3] Invalid token -> 401; not found -> 404.
[scopes/frontend/ARCHITECTURE.md#ARCH-2026-07-10-6de2] Token in localStorage todo.auth.token
```

Every answer cites `[file#ID]` — `cat` the file or `lore history <ID>` to trace why.

### Mirrors

`lore` keeps per-session cost flat with a small index mirror (~600 bytes):

<details>
<summary>Example <code>CLAUDE.md</code> Lore section</summary>

```markdown
<!-- LORE:START -->
## Lore (auto-managed)

Project memory at `.lore/`. Before project-specific questions, read `.lore/SUMMARY.md`
as the digest, then open the referenced entries for the full text; cite entry IDs.

**Structure**:
- Digest: `.lore/SUMMARY.md`
- Global: `.lore/_global/`
- Scopes: `.lore/scopes/`
  - `.lore/scopes/backend/` (Flask 3 + SQLAlchemy 2 + pytest; Python 3.11+)
  - `.lore/scopes/frontend/` (React 18 + TypeScript + Vite + Zustand + Axios)

**Query**: `lore query <term>` or `lore query <scope>:<term>`
<!-- LORE:END -->
---
## My notes (free edit)
- Anything here is preserved verbatim across syncs.
```

</details>

<details>
<summary>Example <code>lore history</code></summary>

```
# history: [DEC-2026-07-10-e45d]
> Entry: scopes/backend/DECISIONS.md  Since: 2026-07-10T00:00:00  File: backend
## 9f264f4 (2026-07-10, Lore Tester) feat(backend): switch password hashing to bcrypt
## ed2b288 (2026-07-10, Lore Tester) feat(backend): password hashing and auth tokens
```

</details>

## How it works

```
.lore/
├── SUMMARY.md              # Digest; agents read first
├── .config.json            # Optional config
├── _global/                # Cross-scope facts
│   ├── ARCHITECTURE.md
│   ├── DECISIONS.md
│   └── CONVENTIONS.md
├── scopes/<scope>/
│   ├── ARCHITECTURE.md
│   ├── DECISIONS.md
│   └── CONVENTIONS.md
├── draft/                  # init proposals
├── audit/                  # audit reports
└── .archive/               # My notes backups on wipe
```

Each entry is one bullet, at most two lines, with a deterministic ID:

```markdown
- [ARCH-2026-07-09-a3f2] Use Next.js App Router; reason: streaming + RSC. #added:2026-07-09
- [DEC-2026-02-03-7c19] Chose Zustand over Redux; reason: 60% less boilerplate. #added:2026-02-03 #verified:2026-06-15
- [CONV-2026-01-20-b1e8] Never commit secrets; use dotenv + .env.local (gitignored). #added:2026-01-20
```

`#superseded-by` links replacements so `compress` / `history` can walk the chain. Spec: [`skill/references/entry-format.md`](skill/references/entry-format.md).

## Workflows

| Command | What it does | Writes | Reference |
|---|---|---|---|
| `init` | Scan project, draft entries, confirm | `.lore/*` + mirrors | [workflows#init](skill/references/workflows.md#init--initialize-the-memory-bank) |
| `sync` | Detect changes, propose updates | `.lore/*` only | [workflows#sync](skill/references/workflows.md#sync--update-after-a-change) |
| `query` | Answer from memory with IDs | nothing | [workflows#query](skill/references/workflows.md#query--answer-from-memory) |
| `audit` | Check memory vs. code, write report | `.lore/audit/*` | [workflows#audit](skill/references/workflows.md#audit--check-memory-vs-reality) |
| `compress` | Rebuild `SUMMARY.md` | `SUMMARY.md` + mirrors | [workflows#compress](skill/references/workflows.md#compress--build-the-top-level-summary) |
| `mirror` | Regenerate mirrors (deduped) | `CLAUDE.md` etc. | [workflows#mirror](skill/references/workflows.md#mirror--regenerate-platform-mirrors) |
| `history` | Git commits for an entry / file / scope | nothing | [workflows#history](skill/references/workflows.md#history--show-git-commits-related-to-a-memory-entry) |

`sync` never touches mirrors — run `lore mirror` or `compress` to publish. Set `sync_updates_mirror: true` to restore per-sync mirrors.

<details>
<summary>Sync trust levels</summary>

| Change type | `high` | `medium` (default) | `low` |
|---|---|---|---|
| De-duplicate hit | auto | auto | confirm |
| REFINED, tags only | auto | auto | confirm |
| REFINED, body changed | auto | confirm | confirm |
| `NEW` entry | auto | confirm | confirm |
| `STALE` mark | auto | confirm | confirm |
| `ALERT` | confirm | confirm | confirm |

`medium` auto-applies low-risk changes; real additions or contradictions require confirmation.

</details>

## Platform mirrors

Canonical store is `.lore/*`; mirrors are projections into files agents already read. Targets auto-detected by scanning the repo root; `lore init` asks which agents to cover, or set `mirror_targets` explicitly.

| Platform | File |
|---|---|
| Claude Code | `CLAUDE.md` |
| Cursor | `.cursorrules` / `.cursor/rules/*.mdc` |
| Cline | `.clinerules` |
| Aider / Codex / OpenCode | `AGENTS.md` |
| Windsurf | `.windsurfrules` |
| GitHub Copilot | `.github/copilot-instructions.md` |
| Continue.dev | `.continue/rules/lore.md` |
| LangGraph / DeepAgents | no file — read `.lore/*.md` directly |

Each mirror has `## Lore (auto-managed)` bounded by `<!-- LORE:START -->` / `<!-- LORE:END -->` and `## My notes (free edit)` preserved verbatim.

<details>
<summary>Token cost</summary>

| Component | Loaded when | Typical size | Per-session |
|---|---|---|---|
| Mirror file | Every session | ~600 bytes (index mode) | yes |
| `skill/SKILL.md` | Every `lore <cmd>` | ~19 KB | per-invocation |
| `skill/references/workflows.md` | Every `lore <cmd>` (routed section) | ~17 KB | per-invocation |
| `.lore/SUMMARY.md` | On demand | 1–30 KB | on demand |
| `scopes/<scope>/*.md` | On demand | 1–5 KB each | on demand |
| `lore query` result | Per query | bounded by matches | per query |

Mirror size scales with scope count, not entry count. Dumping `SUMMARY.md` into the mirror trades session-start cost for zero fetch — not recommended.

</details>

<details>
<summary>Scripts and tests</summary>

```bash
python skill/scripts/id_hash.py "Use Next.js App Router"      # 4-char ID hash
python skill/scripts/list_entries.py --json
python skill/scripts/find_duplicates.py --json
python skill/scripts/find_stale.py --days=90 --json
python skill/scripts/history.py DEC-2026-02-03-7c19
```

Python 3.6+, stdlib only. Tests: `python -m unittest discover -s tests -v`. Details: [`skill/scripts/README.md`](skill/scripts/README.md).

</details>

<details>
<summary>Configuration</summary>

`.lore/.config.json` is optional:

```json
{
  "schema_version": 1,
  "auto_mirror": false,
  "sync_updates_mirror": false,
  "sync_trust": "medium",
  "mirror_targets": ["CLAUDE.md"],
  "mirror_mode": "index",
  "compress_thresholds": { "max_entries": 500, "max_days_since_compress": 30 },
  "sync_thresholds": { "min_lines_changed": 50, "min_directories_changed": 2 }
}
```

See [`skill/references/config.md`](skill/references/config.md) and [`skill/references/compatibility.md`](skill/references/compatibility.md).

</details>

## Upgrading

`git pull` preserves `.lore/` verbatim. Breaking changes are prefixed `BREAKING:` — run `git log --grep=^BREAKING` after pulling. Current `schema_version: 1`.

<details>
<summary>When not to use lore</summary>

- Short-lived scripts or one-off demos
- Rapid prototyping where decisions churn weekly
- Tiny single-file projects
- Projects where agents should be read-only
- Monorepos with 50+ packages (split per cluster instead)

</details>

## FAQ

<details>
<summary>Does lore work without git?</summary>

Mostly. `init` / `query` / `audit` / `compress` / `mirror` work by reading files. `sync` loses `git diff` (agent asks what changed) and `history` requires a repo. Helper scripts work either way.

</details>

<details>
<summary>Can I hand-edit <code>.lore/*.md</code>?</summary>

Yes — plain Markdown. Use `id_hash.py` for new IDs. Run `lore mirror` after to refresh mirrors.

</details>

<details>
<summary>What if I don't want a mirror file?</summary>

Set `mirror_targets: []` in `.config.json`. Only `SUMMARY.md` and entry files matter.

</details>

<details>
<summary>How is this different from <code>.cursorrules</code> / <code>AGENTS.md</code>?</summary>

Those are flat rule lists. lore is structured (ARCH/DEC/CONV), atomic (one fact per entry), and historical (`#added` / `#verified` / `#stale`), and it generates those files for you.

</details>

<details>
<summary>Does lore call the agent API?</summary>

No — pure file I/O. The agent does the semantic work; lore provides layout, ID scheme, markers, and verification scripts.

</details>

<details>
<summary>What about the agent's native <code>/init</code> or <code>/compact</code>?</summary>

Different concerns — `/init` scaffolds a project, `/compact` compresses conversation, lore manages long-term knowledge. They coexist.

</details>

<details>
<summary>I already have a root <code>AGENTS.md</code>. Can I still use lore?</summary>

Run `lore init` and choose take over — your file becomes a two-section mirror, original content preserved as `My notes`. Same for `CLAUDE.md` / `.cursorrules`.

</details>

<details>
<summary>I added a new scope after <code>init</code>. Re-run <code>init</code>?</summary>

No — `lore sync` detects the new scope from changed paths and creates `scopes/<name>/` automatically. Then `lore mirror`.

</details>

<details>
<summary>What is the difference between <code>sync</code> and <code>mirror</code>?</summary>

`sync` updates `.lore/` from code; `mirror` updates agent-facing files from `.lore/`. `sync` deliberately does not touch mirrors so `git log` stays readable.

</details>

<details>
<summary>How is lore different from ADRs?</summary>

ADRs are one file per decision. lore is one fact per entry with stable IDs and lifecycle tags, plus `compress` / `mirror` summaries. Use lore instead of or alongside ADRs (one DEC entry can point to an ADR).

</details>

<details>
<summary>What if I disagree with an entry?</summary>

Edit `.lore/*.md` directly. Next `mirror` / `compress` reflects it. `git checkout .lore/` reverts.

</details>

<details>
<summary>Can I sync <code>.lore/</code> without git?</summary>

Git is recommended. Other sync tools work for plain text but won't understand IDs or tags. Don't run two agents on the same `.lore/` concurrently.

</details>

## License

[MIT](./LICENSE)

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
