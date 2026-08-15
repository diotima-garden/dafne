import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from manifest import effective_requires, parent_dirs, parse_manifest


def make_node(root: Path, body: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "DAFNE.md").write_text(body)
    return root


class TestParseManifest:
    def test_parses_frontmatter(self, tmp_path):
        make_node(tmp_path, "---\nformat: 0\nrequires:\n  - anki\n---\n\n# node\n")
        assert parse_manifest(tmp_path) == {"format": 0, "requires": ["anki"]}

    def test_missing_manifest_returns_empty(self, tmp_path):
        assert parse_manifest(tmp_path) == {}

    def test_no_frontmatter_returns_empty(self, tmp_path):
        make_node(tmp_path, "# just prose, no frontmatter\n")
        assert parse_manifest(tmp_path) == {}

    def test_unknown_fields_ignored(self, tmp_path):
        make_node(
            tmp_path,
            "---\nformat: 0\nrequires: []\nsome_future_field: 42\n---\n",
        )
        manifest = parse_manifest(tmp_path)
        assert manifest["some_future_field"] == 42
        assert manifest["requires"] == []


class TestParentDirs:
    def test_no_parents_directory(self, tmp_path):
        make_node(tmp_path, "---\nformat: 0\nrequires: []\n---\n")
        assert parent_dirs(tmp_path) == []

    def test_enumerates_by_readdir(self, tmp_path):
        node = make_node(tmp_path, "---\nformat: 0\nrequires: []\n---\n")
        (node / "parents" / "deck").mkdir(parents=True)
        (node / "parents" / "other").mkdir(parents=True)
        result = parent_dirs(node)
        assert result == sorted(result)
        assert {p.name for p in result} == {"deck", "other"}


class TestEffectiveRequires:
    def test_leaf_with_no_parents(self, tmp_path):
        node = make_node(tmp_path, "---\nformat: 0\nrequires:\n  - anki\n---\n")
        assert effective_requires(node) == {"anki"}

    def test_unions_two_level_parent_chain(self, tmp_path):
        deck = make_node(tmp_path / "deck", "---\nformat: 0\nrequires:\n  - anki\n---\n")
        language = make_node(
            tmp_path / "language", "---\nformat: 0\nrequires: []\n---\n"
        )
        (language / "parents").mkdir()
        (language / "parents" / "deck").symlink_to(deck, target_is_directory=True)
        spanish = make_node(
            tmp_path / "spanish", "---\nformat: 0\nrequires: []\n---\n"
        )
        (spanish / "parents").mkdir()
        (spanish / "parents" / "language").symlink_to(language, target_is_directory=True)

        assert effective_requires(spanish) == {"anki"}

    def test_child_can_add_to_parent_requires(self, tmp_path):
        deck = make_node(tmp_path / "deck", "---\nformat: 0\nrequires:\n  - anki\n---\n")
        grove = make_node(
            tmp_path / "grove", "---\nformat: 0\nrequires:\n  - some-other-capability\n---\n"
        )
        (grove / "parents").mkdir()
        (grove / "parents" / "deck").symlink_to(deck, target_is_directory=True)

        assert effective_requires(grove) == {"anki", "some-other-capability"}

    def test_node_with_no_manifest_requires_nothing(self, tmp_path):
        bare = tmp_path / "bare"
        bare.mkdir()
        assert effective_requires(bare) == set()
