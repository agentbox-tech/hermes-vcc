# hermes-vcc — follow-ups

## P1 — `touched` recall verb — PARKED (Rain, 2026-10-08: no additional tools for v0)
Decision: v0 ships with ZERO engine tools. Recall rides `session_search` only
(query finds archived rows; #N refs scroll via around_message_id). If a real
workflow need for files-worked-on emerges later, revisit as an engine
`get_tool_schemas()` tool — the ContextEngine ABC seam is already verified.

## P2 — keep:N manual compaction
pi-vcc `/pi-vcc keep:N [prompt]` semantics require owning the cut point, which lives
in host `compress()`. Options: engine `register_command("/vcc", ...)` + a compress variant
that forces the tail boundary; verify against host staleness fences first. Slash command
is not a tool (zero schema cost per API call) — unlike P1 this does not violate the
v0 no-tools decision, but still hold it: v0 runs and evaluates first.

## P3 — eval gate
`evals/compaction/` fixture replay + fact-retention benchmark vs the LLM pipeline
(pi-vcc benchmarks/README methodology). Run before any default-on activation beyond pxl.

## Known gaps (accepted for v1)
- focus_topic (/compress <focus>) ignored — no LLM to steer; deterministic output.
- skipForProviders / skipCustomTypes (pi-vcc config) not ported — no counterpart needed
  on a single-provider fleet yet.
- touched-mode recall parked with P1 — files-worked-on is not recallable as a set
  until then; individual files are recoverable via session_search query + scroll.
