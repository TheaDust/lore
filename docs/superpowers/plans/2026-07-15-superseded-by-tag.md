# `#superseded-by:ID` Link Tag — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an entry tag `#superseded-by:LAYER-YYYY-MM-DD-xxxx` that explicitly links a stale entry to its replacement, turning the implicit narrative chain ("was superseded by bcrypt") into data that `find_stale`, `history`, `compress`, and `audit` can all consume.

**Architecture:** Additive change. New tag added to the closed tag set (`compatibility.md:27` already permits this). No `schema_version` bump — tag is entry-level, not config-schema. Old skills silently ignore unknown tags. New scripts parse and expose a `replaced_by` field; consumers (audit, summary, history) use it to surface chains instead of relying on prose.

**Tech Stack:** Python 3.6+ stdlib only; Markdown; bash for verification.

**Compatibility impact:**
- Non-breaking per `references/compatibility.md:27` ("Adding a new tag is allowed; old skills' tag parsers ... silently ignore unknown tags")
- Non-breaking per `compatibility.md:28` ("Never make a tag required")
- Does NOT require `schema_version` bump — entry format is not config schema
- Does NOT require `scripts/migrate.py`

---

## File map

| File | Action | Responsibility |
|---|---|---|
| `references/entry-format.md` | Modify:30-39, append §superseded-by | Tag spec table + example + interaction with `#stale` |
| `references/stale-new-markers.md` | Modify: append §superseded-by interaction | When `sync` emits `[STALE]`, propose `#superseded-by:NEW_ID` alongside `#stale:DATE` |
| `references/summary-template.md` | Modify: §Selection rule | Skip entries with `replaced_by` set when picking 3–5 per (scope, layer) |
| `references/audit-template.md` | Modify: §CONFLICT example + §Severity | Audit walks the chain; reports `head` only when chain is intact |
| `references/history-command.md` | Modify: §Output, §Synopsis | Document `--follow-superseded` flag and chain traversal |
| `references/compatibility.md` | Modify: §Layer 2 entry format | Update tag-set table; note `#superseded-by` as additive |
| `SKILL.md` | Modify: §sync procedure | Sync workflow sets `#superseded-by` alongside `#stale` when emitting `[STALE]` |
| `scripts/list_entries.py` | Modify: §parse_entry | Parse `#superseded-by:<id>`; expose `replaced_by` field |
| `scripts/find_stale.py` | Modify: §main | Group `pending_archive` by `replaced_by`; surface broken chains |
| `scripts/history.py` | Modify: §main, §render_* | Add `--follow-superseded`; walk chain via repeated `list_entries.py --json` lookup |
| `README.md` + `README.zh-CN.md` | Modify: §What lore does | Mention new tag in feature list |
| `sandbox/mock-todo-app/.lore/scopes/backend/DECISIONS.md` | Modify: line 1 | Add `#superseded-by:DEC-2026-07-10-e45d` to entry `ee31` for E2E |

---

## Task 1: Define the tag spec

**Files:**
- Modify: `references/entry-format.md:30-58`

- [ ] **Step 1: Replace the tag spec table to include the new tag**

In `references/entry-format.md`, replace the current table at lines 30-39 with:

```markdown
| Tag | Meaning |
|---|---|
| `#added:YYYY-MM-DD` | When the entry was created |
| `#verified:YYYY-MM-DD` | Last time a human or audit confirmed the entry is still true |
| `#stale:YYYY-MM-DD` | Flagged by `sync` as superseded or contradicted; user decides keep/archive |
| `#archived:YYYY-MM-DD` | Moved to `archive/` |
| `#superseded-by:LAYER-YYYY-MM-DD-xxxx` | Points to the entry that replaces this one (set together with `#stale`); the `xxxx` is the 4-hex content hash of the replacement |
```

- [ ] **Step 2: Append a new section after the existing examples (after line 60)**

Append to `references/entry-format.md`:

```markdown
## Superseded-by chain

When an entry is replaced by another (e.g. a tech-stack swap, a convention reversal), the old entry carries `#superseded-by:<new-id>` alongside `#stale:<date>`. This turns the replacement relationship from prose into data that scripts can walk.

Syntax: `#superseded-by:LAYER-YYYY-MM-DD-xxxx` — the replacement entry's full ID. The replacement entry itself carries no back-reference; its `#verified:DATE` and `#added:DATE` are sufficient.

Worked example — bcrypt replaces SHA-256 in `scopes/backend/DECISIONS.md`:

