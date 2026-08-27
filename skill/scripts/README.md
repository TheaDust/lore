# lore scripts

Cross-platform Python 3.6+ helpers that reduce repetitive mechanical work. No third-party dependencies. Called by `init` / `sync` / `query` / `audit` / `compress` / `history`; can also be run standalone for ad-hoc inspection.

The script list and quick-reference command examples live in the project root `README.md` "Scripts" section. This file covers the things that don't fit there: design intent, integration points, and limits.

## Design notes

**Cross-platform first.** Python standard library only. No `bash`, no `jq`, no platform-specific tools. The same invocation works on Windows, Linux, macOS.

**JSON-friendly output.** The entry-inspection scripts (`list_entries.py`, `find_duplicates.py`, `find_stale.py`, and `history.py`) support `--json` for machine consumption. `id_hash.py` emits only the four-character hash. Agent callers parse the output; humans pipe JSON results to `less` or `jq` (if available).

**Composition.** `find_duplicates.py`, `find_stale.py`, and `history.py` shell out to `list_entries.py --json` rather than re-implementing the parser. One source of truth for entry format — if the format ever changes, only `list_entries.py` needs updating.

**Read-only by default.** None of these scripts write to `.lore/`. They observe; the agent decides what to do with findings.

**Run from project root.** `list_entries.py` walks up the directory tree looking for `.lore/`. The other scripts depend on it via subprocess, so the same constraint applies transitively.

## When each script is called

| Script | Call site | Purpose |
|---|---|---|
| `history.py` | lore history | List git commits related to a memory entry / file / scope; with `--follow-superseded`, walks the `#superseded-by` chain forward |
| `id_hash.py` | Any time a new entry is written (init / sync) | Compute the 4-char content hash for the entry ID |
| `list_entries.py` | Pre-step of query / audit / compress / history | Enumerate all entries as JSON for downstream processing; emits `replaced_by` per entry when `#superseded-by` is present |
| `find_duplicates.py` | sync step 5 (de-duplication) | Identify candidate duplicate entries before writing |
| `find_stale.py` | audit step 2; compress step 2 | Identify entries past the reference-date threshold (`#verified` if present, else `#added`) or superseded (carrying `#stale` or `#superseded-by`, which implies staleness); groups pending-review entries by their `#superseded-by` target and reports `BROKEN_CHAIN` orphans |

## Workflow integration

The agent routes memory-specific natural-language requests as well as explicit lore commands; these helpers do not decide when the skill loads or which layer a fact belongs to. For classification, follow `SKILL.md`: ARCH may include a brief reason, while comparisons, tradeoffs, and detailed standalone rationale belong in DEC.

Before appending a candidate, run `python <skill>/scripts/find_duplicates.py --json --candidate "<entry body>"`, passing the body without its ID or tags as one safely quoted argument. Use `--candidate-file <utf8-text-file>` when quoting is awkward; it explicitly reads UTF-8, while the existing `--candidate-stdin` option depends on the host's stdin encoding. With no candidate input, only saved entries are compared. For this check, inspect pairs containing `CANDIDATE-unsaved` and confirm semantic equivalence and scope before skipping a candidate; also compare unsaved candidates with each other.

`list_entries.py --json` intentionally returns active and inactive entries. Current-state query and compress consumers must exclude entries with `"stale"` in `tags` or a non-empty `replaced_by`; the same filter applies before sync bumps `#verified` on a duplicate. A stale entry without a successor is still inactive. Untagged entries remain eligible, and date-based age warnings alone do not exclude entries. `find_stale.py` reports explicitly inactive entries under `pending_review`; its `stale` list is the separate age-based review list. Historical queries and audits retain access to all entries.

## Output channels

**stdout is the data channel; stderr is the warning channel.** All scripts follow this split so `--json` consumers never have to filter noise out of their parsers. `list_entries.py` emits config and entry-parse warnings on stderr:

- `[WARN] .lore/.config.json has no schema_version field.` — fires once per invocation when the config file exists but lacks the version field. Add `"schema_version": 1` to silence it.
- `[WARN] .lore/.config.json#schema_version=N is newer than this lore skill expects (max: 1).` — fires when the config version exceeds what this skill understands. Pull the latest lore from upstream.
- `[WARN] entry <id> carries multiple #superseded-by tags; keeping the first only.` — fires when one entry has more than one valid `#superseded-by` tag.
- `[WARN] entry <id> has a malformed #superseded-by value '<value>' (expected LAYER-YYYY-MM-DD-xxxx); chain not resolved.` — fires when a `#superseded-by` value is not a valid entry ID. The tag stays in the entry text and `replaced_by` stays `None`.

All warnings are informational; `list_entries.py` always produces the same stdout regardless of config state. See `references/compatibility.md` for the full schema versioning policy.

`history.py` can also warn on stderr when an entry has no `#added` tag or when `--follow-superseded` is supplied to a non-entry query. Its stdout remains valid Markdown or JSON.

## Testing

Regression tests live in `tests/` (stdlib-only `unittest`, black-box subprocess runs of the real scripts). Run from the repo root:

```bash
python -m unittest discover -s tests -v
```

The suite builds isolated `.lore/` fixtures in temp directories; the `history.py` cases create throwaway git repos and skip automatically when git is not on PATH.

## Limitations

- **Token-overlap dedup, not semantic.** Jaccard similarity catches rewrites with similar words but misses semantic equivalence (e.g. "use TypeScript" vs "TypeScript-only codebase"). Deeper checks still need an LLM pass.
- **Naive date math.** `find_stale.py` uses wall-clock dates from `#verified` / `#added` tags. If the system's clock is wrong, results will be off.
- **No automatic archival.** The script reports superseded entries (tagged `#stale`, or carrying `#superseded-by`) and broken chains but does not move or delete anything. Outdated entries stay in their scope file with their tags; git history preserves the rest.
- **Hash collisions on identical text are theoretically possible** (4 hex chars = 16 bits = 1 in 65536). In practice a lore project will not hit this. If it does, slightly edit the entry text to bump the hash.
