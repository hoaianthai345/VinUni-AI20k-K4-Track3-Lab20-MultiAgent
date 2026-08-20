# Benchmark Report

| Run | Latency (s) | Cost (USD) | Quality | Citation cov. | Failure rate | Notes |
|---|---:|---:|---:|---:|---:|---|
| baseline | 0.02 | 0.0000 | 9.0 | 100% | 0% | offline deterministic benchmark |
| multi-agent | 0.01 | 0.0000 | 10.0 | 100% | 0% | offline deterministic benchmark |

## Failure mode and fix

During validation, the optional LangGraph dependency was incompatible with the installed langchain-core version, causing import-time failure before tests could run. The fix was to pin compatible optional dependency ranges and add a small offline compatibility runner so the lab remains executable without external services. Worker failures are handled separately with one retry, trace events, and a visible `## Workflow failure` fallback.