```markdown
- [DEC-2026-07-10-ee31] SHA-256 + salt for password hashing; reason: no native dep, deterministic. #added:2026-07-10 #stale:2026-07-10 #superseded-by:DEC-2026-07-10-e45d
- [DEC-2026-07-10-e45d] Use bcrypt (rounds=12) for password hashing; reason: industry standard, built-in salt. #added:2026-07-10
```

Consumers:

- `find_stale.py --json` — groups stale entries by their `replaced_by` target; flags chains where the target ID does not exist (broken chain).
- `history.py --follow-superseded <id>` — prints the entry plus every successor along the chain (newest first).
- `compress` — skips entries with `replaced_by` set when selecting the 3–5 entries per (scope, layer).
- `audit` — when reporting CONFLICT between two entries, surfaces the chain if both belong to one.

Constraints:

- The tag is **optional**. Old entries without it continue to work; old skills ignore it.
- Multiple `#superseded-by` tags on one entry are permitted (rare; means the entry was replaced more than once).
- Cross-file references: the ID is sufficient because the LAYER prefix plus hash makes collisions across files vanishingly rare. If two files contain the same ID, prefer the one in the same scope as the entry being read.
```

- [ ] **Step 3: Verify the file is internally consistent**

Run: `Get-Content references/entry-format.md`
Expected: file reads cleanly, the new table row matches the worked-example tag, the cross-references in scripts' docstrings (e.g. `list_entries.py:14-22`) remain accurate.

---

## Task 2: Update compatibility.md tag-set note

**Files:**
- Modify: `references/compatibility.md:27`

- [ ] **Step 1: Update the closed tag-set statement**

Replace line 27 in `references/compatibility.md`:

> Tag set is a closed set today: `#added`, `#verified`, `#stale`, `#archived`.

With:

> Tag set is a closed set today: `#added`, `#verified`, `#stale`, `#archived`, `#superseded-by`. Adding a new tag is allowed; old skills' tag parsers (which match `(added|verified|stale|archived|superseded-by)`) silently ignore unknown tags.

- [ ] **Step 2: Verify**

Run: `Get-Content references/compatibility.md | Select-String -Pattern "superseded-by"`
Expected: at least one match in the updated tag-set statement.

---

## Task 3: Update stale-new-markers.md to teach sync to emit the chain

**Files:**
- Modify: `references/stale-new-markers.md:48-58`

- [ ] **Step 1: Replace the `[STALE]` row in the "Marker → file operation mapping" table**

Replace the row for `[STALE]` (currently: "Append `#stale:<today>` tag to the existing entry; entry stays in the file"):

> Append `#stale:<today>` tag to the existing entry; entry stays in the file

With:

> Append `#stale:<today>` and `#superseded-by:<replacement-id>` tags to the existing entry; entry stays in the file. When `sync` proposes `[STALE]`, it must also know the replacement entry's ID (the one that supersedes it). If the replacement is a `[NEW]` entry in the same proposal, carry its ID forward. If no replacement is known, emit `#stale:<today>` only and let the user fill the chain in a later sync.

- [ ] **Step 2: Update the worked example**

Replace the worked example for `[STALE]` (lines 23-24):

```markdown
## [STALE] Candidates for archive
- [scopes/frontend/ARCHITECTURE.md] [ARCH-2026-01-15-d7a3] Use Pages Router (Next.js). #stale:2026-07-09
  Evidence: `frontend/package.json` shows `"next": "^14.0.0"` with `app/` directory present.
```

With:

```markdown
## [STALE] Candidates for archive
- [scopes/frontend/ARCHITECTURE.md] [ARCH-2026-01-15-d7a3] Use Pages Router (Next.js). #stale:2026-07-09 #superseded-by:ARCH-2026-07-09-b4d2
  Evidence: `frontend/package.json` shows `"next": "^14.0.0"` with `app/` directory present.
  Replaced by: `[ARCH-2026-07-09-b4d2] Use App Router (Next.js 14)` (new entry in this proposal).
```

- [ ] **Step 3: Verify**

Run: `Get-Content references/stale-new-markers.md | Select-String -Pattern "superseded-by"`
Expected: matches in both the table row and the worked example.

---

## Task 4: Update summary-template.md selection rule

**Files:**
- Modify: `references/summary-template.md:40-50`

- [ ] **Step 1: Add a new selection rule before the existing ones**

In `references/summary-template.md`, insert before the current rule "1. Most recent `#verified` date wins":

```markdown
0. **Skip entries with `#superseded-by:<id>`.** These are historical entries replaced by a newer one; the SUMMARY should reflect current state, not chain history.
```

- [ ] **Step 2: Verify by reading the section**

Run: `Get-Content references/summary-template.md`
Expected: rule 0 reads cleanly above the existing priority list (1, 2, 3).

---

## Task 5: Update audit-template.md for chain-aware findings

**Files:**
- Modify: `references/audit-template.md:14-26`

- [ ] **Step 1: Update the worked example to include chain info**

In `references/audit-template.md`, replace the example `### CONFLICT` block (lines 17-19) with:

