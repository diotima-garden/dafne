#!/usr/bin/env python3
"""
DAFNE.md manifest reader.

A DAFNE.md file is YAML frontmatter (--- delimited) followed by prose.
The manifest carries `format`, `requires`, and — for groves — `banks`
config. Unknown fields are ignored, never fatal: a manifest field this
engine version doesn't recognize is not an error.

Parents are never manifest data: enumeration is `readdir(parents/)`, and
their URLs live in `.gitmodules` — this module only walks the directories
that are already there.
"""
from pathlib import Path

import yaml


def parse_manifest(node_root: Path) -> dict:
    """Parse the DAFNE.md at `node_root`. Returns {} if absent or has no
    frontmatter — a node with no manifest is not an error at this layer."""
    manifest_path = node_root / "DAFNE.md"
    if not manifest_path.exists():
        return {}

    text = manifest_path.read_text()
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}

    data = yaml.safe_load(text[3:end])
    return data or {}


def parent_dirs(node_root: Path) -> list[Path]:
    """Enumerate this node's parents by directory listing — never manifest
    data. Sorted for determinism; a bare node with no parents/ has none."""
    parents_dir = node_root / "parents"
    if not parents_dir.is_dir():
        return []
    return sorted(p for p in parents_dir.iterdir() if p.is_dir())


def effective_requires(node_root: Path, seen: set[Path] | None = None) -> set[str]:
    """Union of `requires:` up the parent tree. A node re-declaring a
    capability its parent already requires is redundant but harmless —
    the union absorbs duplicates either way."""
    if seen is None:
        seen = set()
    resolved = node_root.resolve()
    if resolved in seen:
        return set()
    seen.add(resolved)

    manifest = parse_manifest(node_root)
    requires = set(manifest.get("requires") or [])

    for parent in parent_dirs(node_root):
        requires |= effective_requires(parent, seen)

    return requires
