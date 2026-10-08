# hermes-vcc

Algorithmic (no-LLM) context compaction for [Hermes Agent](https://github.com/NousResearch/hermes-agent) — a port of the extraction/formatter core of [pi-vcc](https://github.com/sting8k/pi-vcc) (MIT, © sting8k).

Deterministic, zero-token summaries: the summary is built by regex extraction and formatting, never by a model call. Same transcript in → same bytes out.

## How it plugs in

`VccEngine` is a `ContextCompressor` subclass that overrides exactly the two LLM choke points:

| Override | Effect |
|---|---|
| `_generate_summary` | pi-vcc `compile()` instead of the summary LLM — no network, no tokens, no cooldowns needed |
| `_augment_summary_lean` | drops the verbatim-user-messages section (verbatim imperatives inside a "REFERENCE ONLY" artifact license stale-task resumption); keeps host framing |

Everything else stays host-owned and battle-tested: head/tail protection, token thresholds + per-model overrides, orphaned tool-pair repair, archiving compacted rows to the session DB, summary placement/role selection, commit fences, compression counters, session lifecycle.

## Recall

Compacted turns are archived (`active=0, compacted=1`), never deleted, and stay searchable with the built-in `session_search`:

- `query` finds compacted content by keyword (archived rows are included in FTS by default)
- every brief line carries a `(#N)` ref that is the **DB message id** → `session_search(session_id=..., around_message_id=N)` scrolls the full original text

pi-vcc's `touched` mode and `#N:path` drill-down are deliberately NOT ported in v0 —
no additional engine tools ship; recall surface is `session_search` only.

## Install (pxl pattern)

```bash
git clone https://github.com/agentbox-tech/hermes-vcc.git ~/projects/hermes-vcc
ln -sfn ~/projects/hermes-vcc/engine ~/.hermes/plugins/hermes-vcc
hermes config set context.engine hermes-vcc
```

New sessions pick the engine up at agent init (log line: `Using context engine: hermes-vcc`). Deactivate with `hermes config set context.engine compressor`.

## Config (all optional)

```yaml
context:
  engine: hermes-vcc
  vcc:
    brief_max_lines: 120   # brief transcript budget
    track_commands: []     # command names kept as a [Tracked Commands] ledger
    debug: false           # write $HERMES_HOME/vcc-debug.json per compaction
```

## Measured (pxl, Oct 2026, real session DB replays)

- 69–90% char reduction across three 120–284-message sessions
- 0 role-alternation violations on template-visible roles (host repair intact)
- byte-identical output on repeated compaction of the same transcript

## Layout

```
engine/        # the plugin dir (symlinked to ~/.hermes/plugins/hermes-vcc)
├── __init__.py    # VccEngine — host-facing seam (imports agent.context_compressor)
├── vcc_core.py    # pure port: normalize → filter → extract → brief → format → merge
└── plugin.yaml    # discovery metadata
tests/         # pytest battery (pure tables; no hermes imports)
scripts/       # replay/eval helpers
```

`vcc_core.py` imports nothing from Hermes — unit-testable anywhere.

## License

MIT. Port of pi-vcc (MIT); `mode:touched` follow-up derives from pi-blackhole (MIT, © k0valik).
