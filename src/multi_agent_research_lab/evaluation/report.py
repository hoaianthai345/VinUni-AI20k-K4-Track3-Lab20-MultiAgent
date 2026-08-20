"""Benchmark report rendering."""

from multi_agent_research_lab.core.schemas import BenchmarkMetrics


def render_markdown_report(metrics: list[BenchmarkMetrics], mode: str = "offline") -> str:
    """Render benchmark metrics to markdown.

    Keep the report deterministic and easy to compare across local runs. `mode` records
    whether this run used the offline heuristics or real Tavily+OpenAI provider calls.
    """

    lines = [
        "# Benchmark Report",
        "",
        "| Run | Latency (s) | Cost (USD) | Quality | Citation cov. | Failure rate | Notes |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for item in metrics:
        cost = "" if item.estimated_cost_usd is None else f"{item.estimated_cost_usd:.4f}"
        quality = "" if item.quality_score is None else f"{item.quality_score:.1f}"
        citation = "" if item.citation_coverage is None else f"{item.citation_coverage:.0%}"
        failure = "" if item.failure_rate is None else f"{item.failure_rate:.0%}"
        lines.append(
            f"| {item.run_name} | {item.latency_seconds:.2f} | {cost} | {quality} "
            f"| {citation} | {failure} | {item.notes} |"
        )
    lines.extend(
        [
            "",
            "## Failure mode and fix",
            "",
            (
                "During validation, the optional LangGraph dependency was incompatible with the "
                "installed langchain-core version, causing import failure before tests could run. "
                "The fix was to pin compatible optional dependency ranges and add a small offline "
                "compatibility runner (used in both offline and provider mode) so the lab remains "
                "executable even when the real LangGraph install is broken. Worker failures use "
                "one retry, trace events, and a visible `## Workflow failure` fallback."
            ),
        ]
    )
    if mode == "provider":
        lines.extend(
            [
                "",
                (
                    "This run used real Tavily web search and real OpenAI completions "
                    "(`--mode provider`); cost and latency above reflect actual API usage, "
                    "not the offline proxy formula."
                ),
            ]
        )
    lines.extend(
        [
            "",
            "## Design summary (for peer review)",
            "",
            (
                "**Role clarity** — Supervisor routes purely on state gaps: no sources → "
                "researcher, no analysis → analyst, else → writer, final answer → done. Each "
                "agent owns exactly one output field (`sources`/`research_notes`, "
                "`analysis_notes`, `final_answer`); no overlapping responsibilities."
            ),
            "",
            (
                "**State design** — A single shared `ResearchState` (Pydantic) is mutated in "
                "place and passed through every node, carrying sources, notes, final answer, "
                "trace events, errors, and (in provider mode) real token/cost usage — any "
                "stage can see everything upstream without re-fetching."
            ),
            "",
            (
                "**Failure guard** — Three layers: `max_iterations` (default 6), "
                "`timeout_seconds` (default 60s wall-clock across the whole run), and one "
                "retry per worker before a visible `## Workflow failure` fallback — never a "
                "silent or faked success. All three have dedicated unit tests."
            ),
            "",
            (
                "**Benchmark interpretation** — Multi-agent costs and latency are both higher "
                "than the single-agent baseline for the same query, because it makes 3 "
                "sequential LLM calls (summarize → analyze → write) plus its own search call, "
                "versus the baseline's 1 LLM call + 1 search call. The quality delta is a "
                "deterministic proxy, not a content-quality judgment — see Known limitations."
            ),
            "",
            (
                "**Trace explanation** — Full per-stage trace (route, duration, retries, "
                "token usage, sources) is in `reports/trace_evidence.md`."
            ),
            "",
            "## Known limitations",
            "",
            (
                "- `quality_score` is a deterministic proxy "
                "(`4 + source_count + analysis bonus`, capped at 10), not an LLM-judge or "
                "human evaluation."
            ),
            "- No cost-based guardrail yet — only iteration count and wall-clock time are capped.",
            (
                "- `CriticAgent` (citation-coverage check, in `agents/critic.py`) exists but is "
                "not wired into the compiled graph."
            ),
            (
                "- Provider-mode answers are not reproducible byte-for-byte (no fixed "
                "seed/temperature); route and citation structure are."
            ),
            (
                "- Cost estimate uses a hardcoded per-model price table in `llm_client.py`; "
                "unknown/newer models return no cost estimate."
            ),
        ]
    )
    return "\n".join(lines) + "\n"
