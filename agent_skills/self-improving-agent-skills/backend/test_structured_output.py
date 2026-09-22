"""Tests the optimizer's handling of reasoning models and unenforced schemas.

Two things differ once the agents run on a model like kimi-k3 through Ollama:

  1. It streams its chain of thought as parts marked thought=True. Folding
     those into the answer wraps prose around the JSON callers parse.
  2. Ollama accepts an OpenAI response_format and then ignores it, so a schema
     is only honoured if it is in the prompt the model actually reads.

    python test_structured_output.py
"""

import asyncio
import json
import sys

from adk_optimizer import SkillOptimizer
from model_provider import GEMINI, OLLAMA, ProviderConfig

OLLAMA_PROVIDER = ProviderConfig(
    name=OLLAMA, model="kimi-k3", api_key="k", api_base="https://ollama.com/v1"
)
GEMINI_PROVIDER = ProviderConfig(name=GEMINI, model="gemini-3-flash-preview", api_key="k")

MUTATION = {"description": "d", "reasoning": "r", "new_skill_md": "# improved"}


class Part:
    def __init__(self, text, thought=False):
        self.text = text
        self.thought = thought


def optimizer(provider):
    return SkillOptimizer(api_key=provider.api_key, provider=provider)


class RecordingOptimizer(SkillOptimizer):
    """Captures the prompt and returns a canned reply instead of calling a model."""

    def __init__(self, provider, reply):
        super().__init__(api_key=provider.api_key, provider=provider)
        self.reply = reply
        self.prompts = []

    async def _ask(self, agent, prompt):
        self.prompts.append(prompt)
        return self.reply


def test_thoughts_are_not_part_of_the_answer():
    parts = [Part("Let me think about this...", thought=True), Part('{"a": 1}')]
    assert SkillOptimizer._visible_text(parts) == '{"a": 1}'


def test_plain_text_still_comes_through():
    assert SkillOptimizer._visible_text([Part("hello"), Part(" world")]) == "hello world"


def test_empty_and_missing_parts_are_safe():
    assert SkillOptimizer._visible_text(None) == ""
    assert SkillOptimizer._visible_text([]) == ""


def test_ollama_is_asked_for_json_in_the_prompt():
    """Ollama ignores response_format, so the schema must be in the prompt."""
    opt = RecordingOptimizer(OLLAMA_PROVIDER, json.dumps(MUTATION))
    asyncio.run(opt._ask_json(opt.mutator, "do the thing"))

    prompt = opt.prompts[0]
    assert "do the thing" in prompt, "the original prompt must survive"
    assert "JSON" in prompt, f"no JSON instruction was added: {prompt[-200:]}"
    assert "new_skill_md" in prompt, "the schema's fields should be spelled out"


def test_gemini_prompt_is_left_alone():
    """Gemini enforces output_schema itself; repeating it would be noise."""
    opt = RecordingOptimizer(GEMINI_PROVIDER, json.dumps(MUTATION))
    asyncio.run(opt._ask_json(opt.mutator, "do the thing"))
    assert opt.prompts[0] == "do the thing", opt.prompts[0]


def test_no_schema_means_no_added_instruction():
    """The executor has no output_schema; its prompts already say what to return."""
    opt = RecordingOptimizer(OLLAMA_PROVIDER, json.dumps(MUTATION))
    asyncio.run(opt._ask_json(opt.executor, "analyze this"))
    assert opt.prompts[0] == "analyze this", opt.prompts[0]


def test_json_wrapped_in_a_code_fence_is_parsed():
    """Reasoning models like to fence their output even when told not to."""
    fenced = "```json\n" + json.dumps(MUTATION) + "\n```"
    opt = RecordingOptimizer(OLLAMA_PROVIDER, fenced)
    result = asyncio.run(opt._ask_json(opt.mutator, "p"))
    assert result == MUTATION, result


def test_json_with_prose_around_it_is_parsed():
    noisy = "Here is the change:\n" + json.dumps(MUTATION) + "\nThat is one change."
    opt = RecordingOptimizer(OLLAMA_PROVIDER, noisy)
    assert asyncio.run(opt._ask_json(opt.mutator, "p")) == MUTATION


def test_unparseable_reply_still_falls_back():
    opt = RecordingOptimizer(OLLAMA_PROVIDER, "no json here at all")
    fallback = {"description": "Failed to parse mutation"}
    assert asyncio.run(opt._ask_json(opt.mutator, "p", fallback=fallback)) == fallback


def main():
    tests = [
        test_thoughts_are_not_part_of_the_answer,
        test_plain_text_still_comes_through,
        test_empty_and_missing_parts_are_safe,
        test_ollama_is_asked_for_json_in_the_prompt,
        test_gemini_prompt_is_left_alone,
        test_no_schema_means_no_added_instruction,
        test_json_wrapped_in_a_code_fence_is_parsed,
        test_json_with_prose_around_it_is_parsed,
        test_unparseable_reply_still_falls_back,
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
