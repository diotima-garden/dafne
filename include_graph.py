#!/usr/bin/env python3
"""
Shared #include graph traversal for the DAFNE engine.

Provides resolve_include_path and collect_inputs — used by both
preprocess.py (text assembly) and compiled-is-fresh.py (freshness check).

Includes are `./`-relative only (no project-root-relative form, no `../`
escaping the including node's root); `.private/` targets are visible only
within the node that owns them.
"""
import os
from pathlib import Path


def find_node_root(path: Path) -> Path | None:
    """Nearest ancestor directory of `path` (inclusive of its parent when
    `path` is a file) carrying a DAFNE.md — the node that owns `path`.
    Returns None outside any node (e.g. sandbox fixtures with no manifest)."""
    start = path.parent if path.suffix else path
    for candidate in (start, *start.parents):
        if (candidate / "DAFNE.md").exists():
            return candidate
    return None


def resolve_include_path(path_str: str, from_file: Path) -> Path:
    if not path_str.startswith("."):
        raise ValueError(
            f"non-relative include {path_str!r} in {from_file}: "
            "includes are `./`-relative only — see DAFNE format"
        )

    raw_target = from_file.parent / path_str
    own_root = find_node_root(from_file)

    if own_root is not None:
        # Escape check operates on the authored path lexically (`../` typed
        # in the directive), not on where a parents/ mount physically
        # resolves — a vendored submodule sits inside the node's own tree,
        # so following it is never an escape even though it crosses a
        # mount boundary.
        lexical = Path(os.path.normpath(str(raw_target)))
        if own_root != lexical and own_root not in lexical.parents:
            raise ValueError(
                f"include escapes node root: {path_str!r} in {from_file} "
                f"resolves to {lexical}, outside {own_root} — "
                "no `../` may escape a node's root"
            )

    resolved = raw_target.resolve()

    if own_root is not None:
        target_root = find_node_root(resolved)
        if target_root is not None and target_root != own_root:
            private_root = target_root / ".private"
            if private_root == resolved or private_root in resolved.parents:
                raise ValueError(
                    f"private include: {path_str!r} in {from_file} targets "
                    f".private/ owned by {target_root}, "
                    f"not the including node ({own_root}) — "
                    ".private/ is visible only within its own node"
                )

    return resolved


def collect_inputs(entry: Path, seen: set[Path]) -> list[Path]:
    """Return all files reachable from entry via #include, in DFS order."""
    resolved = entry.resolve()
    if resolved in seen:
        return []
    if not resolved.exists():
        raise FileNotFoundError(f"included file not found: {resolved}")
    seen.add(resolved)
    results = [resolved]
    for line in resolved.read_text().splitlines():
        bare = line.rstrip("\r\n")
        if bare.startswith("#include "):
            path_str = bare[len("#include "):].strip()
            child = resolve_include_path(path_str, resolved)
            results.extend(collect_inputs(child, seen))
    return results


def _main() -> None:
    """CLI: list all transitive #include inputs of an entry file, one per line.

    First line is the entry file itself; the rest are its dependencies in DFS
    order. Paths are printed relative to cwd when possible. Used by the
    propagate skill to discover which source layers compose a compiled file.
    """
    import sys

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <entry-file>", file=sys.stderr)
        sys.exit(2)

    entry = Path(sys.argv[1])
    cwd = Path.cwd()

    if not entry.exists():
        print(f"entry file not found: {entry}", file=sys.stderr)
        sys.exit(1)

    try:
        inputs = collect_inputs(entry, set())
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    for f in inputs:
        try:
            print(f.relative_to(cwd))
        except ValueError:
            print(f)


if __name__ == "__main__":
    _main()
