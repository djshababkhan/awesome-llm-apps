"""Tests that the optimizer builds its agents for the configured provider.

Provider selection is only useful if it actually reaches the model object the
three ADK agents run on.

    python test_optimizer_provider.py
"""

import sys

from adk_optimizer import SkillOptimizer
from google.adk.models import Gemini
from model_provider import (
    DEFAULT_GEMINI_MODEL,
    DEFAULT_OLLAMA_API_BASE,
    GEMINI,
    OLLAMA,
    ProviderConfig,
)

OLLAMA_PROVIDER = ProviderConfig(
    name=OLLAMA,
    model="kimi-k3",
    api_key="ollama-key",
    api_base=DEFAULT_OLLAMA_API_BASE,
)


def agents(optimizer):
    return [optimizer.executor, optimizer.analyst, optimizer.mutator]


def test_defaults_to_gemini_for_a_bare_api_key():
    """The old constructor call still means Gemini."""
    opt = SkillOptimizer(api_key="gemini-key")
    assert opt.model == DEFAULT_GEMINI_MODEL
    for agent in agents(opt):
        assert isinstance(agent.model, Gemini), f"{agent.name}: {agent.model!r}"


def test_gemini_provider_builds_gemini_agents():
    provider = ProviderConfig(name=GEMINI, model="gemini-3-flash-preview", api_key="k")
    opt = SkillOptimizer(api_key=provider.api_key, provider=provider)
    for agent in agents(opt):
        assert isinstance(agent.model, Gemini), f"{agent.name}: {agent.model!r}"
        assert agent.model.model == "gemini-3-flash-preview"


def test_ollama_provider_builds_litellm_agents():
    from google.adk.models.lite_llm import LiteLlm

    opt = SkillOptimizer(api_key=OLLAMA_PROVIDER.api_key, provider=OLLAMA_PROVIDER)
    for agent in agents(opt):
        assert isinstance(agent.model, LiteLlm), f"{agent.name}: {agent.model!r}"


def test_ollama_model_is_addressed_through_the_openai_protocol():
    """Ollama Cloud is OpenAI-compatible, so LiteLLM needs the openai/ prefix."""
    opt = SkillOptimizer(api_key=OLLAMA_PROVIDER.api_key, provider=OLLAMA_PROVIDER)
    assert opt.executor.model.model == "openai/kimi-k3", opt.executor.model.model


def test_ollama_credentials_reach_litellm():
    opt = SkillOptimizer(api_key=OLLAMA_PROVIDER.api_key, provider=OLLAMA_PROVIDER)
    args = opt.executor.model._additional_args
    assert args.get("api_base") == DEFAULT_OLLAMA_API_BASE, args
    assert args.get("api_key") == "ollama-key", "the key must not be lost on the way"


def test_structured_output_agents_keep_their_schemas():
    """The analyst and mutator rely on output_schema; a provider swap must not lose it."""
    opt = SkillOptimizer(api_key=OLLAMA_PROVIDER.api_key, provider=OLLAMA_PROVIDER)
    assert opt.analyst.output_schema is not None
    assert opt.mutator.output_schema is not None


def test_each_agent_gets_its_own_model_object():
    opt = SkillOptimizer(api_key=OLLAMA_PROVIDER.api_key, provider=OLLAMA_PROVIDER)
    models = [id(agent.model) for agent in agents(opt)]
    assert len(set(models)) == len(models), "agents are sharing one model instance"


def main():
    tests = [
        test_defaults_to_gemini_for_a_bare_api_key,
        test_gemini_provider_builds_gemini_agents,
        test_ollama_provider_builds_litellm_agents,
        test_ollama_model_is_addressed_through_the_openai_protocol,
        test_ollama_credentials_reach_litellm,
        test_structured_output_agents_keep_their_schemas,
        test_each_agent_gets_its_own_model_object,
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
