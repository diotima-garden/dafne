# DAFNE — Directory Architecture for Fractal Nested Ecosystems

The deterministic interpreter of the DAFNE node/grove tree: `#include` preprocessing,
manifest reading, and the skills that compile layered context into a single flat
document. Absorbs the former `context-compiler` plugin — same engine, plus the DAFNE
node-tree discipline (`./`-relative includes only, node-root escape rejection,
`.private/` visibility, manifest-driven `requires:` union).

## Subsystem files

| File | Role |
|---|---|
| `include_graph.py` | Shared `#include` graph traversal (`resolve_include_path`, `collect_inputs`, `find_node_root`) |
| `preprocess.py` | CLI preprocessor — resolves `#include` chains |
| `compiled-is-fresh.py` | Freshness check — prints `FRESH`/`STALE`/an error token to stdout/stderr; exit 0 unless the check itself failed |
| `manifest.py` | Reads `DAFNE.md` (`format`, `requires`, bank config) and walks the `requires:` union up `parents/` |
| `skills/compile/` | LLM merge step — collapses preprocessed layers into one readable doc |
| `skills/compile-context/` | Orchestrator — freshness check → preprocess → compile |
| `skills/reverse-propagate/` | Inverse — back-propagates hand-edits in a `compiled.md` to its source layers |

## `#include` directive

```
#include <path>
```

- Must be the entire line, no leading whitespace.
- Path **must** start with `.` or `..` — relative to the including file. A non-relative
  path is a hard error.
- `../` may not escape the including node's root (the nearest ancestor directory
  carrying a `DAFNE.md`). Includes reaching into a `parents/` mount are not an escape —
  a vendored parent lives inside the node's own tree.
- A target under a `.private/` directory is visible only to includes from within the
  node that owns that `.private/` — a child node cannot reach into a parent's private
  content.

**Always put `#include` at the top of the file** — this preserves general → specific
order in the output, which the compile merge step depends on.

## `DAFNE.md` manifest

Every DAFNE node carries a `DAFNE.md`: YAML frontmatter (`format`, `requires`, and —
for groves — `banks` config) followed by prose. Unknown fields are ignored, never
fatal. Parents are never manifest data — enumeration is `readdir(parents/)`, URLs live
in `.gitmodules`. `requires:` unions up the parent tree.

## Deduplication and cycle detection

Each file is included at most once (keyed by canonical resolved path). Circular
includes are an error.

## CLI

```bash
# Write to file
plugins/dafne/.venv/bin/python3 plugins/dafne/preprocess.py <entry-file> <output-file>

# Print to stdout
plugins/dafne/.venv/bin/python3 plugins/dafne/preprocess.py <entry-file>
```

## Skills

| Command | What it does |
|---|---|
| `/dafne:compile <preprocessed.md>` | LLM merge into `compiled.md` (fork context) |
| `/dafne:compile-context <entry-file>` | Full pipeline: freshness check → preprocess → compile |
| `/dafne:reverse-propagate <compiled.md>` | Inverse: back-propagate hand-edits in a compiled file to its source layers |

## Tests

```
tests/
  test_include_graph.py     collect_inputs, resolve_include_path, find_node_root
  test_compiled_is_fresh.py FRESH/STALE tokens, error cases
  test_preprocess.py        content merging, deduplication, error cases
  test_manifest.py          DAFNE.md parsing, requires: union over parents/
```

**Run:**
```bash
plugins/dafne/.venv/bin/python3 -m pytest plugins/dafne/tests/ -v
```

**Setup (one-time):**
```bash
python3 -m venv plugins/dafne/.venv
plugins/dafne/.venv/bin/pip install -r plugins/dafne/requirements.txt
```

## Notes

`include_graph.py` handles path resolution and input collection for both the
preprocessor and the freshness check. If the include discipline changes, update
`resolve_include_path` there — both tools pick up the change automatically.
