# Design Template

## Problem

Xây dựng research assistant offline: truy hồi evidence, phân tích claim và viết câu trả lời có citation.

## Why multi-agent?

Single-agent có thể làm baseline, nhưng khó quan sát handoff và cô lập lỗi. Multi-agent tách retrieval, analysis và writing để trace và retry rõ hơn.

## Agent roles

| Agent | Responsibility | Input | Output | Failure mode |
|---|---|---|---|---|
| Supervisor | Chọn stage còn thiếu | Shared state | route | Bounded iterations |
| Researcher | Truy hồi offline sources | ResearchQuery | sources, research_notes | Search/corpus error |
| Analyst | Rút claim có evidence | sources | analysis_notes | Missing sources |
| Writer | Tổng hợp câu trả lời | analysis_notes | final_answer | Missing analysis |

## Shared state

`request` giữ query; `sources` giữ evidence; `research_notes` và `analysis_notes` là handoff; `final_answer` là output; `route_history`, `trace`, `errors` phục vụ debug và đánh giá failure.

## Routing policy

`START → Supervisor → Researcher → Supervisor → Analyst → Supervisor → Writer → Supervisor → END`. Supervisor dừng khi có `final_answer`.

## Guardrails

- Max iterations: 6 mặc định, cấu hình qua `MAX_ITERATIONS`.
- Timeout: 60 giây mặc định, cấu hình qua `TIMEOUT_SECONDS`.
- Retry: mỗi worker tối đa một retry.
- Fallback: trả về `## Workflow failure` và lưu lỗi/trace, không giả vờ thành công.
- Validation: Pydantic schema, query tối thiểu 5 ký tự, citations được kiểm tra trong benchmark.

## Benchmark plan

Chạy cùng query cho baseline và multi-agent; đo latency, estimated cost, quality proxy, citation coverage và failure rate. Kỳ vọng multi-agent có trace/quality proxy cao hơn, còn baseline thường nhanh hơn trong offline mode.
