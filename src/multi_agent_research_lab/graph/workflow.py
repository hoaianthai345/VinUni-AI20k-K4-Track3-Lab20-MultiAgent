"""Compiled LangGraph workflow for the offline research pipeline."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from time import perf_counter
from typing import Any, cast

try:
    from langgraph.graph import END, START, StateGraph
    from langgraph.graph.state import CompiledStateGraph
except Exception:  # pragma: no cover - compatibility for broken optional installs
    END = "__end__"
    START = "__start__"

    class CompiledStateGraph:  # type: ignore[no-redef]
        """Small compatibility runner when the optional LangGraph install is unusable."""

        def __init__(self, nodes: dict[str, Callable], router: Callable) -> None:
            self._nodes = nodes
            self._router = router

        def invoke(self, graph_state: _GraphState) -> _GraphState:
            current = "supervisor"
            while current != END:
                graph_state = self._nodes[current](graph_state)
                if current == "supervisor":
                    route = self._router(graph_state)
                    current = END if route == "done" else route
                else:
                    current = "supervisor"
            return graph_state

    class StateGraph:  # type: ignore[no-redef]
        def __init__(self, _: type) -> None:
            self.nodes: dict[str, Callable] = {}
            self.router: Callable | None = None

        def add_node(self, name: str, fn: Callable) -> None:
            self.nodes[name] = fn

        def add_edge(self, *_: str) -> None:
            return None

        def add_conditional_edges(self, _: str, router: Callable, __: dict[str, str]) -> None:
            self.router = router

        def compile(self) -> CompiledStateGraph:
            if self.router is None:
                raise RuntimeError("Workflow router was not configured")
            return CompiledStateGraph(self.nodes, self.router)
from typing_extensions import TypedDict

from multi_agent_research_lab.agents.analyst import AnalystAgent
from multi_agent_research_lab.agents.researcher import ResearcherAgent
from multi_agent_research_lab.agents.supervisor import SupervisorAgent
from multi_agent_research_lab.agents.writer import WriterAgent
from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.errors import AgentExecutionError, LabError
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import (
    OfflineSearchClient,
    SearchClient,
    TavilySearchClient,
)


class _GraphState(TypedDict):
    """Keep the mutable Pydantic state as the graph's single state channel."""

    research_state: ResearchState


class MultiAgentWorkflow:
    """Run Supervisor → Researcher → Analyst → Writer as a bounded LangGraph."""

    def __init__(
        self,
        settings: Settings | None = None,
        corpus_root: Path | None = None,
        mode: str = "offline",
    ) -> None:
        if mode not in {"offline", "provider"}:
            raise LabError("mode must be 'offline' or 'provider'")
        self.settings = settings or get_settings()
        self.corpus_root = corpus_root or (
            Path(__file__).resolve().parents[3] / "ai_agent_offline_research_corpus_v2/topics"
        )
        self.mode = mode
        self.supervisor = SupervisorAgent()

        search_client: SearchClient
        llm_client: LLMClient | None
        if mode == "provider":
            if not self.settings.tavily_api_key:
                raise LabError("TAVILY_API_KEY is required for --mode provider")
            if not self.settings.openai_api_key:
                raise LabError("OPENAI_API_KEY is required for --mode provider")
            search_client = TavilySearchClient(self.settings.tavily_api_key)
            llm_client = LLMClient(self.settings)
        else:
            search_client = OfflineSearchClient(self.corpus_root)
            llm_client = None

        self.agents = {
            "researcher": ResearcherAgent(search_client, llm_client),
            "analyst": AnalystAgent(llm_client),
            "writer": WriterAgent(llm_client),
        }
        self._started_at: float | None = None

    def build(self) -> CompiledStateGraph[_GraphState, None, _GraphState, _GraphState]:
        """Compile and return the executable LangGraph workflow."""

        graph = StateGraph(_GraphState)
        graph.add_node("supervisor", cast(Any, self._supervise))
        for route in self.agents:
            graph.add_node(route, cast(Any, self._worker_node(route)))
            graph.add_edge(route, "supervisor")
        graph.add_edge(START, "supervisor")
        graph.add_conditional_edges(
            "supervisor",
            self._route_after_supervisor,
            {"researcher": "researcher", "analyst": "analyst", "writer": "writer", "done": END},
        )
        return graph.compile()

    def run(self, state: ResearchState) -> ResearchState:
        """Invoke the compiled graph and return the same shared state instance."""

        result = cast(_GraphState, self.build().invoke({"research_state": state}))
        return result["research_state"]

    def _supervise(self, graph_state: _GraphState) -> _GraphState:
        state = graph_state["research_state"]
        if state.iteration == 0 or self._started_at is None:
            self._started_at = perf_counter()
        self._enforce_limits(state)
        self.supervisor.run(state)
        return {"research_state": state}

    def _route_after_supervisor(self, graph_state: _GraphState) -> str:
        return graph_state["research_state"].route_history[-1]

    def _worker_node(self, route: str) -> Callable[[_GraphState], _GraphState]:
        def run_worker(graph_state: _GraphState) -> _GraphState:
            state = graph_state["research_state"]
            for attempt in range(1, 3):
                self._enforce_timeout()
                try:
                    with trace_span(
                        route, {"iteration": state.iteration, "attempt": attempt}
                    ) as span:
                        self.agents[route].run(state)
                    state.add_trace_event("workflow.span", span)
                    return {"research_state": state}
                except Exception as exc:
                    state.errors.append(f"{route} attempt {attempt}: {exc}")
                    state.add_trace_event(
                        "workflow.error",
                        {"route": route, "attempt": attempt, "error": str(exc)},
                    )
                    if attempt == 1:
                        state.add_trace_event("workflow.retry", {"route": route, "next_attempt": 2})
                        continue
                    self._record_fallback(state, route, exc)
                    return {"research_state": state}
            raise AssertionError("worker retry loop must return")

        return run_worker

    def _enforce_limits(self, state: ResearchState) -> None:
        self._enforce_timeout()
        if state.iteration >= self.settings.max_iterations:
            raise AgentExecutionError("Workflow exceeded max_iterations before producing an answer")

    def _enforce_timeout(self) -> None:
        if self._started_at is None:
            self._started_at = perf_counter()
        if perf_counter() - self._started_at > self.settings.timeout_seconds:
            raise AgentExecutionError("Workflow exceeded timeout_seconds")

    @staticmethod
    def _record_fallback(state: ResearchState, route: str, exc: Exception) -> None:
        """End safely after a worker exhausts its one retry without faking success."""

        state.final_answer = (
            "## Workflow failure\n\n"
            f"The {route} stage failed after one retry; no research answer was produced. "
            f"Error: {exc}"
        )
        state.add_trace_event(
            "workflow.fallback",
            {"route": route, "outcome": "final_failure_answer", "error": str(exc)},
        )
