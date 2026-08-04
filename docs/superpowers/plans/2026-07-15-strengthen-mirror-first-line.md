# Strengthen Mirror First Line — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the informational opening sentence in every generated platform mirror (`Project memory. Read deeper on demand.`) with an operational instruction that triggers agent action: tells the agent *when* to read `.lore/SUMMARY.md`, *what* to read, and *how* to cite entries back. Convert a passive descriptor into an imperative the agent is more likely to follow.

**Architecture:** Pure template-body change in `references/platform-mirrors.md`. The opening sentence lives inside the auto-managed `## Lore (auto-managed)` section, which is template body — non-breaking per `references/compatibility.md:86` ("Changing the index template body ... is non-breaking: content-based dedup means unchanged mirrors are not rewritten, so old mirrors stay valid"). No `schema_version` bump. No `migrate.py`. No script changes. Existing mirrors keep their old text until the next `lore mirror` / `compress` regenerates them.

**Tech Stack:** Markdown only; verification by reading rendered mirror files.

**Compatibility impact:**
- Non-breaking per `compatibility.md:86` (template body change)
- Does not touch any contract string (`<!-- LORE:START -->`, `<!-- LORE:END -->`, `## Lore (auto-managed)`, `## My notes (free edit)`, `---`)
- Old mirrors remain valid until regenerated; new mirrors use the new opening

---

## File map

| File | Action | Responsibility |
|---|---|---|
| `references/platform-mirrors.md` | Modify: §Index template (line 233-255), §Empty project (line 280-298), §Single-scope (line 301-309), §Monorepo (line 313-323) | Update the opening sentence in every rendered mirror |
| `README.md` | Modify: §What agents see (or equivalent) | Document that the opening line is operational |
| `README.zh-CN.md` | Modify: §What agents see (or equivalent) | Mirror change in Chinese |
| `sandbox/mock-todo-app/AGENTS.md` | Verify | Confirm rendered mirror carries new opening after regen |

---

## Task 1: Draft the replacement sentence

