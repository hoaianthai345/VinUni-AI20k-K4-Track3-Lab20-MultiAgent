"""Researcher agent."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient

_SYSTEM_PROMPT = (
    "You are the Researcher agent in a multi-agent research pipeline. Summarize the retrieved "
    "sources into concise, factual research notes. Keep every citation id in square brackets "
    "exactly as given, and do not invent sources."
)


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def __init__(self, search_client: SearchClient, llm_client: LLMClient | None = None) -> None:
        self.search_client = search_client
        self.llm_client = llm_client

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.sources` and `state.research_notes`.

        Retrieve a bounded set of sources and preserve citation IDs. When a real LLM client
        is configured (`--mode provider`), summarize the sources with it; otherwise fall back
        to a deterministic offline summary.
        """

        state.sources = self.search_client.search(state.request.query, state.request.max_sources)
        citations = ", ".join(str(source.metadata["citation_id"]) for source in state.sources)

        if self.llm_client is not None:
            source_block = "\n".join(
                f"[{source.metadata['citation_id']}] {source.title}: {source.snippet}"
                for source in state.sources
            )
            response = self.llm_client.complete(
                system_prompt=_SYSTEM_PROMPT,
                user_prompt=(
                    f"Query: {state.request.query}\n\nSources:\n{source_block}\n\n"
                    "Write 5-8 bullet point research notes, each ending with its citation id."
                ),
            )
            state.research_notes = response.content
            state.add_llm_usage(response.input_tokens, response.output_tokens, response.cost_usd)
        else:
            state.research_notes = (
                f"Retrieved {len(state.sources)} offline sources for: {state.request.query}. "
                f"Citation IDs: {citations}."
            )

        state.agent_results.append(
            AgentResult(agent=AgentName.RESEARCHER, content=state.research_notes)
        )
        state.add_trace_event("researcher.complete", {"source_count": len(state.sources)})
        return state
