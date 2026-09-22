"""Tests that the optimizer reports progress while it works.

Scoring makes two model calls per scenario and can run for minutes. Without
these events the UI has nothing to show between round results and looks frozen.

    python test_progress.py
"""

import asyncio
import sys

from adk_optimizer import SkillOptimizer

SCENARIOS = [
    {"id": 1, "name": "First scenario", "input": "a"},
    {"id": 2, "name": "Second scenario", "input": "b"},
]
EVALS = [{"id": 1, "name": "e1", "question": "ok?"}]


class RecordingOptimizer(SkillOptimizer):
    """Runs the real _score_skill, but records events instead of calling Gemini."""

    def __init__(self):
        super().__init__(api_key="stub-key")
        self.events = []

        async def emit(event):
            self.events.append(event)

        self._emit = emit

    async def _ask(self, agent, prompt):
        return "output"

    async def _ask_json(self, agent, prompt, fallback=None):
        return {"results": [{"eval_id": 1, "passed": True}]}


def score():
    opt = RecordingOptimizer()
    asyncio.run(opt._score_skill("# skill", SCENARIOS, EVALS))
    return opt.events


def phases(events):
    return [e["data"]["phase"] for e in events if e["type"] == "progress"]


def test_emits_progress_for_every_scenario():
    found = phases(score())
    assert found.count("executing") == len(SCENARIOS), (
        f"got {found.count('executing')} 'executing' events for "
        f"{len(SCENARIOS)} scenarios: {found}"
    )
    assert found.count("scoring") == len(SCENARIOS), (
        f"got {found.count('scoring')} 'scoring' events for "
        f"{len(SCENARIOS)} scenarios: {found}"
    )


def test_progress_identifies_which_scenario():
    events = [e for e in score() if e["type"] == "progress"]
    first = events[0]["data"]

    assert first["scenario_index"] == 1, f"expected index 1, got {first}"
    assert first["scenario_total"] == len(SCENARIOS)
    assert first["scenario_name"] == "First scenario", (
        f"expected the scenario's name so the UI can show it, got {first}"
    )


def test_scenario_index_advances():
    indexes = [
        e["data"]["scenario_index"]
        for e in score()
        if e["type"] == "progress" and e["data"]["phase"] == "executing"
    ]
    assert indexes == [1, 2], f"expected indexes to advance 1..2, got {indexes}"


def test_optimize_wires_its_callback_to_progress():
    """The caller's callback must receive progress, not just round results.

    The RecordingOptimizer above sets _emit by hand, so only running the real
    optimize() proves that it wires the callback up for itself.
    """
    opt = RecordingOptimizer()
    opt._emit = None
    received = []

    async def callback(event):
        received.append(event)

    asyncio.run(
        opt.optimize(
            {"SKILL.md": "# skill"},
            SCENARIOS,
            EVALS,
            max_rounds=1,
            callback=callback,
        )
    )

    progress = [e for e in received if e["type"] == "progress"]
    assert progress, (
        f"optimize() never forwarded progress to the callback; "
        f"got event types {[e['type'] for e in received]}"
    )


def test_no_emitter_is_safe():
    """A direct caller with no emitter must not crash."""
    opt = RecordingOptimizer()
    opt._emit = None
    asyncio.run(opt._score_skill("# skill", SCENARIOS, EVALS))


def main():
    tests = [
        test_emits_progress_for_every_scenario,
        test_progress_identifies_which_scenario,
        test_scenario_index_advances,
        test_optimize_wires_its_callback_to_progress,
        test_no_emitter_is_safe,
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
