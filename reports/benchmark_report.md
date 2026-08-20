# Benchmark Report

| Run | Latency (s) | Cost (USD) | Quality | Citation cov. | Failure rate | Notes |
|---|---:|---:|---:|---:|---:|---|
| baseline | 10.49 | 0.0005 | 9.0 | 100% | 0% | real online run (Tavily search + OpenAI) |
| multi-agent | 20.37 | 0.0012 | 10.0 | 100% | 0% | real online run (Tavily search + OpenAI) |

## Failure mode and fix

During validation, the optional LangGraph dependency was incompatible with the installed langchain-core version, causing import failure before tests could run. The fix was to pin compatible optional dependency ranges and add a small offline compatibility runner (used in both offline and provider mode) so the lab remains executable even when the real LangGraph install is broken. Worker failures use one retry, trace events, and a visible `## Workflow failure` fallback.

This run used real Tavily web search and real OpenAI completions (`--mode provider`); cost and latency above reflect actual API usage, not the offline proxy formula.

## Design summary (for peer review)

**Role clarity** — Supervisor routes purely on state gaps: no sources → researcher, no analysis → analyst, else → writer, final answer → done. Each agent owns exactly one output field (`sources`/`research_notes`, `analysis_notes`, `final_answer`); no overlapping responsibilities.

**State design** — A single shared `ResearchState` (Pydantic) is mutated in place and passed through every node, carrying sources, notes, final answer, trace events, errors, and (in provider mode) real token/cost usage — any stage can see everything upstream without re-fetching.

**Failure guard** — Three layers: `max_iterations` (default 6), `timeout_seconds` (default 60s wall-clock across the whole run), and one retry per worker before a visible `## Workflow failure` fallback — never a silent or faked success. All three have dedicated unit tests.

**Benchmark interpretation** — Multi-agent costs and latency are both higher than the single-agent baseline for the same query, because it makes 3 sequential LLM calls (summarize → analyze → write) plus its own search call, versus the baseline's 1 LLM call + 1 search call. The quality delta is a deterministic proxy, not a content-quality judgment — see Known limitations.

**Trace explanation** — Full per-stage trace (route, duration, retries, token usage, sources) is in `reports/trace_evidence.md`.

## Known limitations

- `quality_score` is a deterministic proxy (`4 + source_count + analysis bonus`, capped at 10), not an LLM-judge or human evaluation.
- No cost-based guardrail yet — only iteration count and wall-clock time are capped.
- `CriticAgent` (citation-coverage check, in `agents/critic.py`) exists but is not wired into the compiled graph.
- Provider-mode answers are not reproducible byte-for-byte (no fixed seed/temperature); route and citation structure are.
- Cost estimate uses a hardcoded per-model price table in `llm_client.py`; unknown/newer models return no cost estimate.
