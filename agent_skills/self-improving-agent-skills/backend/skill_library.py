"""Keeps uploaded skills so the dashboard can list them beside the repo's own.

The dashboard's skill list used to show only the folders that ship with the
repository, so a skill uploaded as a .zip or folder disappeared as soon as you
left its run. Uploads are copied here, one folder per skill name, and listed
alongside the repository skills.
"""

import logging
import re
import shutil
from pathlib import Path
from typing import Iterable, List, Optional

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent.parent / ".run" / "skills"

# Names come from a skill's own frontmatter, so only a plain token may become a
# folder name.
SAFE_NAME = re.compile(r"[a-zA-Z0-9_-]+")


def _folder_name(metadata: dict) -> Optional[str]:
    name = str(metadata.get("name", "")).strip().lower().replace(" ", "-")
    return name if SAFE_NAME.fullmatch(name) else None


def _is_inside(relative: str) -> bool:
    path = Path(relative)
    return not path.is_absolute() and ".." not in path.parts


def _rooted_at_skill_md(skill_files: dict) -> dict:
    """The files relative to the folder holding SKILL.md, so it sits at the root.

    A single-folder zip keeps its folder in every path, and the dashboard only
    lists folders with a SKILL.md directly inside.
    """
    skill_md = min(
        (name for name in skill_files if Path(name).name == "SKILL.md"),
        key=lambda name: len(Path(name).parts),
        default=None,
    )
    if skill_md is None:
        return skill_files

    root = Path(skill_md).parent
    return {
        str(Path(name).relative_to(root)): content
        for name, content in skill_files.items()
        if Path(name).is_relative_to(root)
    }


def save_skill(
    skill_files: dict, metadata: dict, reserved: Iterable[str] = ()
) -> Optional[str]:
    """Saves an uploaded skill, returning its folder name, or None if skipped.

    A skill already in the repository (a name in `reserved`) is not copied, so it
    never shows up twice. Uploading the same name again replaces the old copy.
    Failures are logged, never raised: saving must not fail the upload itself.
    """
    name = _folder_name(metadata)
    if name is None or name in set(reserved):
        return None

    target = SKILLS_DIR / name
    # Written beside the target first so a crash cannot leave a half skill.
    pending = SKILLS_DIR / f".{name}.pending"
    try:
        shutil.rmtree(pending, ignore_errors=True)
        for relative, content in _rooted_at_skill_md(skill_files).items():
            if not _is_inside(relative):
                logger.warning("Not saving unsafe skill file: %s", relative)
                continue
            path = pending / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

        shutil.rmtree(target, ignore_errors=True)
        pending.rename(target)
    except OSError:
        logger.exception("Could not save uploaded skill %s", name)
        shutil.rmtree(pending, ignore_errors=True)
        return None
    return name


def list_saved_skills() -> List[Path]:
    """Folders of every saved skill that still has a SKILL.md, sorted by name."""
    if not SKILLS_DIR.is_dir():
        return []
    return sorted(
        path
        for path in SKILLS_DIR.iterdir()
        if not path.name.startswith(".") and (path / "SKILL.md").is_file()
    )


def find_saved_skill(name: str) -> Optional[Path]:
    """The saved skill's folder, or None if there is no such skill."""
    if not SAFE_NAME.fullmatch(name or ""):
        return None
    folder = SKILLS_DIR / name
    return folder if (folder / "SKILL.md").is_file() else None
