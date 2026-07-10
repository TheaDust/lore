#!/usr/bin/env python3
"""List all mem-man entries in `.mem-man/` as JSON or human-readable text.

Usage:
    python list_entries.py                 # human-readable
    python list_entries.py --json          # JSON output
    python list_entries.py --scope=frontend
    python list_entries.py --layer=ARCH

Walks `.mem-man/_global/*` and `.mem-man/scopes/*/*` and parses every
Markdown bullet that matches the entry format. Output is one record per
entry with these fields:

    id              full ID, e.g. "ARCH-2026-07-09-a3f2"
    layer           prefix, e.g. "ARCH" / "DEC" / "CONV"
    layer_file      source file stem, e.g. "ARCHITECTURE"
    scope           scope name, or "_global"
    file            path relative to .mem-man/, e.g. "scopes/frontend/ARCHITECTURE.md"
    text            entry body, with tags stripped
    tags            dict of tag name -> value, e.g. {"added": "2026-07-09", "verified": "2026-07-15"}
    last_verified   value of #verified tag, or None

Used by:
    - query / audit / compress workflows (pre-step enumeration)
    - find_duplicates.py
    - find_stale.py
"""
import json
import re
import sys
from pathlib import Path


def find_lore_root(start: Path) -> Path:
    """Walk up from start to find the project root containing .lore/."""
    p = start.resolve()
    while p != p.parent:
        if (p / ".lore").is_dir():
            return p / ".lore"
        p = p.parent
    return None


def parse_entry(line: str):
    """Parse one Markdown bullet line. Returns dict or None if not an entry."""
    m = re.match(
        r"^\s*-\s*\[([A-Z]+)-(\d{4}-\d{2}-\d{2})-([a-f0-9]{4})\]\s+(.*?)\s*$",
        line,
    )
    if not m:
        return None

    layer, date, h, rest = m.group(1), m.group(2), m.group(3), m.group(4)
    eid = f"{layer}-{date}-{h}"

    # Extract #tag:value pairs
    tag_re = re.compile(r"#(added|verified|stale|archived):(\S+)")
    tags = {name: val for name, val in tag_re.findall(rest)}
    text = tag_re.sub("", rest).strip()

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


def collect_entries(root: Path):
    entries = []
    layers_dirs = [("_global", root / "_global"), ("scopes", root / "scopes")]

    for section_name, section_path in layers_dirs:
        if not section_path.exists():
            continue
        for md_file in sorted(section_path.rglob("*.md")):
            if section_name == "_global":
                scope = "_global"
            else:
                scope = md_file.parent.name
            layer_file = md_file.stem
            try:
                with open(md_file, encoding="utf-8") as f:
                    for line in f:
                        e = parse_entry(line)
                        if e is None:
                            continue
                        e["scope"] = scope
                        e["layer_file"] = layer_file
                        e["file"] = str(md_file.relative_to(root))
                        entries.append(e)
            except OSError as exc:
                print(f"warning: cannot read {md_file}: {exc}", file=sys.stderr)
    return entries


def main():
    args = sys.argv[1:]

    scope_filter = None
    layer_filter = None
    json_output = "--json" in args

    for arg in args:
        if arg.startswith("--scope="):
            scope_filter = arg.split("=", 1)[1]
        elif arg.startswith("--layer="):
            layer_filter = arg.split("=", 1)[1]

    root = find_lore_root(Path("."))
    if root is None:
        print("error: .lore/ not found (run from project root or below)",
              file=sys.stderr)
        sys.exit(1)

    entries = collect_entries(root)

    if scope_filter:
        entries = [e for e in entries if e["scope"] == scope_filter]
    if layer_filter:
        entries = [e for e in entries if e["layer"] == layer_filter]

    if json_output:
        print(json.dumps(entries, indent=2, ensure_ascii=False))
        return

    if not entries:
        print("(no entries)")
        return

    for e in entries:
        verified = (
            f" [verified:{e['last_verified']}]" if e["last_verified"] else ""
        )
        stale = " [STALE]" if "stale" in e["tags"] else ""
        print(f"[{e['file']}] {e['id']} {e['text']}{verified}{stale}")


if __name__ == "__main__":
    main()
