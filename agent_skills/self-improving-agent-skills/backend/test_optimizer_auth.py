"""Tests that each SkillOptimizer carries its own credentials.

The backend builds one SkillOptimizer per request, so credentials must be
per-instance. Anything process-global leaks one user's key into another user's
in-flight run. Stdlib only, so it runs without extra dependencies:

    python test_optimizer_auth.py
"""

import os
import sys

from adk_optimizer import SkillOptimizer

KEY_A = "test-key-aaaa"
KEY_B = "test-key-bbbb"

AGENT_NAMES = ("executor", "analyst", "mutator")


def agent_key(optimizer, agent_name):
    """The API key the named agent would actually authenticate with."""
    agent = getattr(optimizer, agent_name)
    return agent.model.client._api_client.api_key


def test_concurrent_optimizers_keep_separate_keys():
    first = SkillOptimizer(api_key=KEY_A)
    second = SkillOptimizer(api_key=KEY_B)

    # Constructing `second` must not retroactively change `first`, which is what
    # happens when the key is written to os.environ.
    for name in AGENT_NAMES:
        assert agent_key(first, name) == KEY_A, (
            f"{name} of the first optimizer authenticates with "
            f"{agent_key(first, name)!r}, expected {KEY_A!r} — "
            "a second optimizer overwrote the first one's credentials"
        )
        assert agent_key(second, name) == KEY_B, (
            f"{name} of the second optimizer authenticates with "
            f"{agent_key(second, name)!r}, expected {KEY_B!r}"
        )


def test_does_not_mutate_process_environment():
    sentinel = "preexisting-ambient-key"
    os.environ["GOOGLE_API_KEY"] = sentinel
    try:
        SkillOptimizer(api_key=KEY_A)
        assert os.environ["GOOGLE_API_KEY"] == sentinel, (
            "SkillOptimizer overwrote the ambient GOOGLE_API_KEY "
            f"with {os.environ['GOOGLE_API_KEY']!r}"
        )
    finally:
        os.environ.pop("GOOGLE_API_KEY", None)


def main():
    tests = [
        test_concurrent_optimizers_keep_separate_keys,
        test_does_not_mutate_process_environment,
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