```markdown
### CONFLICT
- [DEC-2026-01-20-b1e8] claims "all packages TypeScript strict mode"
  Evidence: `packages/legacy/tsconfig.json` has `"strict": false`
  Note: entry `DEC-2026-01-20-b1e8` carries `#superseded-by:DEC-2026-03-15-c5e1`; if the chain is intact, treat the conflict as a chain-resolution case (see `references/entry-format.md#superseded-by-chain`).
```

- [ ] **Step 2: Add a worked example showing a broken chain**

Append a new section after the existing "Severity definitions":

```markdown
## Broken chains

If `audit` finds an entry tagged `#superseded-by:<id>` but `<id>` does not exist anywhere in `.lore/`, surface as a `BROKEN_CHAIN` finding under the scope containing the orphan. Example:

```markdown
## Scope: backend

### BROKEN_CHAIN
- [DEC-2026-07-10-ee31] carries `#superseded-by:DEC-2026-07-10-e45d`
  Evidence: target ID `DEC-2026-07-10-e45d` not found in any `.lore/*.md`. The replacement entry was never written (or was deleted, which lore does not normally do).
  Recommended action: write the replacement entry, or remove the `#superseded-by:` tag.
```

This severity is distinct from `CONFLICT` because the entries don't disagree — one is just orphaned.
```

- [ ] **Step 3: Add BROKEN_CHAIN to the severity table**

In `references/audit-template.md`, replace the severity table (lines 47-51) with:

```markdown
| Severity | Meaning |
|---|---|
| `CONFLICT` | Code/config directly contradicts the entry content (e.g. memory says `react@18`, `package.json` says `16`). If the entry is in a `#superseded-by` chain, check whether the chain resolves the conflict before reporting. |
| `STALE` | Entry references a resource (file, API, version) that no longer exists |
| `UNVERIFIED` | Entry's `#verified` date is >90 days; needs re-confirmation |
| `BROKEN_CHAIN` | Entry carries `#superseded-by:<id>` but `<id>` is not present in `.lore/` |
```

- [ ] **Step 4: Verify**

Run: `Get-Content references/audit-template.md | Select-String -Pattern "BROKEN_CHAIN|superseded-by"`
Expected: at least 4 matches across the severity table, worked example, broken-chain section, and severity definitions.

---

## Task 6: Update history-command.md with --follow-superseded

**Files:**
- Modify: `references/history-command.md:5-15, 41-74`

- [ ] **Step 1: Update the Synopsis to add the new flag**

Replace the Synopsis (lines 5-15):

```
lore history <entry-id>
lore history <file-path>
lore history --scope=<name>
lore history --since=<YYYY-MM-DD>
lore history --json
```

With:

```
lore history <entry-id>
lore history <file-path>
lore history --scope=<name>
lore history --since=<YYYY-MM-DD>
lore history --follow-superseded
lore history --json
```

- [ ] **Step 2: Add a new section after "Forms" (after line 24)**

Append:

```markdown
### `--follow-superseded`

When set on the entry form, prints not just the requested entry's git history, but the history of every entry in its `#superseded-by` chain (newest successor first). Stops when an entry has no `#superseded-by` tag or the chain reaches a non-existent ID. Output prepends a `## Chain` section listing each entry's ID and file path before the per-entry `git log` blocks.

Example:

```
$ lore history --follow-superseded DEC-2026-07-10-ee31

# history: [DEC-2026-07-10-ee31] --follow-superseded

## Chain
1. [DEC-2026-07-10-ee31] (scopes/backend/DECISIONS.md) — SHA-256 + salt
   → superseded-by → DEC-2026-07-10-e45d
2. [DEC-2026-07-10-e45d] (scopes/backend/DECISIONS.md) — bcrypt (rounds=12)
   → no successor

# history: [DEC-2026-07-10-ee31]

> Entry: scopes/backend/DECISIONS.md
> Since: 2026-07-10
> File: backend/app/auth.py
> Commits: 3 (showing all)

...
```
```

- [ ] **Step 3: Update the JSON output example (lines 53-74) to add `chain` field**

Replace the JSON example with:

```json
{
  "entry_id": "DEC-2026-02-03-7c19",
  "lore_file": "scopes/frontend/DECISIONS.md",
  "code_file": "frontend/src/store/index.ts",
  "since": "2026-02-03",
  "since_source": "entry_added",
  "chain": null,
  "commits": [
    {
      "hash": "...",
      "short": "abc1234",
      "author": "alice",
      "date": "2026-04-12",
      "subject": "Use Zustand v4",
      "body": "Migrate notes here.",
      "refs": ["#234"]
    }
  ]
}
```

When `--follow-superseded` is set, `chain` is an array of `{entry_id, lore_file, code_file, since}` for each successor; otherwise `null`.

- [ ] **Step 4: Verify**

Run: `Get-Content references/history-command.md | Select-String -Pattern "follow-superseded|chain"`
Expected: matches in Synopsis, new section, and JSON example.

---

## Task 7: Update SKILL.md sync workflow

**Files:**
- Modify: `SKILL.md` sync procedure around line 215

- [ ] **Step 1: Find the current sync procedure's `[STALE]` step**

Run: `Get-Content SKILL.md | Select-String -Pattern "STALE|superseded" -Context 2,2`
Expected: see the existing bullet about marking old entries `#stale:<today>` and emitting an ALERT.

