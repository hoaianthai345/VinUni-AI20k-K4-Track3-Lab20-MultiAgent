"""Researcher agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.search_client import SearchClient


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def __init__(self, search_client: SearchClient) -> None:
        self.search_client = search_client

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.sources` and `state.research_notes`.

        Retrieve a bounded set of embedded sources and preserve citation IDs.
        """

        state.sources = self.search_client.search(state.request.query, state.request.max_sources)
        citations = ", ".join(str(source.metadata["citation_id"]) for source in state.sources)
        state.research_notes = (
            f"Retrieved {len(state.sources)} offline sources for: {state.request.query}. "
            f"Citation IDs: {citations}."
        )
        state.agent_results.append(
            AgentResult(agent=AgentName.RESEARCHER, content=state.research_notes)
        )
        state.add_trace_event("researcher.complete", {"source_count": len(state.sources)})
        return state
