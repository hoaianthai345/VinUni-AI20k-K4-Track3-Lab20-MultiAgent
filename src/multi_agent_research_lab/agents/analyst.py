"""Analyst agent."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient

_SYSTEM_PROMPT = (
    "You are the Analyst agent in a multi-agent research pipeline. Turn research notes into "
    "compact, source-grounded claims for the Writer agent. Every claim must end with its "
    "citation id in square brackets and must not introduce unsupported facts."
)


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.analysis_notes`.

        Create compact, source-grounded claims for the writer. Uses a real LLM call when
        `llm_client` is configured (`--mode provider`); otherwise a deterministic extraction.
        """

        if not state.sources:
            raise ValueError("Analyst requires sources before analysis")

        if self.llm_client is not None:
            source_block = "\n".join(
                f"[{source.metadata['citation_id']}] {source.title}: {source.snippet}"
                for source in state.sources
            )
            response = self.llm_client.complete(
                system_prompt=_SYSTEM_PROMPT,
                user_prompt=(
                    f"Research notes:\n{state.research_notes}\n\nSources:\n{source_block}\n\n"
                    "Write one bullet claim per source, each ending with its citation id."
                ),
            )
            state.analysis_notes = response.content
            state.add_llm_usage(response.input_tokens, response.output_tokens, response.cost_usd)
        else:
            claims = []
            for source in state.sources:
                citation = str(source.metadata["citation_id"])
                claim = source.snippet.split(".", maxsplit=1)[0].strip()
                claims.append(f"- {claim}. [{citation}]")
            state.analysis_notes = "\n".join(claims)

        state.agent_results.append(
            AgentResult(agent=AgentName.ANALYST, content=state.analysis_notes)
        )
        state.add_trace_event(
            "analyst.complete", {"claim_count": len(state.analysis_notes.splitlines())}
        )
        return state
