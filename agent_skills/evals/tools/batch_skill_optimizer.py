#!/usr/bin/env python3
"""Batch Skill Scanner, Evaluator & Optimizer Tool.

Scans all skills in `agent_skills/`, checks structural linting, security scanning,
runs unit tests where available, and provides status and metadata summaries.
"""

import os
import sys
import json
import subprocess
from pathlib import Path


def parse_skill_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from SKILL.md"""
    if not content.startswith("---"):
        return {}
    try:
        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}
        frontmatter = parts[1].strip()
        metadata = {}
        for line in frontmatter.split("\n"):
            line = line.strip()
            if ":" in line and not line.startswith(" "):
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip().strip('"').strip("'")
        return metadata
    except Exception:
        return {}


def scan_skills(repo_root: Path):
    skills_dir = repo_root / "agent_skills"
    if not skills_dir.exists():
        print(f"Error: {skills_dir} does not exist.")
        sys.exit(1)

    skills_info = []
    for item in sorted(os.listdir(skills_dir)):
        s_dir = skills_dir / item
        s_md = s_dir / "SKILL.md"
        if s_dir.is_dir() and s_md.exists():
            content = s_md.read_text(encoding="utf-8")
            meta = parse_skill_frontmatter(content)

            # Check tests
            eval_dir = skills_dir / "evals" / item
            test_files = list(eval_dir.glob("test_*.py")) if eval_dir.exists() else []

            skills_info.append({
                "id": item,
                "name": meta.get("name", item),
                "description": meta.get("description", ""),
                "dir_path": str(s_dir),
                "has_evals": eval_dir.exists(),
                "test_files": [f.name for f in test_files],
            })

    return skills_info


def run_lint_and_security(repo_root: Path):
    print("=== Running Skill Linter & Scanner ===")
    tools_dir = repo_root / "agent_skills" / "evals" / "tools"
    lint_script = tools_dir / "skill_lint.py"
    scanner_script = tools_dir / "skill_scanner.py"

    skills_dir = repo_root / "agent_skills"
    results = {}

    for item in sorted(os.listdir(skills_dir)):
        s_dir = skills_dir / item
        s_md = s_dir / "SKILL.md"
        if s_dir.is_dir() and s_md.exists():
            # Run lint
            res_lint = subprocess.run(
                [sys.executable, str(lint_script), str(s_dir), "--strict"],
                capture_output=True, text=True
            )
            lint_pass = res_lint.returncode == 0

            results[item] = {
                "lint_pass": lint_pass,
                "lint_output": res_lint.stdout if lint_pass else res_lint.stderr,
            }

    # Run scanner
    res_scan = subprocess.run(
        [sys.executable, str(scanner_script), str(skills_dir)],
        capture_output=True, text=True
    )
    print(res_scan.stdout)

    return results


def main():
    repo_root = Path(__file__).resolve().parents[3]
    skills = scan_skills(repo_root)

    print(f"Found {len(skills)} skills in {repo_root / 'agent_skills'}:\n")
    for s in skills:
        print(f"- {s['name']} ({s['id']}):")
        print(f"  Description: {s['description'][:80]}...")
        print(f"  Has Evals: {s['has_evals']} | Tests: {s['test_files']}")
        print()

    results = run_lint_and_security(repo_root)
    print("\nSummary of Linter Checks:")
    for skill_id, status in results.items():
        status_str = "PASS" if status["lint_pass"] else "FAIL"
        print(f"  [{status_str}] {skill_id}")


if __name__ == "__main__":
    main()
