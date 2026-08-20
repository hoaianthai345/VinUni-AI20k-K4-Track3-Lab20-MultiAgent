"""Analyst agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.analysis_notes`.

        Create compact, source-grounded claims for the writer.
        """

        if not state.sources:
            raise ValueError("Analyst requires sources before analysis")
        claims = []
        for source in state.sources:
            citation = str(source.metadata["citation_id"])
            claim = source.snippet.split(".", maxsplit=1)[0].strip()
            claims.append(f"- {claim}. [{citation}]")
        state.analysis_notes = "\n".join(claims)
        state.agent_results.append(
            AgentResult(agent=AgentName.ANALYST, content=state.analysis_notes)
        )
        state.add_trace_event("analyst.complete", {"claim_count": len(claims)})
        return state
