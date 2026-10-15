"""Tests that an upload shows up in the dashboard's skill list and loads again.

    python test_uploaded_skills_api.py
"""

import io
import sys
import tempfile
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

import app as app_module
import skill_library

SKILL_MD = "---\nname: api-test-skill\ndescription: A skill uploaded in a test\n---\n\n# Test\n"


def with_library():
    previous = skill_library.SKILLS_DIR
    temp = tempfile.TemporaryDirectory()
    skill_library.SKILLS_DIR = Path(temp.name) / "skills"

    def restore():
        skill_library.SKILLS_DIR = previous
        temp.cleanup()

    return restore


def zipped(files: dict) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buffer.getvalue()


def upload(client, files):
    body = zipped(files)
    return client.post("/api/upload", files={"file": ("skill.zip", body, "application/zip")})


def listed(client):
    return {e["id"]: e for e in client.get("/api/examples").json()["examples"]}


def test_an_uploaded_zip_joins_the_skill_list():
    restore = with_library()
    try:
        client = TestClient(app_module.app)
        assert upload(client, {"api-test-skill/SKILL.md": SKILL_MD}).status_code == 200
        skill = listed(client).get("api-test-skill")
        assert skill is not None, "uploaded skill missing from the list"
        assert skill["source"] == "uploaded"
        assert skill["description"] == "A skill uploaded in a test"
    finally:
        restore()


def test_an_uploaded_skill_can_be_loaded_again():
    restore = with_library()
    try:
        client = TestClient(app_module.app)
        upload(client, {"SKILL.md": SKILL_MD, "references/a.md": "ref"})
        response = client.post("/api/examples/api-test-skill/load")
        assert response.status_code == 200, response.text
        assert sorted(response.json()["file_list"]) == ["SKILL.md", "references/a.md"]
    finally:
        restore()


def test_repository_skills_are_still_listed_first():
    restore = with_library()
    try:
        client = TestClient(app_module.app)
        upload(client, {"SKILL.md": SKILL_MD})
        sources = [e["source"] for e in client.get("/api/examples").json()["examples"]]
        assert sources == sorted(sources, key=lambda s: s != "repository")
        assert "repository" in sources
    finally:
        restore()


def main():
    tests = [
        test_an_uploaded_zip_joins_the_skill_list,
        test_an_uploaded_skill_can_be_loaded_again,
        test_repository_skills_are_still_listed_first,
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