- [ ] **Step 2: Update that bullet to also set `#superseded-by`**

Locate the bullet in `SKILL.md` that says (approximately):

> Contradicts an existing entry in the same scope/layer → mark the old one `#stale:<today>`. Emit an ALERT.

Replace with:

> Contradicts an existing entry in the same scope/layer → mark the old one `#stale:<today>` and `#superseded-by:<new-id>` (where `<new-id>` is the entry in this proposal that replaces it). Emit an ALERT.
>
> No replacement entry exists yet (user is removing a fact without substituting) → mark the old one `#stale:<today>` only; the chain can be backfilled later.

- [ ] **Step 3: Verify**

Run: `Get-Content SKILL.md | Select-String -Pattern "superseded-by" -Context 1,1`
Expected: at least one match in the sync procedure.

---

## Task 8: Update `scripts/list_entries.py` to parse the new tag

**Files:**
- Modify: `scripts/list_entries.py:82-108`

- [ ] **Step 1: Add `#superseded-by` to the tag regex**

Replace line 95:

```python
tag_re = re.compile(r"#(added|verified|stale|archived):(\S+)")
```

With:

```python
# #superseded-by:<id> where <id> is LAYER-YYYY-MM-DD-xxxx; treat the
# value as a single token (no spaces) so the same regex captures the
# rest of the line cleanly.
ENTRY_ID = r"[A-Z]+-\d{4}-\d{2}-\d{2}-[a-f0-9]{4}"
tag_re = re.compile(
    r"#(added|verified|stale|archived):(\S+)"
    r"|#superseded-by:(" + ENTRY_ID + r")"
)
```

- [ ] **Step 2: Replace the tag-extraction block to populate `tags` and `replaced_by` separately**

Replace lines 94-97:

```python
    # Extract #tag:value pairs
    tag_re = re.compile(r"#(added|verified|stale|archived):(\S+)")
    tags = {name: val for name, val in tag_re.findall(rest)}
    text = tag_re.sub("", rest).strip()
```

With:

```python
    tags = {}
    replaced_by = None
    for m in tag_re.finditer(rest):
        if m.group(1):
            tags[m.group(1)] = m.group(2)
        elif m.group(3):
            if replaced_by is None:
                replaced_by = m.group(3)
            else:
                # Multiple #superseded-by tags: keep the first, drop the rest
                # from `tags` to avoid surprising downstream consumers.
                # (Documented as permitted in references/entry-format.md.)
                pass
    text = tag_re.sub("", rest).strip()
```

- [ ] **Step 3: Add `replaced_by` to the returned dict**

Replace the return block (lines 99-108):

```python
    return {
        "id": eid,
        "layer": layer,
        "layer_file": None,  # filled in by caller
        "scope": None,       # filled in by caller
        "file": None,        # filled in by caller
        "text": text,
        "tags": tags,
        "last_verified": tags.get("verified"),
    }
```

With:

```python
    return {
        "id": eid,
        "layer": layer,
        "layer_file": None,  # filled in by caller
        "scope": None,       # filled in by caller
        "file": None,        # filled in by caller
        "text": text,
        "tags": tags,
        "last_verified": tags.get("verified"),
        "replaced_by": replaced_by,
    }
```

- [ ] **Step 4: Update the human-readable output to surface `replaced_by`**

Replace lines 174-179:

```python
    for e in entries:
        verified = (
            f" [verified:{e['last_verified']}]" if e["last_verified"] else ""
        )
        stale = " [STALE]" if "stale" in e["tags"] else ""
        print(f"[{e['file']}] {e['id']} {e['text']}{verified}{stale}")
```

With:

