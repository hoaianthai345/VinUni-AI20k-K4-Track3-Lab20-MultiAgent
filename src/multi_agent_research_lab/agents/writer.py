"""Writer agent."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient

_SYSTEM_PROMPT = (
    "You are the Writer agent in a multi-agent research pipeline. Synthesize a clear, "
    "well-cited answer for the requested audience from the analysis notes. Every factual "
    "claim must carry a citation id in square brackets taken from the provided sources, and "
    "you must not invent citation ids."
)


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer`.

        Synthesize a concise answer with citations. Uses a real LLM call when `llm_client`
        is configured (`--mode provider`); otherwise a deterministic offline template.
        """

        if not state.analysis_notes:
            raise ValueError("Writer requires analysis notes")
        citations = ", ".join(f"[{source.metadata['citation_id']}]" for source in state.sources)

        if self.llm_client is not None:
            response = self.llm_client.complete(
                system_prompt=_SYSTEM_PROMPT,
                user_prompt=(
                    f"Query: {state.request.query}\nAudience: {state.request.audience}\n\n"
                    f"Analysis notes:\n{state.analysis_notes}\n\n"
                    f"Available citation ids: {citations}\n\n"
                    "Write the final answer (roughly 400-500 words) with inline citations."
                ),
            )
            state.final_answer = f"## Answer\n\n{response.content}\n\nSources: {citations}"
            state.add_llm_usage(response.input_tokens, response.output_tokens, response.cost_usd)
        else:
            state.final_answer = (
                f"## Answer\n\n{state.request.query}\n\n"
                "The offline evidence indicates that the appropriate design depends on task "
                "structure, evidence needs, and coordination cost. The main supporting "
                f"observations are:\n{state.analysis_notes}\n\nSources: {citations}"
            )

        state.agent_results.append(AgentResult(agent=AgentName.WRITER, content=state.final_answer))
        state.add_trace_event("writer.complete", {"citation_count": len(state.sources)})
        return state
