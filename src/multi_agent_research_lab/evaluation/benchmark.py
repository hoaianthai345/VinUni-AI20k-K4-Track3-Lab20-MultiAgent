"""Benchmark skeleton for single-agent vs multi-agent."""

from collections.abc import Callable
from time import perf_counter

from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState

Runner = Callable[[str], ResearchState]


def run_benchmark(
    run_name: str,
    query: str,
    runner: Runner,
    notes: str = "offline deterministic benchmark",
) -> tuple[ResearchState, BenchmarkMetrics]:
    """Measure latency, cost, and quality proxies for one run.

    `notes` should describe how the run was produced (offline heuristics vs. a real
    provider call) so the report doesn't mislabel a real online run as offline.
    """

    started = perf_counter()
    state = runner(query)
    latency = perf_counter() - started
    failed = not state.final_answer or state.final_answer.startswith("## Workflow failure")
    final_answer = state.final_answer
    citation_coverage = 0.0
    if not failed and final_answer is not None and state.sources:
        cited = sum(
            str(source.metadata["citation_id"]) in final_answer for source in state.sources
        )
        citation_coverage = cited / len(state.sources)
    quality_score = (
        0.0
        if failed
        else min(10.0, 4.0 + len(state.sources) + (2.0 if state.analysis_notes else 0.0))
    )
    metrics = BenchmarkMetrics(
        run_name=run_name,
        latency_seconds=latency,
        estimated_cost_usd=state.llm_cost_usd,
        quality_score=quality_score,
        citation_coverage=citation_coverage,
        failure_rate=1.0 if failed else 0.0,
        notes=notes,
    )
    return state, metrics
