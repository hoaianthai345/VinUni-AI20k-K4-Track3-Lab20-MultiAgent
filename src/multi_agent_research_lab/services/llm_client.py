"""LLM client abstraction.

Production note: agents should depend on this interface instead of importing an SDK directly.
"""

from dataclasses import dataclass

from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.errors import LabError


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


# USD per 1K tokens, OpenAI published pricing as of this lab's writing. Unknown models
# fall back to no cost estimate rather than a guess.
_PRICING_USD_PER_1K_TOKENS: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4.1-mini": {"input": 0.0004, "output": 0.0016},
}


def _estimate_cost_usd(
    model: str, input_tokens: int | None, output_tokens: int | None
) -> float | None:
    pricing = _PRICING_USD_PER_1K_TOKENS.get(model)
    if pricing is None or input_tokens is None or output_tokens is None:
        return None
    return (input_tokens / 1000) * pricing["input"] + (output_tokens / 1000) * pricing["output"]


class LLMClient:
    """Small OpenAI adapter kept behind the lab's provider-agnostic interface."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Return a model completion.

        The optional SDK is imported lazily so offline runs need no API key.
        """
        if not self.settings.openai_api_key:
            raise LabError("OPENAI_API_KEY is required for provider LLM calls")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LabError("Install the optional 'llm' dependencies to use provider mode") from exc

        client = OpenAI(api_key=self.settings.openai_api_key, timeout=self.settings.timeout_seconds)
        response = client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else None
        output_tokens = usage.completion_tokens if usage else None
        return LLMResponse(
            content=response.choices[0].message.content or "",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=_estimate_cost_usd(self.settings.openai_model, input_tokens, output_tokens),
        )
