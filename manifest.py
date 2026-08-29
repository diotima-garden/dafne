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
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

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


@dataclass(frozen=True)
class Requirement:
    name: str
    declared_by: tuple[PurePosixPath, ...]  # relative to the queried node; "." = the node itself


def requirements_with_provenance(node_root: Path) -> list[Requirement]:
    """Same recursion as effective_requires, retaining where each name came
    from. Paths are relative to the queried node, POSIX-normalized, spelling
    out the parents/ chain (e.g. parents/language/parents/deck) since that
    chain is the inheritance route — not a node name, which isn't unique.
    All declaring nodes are listed, not just the first found. Sorted by
    name; declared_by sorted by path."""
    declared: dict[str, set[PurePosixPath]] = {}

    def walk(current: Path, rel: PurePosixPath, ancestors: frozenset[Path]) -> None:
        # `ancestors` guards against real cycles (a node reachable from
        # itself along one path) without suppressing a diamond, where the
        # same physical node is legitimately reached via two distinct
        # sibling branches and must be visited — and recorded — both times.
        resolved = current.resolve()
        if resolved in ancestors:
            return

        manifest = parse_manifest(current)
        for name in manifest.get("requires") or []:
            declared.setdefault(name, set()).add(rel)

        for parent in parent_dirs(current):
            walk(parent, rel / "parents" / parent.name, ancestors | {resolved})

    walk(node_root, PurePosixPath("."), frozenset())

    return [
        Requirement(name=name, declared_by=tuple(sorted(paths)))
        for name, paths in sorted(declared.items())
    ]


def discover_banks(node_root: Path, seen: set[Path] | None = None) -> list[dict]:
    """Same recursion as effective_requires, collecting manifest['banks']
    instead of manifest['requires']. Each entry's `bank:` key is resolved
    from './'-relative to an absolute path against node_root — every other
    key is opaque payload, copied through verbatim. Dafne understands only
    that `bank:` is a path; what a bank is for is not this engine's
    concern."""
    if seen is None:
        seen = set()
    resolved = node_root.resolve()
    if resolved in seen:
        return []
    seen.add(resolved)

    manifest = parse_manifest(node_root)
    banks = []
    for entry in manifest.get("banks") or []:
        entry = dict(entry)
        if "bank" in entry:
            entry["bank"] = str((resolved / entry["bank"]).resolve())
        banks.append(entry)

    for parent in parent_dirs(node_root):
        banks.extend(discover_banks(parent, seen))

    return banks


def discover_grove_banks(base_dir: Path) -> list[dict]:
    """readdir(base_dir), keep children carrying a DAFNE.md, discover_banks()
    each. Mirrors parent_dirs' readdir-not-manifest discipline: which
    groves exist is a directory listing, never configuration."""
    base_dir = Path(base_dir)
    if not base_dir.is_dir():
        return []
    banks = []
    for child in sorted(base_dir.iterdir()):
        if child.is_dir() and (child / "DAFNE.md").exists():
            banks.extend(discover_banks(child))
    return banks
