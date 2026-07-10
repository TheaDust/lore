# Mirror Index Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `mirror_mode: "summary"` / `"full"` with a single `mirror_mode: "index"` that emits a ~500-byte index pointing into `.lore/` instead of dumping SUMMARY content. Cuts per-session token cost from 5–40 KB to ~500 B regardless of project size.

**Architecture:** Pure documentation change. The mirror template (currently described in `references/platform-mirrors.md`) is rewritten as a small index structure with adaptive rendering rules. Config schema narrows `mirror_mode` to `"index"` only. No Python code touched; AI agents reading the docs implement the new behavior when they run `lore mirror`.

**Tech Stack:** Markdown documentation. No code changes. No new dependencies.

---

## File Structure

| File | Change | Purpose |
|---|---|---|
| `references/platform-mirrors.md` | Modify | Replace "What gets mirrored" section with new index template + adaptive renderings + scope-description extraction rule |
| `references/config.md` | Modify | Narrow `mirror_mode` to `"index"` only; update default + reject-other-values |
| `SKILL.md` | Modify | Update line 116 (Lore section description) and any nearby text referring to SUMMARY content in mirror |
| `README.md` | Modify | Config example `"summary"` → `"index"`; add "Token cost" section |
| `README.zh-CN.md` | Modify | Same as README.md (Chinese version) |

No new files. No Python code touched. Spec/plan live under `.superpowers/` which is gitignored per project convention.

---

## Task 1: Update `references/platform-mirrors.md` — replace "What gets mirrored" section with index template

**Files:**
- Modify: `references/platform-mirrors.md:199-207` (the "What gets mirrored" section)

- [ ] **Step 1: Read the current "What gets mirrored" section to anchor the edit**

Run: `Get-Content references/platform-mirrors.md | Select-Object -Skip 198 -First 12`
Expected: shows the current heading and prose describing SUMMARY + scope-tagged index content.

- [ ] **Step 2: Replace the section with the index template + adaptive renderings + extraction rule**

