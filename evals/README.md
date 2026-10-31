# evals — fact-retention benchmark for hermes-vcc

Answers the question the replay gate can't: **not "does compaction shrink and
stay deterministic" but "what do you still know after compaction"** — and how
that compares to the built-in LLM pipeline. Grist task 72; the numbers here
are the gate for default-on activation beyond pxl.

Methodology is pi-vcc's (`benchmarks/README.md` upstream), adapted to Hermes:
reference facts are established from the FULL transcript, then every candidate
producer — vcc and the baseline — is scored by the SAME checker
(`fact_bank.score`), symmetric by construction. Matching is normalized
substring (casefold + whitespace collapse), not embeddings.

## Layout

    evals/
      fact_bank.py       fact model: categories, weights, symmetric checkers
      gen_fixtures.py    regenerates fixtures/ (edit here, then regenerate)
      fixtures/*.json    synthetic sessions + planted ground-truth facts
      run_eval.py        the runner (see usage below)
      gate.json          measured regression floors (--bless rewrites them)

## Fact model

Weights follow pi-vcc's doctrine — an error state carried forward is worth
more than an `ls`:

| category           | w | notes                                                        |
|--------------------|--:|--------------------------------------------------------------|
| failed_command     | 6 | the failure the next context window must not forget           |
| commit             | 5 | hash AND subject must both appear (when hash is known)        |
| modified_file    | 4 | prefix-trim tolerant: trailing 2 segments match the header    |
| goal / scope_change / preference / blocker | 4 | user intent and state   |
| blocker_volatile | 4 | deep/early blocker — dropping is the DOCUMENTED fresh-only policy; the low score is the measurement, not a bug |
| created_file     | 3 |                                                              |
| tracked_command  | 2 | requires the fixture's `track_commands`                       |
| identifier       | 2 | trace/ticket ids — probes the USER_TEXT_CLIP=256 wall         |
| read_file        | 1 |                                                              |

**Matching subtleties that are the whole point:** facts can survive in
different places — the structured header (capped per section) or the brief
transcript (tail-capped at `brief_max_lines`). Where a fact is *expected* to
survive is annotated in each fixture fact's `note` (e.g. pref-11/12 fall past
`PREF_CAP=10` in the header but ride on as `[user]` brief lines; the early
pytest in long-cap-session survives only because Tracked Commands keeps its
own tail-retained bucket).

## Producers

- `pure` — `vcc_core.compile_summary` directly. Offline, zero host imports.
- `engine` — `VccEngine._generate_summary`: the shipped path (host strict
  redaction, SUMMARY_PREFIX, fixture `track_commands`/`brief_max_lines`
  injected into `_vcc_options`, `previous_summary` seeded for chain fixtures).
- `baseline` — host `ContextCompressor._generate_summary` against the live
  route from pxl config (`model:` block → providers registry). One real aux
  call per fixture. Non-deterministic by nature: **reported, never gated.**

Interpreter: run under `~/.hermes/hermes-agent/venv/bin/python` (the runtime
that owns the host tree). The runner self-checks for `ruamel.yaml` at startup
and re-execs with the venv site-packages pinned via `PYTHONPATH` — the
relocatable venv bootstrap on pxl occasionally comes up without its
generation prefix under load, which surfaces as a phantom
`ModuleNotFoundError: No module named 'ruamel'` in any host-chain import.

## Running

```bash
# offline regression (fixtures, pure+engine)
~/.hermes/hermes-agent/venv/bin/python evals/run_eval.py

# with the built-in LLM pipeline for comparison (spends aux tokens)
~/.hermes/hermes-agent/venv/bin/python evals/run_eval.py --baseline

# live-session replay scoring, symmetric generic extractor (read-only on state.db)
~/.hermes/hermes-agent/venv/bin/python evals/run_eval.py --real 3

# gate mode (floors in gate.json) / re-bless after an intentional change
~/.hermes/hermes-agent/venv/bin/python evals/run_eval.py --gate
~/.hermes/hermes-agent/venv/bin/python evals/run_eval.py --bless
```

Gate = recall/reduction floors per fixture×path (measured − 0.02), plus
determinism required on pure+engine. Re-bless only with the reason in the
commit message.

## Results (v0.1.0, pxl, 2026-10-31; baseline = live route qwen3.8-flash-next)

| fixture | vcc engine recall | vcc reduction | baseline recall | baseline reduction |
|---|--:|--:|--:|--:|
| coding-session | 96.5% | 72.0% | 100% | −0.2% (16,971c) |
| error-recovery | **100%** | 80.2% | 74.2% — loses BOTH blockers | 33.2% |
| long-cap-session | 100% | 95.4% | 100% | 81.5% (36,879c) |
| multi-compact-chain | **89.5%** | −574% | 55.3% — loses prev goal/commit/pref | −2042% |
| preference-heavy | 100% | −260% | 100% | −1192% |

Reading: vcc is small-and-lossless on durable structure; the LLM baseline is
big and degrades exactly where it matters — blocker state (error-recovery:
0/2) and cumulative merge across repeated compactions (55.3%: iterative
rewrites drop the previous goal, commit, and preference; vcc's
section-merge keeps them). The baseline's one recall win is verbatim
identifiers past vcc's `USER_TEXT_CLIP=256` (coding-session 100% vs 96.5%)
at ~3.6× the summary size. Negative reductions on tiny fact-dense fixtures
mean the summary legitimately exceeds a thin input — real sessions carry the
real numbers (`--real`).

Out-of-sample (`--real 3`, live pxl sessions, symmetric generic extractor):
**100% weighted recall on all three** — 133/133w over 221 msgs, 65/65w over
189, 165/165w over 404. Facts the engine never saw labeled (commands, paths,
commits, failed commands re-extracted independently) all survive.

## What v0 is known to lose (probed, not guessed)

| gap | probe | observed |
|---|---|---|
| `focus_topic` ignored | engine run with vs without focus, byte-compare | no-op CONFIRMED — deterministic summaries identical |
| identifiers past `USER_TEXT_CLIP=256` | `ident-clipped` fact in coding-session | dropped — known gap, floor records it |
| prev Outstanding Context | multi-compact-chain `prev-blocker` | dropped — fresh-only policy by design |
| skipForProviders / skipCustomTypes | not ported; no v0 knob exists | anything non-synthetic compiles |
| touched-not-recallable-as-set | v0 ships zero engine tools (Rain 2026-10-08) | file set survives only as header/ brief lines; no query surface |

Reduction on tiny fact-dense fixtures (multi-compact-chain, preference-heavy)
is negative — the summary legitimately exceeds a thin input; real sessions
carry the real numbers (`--real`).
