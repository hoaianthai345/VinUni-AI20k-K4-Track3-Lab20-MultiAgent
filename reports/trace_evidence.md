# Trace Evidence — Multi-Agent End-to-End Run

This is a reproducible local trace for the offline workflow. It can be used as the source for a
screenshot in the submission. No external API key or network call is required.

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

## Trace events

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

The `workflow.span` events contain stage duration and attempt metadata in the JSON output. For the
final submission, run the command above and capture the terminal output or upload a screenshot of this
trace table to the personal GitHub repository.
