from multi_agent_research_lab.core.schemas import BenchmarkMetrics, ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report


def test_report_renders_markdown() -> None:
    report = render_markdown_report([BenchmarkMetrics(run_name="baseline", latency_seconds=1.23)])
    assert "Benchmark Report" in report
    assert "baseline" in report


def test_benchmark_records_offline_metrics() -> None:
    def runner(query: str) -> ResearchState:
        state = ResearchState(request=ResearchQuery(query=query))
        state.final_answer = "answer"
        return state

    _, metrics = run_benchmark("baseline", "Explain agent systems", runner)
    assert metrics.estimated_cost_usd == 0.0
    assert metrics.failure_rate == 0.0


def test_benchmark_marks_failed_run_without_final_answer() -> None:
    def runner(query: str) -> ResearchState:
        state = ResearchState(request=ResearchQuery(query=query))
        state.errors.append("writer failed")
        return state

    _, metrics = run_benchmark("failed", "Explain agent systems", runner)
    assert metrics.failure_rate == 1.0
    assert metrics.quality_score == 0.0


def test_benchmark_ignores_historical_retry_errors_when_answer_is_valid() -> None:
    def runner(query: str) -> ResearchState:
        state = ResearchState(request=ResearchQuery(query=query))
        state.errors.append("researcher attempt 1: transient failure")
        state.final_answer = "A valid recovered answer"
        return state

    _, metrics = run_benchmark("recovered", "Explain agent systems", runner)
    assert metrics.failure_rate == 0.0
    assert metrics.quality_score is not None
    assert metrics.quality_score > 0.0