```python
    for e in entries:
        verified = (
            f" [verified:{e['last_verified']}]" if e["last_verified"] else ""
        )
        stale = " [STALE]" if "stale" in e["tags"] else ""
        chain = (
            f" → {e['replaced_by']}" if e.get("replaced_by") else ""
        )
        print(f"[{e['file']}] {e['id']} {e['text']}{verified}{stale}{chain}")
```

- [ ] **Step 5: Verify against sandbox fixture**

Run (from `sandbox/mock-todo-app/`):

```bash
cd sandbox/mock-todo-app && python ../../scripts/list_entries.py
```

Expected: each entry prints as before; entries with `#superseded-by:` (added in Task 12) show `→ <id>`.

Run with `--json`:

```bash
cd sandbox/mock-todo-app && python ../../scripts/list_entries.py --json | python -c "import json,sys; d=json.load(sys.stdin); print([e for e in d if e.get('replaced_by')])"
```

Expected: a non-empty list of entries with `replaced_by` populated once Task 12 lands. (Before Task 12, the list is empty — that's correct too.)

---

## Task 9: Update `scripts/find_stale.py` to surface chains

**Files:**
- Modify: `scripts/find_stale.py:67-94, 98-113`

- [ ] **Step 1: Group `pending_archive` entries by `replaced_by` and detect broken chains**

Replace the entry-classification loop (lines 71-86):

```python
    for e in entries:
        # Already marked stale → pending archive
        if "stale" in e["tags"]:
            pending_arch.append(e)
            continue

        # Determine the entry's freshness date
        last_v = parse_date(e["last_verified"])
        added = parse_date(e["tags"].get("added"))
        ref_date = last_v or added

        if ref_date is None:
            continue  # no date info, can't decide

        if ref_date < cutoff:
            stale.append(e)
```

With:

```python
    # Build a quick lookup for chain validation.
    by_id = {e["id"]: e for e in entries}

    broken_chains = []
    pending_arch_by_chain = {}  # replaced_by -> [entry, ...]

    for e in entries:
        # Already marked stale → pending archive (and maybe broken chain)
        if "stale" in e["tags"]:
            target = e.get("replaced_by")
            if target and target not in by_id:
                broken_chains.append({
                    "id": e["id"],
                    "file": e["file"],
                    "text": e["text"],
                    "missing_target": target,
                })
            if target:
                pending_arch_by_chain.setdefault(target, []).append(e)
            else:
                # No chain info — keep under a sentinel so the existing
                # output still includes it.
                pending_arch_by_chain.setdefault(None, []).append(e)
            continue

        # Determine the entry's freshness date
        last_v = parse_date(e["last_verified"])
        added = parse_date(e["tags"].get("added"))
        ref_date = last_v or added

        if ref_date is None:
            continue  # no date info, can't decide

        if ref_date < cutoff:
            stale.append(e)
```

- [ ] **Step 2: Update the JSON output to include `chains` and `broken_chains`**

Replace lines 88-96:

```python
    if json_output:
        out = {
            "threshold_days": days,
            "as_of": today.isoformat(),
            "stale": stale,
            "pending_archive": pending_arch,
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return
```

With:

```python
    if json_output:
        out = {
            "threshold_days": days,
            "as_of": today.isoformat(),
            "stale": stale,
            "pending_archive": pending_arch,
            "chains": {
                target: [e["id"] for e in entries_]
                for target, entries_ in pending_arch_by_chain.items()
                if target is not None
            },
            "broken_chains": broken_chains,
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return
```

- [ ] **Step 3: Update the human-readable output to show chains**

Replace lines 98-112:

```python
    print(f"=== Stale (unverified > {days} days, as of {today}) ===")
    if not stale:
        print("  (none)")
    for e in stale:
        ref = e["last_verified"] or e["tags"].get("added", "unknown")
        print(f"  [{e['file']}] {e['id']} {e['text']}")
        print(f"    ref date: {ref}")

    print()
    print("=== Pending archive (tagged #stale) ===")
    if not pending_arch:
        print("  (none)")
    for e in pending_arch:
        print(f"  [{e['file']}] {e['id']} {e['text']}")
        print(f"    marked stale: {e['tags']['stale']}")
```

With:

```python
    print(f"=== Stale (unverified > {days} days, as of {today}) ===")
    if not stale:
        print("  (none)")
    for e in stale:
        ref = e["last_verified"] or e["tags"].get("added", "unknown")
        print(f"  [{e['file']}] {e['id']} {e['text']}")
        print(f"    ref date: {ref}")

    print()
    print("=== Pending archive (tagged #stale, grouped by replacement) ===")
    if not pending_arch_by_chain:
        print("  (none)")
    for target, entries_ in sorted(
        pending_arch_by_chain.items(), key=lambda kv: (kv[0] is None, kv[0] or "")
    ):
        if target is None:
            print("  (no #superseded-by chain):")
        else:
            print(f"  → superseded-by {target}:")
        for e in entries_:
            chain = (
                f" → {e['replaced_by']}" if e.get("replaced_by") else ""
            )
            print(f"    [{e['file']}] {e['id']} {e['text']}{chain}")

    if broken_chains:
        print()
        print("=== Broken chains (#superseded-by target not found) ===")
        for b in broken_chains:
            print(f"  [{b['file']}] {b['id']} {b['text']}")
            print(f"    missing: {b['missing_target']}")
```

- [ ] **Step 4: Verify**

Run (from `sandbox/mock-todo-app/`, after Task 12):

```bash
cd sandbox/mock-todo-app && python ../../scripts/find_stale.py --json | python -c "import json,sys; d=json.load(sys.stdin); print(d['chains']); print(d['broken_chains'])"
```

Expected: `chains` shows `{"DEC-2026-07-10-e45d": ["DEC-2026-07-10-ee31"]}` and `broken_chains` is `[]`.

---

## Task 10: Update `scripts/history.py` to add `--follow-superseded`

**Files:**
- Modify: `scripts/history.py:432-480`

- [ ] **Step 1: Add `follow_superseded` to the args parsing**

Replace lines 433-446:

```python
def main():
    args = sys.argv[1:]
    json_mode = "--json" in args
    since_override = None
    for a in args:
        if a.startswith("--since="):
            since_override = a.split("=", 1)[1]

    positional = [a for a in args if a != "--json" and not a.startswith("--since=")]
    if not positional:
        print("usage: lore history <entry-id|file-path|--scope=NAME>",
              file=sys.stderr)
        die(ERR_USAGE, "missing argument")
```

With:

```python
def main():
    args = sys.argv[1:]
    json_mode = "--json" in args
    follow_superseded = "--follow-superseded" in args
    since_override = None
    for a in args:
        if a.startswith("--since="):
            since_override = a.split("=", 1)[1]

    positional = [
        a for a in args
        if a != "--json"
        and a != "--follow-superseded"
        and not a.startswith("--since=")
    ]
    if not positional:
        print(
            "usage: lore history <entry-id|file-path|--scope=NAME> "
            "[--follow-superseded] [--since=YYYY-MM-DD] [--json]",
            file=sys.stderr,
        )
        die(ERR_USAGE, "missing argument")
```

- [ ] **Step 2: Add a chain-traversal function before `main()`**

Insert just before `def main():` (after line 431):

```python
def walk_supersede_chain(entries_by_id, start_id, max_depth=20):
    """Follow #superseded-by links forward from start_id.

    Returns a list of entry dicts [start, successor1, successor2, ...].
    Stops when an entry has no replaced_by tag, the target is missing,
    or max_depth is reached (cycle protection).

    `entries_by_id` is a dict {id: entry_dict} from list_entries.py --json.
    """
    chain = []
    seen = set()
    current_id = start_id
    for _ in range(max_depth):
        if current_id in seen:
            break  # cycle; don't loop forever
        seen.add(current_id)
        entry = entries_by_id.get(current_id)
        if entry is None:
            break
        chain.append(entry)
        next_id = entry.get("replaced_by")
        if not next_id:
            break
        current_id = next_id
    return chain
```

- [ ] **Step 3: Wire `--follow-superseded` into the entry form**

Replace the entry-form branch (lines 457-480):

```python
    if parsed["form"] == "entry":
        entries = _load_entries_via_subprocess()
        entry = find_entry(entries, parsed["value"])
        if entry is None:
            ids = ", ".join(e["id"] for e in entries[:20])
            more = "" if len(entries) <= 20 else f" (and {len(entries)-20} more)"
            die(ERR_NO_ENTRY,
                f"Entry {parsed['value']} not found. Available: {ids}{more}")
        since = since_override or extract_added_date(entry.get("tags", {}))
        if since is None:
            print("warning: entry has no #added tag; using full history",
                  file=sys.stderr)
            since = "1970-01-01"
        since = normalize_since(since)
        code_file = resolve_code_file(entry)
        try:
            commits = run_git_log(project_root, since, code_file)
        except RuntimeError as exc:
            die(ERR_GIT_FAIL, str(exc))
        _enrich_commits_with_body_and_refs(project_root, commits)
        meta = _build_meta_entry(entry, code_file, since, "entry_added")
        out = render_json(meta, commits) if json_mode else render_markdown(meta, commits)
        print(out)
        return
```

With:

```python
    if parsed["form"] == "entry":
        entries = _load_entries_via_subprocess()
        entries_by_id = {e["id"]: e for e in entries}
        entry = find_entry(entries, parsed["value"])
        if entry is None:
            ids = ", ".join(e["id"] for e in entries[:20])
            more = "" if len(entries) <= 20 else f" (and {len(entries)-20} more)"
            die(ERR_NO_ENTRY,
                f"Entry {parsed['value']} not found. Available: {ids}{more}")

        chain = ([entry] if not follow_superseded
                 else walk_supersede_chain(entries_by_id, entry["id"]))

        # Render the requested entry's history first (unchanged behavior),
        # then optionally prepend a chain summary.
        since = since_override or extract_added_date(entry.get("tags", {}))
        if since is None:
            print("warning: entry has no #added tag; using full history",
                  file=sys.stderr)
            since = "1970-01-01"
        since = normalize_since(since)
        code_file = resolve_code_file(entry)
        try:
            commits = run_git_log(project_root, since, code_file)
        except RuntimeError as exc:
            die(ERR_GIT_FAIL, str(exc))
        _enrich_commits_with_body_and_refs(project_root, commits)
        meta = _build_meta_entry(entry, code_file, since, "entry_added")
        if follow_superseded:
            meta["chain"] = [
                {
                    "entry_id": e["id"],
                    "lore_file": e["file"],
                    "code_file": resolve_code_file(e),
                    "since": extract_added_date(e.get("tags", {})) or "1970-01-01",
                }
                for e in chain
            ]
        else:
            meta["chain"] = None
        out = render_json(meta, commits) if json_mode else render_markdown(meta, commits)
        print(out)
        return
```

- [ ] **Step 4: Verify**

Run (from `sandbox/mock-todo-app/`, after Task 12):

```bash
cd sandbox/mock-todo-app && python ../../scripts/history.py DEC-2026-07-10-ee31
```

Expected: prints history of the SHA-256 entry as before.

```bash
cd sandbox/mock-todo-app && python ../../scripts/history.py --follow-superseded DEC-2026-07-10-ee31
```

Expected: prints a `## Chain` section listing both `ee31` and `e45d`, then the history of `ee31`.

```bash
cd sandbox/mock-todo-app && python ../../scripts/history.py --follow-superseded DEC-2026-07-10-ee31 --json
```

Expected: JSON output has a non-null `chain` array of length 2.

---

## Task 11: Update README.md and README.zh-CN.md

**Files:**
- Modify: `README.md` (find the "Features" or "How lore works" section)
- Modify: `README.zh-CN.md` (same)

- [ ] **Step 1: Find the right insertion point in `README.md`**

Run: `Get-Content README.md | Select-String -Pattern "stale|#verified|entry.*tag" -Context 1,1`
Expected: a paragraph that lists tags like `#added`, `#verified`, `#stale`, `#archived`.

- [ ] **Step 2: Add `#superseded-by` to the tag list**

Add a new sentence to that paragraph:

> Entries can also carry `#superseded-by:LAYER-YYYY-MM-DD-xxxx`, which points to the entry that replaced this one — letting `find_stale`, `history`, and `compress` walk the replacement chain instead of inferring it from prose.

- [ ] **Step 3: Mirror the change in `README.zh-CN.md`**

Add the Chinese equivalent in the same paragraph:

> 条目还可以携带 `#superseded-by:LAYER-YYYY-MM-DD-xxxx`，指向取代本条目的新条目——让 `find_stale`、`history`、`compress` 能沿替换链追溯，而不是从叙述中推断。

- [ ] **Step 4: Verify**

Run: `Get-Content README.md | Select-String -Pattern "superseded-by"`
Expected: at least one match.
Run: `Get-Content README.zh-CN.md | Select-String -Pattern "superseded-by"`
Expected: at least one match.

---

## Task 12: Wire the E2E fixture in `sandbox/mock-todo-app/`

**Files:**
- Modify: `sandbox/mock-todo-app/.lore/scopes/backend/DECISIONS.md:1`

- [ ] **Step 1: Add the chain tag to the SHA-256 entry**

Replace line 1 of `sandbox/mock-todo-app/.lore/scopes/backend/DECISIONS.md`:

```markdown
- [DEC-2026-07-10-ee31] SHA-256 + salt for password hashing; reason: no native dep, deterministic. #added:2026-07-10 #stale:2026-07-10
```

With:

```markdown
- [DEC-2026-07-10-ee31] SHA-256 + salt for password hashing; reason: no native dep, deterministic. #added:2026-07-10 #stale:2026-07-10 #superseded-by:DEC-2026-07-10-e45d
```

- [ ] **Step 2: Re-run all scripts against the sandbox**

```bash
cd sandbox/mock-todo-app && python ../../scripts/list_entries.py --json | python -c "import json,sys; d=json.load(sys.stdin); print([e['id'] for e in d if e.get('replaced_by')])"
```

Expected output: `['DEC-2026-07-10-ee31']`.

```bash
cd sandbox/mock-todo-app && python ../../scripts/find_stale.py --json | python -c "import json,sys; d=json.load(sys.stdin); print(d['chains']); print('broken:', d['broken_chains'])"
```

Expected output:
```
{'DEC-2026-07-10-e45d': ['DEC-2026-07-10-ee31']}
broken: []
```

```bash
cd sandbox/mock-todo-app && python ../../scripts/history.py --follow-superseded DEC-2026-07-10-ee31
```

Expected: prints `## Chain` listing both IDs, then the per-entry history block.

- [ ] **Step 3: Run the full verification suite from `AGENTS.md`**

```bash
python scripts/id_hash.py "test entry"
python scripts/list_entries.py
python scripts/list_entries.py --json | head -20
python scripts/find_duplicates.py --json
python scripts/find_stale.py --days=90 --json
```

All expected to exit 0 and produce sensible output. The bcrypt/SHA-256 fixture in the sandbox should now show a chain instead of two orphan stale entries.

- [ ] **Step 4: Run sandbox E2E**

```bash
cd sandbox/mock-todo-app && python ../../scripts/list_entries.py --json | head -30
```

Expected: every entry in the sandbox parses, the SHA-256 entry carries `replaced_by: "DEC-2026-07-10-e45d"`, no entries are broken.

---

## Self-review checklist (run before reporting done)

- [ ] **Spec coverage:**
  - Tag defined in entry-format.md: Task 1 ✓
  - Compat policy updated: Task 2 ✓
  - sync emits chain: Task 3, Task 7 ✓
  - SUMMARY skips superseded: Task 4 ✓
  - audit handles chains + broken chains: Task 5 ✓
  - history follows chains: Task 6, Task 10 ✓
  - scripts parse and propagate: Task 8, Task 9, Task 10 ✓
  - README mentions: Task 11 ✓
  - sandbox fixture updated: Task 12 ✓

- [ ] **Placeholder scan:** search the plan for "TBD", "TODO", "implement later", "similar to Task N" — none should appear.

- [ ] **Type consistency:** `replaced_by` field is named the same in `list_entries.py`, `find_stale.py`, `history.py`, and `references/entry-format.md`. `walk_supersede_chain` returns `list[entry_dict]`. `--follow-superseded` flag spelling matches across SKILL.md, history-command.md, history.py, and the synopsis.

- [ ] **Compatibility:** no required tags, no required config fields, no renames. All consumers (`find_stale`, `compress`, `audit`, `history`) gracefully handle the absence of `replaced_by` (returns `None`).

- [ ] **No `migrate.py` needed:** additive only.

- [ ] **No `schema_version` bump:** tag addition does not change config schema.

---

## Verification matrix

| Test | Command | Expected |
|---|---|---|
| Tag parsed | `python scripts/list_entries.py --json \| jq '.[0].replaced_by'` | `null` for entries without chain; ID string for entries with |
| Chain grouping | `python scripts/find_stale.py --json \| jq '.chains'` | dict of `{replacement_id: [stale_ids]}` |
| No broken chains in healthy fixture | `python scripts/find_stale.py --json \| jq '.broken_chains'` | `[]` |
| History traversal | `python scripts/history.py --follow-superseded <id>` | prints `## Chain` then history block |
| JSON chain field | `python scripts/history.py --follow-superseded <id> --json \| jq '.chain'` | array of `{entry_id, lore_file, code_file, since}` |
| Backward compat | run `list_entries.py` on a `.lore/` with no `#superseded-by` | works; `replaced_by` is `null` for all entries |
| Sandbox fixture | `cd sandbox/mock-todo-app && python ../../scripts/find_stale.py --json \| jq '.chains'` | `{"DEC-2026-07-10-e45d": ["DEC-2026-07-10-ee31"]}` |

---

## Out of scope (deferred)

- Migrating historical `#stale` entries to backfill `#superseded-by` — impossible without manual info; users add the chain during next `sync`.
- A reverse link from replacement → replaced (e.g. `#replaces:OLD_ID`) — adds noise to the new entry; the new entry's `#added:DATE` plus a `history.py` chain walk is sufficient.
- `lore history` rendering with `--follow-superseded` on a chain longer than 5 — current code handles arbitrary length via the loop; output format may grow unwieldy. Document but don't fix in this PR.
- Schema bump to v3 — not needed for additive tag; revisit if future breaking changes accumulate.