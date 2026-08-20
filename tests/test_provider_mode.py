"""Tests for --mode provider wiring: Tavily search + OpenAI LLM, without real network calls."""

from dataclasses import dataclass

import httpx
import pytest

from multi_agent_research_lab.agents.analyst import AnalystAgent
from multi_agent_research_lab.agents.researcher import ResearcherAgent
from multi_agent_research_lab.agents.writer import WriterAgent
from multi_agent_research_lab.core.config import Settings
from multi_agent_research_lab.core.errors import LabError
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.services.llm_client import LLMClient, LLMResponse
from multi_agent_research_lab.services.search_client import TavilySearchClient


@dataclass
class _FakeLLMClient:
    """Stand-in for LLMClient that returns a canned response instead of calling OpenAI."""

    reply: str = "fake llm output"

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        return LLMResponse(content=self.reply, input_tokens=10, output_tokens=20, cost_usd=0.01)


class _FakeSearchClient:
    """Stand-in search client so agent tests never hit the network."""

    def search(self, query: str, max_results: int = 5):
        from multi_agent_research_lab.core.schemas import SourceDocument

        return [
            SourceDocument(
                title="Fake source",
                url="https://example.com",
                snippet="fake snippet",
                metadata={"citation_id": "fake_1", "topic": query, "synthetic": False},
            )
        ]


def test_researcher_uses_llm_client_when_configured() -> None:
    state = ResearchState(request=ResearchQuery(query="Compare single vs multi agent"))
    agent = ResearcherAgent(_FakeSearchClient(), llm_client=_FakeLLMClient())

    agent.run(state)

    assert state.research_notes == "fake llm output"
    assert state.llm_cost_usd == pytest.approx(0.01)
    assert state.llm_input_tokens == 10
    assert state.llm_output_tokens == 20


def test_analyst_and_writer_accumulate_llm_usage() -> None:
    state = ResearchState(request=ResearchQuery(query="Compare single vs multi agent"))
    ResearcherAgent(_FakeSearchClient(), llm_client=_FakeLLMClient()).run(state)
    AnalystAgent(llm_client=_FakeLLMClient()).run(state)
    WriterAgent(llm_client=_FakeLLMClient()).run(state)

    assert state.final_answer is not None
    assert "fake llm output" in state.final_answer
    # three LLM calls, each contributing 0.01 -> 0.03 total
    assert state.llm_cost_usd == pytest.approx(0.03)
    assert state.llm_input_tokens == 30
    assert state.llm_output_tokens == 60


def test_tavily_search_client_parses_results(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url: str, json: dict, timeout: float):  # noqa: A002 - match httpx signature
        assert url == "https://api.tavily.com/search"
        assert json["query"] == "graphrag"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "GraphRAG paper",
                        "url": "https://x.test",
                        "content": "abc",
                        "score": 0.9,
                    }
                ]
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    client = TavilySearchClient(api_key="dummy-key")

    results = client.search("graphrag", max_results=3)

    assert len(results) == 1
    assert results[0].title == "GraphRAG paper"
    assert results[0].metadata["citation_id"] == "tavily_1"
    assert results[0].metadata["synthetic"] is False


def test_tavily_search_client_requires_api_key() -> None:
    with pytest.raises(LabError):
        TavilySearchClient(api_key="")


def test_workflow_provider_mode_requires_api_keys() -> None:
    with pytest.raises(LabError, match="TAVILY_API_KEY"):
        MultiAgentWorkflow(settings=Settings(), mode="provider")


def test_workflow_provider_mode_wires_provider_clients() -> None:
    settings = Settings(openai_api_key="sk-test", tavily_api_key="tv-test")
    workflow = MultiAgentWorkflow(settings=settings, mode="provider")

    assert isinstance(workflow.agents["researcher"].search_client, TavilySearchClient)
    assert isinstance(workflow.agents["researcher"].llm_client, LLMClient)
    assert isinstance(workflow.agents["analyst"].llm_client, LLMClient)
    assert isinstance(workflow.agents["writer"].llm_client, LLMClient)
