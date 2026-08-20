# Trace Evidence — Multi-Agent End-to-End Run

Two reproducible traces are documented below: an **offline** run (no API key, deterministic,
used for grading/CI) and a **real online run** (`--mode provider`, real Tavily search + real
OpenAI completions) used as the evidence for this submission's report.

## 1. Online run — real Tavily search + real OpenAI (submission evidence)

Command:

```bash
PYTHONPATH=src python3 -m multi_agent_research_lab.cli multi-agent --mode provider \
  --query "Compare single-agent and multi-agent research"
```

Observed result:

- Route: `researcher → analyst → writer → done`
- Sources retrieved: `5` (real web pages via Tavily, e.g. Anthropic's "How we built our
  multi-agent research system" engineering blog post)
- Claims produced by Analyst: `15` lines
- Citations written by Writer: `5`
- Workflow errors: `0`
- Token usage: `2421` input / `1245` output
- Estimated cost: `$0.00111`

### Trace events

| # | Event | Evidence |
|---:|---|---|
| 1 | `supervisor.route` | next=`researcher`, iteration=`1` |
| 2 | `researcher.complete` | source_count=`5` |
| 3 | `workflow.span` | researcher, duration=`11.86s`, attempt=`1` |
| 4 | `supervisor.route` | next=`analyst`, iteration=`2` |
| 5 | `analyst.complete` | claim_count=`15` |
| 6 | `workflow.span` | analyst, duration=`5.11s`, attempt=`1` |
| 7 | `supervisor.route` | next=`writer`, iteration=`3` |
| 8 | `writer.complete` | citation_count=`5` |
| 9 | `workflow.span` | writer, duration=`7.44s`, attempt=`1` |
| 10 | `supervisor.route` | next=`done`, iteration=`4` |

### Retrieved sources

| Citation | Title | URL |
|---|---|---|
| `tavily_1` | Single-Agent vs Multi-Agent AI: When to Scale Your Dev Workflow | https://www.augmentcode.com/guides/single-agent-vs-multi-agent-ai |
| `tavily_2` | How we built our multi-agent research system | https://www.anthropic.com/engineering/multi-agent-research-system |
| `tavily_3` | Multi-agent vs single-agent AI systems: 2026 decision guide | http://www.lyzr.ai/blog/multi-agent-vs-single-agent |
| `tavily_4` | Single-agent vs. multi-agent systems in comparison | https://blog.doubleslash.de/en/software-technologien/kuenstliche-intelligenz/more-ki-agents-do-not-always-mean-better-results-the-fallacy-in-detail |
| `tavily_5` | Multi-agent vs single-agent AI systems: 2026 decision guide (Lyzr, mirror) | https://www.lyzr.ai/blog/multi-agent-vs-single-agent |

### Final answer (excerpt)

> ## Answer
>
> When comparing single-agent and multi-agent research systems, it's essential to consider
> their operational mechanisms, advantages, and limitations... Multi-agent systems, such as
> the one developed by Anthropic featuring Claude Opus 4 and its sub-agents Claude Sonnet 4,
> demonstrate significant performance gains in internal evaluations. Specifically, this
> multi-agent configuration outperformed the single-agent counterpart by an impressive 90%...

Full JSON output (route history, all sources, full answer, full trace) was captured locally
and can be re-generated at any time by re-running the command above with `OPENAI_API_KEY` and
`TAVILY_API_KEY` set.

## 2. Offline run (no API key, deterministic — used for grading/CI)

Command:

```bash
PYTHONPATH=src python3 -m multi_agent_research_lab.cli multi-agent \
  --query "Compare single-agent and multi-agent research"
```

Observed result:

- Route: `researcher → analyst → writer → done`
- Sources retrieved: `5`
- Claims produced by Analyst: `5`
- Citations written by Writer: `5`
- Workflow errors: `0`

### Trace events

| # | Event | Evidence |
|---:|---|---|
| 1 | `supervisor.route` | next=`researcher`, iteration=`1` |
| 2 | `researcher.complete` | source_count=`5` |
| 3 | `workflow.span` | researcher, attempt=`1` |
| 4 | `supervisor.route` | next=`analyst`, iteration=`2` |
| 5 | `analyst.complete` | claim_count=`5` |
| 6 | `workflow.span` | analyst, attempt=`1` |
| 7 | `supervisor.route` | next=`writer`, iteration=`3` |
| 8 | `writer.complete` | citation_count=`5` |
| 9 | `workflow.span` | writer, attempt=`1` |
| 10 | `supervisor.route` | next=`done`, iteration=`4` |

The `workflow.span` events contain stage duration and attempt metadata in the JSON output. For
the final submission, run either command above and capture the terminal output or upload a
screenshot of the trace table to the personal GitHub repository.
