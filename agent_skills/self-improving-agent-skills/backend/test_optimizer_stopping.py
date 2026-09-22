"""Tests that the optimization loop stops once the target pass rate is reached.

Continuing past a perfect score wastes API spend and risks mutating a skill that
already passes everything. Stdlib only:

    python test_optimizer_stopping.py
"""

import asyncio
import sys

from adk_optimizer import SkillOptimizer

SKILL_FILES = {"SKILL.md": "# test skill"}
SCENARIOS = [{"id": 1, "name": "s1", "input": "hi"}]
EVALS = [{"id": 1, "name": "e1", "question": "ok?"}]

MAX_ROUNDS = 20


class StubOptimizer(SkillOptimizer):
    """Replaces every model call with a scripted pass rate, so no network is used."""

    def __init__(self, pass_rates):
        super().__init__(api_key="stub-key")
        self._pass_rates = list(pass_rates)
        self.rounds_run = 0

    def _score(self, pct):
        passed = int(pct)
        return {
            "passed": passed,
            "total": 100,
            "per_eval": [{"eval_id": 1, "passed": passed, "total": 100}],
            "details": [],
        }

    async def _score_skill(self, skill_md, scenarios, evals):
        # Last value repeats once the script runs out.
        pct = self._pass_rates[0] if len(self._pass_rates) == 1 else self._pass_rates.pop(0)
        return self._score(pct)

    async def _analyze_failures(self, *args, **kwargs):
        self.rounds_run += 1
        return {"diagnosis": "d", "mutation_strategy": "add_constraint"}

    async def _mutate_skill(self, *args, **kwargs):
        return {"new_skill_md": "# mutated", "description": "change"}


def run(pass_rates):
    opt = StubOptimizer(pass_rates)
    result = asyncio.run(
        opt.optimize(
            skill_files=SKILL_FILES,
            scenarios=SCENARIOS,
            evals=EVALS,
            max_rounds=MAX_ROUNDS,
        )
    )
    return opt, result


def test_stops_immediately_when_baseline_is_perfect():
    opt, result = run([100])
    assert opt.rounds_run == 0, (
        f"ran {opt.rounds_run} mutation rounds on a skill that already scored "
        "100% at baseline; expected 0"
    )
    assert result["final_score"] == 100


def test_stops_as_soon_as_target_is_reached():
    # 50% baseline, then round 1 hits 100%.
    opt, result = run([50, 100])
    assert opt.rounds_run == 1, (
        f"ran {opt.rounds_run} mutation rounds after reaching 100% in round 1; "
        "expected it to stop at 1"
    )
    assert result["final_score"] == 100


def test_uses_all_rounds_when_target_is_never_reached():
    opt, _ = run([50, 60])
    assert opt.rounds_run == MAX_ROUNDS, (
        f"ran {opt.rounds_run} rounds without reaching the target; "
        f"expected all {MAX_ROUNDS}"
    )


def main():
    tests = [
        test_stops_immediately_when_baseline_is_perfect,
        test_stops_as_soon_as_target_is_reached,
        test_uses_all_rounds_when_target_is_never_reached,
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
