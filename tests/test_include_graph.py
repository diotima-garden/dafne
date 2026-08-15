import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from include_graph import collect_inputs, find_node_root, resolve_include_path


def make_node(root: Path, manifest: str = "---\nformat: 0\nrequires: []\n---\n") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "DAFNE.md").write_text(manifest)
    return root


class TestResolveIncludePath:
    def test_relative_path(self, tmp_path):
        from_file = tmp_path / "sub" / "file.md"
        result = resolve_include_path("./other.md", from_file)
        assert result == (tmp_path / "sub" / "other.md").resolve()

    def test_non_dotted_path_is_hard_error(self, tmp_path):
        from_file = tmp_path / "sub" / "file.md"
        with pytest.raises(ValueError, match="`./`-relative only"):
            resolve_include_path("groves/lang.md", from_file)

    def test_dotdot_within_node_root_allowed(self, tmp_path):
        node = make_node(tmp_path)
        from_file = node / "sub" / "file.md"
        result = resolve_include_path("../other.md", from_file)
        assert result == (node / "other.md").resolve()

    def test_dotdot_escaping_node_root_rejected(self, tmp_path):
        node = make_node(tmp_path / "node")
        from_file = node / "file.md"
        with pytest.raises(ValueError, match="escapes node root"):
            resolve_include_path("../outside.md", from_file)

    def test_private_within_own_node_allowed(self, tmp_path):
        node = make_node(tmp_path)
        from_file = node / "file.md"
        (node / ".private").mkdir()
        result = resolve_include_path("./.private/secret.md", from_file)
        assert result == (node / ".private" / "secret.md").resolve()

    def test_private_in_parent_node_rejected(self, tmp_path):
        child_root = make_node(tmp_path / "child")
        vendored = child_root / "parents" / "parent"
        vendored.mkdir(parents=True)
        (vendored / "DAFNE.md").write_text("---\nformat: 0\nrequires: []\n---\n")
        (vendored / ".private").mkdir()
        from_file = child_root / "file.md"
        with pytest.raises(ValueError, match="private include"):
            resolve_include_path("./parents/parent/.private/secret.md", from_file)

    def test_no_node_root_skips_validation(self, tmp_path):
        # Sandbox/fixture files with no DAFNE.md ancestor: only the dotted
        # prefix rule applies, no node-boundary checks.
        from_file = tmp_path / "sub" / "file.md"
        result = resolve_include_path("../../elsewhere.md", from_file)
        assert result == (tmp_path.parent / "elsewhere.md").resolve()


class TestFindNodeRoot:
    def test_finds_nearest_manifest(self, tmp_path):
        node = make_node(tmp_path)
        nested = node / "a" / "b"
        nested.mkdir(parents=True)
        assert find_node_root(nested / "file.md") == node

    def test_none_when_no_manifest(self, tmp_path):
        assert find_node_root(tmp_path / "file.md") is None


class TestCollectInputs:
    def test_entry_only(self, tmp_path):
        entry = tmp_path / "a.md"
        entry.write_text("# no includes\n")
        result = collect_inputs(entry, set())
        assert result == [entry.resolve()]

    def test_single_include(self, tmp_path):
        b = tmp_path / "b.md"
        b.write_text("# b\n")
        a = tmp_path / "a.md"
        a.write_text("#include ./b.md\n")
        result = collect_inputs(a, set())
        assert result == [a.resolve(), b.resolve()]

    def test_transitive(self, tmp_path):
        c = tmp_path / "c.md"
        c.write_text("# c\n")
        b = tmp_path / "b.md"
        b.write_text("#include ./c.md\n")
        a = tmp_path / "a.md"
        a.write_text("#include ./b.md\n")
        result = collect_inputs(a, set())
        assert result == [a.resolve(), b.resolve(), c.resolve()]

    def test_deduplication(self, tmp_path):
        shared = tmp_path / "shared.md"
        shared.write_text("# shared\n")
        b = tmp_path / "b.md"
        b.write_text("#include ./shared.md\n")
        a = tmp_path / "a.md"
        a.write_text("#include ./b.md\n#include ./shared.md\n")
        result = collect_inputs(a, set())
        assert result.count(shared.resolve()) == 1

    def test_missing_include_raises(self, tmp_path):
        a = tmp_path / "a.md"
        a.write_text("#include ./missing.md\n")
        with pytest.raises(FileNotFoundError, match="missing.md"):
            collect_inputs(a, set())

    def test_missing_entry_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            collect_inputs(tmp_path / "nonexistent.md", set())

    def test_non_dotted_include_raises(self, tmp_path):
        a = tmp_path / "a.md"
        a.write_text("#include b.md\n")
        with pytest.raises(ValueError, match="`./`-relative only"):
            collect_inputs(a, set())
