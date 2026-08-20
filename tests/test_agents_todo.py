from pathlib import Path

import pytest

from multi_agent_research_lab.core.config import Settings
from multi_agent_research_lab.core.errors import AgentExecutionError
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph import workflow as workflow_module
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow

CORPUS_ROOT = Path("ai_agent_offline_research_corpus_v2/topics")


def test_workflow_routes_all_required_agents_and_keeps_citations() -> None:
    state = ResearchState(
        request=ResearchQuery(query="Compare single-agent and multi-agent research")
    )
    result = MultiAgentWorkflow(corpus_root=CORPUS_ROOT).run(state)

    assert result.route_history == ["researcher", "analyst", "writer", "done"]
    assert result.final_answer is not None
    assert result.sources
    assert all(source.metadata["citation_id"] in result.final_answer for source in result.sources)
    assert any(event["name"] == "workflow.span" for event in result.trace)


def test_workflow_builds_a_compiled_langgraph() -> None:
    graph = MultiAgentWorkflow(corpus_root=CORPUS_ROOT).build()

    assert graph.__class__.__name__ == "CompiledStateGraph"


def test_compiled_graph_direct_invoke_routes_fresh_state() -> None:
    workflow = MultiAgentWorkflow(corpus_root=CORPUS_ROOT)
    state = ResearchState(
        request=ResearchQuery(query="Compare single-agent and multi-agent research")
    )

    result = workflow.build().invoke({"research_state": state})

    assert result["research_state"].route_history == ["researcher", "analyst", "writer", "done"]
    assert result["research_state"].final_answer


def test_compiled_graph_direct_invoke_is_reusable_for_fresh_states() -> None:
    workflow = MultiAgentWorkflow(corpus_root=CORPUS_ROOT)

    first = ResearchState(
        request=ResearchQuery(query="Compare single-agent and multi-agent research")
    )
    second = ResearchState(
        request=ResearchQuery(query="Explain offline research evaluation")
    )

    first_result = workflow.build().invoke({"research_state": first})
    second_result = workflow.build().invoke({"research_state": second})

    assert first_result["research_state"].final_answer
    assert second_result["research_state"].route_history == [
        "researcher",
        "analyst",
        "writer",
        "done",
    ]


def test_workflow_fails_loudly_at_iteration_limit() -> None:
    state = ResearchState(
        request=ResearchQuery(query="Compare single-agent and multi-agent research")
    )
    settings = Settings(max_iterations=1)
    with pytest.raises(AgentExecutionError, match="max_iterations"):
        MultiAgentWorkflow(settings=settings, corpus_root=CORPUS_ROOT).run(state)


def test_workflow_fails_loudly_at_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    workflow = MultiAgentWorkflow(settings=Settings(timeout_seconds=5), corpus_root=CORPUS_ROOT)
    state = ResearchState(
        request=ResearchQuery(query="Compare single-agent and multi-agent research")
    )
    clock = iter((0.0, 6.0))
    monkeypatch.setattr(workflow_module, "perf_counter", lambda: next(clock))

    with pytest.raises(AgentExecutionError, match="timeout_seconds"):
        workflow.run(state)


def test_workflow_retries_then_falls_back_with_trace(monkeypatch: pytest.MonkeyPatch) -> None:
    workflow = MultiAgentWorkflow(corpus_root=CORPUS_ROOT)
    state = ResearchState(
        request=ResearchQuery(query="Compare single-agent and multi-agent research")
    )

    def fail_writer(_: ResearchState) -> ResearchState:
        raise ValueError("writer unavailable")

    monkeypatch.setattr(workflow.agents["writer"], "run", fail_writer)
    result = workflow.run(state)

    assert result.final_answer is not None
    assert result.final_answer.startswith("## Workflow failure")
    assert len(result.errors) == 2
    assert [event["name"] for event in result.trace].count("workflow.retry") == 1
    assert any(event["name"] == "workflow.fallback" for event in result.trace)
    assert result.route_history == ["researcher", "analyst", "writer", "done"]
