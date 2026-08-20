"""Command-line entrypoint for reproducible offline lab runs."""

from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.services.search_client import OfflineSearchClient
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


def _require_offline(mode: str) -> None:
    if mode == "offline":
        return
    if mode != "provider":
        raise typer.BadParameter("mode must be 'offline' or 'provider'")
    if not get_settings().openai_api_key:
        raise typer.BadParameter("OPENAI_API_KEY is required when --mode provider is selected")
    raise typer.BadParameter("provider mode is not enabled in this offline-only lab runtime")


def _baseline_state(query: str) -> ResearchState:
    state = ResearchState(request=_parse_query(query))
    state.sources = OfflineSearchClient(CORPUS_ROOT).search(query, state.request.max_sources)
    citations = ", ".join(f"[{source.metadata['citation_id']}]" for source in state.sources)
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
    """Run the deterministic single-agent offline baseline."""
    _init()
    _require_offline(mode)
    typer.echo(_baseline_state(query).model_dump_json(indent=2))


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
    mode: Annotated[
        str, typer.Option("--mode", help="Execution mode: offline or provider")
    ] = "offline",
) -> None:
    """Run Supervisor → Researcher → Analyst → Writer offline."""
    _init()
    _require_offline(mode)
    state = ResearchState(request=_parse_query(query))
    result = MultiAgentWorkflow(corpus_root=CORPUS_ROOT).run(state)
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
    _require_offline(mode)
    _, baseline_metrics = run_benchmark("baseline", query, _baseline_state)

    def run_multi(request: str) -> ResearchState:
        return MultiAgentWorkflow(corpus_root=CORPUS_ROOT).run(
            ResearchState(request=_parse_query(request))
        )

    _, multi_metrics = run_benchmark("multi-agent", query, run_multi)
    report = render_markdown_report([baseline_metrics, multi_metrics])
    report_path = LocalArtifactStore().write_text("benchmark_report.md", report)
    console.print(report)
    console.print(f"Report written: {report_path}")


if __name__ == "__main__":
    app()