**Files:** none (planning only — captured in Task 2's edits)

- [ ] **Step 1: Confirm the replacement sentence**

The new opening sentence is:

```markdown
Project memory at `.lore/`. Before project-specific questions, read `.lore/SUMMARY.md`; cite entry IDs (e.g. `_global/ARCHITECTURE.md#ARCH-2026-01-15-d7a3`) when using memory.
```

Rationale (do not edit; for reviewer context):

- **Trigger:** `Before project-specific questions` — gives the agent a clear condition, not an open-ended "on demand".
- **Action:** `read \`.lore/SUMMARY.md\`` — names the single file the agent should pull first. Deeper lookups go through `lore query`, which the `**Query**:` line below already documents.
- **Citation format:** `cite entry IDs (e.g. \`_global/...\`)` — gives the agent a concrete output convention so downstream consumers can detect lore-grounded answers.
- **Cost:** ~210 chars including backticks; old line was ~38 chars. Net +172 chars per mirror — well under the ~500B flat budget per `config.md:86`.
- **Style:** preserves the `Project memory at <location>.` noun phrase so existing readers see familiar framing; the imperative clause follows.

If the reviewer wants a tighter version (for stricter budget), the fallback is:

```markdown
Project memory at `.lore/`. Before project-specific questions, read `.lore/SUMMARY.md`; cite entry IDs when using memory.
```

~140 chars. Pick one and proceed.

- [ ] **Step 2: Record the choice**

Write the chosen sentence into a comment block in the PR description so the implementer knows which version to use in Task 2.

---

## Task 2: Update the four template renderings in `platform-mirrors.md`

**Files:**
- Modify: `references/platform-mirrors.md:240, 286, 304-309, 313-323`

- [ ] **Step 1: Replace the main "Index template" opening**

In `references/platform-mirrors.md`, locate the main template (around lines 233-255) and replace the line:

```
Project memory. Read deeper on demand.
```

With the sentence chosen in Task 1.

For reference, the section starts at line 233 with `### Index template` and the opening line is at line 240, between `## Lore (auto-managed)` and the blank line before `**Structure**:`.

- [ ] **Step 2: Replace the "Empty project" template opening**

Locate the "Empty project" rendering (around lines 280-298). Replace:

```
Project memory. Read deeper on demand.
```

With the same sentence chosen in Task 1.

- [ ] **Step 3: Replace the "Single-scope project" template opening**

Locate the "Single-scope project" rendering (around lines 301-309). Replace:

```
Project memory. Read deeper on demand.
```

With the same sentence.

- [ ] **Step 4: Replace the "Monorepo with multiple scopes" template opening**

Locate the "Monorepo with multiple scopes" rendering (around lines 313-323). Replace:

```
Project memory. Read deeper on demand.
```

With the same sentence.

- [ ] **Step 5: Verify all four occurrences are consistent**

Run:

```bash
Get-Content references/platform-mirrors.md | Select-String -Pattern "Read deeper on demand"
```

Expected: zero matches.

Run:

```bash
Get-Content references/platform-mirrors.md | Select-String -Pattern "Before project-specific questions"
```

Expected: four matches (one per template rendering).

---

## Task 3: Update the "Adaptive renderings" header commentary

**Files:**
- Modify: `references/platform-mirrors.md:276-278`

- [ ] **Step 1: Update the rule about what stays constant across renderings**

Locate the section starting at line 276 (the `### Adaptive renderings` block). The current sentence says only the `**Structure**:` body varies. Replace the sentence:

> Only the `**Structure**:` body varies. The `<!-- LORE:START -->` / `<!-- LORE:END -->` markers, `## Lore (auto-managed)` opener, `---` separator, and `## My notes (free edit)` closer are always present and unchanged in new mirrors.

With:

> Only the `**Structure**:` body varies. The `<!-- LORE:START -->` / `<!-- LORE:END -->` markers, `## Lore (auto-managed)` opener, the first-line instruction (see below), the `---` separator, and the `## My notes (free edit)` closer are always present and unchanged in new mirrors.
>
> **First-line instruction.** The opening sentence after `## Lore (auto-managed)` is the agent-facing imperative that triggers memory lookup. It is constant across all renderings (empty / single-scope / multi-scope) because the agent's responsibility is the same regardless of project shape. Editing this sentence is a template-body change (non-breaking per `references/compatibility.md`).

- [ ] **Step 2: Verify**

Run: `Get-Content references/platform-mirrors.md | Select-String -Pattern "First-line instruction"`
Expected: at least one match.

---

## Task 4: Update README.md

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Locate the section that describes what agents see**

Run: `Get-Content README.md | Select-String -Pattern "Project memory|Read deeper|MIRROR|## How lore"`
Expected: a paragraph or section describing the mirror file's structure or content.

- [ ] **Step 2: Update the description of the opening line**

Find the sentence(s) that describe the mirror's opening line. Replace any text saying the opening line is "informational" or quoting the old `Project memory. Read deeper on demand.` text with:

> The mirror file opens with an imperative sentence (e.g. "Before project-specific questions, read `.lore/SUMMARY.md`; cite entry IDs when using memory.") so the consuming agent has a clear trigger to load memory. The line lives in `## Lore (auto-managed)` and is rewritten on every `compress` or `lore mirror` regeneration.

- [ ] **Step 3: Verify**

Run: `Get-Content README.md | Select-String -Pattern "Before project-specific questions"`
Expected: at least one match.

---

## Task 5: Update README.zh-CN.md

**Files:**
- Modify: `README.zh-CN.md`

- [ ] **Step 1: Mirror the README change in Chinese**

In the equivalent section of `README.zh-CN.md`, replace the description of the opening line with:

> 镜像文件以一句祈使句开头（例如："Before project-specific questions, read `.lore/SUMMARY.md`; cite entry IDs when using memory."），让消费侧 agent 有明确的触发条件去加载 memory。该行位于 `## Lore (auto-managed)` 段落内，每次 `compress` 或 `lore mirror` 重新生成时会被覆写。

(Translation kept English for the example sentence so reviewers see the actual rendered text; the surrounding explanation is in Chinese.)

- [ ] **Step 2: Verify**

Run: `Get-Content README.zh-CN.md | Select-String -Pattern "Before project-specific questions"`
Expected: at least one match.

---

## Task 6: Regenerate and verify the sandbox mirror

**Files:**
- Verify: `sandbox/mock-todo-app/AGENTS.md`

- [ ] **Step 1: Confirm the sandbox mirror file currently has the old opening**

Run: `Get-Content sandbox/mock-todo-app/AGENTS.md | Select-String -Pattern "Read deeper on demand"`
Expected: one match (the old sentence still in the sandbox mirror).

- [ ] **Step 2: Regenerate the mirror in the sandbox**

The exact regeneration command depends on how `lore mirror` is invoked in the sandbox fixture. If the sandbox has a helper script, run it; otherwise invoke the skill's mirror-generation workflow directly. Expected output: "Mirror updated: AGENTS.md".

For a manual regeneration without invoking the full skill:

- Read `sandbox/mock-todo-app/.lore/_global/ARCHITECTURE.md` (and the scope ARCHITECTURE.md files) for the `<!-- description: ... -->` lines.
- Re-emit the `## Lore (auto-managed)` block using the new template from Task 2.
- Replace the block in `sandbox/mock-todo-app/AGENTS.md` between `<!-- LORE:START -->` and `<!-- LORE:END -->`.
- Preserve everything after `<!-- LORE:END -->` verbatim.

- [ ] **Step 3: Verify the new opening landed**

Run: `Get-Content sandbox/mock-todo-app/AGENTS.md | Select-String -Pattern "Read deeper on demand"`
Expected: zero matches.

Run: `Get-Content sandbox/mock-todo-app/AGENTS.md | Select-String -Pattern "Before project-specific questions"`
Expected: one match.

- [ ] **Step 4: Verify My notes section was preserved verbatim**

Run: `Get-Content sandbox/mock-todo-app/AGENTS.md`
Expected: the section after `---` and `## My notes (free edit)` is identical to what it was before regeneration. If My notes was empty, it is still empty; if it had user content, that content is unchanged.

---

## Task 7: Sanity-check the full skill

**Files:** none

- [ ] **Step 1: Re-run the standard verification commands from `AGENTS.md`**

```bash
python scripts/id_hash.py "test entry"
python scripts/list_entries.py
python scripts/list_entries.py --json | head -20
python scripts/find_duplicates.py --json
python scripts/find_stale.py --days=90 --json
```

All expected to exit 0 with sensible output. (No scripts touched, so this is just a regression guard.)

- [ ] **Step 2: Spot-check that no contract string was changed**

Run: `Get-Content references/platform-mirrors.md | Select-String -Pattern "LORE:START|LORE:END|Lore \(auto-managed\)|My notes \(free edit\)"`
Expected: all four contract strings still appear unchanged (they are inside `<!-- -->` HTML comments or `##` headers; verify line text matches the contract).

- [ ] **Step 3: Spot-check the rendered mirror file**

Open `sandbox/mock-todo-app/AGENTS.md` and confirm:

- The `<!-- LORE:START -->` opener is unchanged.
- `## Lore (auto-managed)` header is unchanged.
- The new opening sentence follows on the next line.
- `**Structure**:` body shows current scope structure (single-scope or multi-scope, whichever applies).
- `**Query**:` and `**Update**:` lines are unchanged.
- `<!-- LORE:END -->` closer is unchanged.
- `---` separator is unchanged.
- `## My notes (free edit)` is unchanged.

---

## Self-review checklist

- [ ] **Spec coverage:**
  - New opening sentence in all four template renderings: Task 2 ✓
  - Adaptive-renderings rule documents the new constant: Task 3 ✓
  - README describes the new line: Task 4 ✓
  - README.zh-CN mirrors: Task 5 ✓
  - Sandbox mirror updated: Task 6 ✓
  - Full skill regression-checked: Task 7 ✓

- [ ] **Placeholder scan:** none of "TBD", "TODO", "implement later", "similar to Task N" appear.

- [ ] **Contract strings preserved:** `<!-- LORE:START -->`, `<!-- LORE:END -->`, `## Lore (auto-managed)`, `## My notes (free edit)`, `---` all unchanged.

- [ ] **No `migrate.py`:** template body change only.

- [ ] **No `schema_version` bump:** no config schema touched.

- [ ] **No script changes:** `scripts/*.py` untouched.

---

## Verification matrix

| Test | Command | Expected |
|---|---|---|
| Template renderings consistent | `Get-Content references/platform-mirrors.md \| Select-String -Pattern "Before project-specific questions"` | 4 matches |
| Old sentence gone from spec | `Get-Content references/platform-mirrors.md \| Select-String -Pattern "Read deeper on demand"` | 0 matches |
| README mentions new line | `Get-Content README.md \| Select-String -Pattern "Before project-specific questions"` | ≥1 match |
| README.zh-CN mentions new line | `Get-Content README.zh-CN.md \| Select-String -Pattern "Before project-specific questions"` | ≥1 match |
| Sandbox mirror has new opening | `Get-Content sandbox/mock-todo-app/AGENTS.md \| Select-String -Pattern "Before project-specific questions"` | 1 match |
| Sandbox mirror preserves My notes | Visual diff of `sandbox/mock-todo-app/AGENTS.md` after/before | My notes section byte-identical |
| Scripts untouched | `git diff --stat scripts/` | empty |
| Contract strings untouched | grep for the five contract strings in `platform-mirrors.md` | all present, text unchanged |

---

## Out of scope (deferred)

- **Per-platform customization** of the opening sentence (e.g. a Claude-specific phrasing vs. an OpenCode-specific one). Premature; one-size-fits-all is fine until evidence shows otherwise.
- **Embedding SUMMARY excerpts** in the mirror — explicitly rejected (would re-introduce selection bias and blow the 500B flat budget; see Plan A context).
- **Auto-instrumenting agent compliance** (e.g. logging whether the agent actually read `.lore/SUMMARY.md` after seeing the instruction). Out of scope for this skill.
- **Migrating existing mirrors** — content-based dedup handles this naturally; old mirrors stay valid until the next regeneration, at which point they pick up the new line.