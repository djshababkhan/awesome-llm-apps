"""Tests that scoring runs scenarios concurrently.

Scoring is two model calls per scenario, and a round cannot finish until every
scenario is done. Run one at a time, a four-scenario round waits for eight calls
in series — the single biggest cost in a run.

    python test_concurrent_scoring.py
"""

import asyncio
import sys
import time

from adk_optimizer import MAX_CONCURRENT_SCENARIOS, SkillOptimizer

CALL_SECONDS = 0.1
EVALS = [{"id": 1, "name": "e1", "question": "ok?"}]


def scenarios(count):
    return [
        {"id": i, "name": f"Scenario {i}", "input": f"input {i}"}
        for i in range(1, count + 1)
    ]


class SlowOptimizer(SkillOptimizer):
    """Every model call takes CALL_SECONDS and records how many overlap."""

    def __init__(self, delays=None):
        super().__init__(api_key="stub-key")
        self.in_flight = 0
        self.peak_in_flight = 0
        self.delays = delays or {}
        self.finished = []

    async def _sleep_for(self, prompt):
        self.in_flight += 1
        self.peak_in_flight = max(self.peak_in_flight, self.in_flight)
        try:
            delay = next(
                (d for key, d in self.delays.items() if key in prompt), CALL_SECONDS
            )
            await asyncio.sleep(delay)
        finally:
            self.in_flight -= 1

    async def _ask(self, agent, prompt):
        await self._sleep_for(prompt)
        return "output"

    async def _ask_json(self, agent, prompt, fallback=None):
        await self._sleep_for(prompt)
        for key in self.delays:
            if key in prompt:
                self.finished.append(key)
        return {"results": [{"eval_id": 1, "passed": True}]}


def score(optimizer, count):
    return asyncio.run(optimizer._score_skill("# skill", scenarios(count), EVALS))


def test_scenarios_do_not_wait_for_each_other():
    opt = SlowOptimizer()
    started = time.monotonic()
    score(opt, 4)
    elapsed = time.monotonic() - started

    # Sequential would be 4 scenarios x 2 calls x CALL_SECONDS.
    sequential = 4 * 2 * CALL_SECONDS
    assert elapsed < sequential * 0.75, (
        f"took {elapsed:.2f}s; sequential would be {sequential:.2f}s"
    )


def test_more_than_one_scenario_is_in_flight():
    opt = SlowOptimizer()
    score(opt, 4)
    assert opt.peak_in_flight > 1, "scenarios still ran one at a time"


def test_concurrency_is_bounded():
    """An unbounded fan-out would hit provider rate limits on a big skill."""
    opt = SlowOptimizer()
    score(opt, MAX_CONCURRENT_SCENARIOS + 3)
    assert opt.peak_in_flight <= MAX_CONCURRENT_SCENARIOS, (
        f"{opt.peak_in_flight} calls in flight, limit is {MAX_CONCURRENT_SCENARIOS}"
    )


def test_every_scenario_is_still_counted():
    opt = SlowOptimizer()
    result = score(opt, 4)
    assert result["total"] == 4, result
    assert result["passed"] == 4, result
    assert len(result["details"]) == 4, result


def test_results_keep_scenario_order_whatever_finishes_first():
    """Out-of-order completion must not shuffle the details the analyst reads."""
    opt = SlowOptimizer(delays={"input 1": 0.3, "input 2": 0.05})
    result = score(opt, 2)
    assert [d["scenario_id"] for d in result["details"]] == [1, 2], result["details"]
    assert opt.finished[0] == "input 2", "the slow scenario was expected to finish last"


def test_stopping_skips_the_remaining_scenarios():
    opt = SlowOptimizer()
    opt._should_stop = lambda: True
    result = score(opt, 4)
    assert result["total"] == 0, result
    assert opt.peak_in_flight == 0, "no calls should have been made"


def main():
    tests = [
        test_scenarios_do_not_wait_for_each_other,
        test_more_than_one_scenario_is_in_flight,
        test_concurrency_is_bounded,
        test_every_scenario_is_still_counted,
        test_results_keep_scenario_order_whatever_finishes_first,
        test_stopping_skips_the_remaining_scenarios,
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
