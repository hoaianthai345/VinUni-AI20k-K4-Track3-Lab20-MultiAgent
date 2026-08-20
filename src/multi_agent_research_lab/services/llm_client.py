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
        return LLMResponse(
            content=response.choices[0].message.content or "",
            input_tokens=usage.prompt_tokens if usage else None,
            output_tokens=usage.completion_tokens if usage else None,
        )
