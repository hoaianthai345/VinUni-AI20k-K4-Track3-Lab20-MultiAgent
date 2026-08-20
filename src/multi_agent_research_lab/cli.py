"""Command-line entrypoint for reproducible offline and provider lab runs."""

from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel

from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import OfflineSearchClient, TavilySearchClient
from multi_agent_research_lab.services.storage import LocalArtifactStore

app = typer.Typer(help="Multi-Agent Research Lab CLI")
console = Console()
CORPUS_ROOT = Path(__file__).resolve().parents[2] / "ai_agent_offline_research_corpus_v2/topics"


def _init() -> None:
    configure_logging(get_settings().log_level)


def _parse_query(query: str) -> ResearchQuery:
    try:
        return ResearchQuery(query=query)
    except ValidationError as exc:
        console.print(Panel.fit(f"Invalid query: {exc.errors()[0]['msg']}", title="Input Error"))
        raise typer.Exit(code=1) from exc


def _validate_mode(mode: str, settings: Settings) -> None:
    """Check the mode is known and that provider mode has the keys it needs.

    Offline mode never touches the network. Provider mode makes real Tavily search calls
    and real OpenAI completions, so it costs money and needs both API keys set.
    """
    if mode not in {"offline", "provider"}:
        raise typer.BadParameter("mode must be 'offline' or 'provider'")
    if mode != "provider":
        return
    if not settings.openai_api_key:
        raise typer.BadParameter("OPENAI_API_KEY is required when --mode provider is selected")
    if not settings.tavily_api_key:
        raise typer.BadParameter("TAVILY_API_KEY is required when --mode provider is selected")


def _baseline_state(query: str, mode: str = "offline") -> ResearchState:
    settings = get_settings()
    state = ResearchState(request=_parse_query(query))

    if mode == "provider":
        search_client = TavilySearchClient(settings.tavily_api_key or "")
    else:
        search_client = OfflineSearchClient(CORPUS_ROOT)
    state.sources = search_client.search(query, state.request.max_sources)
    citations = ", ".join(f"[{source.metadata['citation_id']}]" for source in state.sources)

    if mode == "provider":
        source_block = "\n".join(
            f"[{source.metadata['citation_id']}] {source.title}: {source.snippet}"
            for source in state.sources
        )
        response = LLMClient(settings).complete(
            system_prompt=(
                "You are a single-agent research baseline: retrieve and synthesize evidence "
                "in one step, with no specialist roles. Cite every claim with the given "
                "citation ids in square brackets."
            ),
            user_prompt=(
                f"Query: {query}\n\nSources:\n{source_block}\n\n"
                "Write a roughly 500-word answer with inline citations."
            ),
        )
        state.final_answer = f"## Baseline answer\n\n{response.content}\n\nSources: {citations}"
        state.add_llm_usage(response.input_tokens, response.output_tokens, response.cost_usd)
    else:
        state.final_answer = (
            f"## Baseline answer\n\n{query}\n\n"
            "A single-agent baseline retrieves and synthesizes the available offline evidence "
            "in one step. "
            f"Sources: {citations}"
        )

    state.record_route("baseline")
    state.add_trace_event("baseline.complete", {"source_count": len(state.sources)})
    return state


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
    mode: Annotated[
        str, typer.Option("--mode", help="Execution mode: offline or provider")
    ] = "offline",
) -> None:
    """Run the single-agent baseline (offline deterministic, or provider with real search+LLM)."""
    _init()
    _validate_mode(mode, get_settings())
    typer.echo(_baseline_state(query, mode).model_dump_json(indent=2))


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
    mode: Annotated[
        str, typer.Option("--mode", help="Execution mode: offline or provider")
    ] = "offline",
) -> None:
    """Run Supervisor → Researcher → Analyst → Writer (offline, or provider with Tavily+OpenAI)."""
    _init()
    _validate_mode(mode, get_settings())
    state = ResearchState(request=_parse_query(query))
    result = MultiAgentWorkflow(corpus_root=CORPUS_ROOT, mode=mode).run(state)
    typer.echo(result.model_dump_json(indent=2))


@app.command()
def benchmark(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
    mode: Annotated[
        str, typer.Option("--mode", help="Execution mode: offline or provider")
    ] = "offline",
) -> None:
    """Run both pipelines and write a local benchmark report."""
    _init()
    _validate_mode(mode, get_settings())

    notes = (
        "real online run (Tavily search + OpenAI)"
        if mode == "provider"
        else "offline deterministic benchmark"
    )

    def run_baseline(request: str) -> ResearchState:
        return _baseline_state(request, mode)

    _, baseline_metrics = run_benchmark("baseline", query, run_baseline, notes=notes)

    def run_multi(request: str) -> ResearchState:
        return MultiAgentWorkflow(corpus_root=CORPUS_ROOT, mode=mode).run(
            ResearchState(request=_parse_query(request))
        )

    _, multi_metrics = run_benchmark("multi-agent", query, run_multi, notes=notes)
    report = render_markdown_report([baseline_metrics, multi_metrics], mode=mode)
    report_path = LocalArtifactStore().write_text("benchmark_report.md", report)
    console.print(report)
    console.print(f"Report written: {report_path}")


if __name__ == "__main__":
    app()
