"""Tests that an uploaded skill joins the dashboard's skill list.

The dashboard only listed skill folders that ship with the repository, so a
skill uploaded as a .zip or folder vanished once you left its run — there was
no card to pick it again from.

    python test_skill_library.py
"""

import sys
import tempfile
from pathlib import Path

import skill_library
from skill_library import find_saved_skill, list_saved_skills, save_skill

SKILL_FILES = {
    "SKILL.md": "---\nname: wedding-blog\n---\n\n# Wedding blog\n",
    "references/brand.md": "Brand notes.",
}
METADATA = {"name": "wedding-blog"}


def with_library():
    """Points the library at a throwaway directory, returning a restore callable."""
    previous = skill_library.SKILLS_DIR
    temp = tempfile.TemporaryDirectory()
    skill_library.SKILLS_DIR = Path(temp.name) / "skills"

    def restore():
        skill_library.SKILLS_DIR = previous
        temp.cleanup()

    return restore


def test_an_uploaded_skill_is_listed():
    restore = with_library()
    try:
        assert save_skill(SKILL_FILES, METADATA) == "wedding-blog"
        assert [p.name for p in list_saved_skills()] == ["wedding-blog"]
    finally:
        restore()


def test_every_file_of_the_skill_is_kept():
    restore = with_library()
    try:
        save_skill(SKILL_FILES, METADATA)
        folder = find_saved_skill("wedding-blog")
        assert (folder / "SKILL.md").read_text() == SKILL_FILES["SKILL.md"]
        assert (folder / "references" / "brand.md").read_text() == "Brand notes."
    finally:
        restore()


def test_uploading_again_replaces_the_old_copy():
    restore = with_library()
    try:
        save_skill(SKILL_FILES, METADATA)
        save_skill({"SKILL.md": "# v2"}, METADATA)
        folder = find_saved_skill("wedding-blog")
        assert (folder / "SKILL.md").read_text() == "# v2"
        assert not (folder / "references").exists(), "stale files from v1 survived"
    finally:
        restore()


def test_a_skill_inside_a_folder_is_saved_from_that_folder():
    restore = with_library()
    try:
        files = {f"wedding-blog/{name}": content for name, content in SKILL_FILES.items()}
        save_skill(files, METADATA)
        folder = find_saved_skill("wedding-blog")
        assert folder is not None, "SKILL.md was not at the saved folder's root"
        assert (folder / "references" / "brand.md").is_file()
    finally:
        restore()


def test_a_repository_skill_is_not_duplicated():
    restore = with_library()
    try:
        assert save_skill(SKILL_FILES, METADATA, reserved={"wedding-blog"}) is None
        assert list_saved_skills() == []
    finally:
        restore()


def test_a_skill_without_a_usable_name_is_not_saved():
    restore = with_library()
    try:
        assert save_skill(SKILL_FILES, {}) is None
        assert save_skill(SKILL_FILES, {"name": "../../etc"}) is None
        assert list_saved_skills() == []
    finally:
        restore()


def test_file_names_cannot_escape_the_skill_folder():
    restore = with_library()
    try:
        files = {**SKILL_FILES, "../escape.md": "x", "/abs.md": "x"}
        save_skill(files, METADATA)
        root = skill_library.SKILLS_DIR
        assert not (root / "escape.md").exists()
        assert sorted(p.name for p in find_saved_skill("wedding-blog").rglob("*.md")) == [
            "SKILL.md",
            "brand.md",
        ]
    finally:
        restore()


def test_lookups_cannot_escape_the_library():
    restore = with_library()
    try:
        save_skill(SKILL_FILES, METADATA)
        assert find_saved_skill("../skills") is None
        assert find_saved_skill("missing") is None
    finally:
        restore()


def test_no_saved_skills_is_not_an_error():
    restore = with_library()
    try:
        assert list_saved_skills() == []
    finally:
        restore()


def main():
    tests = [
        test_an_uploaded_skill_is_listed,
        test_every_file_of_the_skill_is_kept,
        test_uploading_again_replaces_the_old_copy,
        test_a_skill_inside_a_folder_is_saved_from_that_folder,
        test_a_repository_skill_is_not_duplicated,
        test_a_skill_without_a_usable_name_is_not_saved,
        test_file_names_cannot_escape_the_skill_folder,
        test_lookups_cannot_escape_the_library,
        test_no_saved_skills_is_not_an_error,
    ]

    failures = 0
    for test in tests:
        try:
            test()
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {test.__name__}\n     {exc}")
        else:
            print(f"PASS {test.__name__}")

    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
