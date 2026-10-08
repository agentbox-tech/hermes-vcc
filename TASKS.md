# hermes-vcc — follow-ups

## P1 — `touched` recall verb (port of pi-vcc mode:'touched' / pi-blackhole)
No session_search equivalent exists (verified against hermes-agent source Oct 2026:
no files-worked-on aggregation anywhere in session_search_tool.py / hermes_state_search.py).
Ship as the engine's `get_tool_schemas()` + `handle_tool_call()` (the ContextEngine ABC
exposes both; host injects engine tools gated by the `context_engine` toolset):
- mode:'touched' → files from read_file/write_file/patch/terminal tool_calls in the
  session's archived+active rows, each with the #N (DB row id) to scroll to.
- `#N:path` drill-down → read_file live, or session_search scroll for historical content.

## P2 — keep:N manual compaction
pi-vcc `/pi-vcc keep:N [prompt]` semantics require owning the cut point, which lives
in host `compress()`. Options: engine `register_command("/vcc", ...)` + a compress variant
that forces the tail boundary; verify against host staleness fences first.

## P3 — eval gate
`evals/compaction/` fixture replay + fact-retention benchmark vs the LLM pipeline
(pi-vcc benchmarks/README methodology). Run before any default-on activation beyond pxl.

## Known gaps (accepted for v1)
- focus_topic (/compress <focus>) ignored — no LLM to steer; deterministic output.
- skipForProviders / skipCustomTypes (pi-vcc config) not ported — no counterpart needed
  on a single-provider fleet yet.
