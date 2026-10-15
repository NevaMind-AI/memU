import pytest

from memu.recall_file_names import canonical_recall_file_name


def test_existing_kebab_case_names_are_unchanged() -> None:
    names = [
        "memu-claude-code-windows-install",
        "memu-hermes-windows-install",
        "memu-pr574-claude-standalone-cli-prereq",
        "memu-pi-windows-install",
    ]
    for name in names:
        assert canonical_recall_file_name(name) == name


def test_equivalent_name_variants_share_one_canonical_name() -> None:
    for name in ("Project Preferences", "project_preferences", " project--preferences "):
        assert canonical_recall_file_name(name) == "project-preferences"


@pytest.mark.parametrize("name", ["../notes", "notes/path", "notes\\path", "notes\x00", ".", ".."])
def test_rejects_unsafe_paths(name: str) -> None:
    with pytest.raises(ValueError):
        canonical_recall_file_name(name)


def test_preserves_other_characters() -> None:
    for name in ("项目-偏好", "café-notes", "notes!", "project.preferences", "i\u0307stanbul"):
        assert canonical_recall_file_name(name) == name
