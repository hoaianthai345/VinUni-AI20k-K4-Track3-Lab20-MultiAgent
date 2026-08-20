"""Writer agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer`.

        Synthesize a concise answer with citations from the offline corpus.
        """

        if not state.analysis_notes:
            raise ValueError("Writer requires analysis notes")
        citations = ", ".join(f"[{source.metadata['citation_id']}]" for source in state.sources)
        state.final_answer = (
            f"## Answer\n\n{state.request.query}\n\n"
            "The offline evidence indicates that the appropriate design depends on task structure, "
            "evidence needs, and coordination cost. The main supporting observations are:\n"
            f"{state.analysis_notes}\n\nSources: {citations}"
        )
        state.agent_results.append(AgentResult(agent=AgentName.WRITER, content=state.final_answer))
        state.add_trace_event("writer.complete", {"citation_count": len(state.sources)})
        return state
