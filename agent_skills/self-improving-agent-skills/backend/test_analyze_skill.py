"""Tests the analyze step that runs when a skill is uploaded.

Analysis is the first thing every upload hits, so a failure here blocks the
whole dashboard.

    python test_analyze_skill.py
"""

import asyncio
import sys

from adk_optimizer import SkillOptimizer

SKILL_FILES = {
    "SKILL.md": "---\nname: demo\n---\n\n# Demo skill\n",
    "references/notes.md": "Some reference material.",
}

ANALYSIS = {
    "scenarios": [{"id": 1, "name": "A scenario", "input": "do the thing"}],
    "evals": [{"id": 1, "name": "Did it work", "question": "Did it work?"}],
}


class StubOptimizer(SkillOptimizer):
    """Answers with canned JSON instead of calling Gemini."""

    def __init__(self):
        super().__init__(api_key="stub-key")
        self.prompts = []

    async def _ask_json(self, agent, prompt, fallback=None):
        self.prompts.append(prompt)
        return ANALYSIS


def analyze(skill_files=SKILL_FILES):
    opt = StubOptimizer()
    result = asyncio.run(opt.analyze_skill(skill_files))
    return opt, result


def test_analyze_returns_scenarios_and_evals():
    _, result = analyze()
    assert result == ANALYSIS, f"expected the model's analysis, got {result}"


def test_analyze_does_not_need_an_emitter():
    """analyze_skill has no progress stream; it must not reach for one."""
    opt, _ = analyze()
    assert opt._emit is None, f"expected no emitter, got {opt._emit!r}"


def test_analyze_prompt_includes_the_skill_and_its_references():
    opt, _ = analyze()
    prompt = opt.prompts[0]
    assert "# Demo skill" in prompt, "SKILL.md content is missing from the prompt"
    assert "Some reference material." in prompt, "reference files are missing"


def test_analyze_survives_a_skill_with_no_references():
    _, result = analyze({"SKILL.md": "# Bare skill"})
    assert result == ANALYSIS


def main():
    tests = [
        test_analyze_returns_scenarios_and_evals,
        test_analyze_does_not_need_an_emitter,
        test_analyze_prompt_includes_the_skill_and_its_references,
        test_analyze_survives_a_skill_with_no_references,
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