Find:
```
## What gets mirrored

By default, the mirror's Lore section contains:
- `SUMMARY.md` content (top-level digest)
- A scope-tagged index pointing into `.lore/*`

The full per-file content (every entry in every layer) is **not** mirrored by default. Mirrors are entry points, not full copies. Agents that need details should read `.lore/*` directly.

To mirror full content instead, set `mirror_mode: full` in `.lore/.config.json` (see `references/config.md`).
```

Replace with:
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
```

- [ ] **Step 3: Verify the file reads cleanly**

Run: `Select-String -Path references/platform-mirrors.md -Pattern 'index template|Field sources|Section visibility|description extraction'`
Expected: all four section headings match. The old "To mirror full content instead, set `mirror_mode: full`" line should NOT appear (use a negative check).

Run: `Select-String -Path references/platform-mirrors.md -Pattern 'mirror_mode: full'`
Expected: no matches (the old full-mode recommendation is gone).

- [ ] **Step 4: Commit**

```bash
git add references/platform-mirrors.md
git commit -m "docs(platform-mirrors): switch mirror to index template"
```

---

## Task 2: Update `references/config.md` — narrow `mirror_mode` to `"index"` only

**Files:**
- Modify: `references/config.md:14` (the JSON example showing `"mirror_mode": "summary" | "full"`)
- Modify: `references/config.md:70-78` (the `mirror_mode` field description section)

- [ ] **Step 1: Read the current `mirror_mode` field description to anchor the edit**

Run: `Get-Content references/config.md | Select-Object -Skip 68 -First 12`
Expected: shows the heading `### mirror_mode`, current default, and full/summary descriptions.

- [ ] **Step 2: Update the JSON example**

Find (line 14):
```
  "mirror_mode": "summary" | "full",
```

Replace with:
```
  "mirror_mode": "index",
```

- [ ] **Step 3: Replace the field description**

Find:
```
### `mirror_mode`

Default: `"summary"`.

- `"summary"` — Mirror only `SUMMARY.md` content (plus a scope-tagged index). Recommended for most projects.
- `"full"` — Mirror full per-file content. Useful for agents that don't reliably read `.lore/*` directly.
```

Replace with:
```
### `mirror_mode`

Default: `"index"`.

Only `"index"` is accepted. The mirror renders a small index structure pointing into `.lore/` (see `references/platform-mirrors.md` for the template and adaptive rendering rules). Per-session token cost stays flat (~500 B) regardless of project size.

Any other value (e.g., the historical `"summary"` or `"full"`) is rejected at config-load time with an error. Remove the field, or set it to `"index"`.
```

- [ ] **Step 4: Verify the file reads cleanly**

Run: `Select-String -Path references/config.md -Pattern 'mirror_mode|"index"|"summary"|"full"'`
Expected: only `"index"` appears as a valid value. No `"summary"` or `"full"` recommended values remain in the field description.

- [ ] **Step 5: Commit**

```bash
git add references/config.md
git commit -m "docs(config): mirror_mode only accepts index"
```

---

## Task 3: Update `SKILL.md` line 116 — describe index instead of summary content

**Files:**
- Modify: `SKILL.md:116` (the "By default the Lore section contains..." sentence)

- [ ] **Step 1: Find the current sentence**

Run: `Select-String -Path SKILL.md -Pattern 'By default the Lore section contains'`
Expected: exactly one match at line 116 with the old "SUMMARY.md plus a scope-tagged index — not the full content. Full-content mirroring is opt-in via `mirror_mode: full`." sentence.

- [ ] **Step 2: Replace the sentence**

Find:
```
By default the Lore section contains `SUMMARY.md` plus a scope-tagged index — not the full content. Full-content mirroring is opt-in via `mirror_mode: full`.
```

Replace with:
```
By default the Lore section is an **index** into `.lore/` — paths plus a per-scope one-line description, ~500 bytes total. The agent reads `.lore/SUMMARY.md` (or calls `lore query <term>`) on demand. See `references/platform-mirrors.md` for the template and adaptive rendering rules.
```

- [ ] **Step 3: Verify no other mentions of `mirror_mode: full` or `"summary"` mode remain in SKILL.md**

Run: `Select-String -Path SKILL.md -Pattern 'mirror_mode.*full|mirror_mode.*summary|mirror_mode.*"full"|mirror_mode.*"summary"'`
Expected: no matches. The old full/summary wording is fully removed.

Run: `Select-String -Path SKILL.md -Pattern 'is an .index. into'`
Expected: exactly one match at the new line 116.

- [ ] **Step 4: Commit**

```bash
git add SKILL.md
git commit -m "docs(skill): describe index mirror instead of summary"
```

---

## Task 4: Update `README.md` — config example + new "Token cost" section

**Files:**
- Modify: `README.md:160` (config example line `"mirror_mode": "summary"`)
- Insert: new "Token cost" section in README.md (placement discussed below)

- [ ] **Step 1: Find the config example**

Run: `Select-String -Path README.md -Pattern 'mirror_mode.*summary'`
Expected: one match at line 160.

- [ ] **Step 2: Update the config example**

Find:
```
  "mirror_mode": "summary",
```

Replace with:
```
  "mirror_mode": "index",
```

- [ ] **Step 3: Find a good location for the new "Token cost" section**

Run: `Get-Content README.md | Select-String -Pattern '^## '`
Expected: a list of `##`-level headings. Look for the section just before or after "Platform mirrors" — that is the most natural place to put cost information.

Recommended placement: immediately after the "Platform mirrors" section ends (the section that ends with the My notes template). Insert a new `## Token cost` section there.

- [ ] **Step 4: Insert the new "Token cost" section after the Platform mirrors section**

Find the end of the Platform mirrors section (the closing line of the markdown code block showing the two-section template, then a blank line, then the next `##` heading).

Insert this block before the next `##` heading:

```markdown
## Token cost

`CLAUDE.md` and equivalent platform files are loaded by your agent on **every session**. lore keeps this cost flat by emitting an index (~500 bytes) rather than the project digest content.

Typical mirror sizes:

| Project state | Mirror size | Per-session context cost |
|---|---|---|
| Empty / new | ~200 bytes | negligible |
| Small (~30 entries) | ~500 bytes | negligible |
| Medium (~120 entries) | ~500 bytes | negligible |
| Large (~250 entries) | ~500 bytes | negligible |

Index size does not grow with project size. The agent fetches detail on demand via standard file reads or `lore query <term>`.

If you need ambient knowledge (the agent has full context immediately, no fetch step), be aware that ambient knowledge is no longer the default. See `references/platform-mirrors.md` for the index template details.
```

- [ ] **Step 5: Verify the file reads cleanly**

Run: `Select-String -Path README.md -Pattern 'Token cost|mirror_mode.*index'`
Expected: both patterns match — "Token cost" appears as a new section heading, and `"mirror_mode": "index"` is the config example.

Run: `Select-String -Path README.md -Pattern '"summary"'`
Expected: no matches (old `"summary"` value is gone).

- [ ] **Step 6: Commit**

```bash
git add README.md
git commit -m "docs(readme): index mode config example and Token cost section"
```

---

## Task 5: Update `README.zh-CN.md` — mirror the README.md changes

**Files:**
- Modify: `README.zh-CN.md` config example line
- Insert: new "Token cost" section (Chinese translation)

- [ ] **Step 1: Find the config example in the Chinese README**

Run: `Select-String -Path README.zh-CN.md -Pattern 'mirror_mode.*summary'`
Expected: one match.

- [ ] **Step 2: Update the config example**

Find:
```
  "mirror_mode": "summary",
```

Replace with:
```
  "mirror_mode": "index",
```

- [ ] **Step 3: Find the equivalent insertion point in the Chinese README**

Run: `Get-Content README.zh-CN.md | Select-String -Pattern '^## '`
Expected: Chinese section headings. Locate the section that ends after the two-section markdown template — insert the new `## Token cost` (or `## Token 成本` if you prefer Chinese title) section there.

Recommended title: `## Token 成本` for consistency with other Chinese headings in the file.

- [ ] **Step 4: Insert the new "Token 成本" section**

Insert immediately after the Platform mirrors section ends:

```markdown
## Token 成本

`CLAUDE.md` 等平台文件 agent 每次会话都会自动加载。lore 通过只输出索引（约 500 字节）而不是项目摘要内容来保持这个成本稳定。

典型 mirror 大小：

| 项目状态 | Mirror 大小 | 每次会话成本 |
|---|---|---|
| 空 / 新项目 | ~200 字节 | 可忽略 |
| 小（~30 entries） | ~500 字节 | 可忽略 |
| 中（~120 entries） | ~500 字节 | 可忽略 |
| 大（~250 entries） | ~500 字节 | 可忽略 |

索引大小不随项目增长。Agent 按需通过标准文件读取或 `lore query <term>` 获取详情。

如果需要 ambient knowledge（agent 立即拥有全部上下文，无需 fetch 步骤），请注意这不再是默认行为。详见 `references/platform-mirrors.md`。
```

- [ ] **Step 5: Verify the file reads cleanly**

Run: `Select-String -Path README.zh-CN.md -Pattern 'Token 成本|mirror_mode.*index'`
Expected: both patterns match.

Run: `Select-String -Path README.zh-CN.md -Pattern '"summary"'`
Expected: no matches.

- [ ] **Step 6: Commit**

```bash
git add README.zh-CN.md
git commit -m "docs(readme.zh): index mode config example and Token cost section"
```

---

## Task 6: Manual verification — empty project (no entries)

Verifies the adaptive "Global/Scopes omitted" rendering. Run in a temp directory; this task does not modify any project files.

- [ ] **Step 1: Set up an empty temp project with only `.lore/` initialized**

Run:
```bash
$TEMP = New-Item -ItemType Directory -Path "$env:TEMP\lore-index-verify-1" -Force
Push-Location $TEMP.FullName
git init -q
# Simulate a freshly-initialized lore project with only SUMMARY.md placeholder
New-Item -ItemType Directory -Force -Path .lore/_global | Out-Null
New-Item -ItemType Directory -Force -Path .lore/frontend | Out-Null
'{"schema_version":1,"mirror_targets":["CLAUDE.md"]}' | Out-File -Encoding ascii .lore/.config.json
"# Project summary`nPlaceholder.`n" | Out-File -Encoding ascii .lore/SUMMARY.md
```

- [ ] **Step 2: Empty `.lore/_global/` and `.lore/frontend/` so the empty-project adaptive rendering applies**

Run:
```bash
# Remove any entries from these scopes so Global/Scopes sections are empty
Get-ChildItem .lore/_global, .lore/frontend -Recurse -ErrorAction SilentlyContinue |
    Where-Object { -not $_.PSIsContainer } | Remove-Item -Force
```

- [ ] **Step 3: Invoke `lore mirror` via the AI agent and verify the rendered CLAUDE.md**

Load the `lore` skill in your AI agent and run `lore mirror`. The agent should write `CLAUDE.md` containing:

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

Verify:
- `Test-Path CLAUDE.md` returns `True`
- `Get-Content CLAUDE.md` matches the template above
- No `Global:` or `Scopes:` block is present (adaptive rendering)

If `Global:` or `Scopes:` appears despite empty `.lore/_global/` and `.lore/frontend/`, the section-visibility rules in `references/platform-mirrors.md` are not being followed — re-check Task 1.

- [ ] **Step 4: Clean up**

Run: `Pop-Location; Remove-Item -Recurse -Force "$env:TEMP\lore-index-verify-1"`

---

## Task 7: Manual verification — single scope with description

Verifies scope-description extraction from the `<!-- description: ... -->` HTML comment.

- [ ] **Step 1: Set up a temp project with one scope and a description comment**

Run:
```bash
$TEMP = New-Item -ItemType Directory -Path "$env:TEMP\lore-index-verify-2" -Force
Push-Location $TEMP.FullName
git init -q
New-Item -ItemType Directory -Force -Path .lore/_global/entries | Out-Null
New-Item -ItemType Directory -Force -Path .lore/frontend/entries | Out-Null
'{"schema_version":1,"mirror_targets":["CLAUDE.md"]}' | Out-File -Encoding ascii .lore/.config.json
"# Global`nOne global entry.`n" | Out-File -Encoding ascii .lore/SUMMARY.md
'<!-- description: React 18 + TypeScript frontend -->`n# Frontend`nUI code.`n' | Out-File -Encoding ascii .lore/frontend/SUMMARY.md
"content`n" | Out-File -Encoding ascii .lore/_global/entries/GLOBAL-2026-01-01-test.md
"content`n" | Out-File -Encoding ascii .lore/frontend/entries/FE-2026-01-01-test.md
New-Item -ItemType Directory -Force -Path packages/frontend | Out-Null
```

- [ ] **Step 2: Invoke `lore mirror` and verify the rendered CLAUDE.md**

Load the `lore` skill and run `lore mirror`. The agent should write `CLAUDE.md` containing the `Scopes:` block with one entry, including the description:

```markdown
**Structure**:
- Digest: `.lore/SUMMARY.md` (top-level overview)
- Global: `.lore/_global/` (architecture, decisions, conventions)
- Scopes:
  - `frontend` — packages/frontend/ (React 18 + TypeScript)
```

Verify:
- `Scopes:` block is present with exactly one row
- Row contains the description text "React 18 + TypeScript frontend" extracted from the HTML comment
- Path "packages/frontend/" appears (or the actual scope_dir value if auto-detected differently)

If the description text does not appear, the extraction rule in `references/platform-mirrors.md` is not being applied — re-check Task 1's "Scope description extraction" subsection.

- [ ] **Step 3: Clean up**

Run: `Pop-Location; Remove-Item -Recurse -Force "$env:TEMP\lore-index-verify-2"`

---

## Task 8: Manual verification — monorepo, mix of with-description and without-description

Verifies the multi-scope adaptive rendering with mixed description availability.

- [ ] **Step 1: Set up a temp monorepo with two scopes, one with description, one without**

Run:
```bash
$TEMP = New-Item -ItemType Directory -Path "$env:TEMP\lore-index-verify-3" -Force
Push-Location $TEMP.FullName
git init -q
New-Item -ItemType Directory -Force -Path .lore/_global/entries | Out-Null
New-Item -ItemType Directory -Force -Path .lore/frontend/entries | Out-Null
New-Item -ItemType Directory -Force -Path .lore/backend/entries | Out-Null
'{"schema_version":1,"mirror_targets":["CLAUDE.md"]}' | Out-File -Encoding ascii .lore/.config.json
"# Global`nOverview.`n" | Out-File -Encoding ascii .lore/SUMMARY.md
'<!-- description: React 18 + TypeScript frontend -->`n# Frontend`nUI.`n' | Out-File -Encoding ascii .lore/frontend/SUMMARY.md
"# Backend`n(no description comment)`nAPI.`n" | Out-File -Encoding ascii .lore/backend/SUMMARY.md
"g`n" | Out-File -Encoding ascii .lore/_global/entries/GLOBAL-2026-01-01-x.md
"f`n" | Out-File -Encoding ascii .lore/frontend/entries/FE-2026-01-01-x.md
"b`n" | Out-File -Encoding ascii .lore/backend/entries/BE-2026-01-01-x.md
New-Item -ItemType Directory -Force -Path packages/frontend | Out-Null
New-Item -ItemType Directory -Force -Path apps/backend | Out-Null
```

- [ ] **Step 2: Invoke `lore mirror` and verify the rendered CLAUDE.md**

Load the `lore` skill and run `lore mirror`. The agent should produce:

```markdown
**Structure**:
- Digest: `.lore/SUMMARY.md`
- Global: `.lore/_global/`
- Scopes:
  - `frontend` — packages/frontend/ (React 18 + TypeScript)
  - `backend` — apps/backend/
```

Verify:
- `frontend` row has the parenthetical description "React 18 + TypeScript frontend"
- `backend` row has NO parenthetical (description comment was absent)
- `backend` row still appears (omission means no parenthetical, not full row removal)

If `backend` is missing entirely, the "no description = omit description" rule is misapplied as "no description = omit scope" — re-check Task 1's "Field sources" subsection.

- [ ] **Step 3: Verify content-based dedup still works**

Run `lore mirror` a second time without changing anything. The agent should report `No changes needed: CLAUDE.md` for all targets (content is byte-identical to what's already on disk).

If a regeneration happens (file is rewritten unnecessarily), the dedup step in the mirror procedure is broken — but that's a pre-existing concern, not introduced by this change.

- [ ] **Step 4: Clean up**

Run: `Pop-Location; Remove-Item -Recurse -Force "$env:TEMP\lore-index-verify-3"`

---

## Self-review checklist (run before declaring done)

- [ ] All 5 doc files committed: `references/platform-mirrors.md`, `references/config.md`, `SKILL.md`, `README.md`, `README.zh-CN.md`.
- [ ] No mention of `mirror_mode: full` or `"summary"` as a recommended value remains anywhere in the modified files.
- [ ] `references/platform-mirrors.md` has the four new subsections: Index template, Field sources, Section visibility rules, Adaptive renderings, Scope description extraction.
- [ ] `references/config.md` `mirror_mode` description states `"index"` is the only accepted value and that other values error at config load.
- [ ] `SKILL.md:116` describes the mirror as an index, not as SUMMARY content.
- [ ] Both READMEs have the new "Token cost" / "Token 成本" section.
- [ ] Three manual scenarios pass (Tasks 6, 7, 8).
- [ ] `git status` clean on `main`.