"""Optional critic agent skeleton for bonus work."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState


class CriticAgent(BaseAgent):
    """Optional fact-checking and safety-review agent."""

    name = "critic"

    def run(self, state: ResearchState) -> ResearchState:
        """Validate final answer and append findings.

        Check that the answer exists and cites every retrieved source.
        """
        if not state.final_answer:
            raise ValueError("Critic requires a final answer")
        missing = [
            str(source.metadata.get("citation_id", "unknown"))
            for source in state.sources
            if str(source.metadata.get("citation_id", "")) not in state.final_answer
        ]
        content = "Citation check passed."
        if missing:
            content = f"Citation check found missing citations: {', '.join(missing)}."
            state.errors.append(content)
        state.agent_results.append(AgentResult(agent=AgentName.CRITIC, content=content))
        state.add_trace_event("critic.complete", {"missing_citations": missing})
        return state
