"""hermes-vcc: algorithmic (no-LLM) compaction engine for Hermes.

A ContextEngine plugin (ContextCompressor subclass, register(ctx) ->
ctx.register_context_engine). Port of pi-vcc
(https://github.com/sting8k/pi-vcc, MIT) onto the built-in
ContextCompressor by overriding its two LLM choke points:

- ``_generate_summary``: replaces the summary LLM call with deterministic
  extraction+formatting from ``vcc_core.compile_summary``. No network, no
  tokens, same input -> same bytes.
- ``_augment_summary_lean``: keeps the host's deterministic anchor index and
  recovery footer, DROPS the verbatim-user-messages section — verbatim
  imperatives from the compacted region compete with the REFERENCE-ONLY
  framing and license stale-task resumption (observed in production).

Everything else stays host-owned: head/tail protection, token thresholds and
per-model overrides, orphaned tool-pair repair, archival to the session DB
(compacteds stay searchable via session_search), summary placement/roles,
commit fences, compression counters, session lifecycle.

#id refs in the brief are DB message ids (``_row_id``) where the host has
stamped them, so ``session_search(session_id=..., around_message_id=N)``
consumes them directly; messages without a row id render no ref (fail-closed).

Activate with:  hermes config set context.engine hermes-vcc
Config block (all optional):
    context:
      engine: hermes-vcc
      vcc:
        brief_max_lines: 120
        track_commands: []
        debug: false
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from typing import Any, Dict, List, Optional

from agent.context_compressor import (
    ContextCompressor,
    _collect_ghosted_skill_names,
    _extract_pruned_skill_names,
    _redact_compaction_text,
    _reinject_pruned_skill_markers,
)

from . import vcc_core
from .vcc_core import VccOptions

logger = logging.getLogger(__name__)

ENGINE_NAME = "hermes-vcc"
_MAX_PRUNED_SKILL_MARKERS = 8


def _config_blocks() -> Dict[str, Any]:
    """``context.vcc`` merged over ``compression`` fallbacks; empty on any failure."""
    try:
        from hermes_cli.config import load_config
        cfg = load_config() or {}
    except Exception:
        return {}
    ctx = cfg.get("context") if isinstance(cfg.get("context"), dict) else {}
    vcc = ctx.get("vcc") if isinstance(ctx.get("vcc"), dict) else {}
    comp = cfg.get("compression") if isinstance(cfg.get("compression"), dict) else {}
    return {"vcc": vcc, "compression": comp}


def _coerce_int(value: Any, default: int) -> int:
    try:
        out = int(value)
        return out if out > 0 else default
    except (TypeError, ValueError):
        return default


def _row_ref(msg: Dict[str, Any]) -> Optional[int]:
    """DB message id for (#N) refs: host-stamped _row_id first, then id."""
    for key in ("_row_id", "id"):
        val = msg.get(key)
        if isinstance(val, int) and val > 0:
            return val
        if isinstance(val, str) and val.isdigit():
            return int(val)
    return None


class VccEngine(ContextCompressor):
    """ContextCompressor with a deterministic pi-vcc summarizer."""

    @property
    def name(self) -> str:  # noqa: ANN401
        return ENGINE_NAME

    def __init__(self, model: str = "", **kwargs: Any) -> None:
        blocks = _config_blocks()
        vcc_cfg, comp_cfg = blocks.get("vcc", {}), blocks.get("compression", {})
        # Threshold/protect parity with the host compression config so the
        # engine is behavior-configurable through the same dials (plugin
        # engines own their policy; nothing is pushed by the host).
        kwargs.setdefault("threshold_percent", _coerce_float(
            comp_cfg.get("threshold"), 0.75))
        kwargs.setdefault("protect_first_n", _coerce_int(comp_cfg.get("protect_first_n"), 3))
        kwargs.setdefault("protect_last_n", _coerce_int(comp_cfg.get("protect_last_n"), 20))
        super().__init__(model=model, quiet_mode=True, **kwargs)
        self._vcc_options = VccOptions(
            brief_max_lines=_coerce_int(vcc_cfg.get("brief_max_lines"),
                                         vcc_core.BRIEF_MAX_LINES_DEFAULT),
            track_commands=tuple(str(c) for c in (vcc_cfg.get("track_commands") or [])),
        )
        self._vcc_debug = bool(vcc_cfg.get("debug"))
        self._hermes_home = ""

    # ── session/state ────────────────────────────────────────────────────

    def on_session_start(self, session_id: str, **kwargs: Any) -> None:
        super().on_session_start(session_id, **kwargs)
        self._hermes_home = str(kwargs.get("hermes_home") or self._hermes_home or "")

    def clone_for_agent(self) -> "VccEngine":
        """Deepcopy would choke on a bound session DB; the host re-binds DB
        state after cloning, so carry options + budget counters only."""
        clone = VccEngine(model=self.model)
        clone.threshold_percent = self.threshold_percent
        clone.threshold_tokens = self.threshold_tokens
        clone.context_length = self.context_length
        clone.protect_first_n = self.protect_first_n
        clone.protect_last_n = self.protect_last_n
        clone._vcc_options = self._vcc_options
        clone._vcc_debug = self._vcc_debug
        return clone

    # ── the ported summarizer ────────────────────────────────────────────

    def _generate_summary(
        self, turns_to_summarize: List[Dict[str, Any]], focus_topic: Optional[str] = None,
        memory_context: str = "", bypass_cooldown: bool = False,
    ) -> Optional[str]:
        """Deterministic pi-vcc compile. focus_topic/memory_context are accepted
        for host-signature parity and unused: there is no LLM to steer."""
        started = time.monotonic()
        try:
            redacted = _redact_compaction_text  # host's strict redactor, applied per-turn
            sanitized: List[Dict[str, Any]] = []
            for msg in turns_to_summarize:
                if not isinstance(msg, dict):
                    continue
                copy = dict(msg)
                if isinstance(copy.get("content"), str):
                    copy["content"] = redacted(copy["content"])
                ref = _row_ref(msg)
                if ref is not None:
                    copy["id"] = ref  # (#N) brief refs are consumable by session_search
                sanitized.append(copy)

            previous = self._previous_summary
            if isinstance(previous, str) and previous:
                previous = redacted(previous)

            opts = self._vcc_options
            try:
                from agent.context_compressor import _SYNTHETIC_USER_ROW_PREFIXES
                opts = VccOptions(brief_max_lines=opts.brief_max_lines,
                                  track_commands=opts.track_commands,
                                  synthetic_user_prefixes=_SYNTHETIC_USER_ROW_PREFIXES)
            except Exception:
                pass

            summary = vcc_core.compile_summary(sanitized, previous, opts)
        except Exception as exc:  # fail-closed: host inserts its deterministic fallback
            self._last_summary_error = f"vcc compile failed: {exc}"
            logger.warning("hermes-vcc: deterministic summary failed (%s) — host fallback will apply", exc)
            return None

        if not summary:
            self._last_summary_error = "vcc compile produced nothing"
            return None

        # Ghost-skill defense, same as the built-in: markers survive verbatim.
        names = list(dict.fromkeys(
            _collect_ghosted_skill_names(turns_to_summarize)
            + _extract_pruned_skill_names(previous or "")))[:_MAX_PRUNED_SKILL_MARKERS]
        if names:
            summary = _reinject_pruned_skill_markers(summary, names)

        from agent.context_compressor import HISTORICAL_TASK_HEADING  # noqa: F401 (ownership marker)
        self._previous_summary = summary
        self._last_summary_error = None
        self._summary_model_fallen_back = False
        elapsed_ms = (time.monotonic() - started) * 1000.0
        if self._vcc_debug:
            self._write_debug(turns_to_summarize, summary, elapsed_ms)
        logger.info("hermes-vcc: deterministic summary in %.1fms (%d chars from %d turns)",
                    elapsed_ms, len(summary), len(turns_to_summarize))
        return self._with_summary_prefix(summary)

    # ── lean augment policy: anchors + recovery, NO verbatim user section ──

    def _augment_summary_lean(self, summary: str, turns_to_summarize: List[Dict[str, Any]]) -> str:
        """Not called on the v1 path (overridden _generate_summary does not use
        it); kept for any host refactor that re-routes through it."""
        return summary

    # ── debug artifact ─────────────────────────────────────────────────────

    def _write_debug(self, turns: List[Dict[str, Any]], summary: str, elapsed_ms: float) -> None:
        try:
            home = self._hermes_home or os.environ.get("HERMES_HOME", "")
            if not home:
                return
            payload = {
                "at": time.time(),
                "session_id": getattr(self, "_session_id", ""),
                "turns": len(turns),
                "elapsed_ms": round(elapsed_ms, 2),
                "summary_chars": len(summary),
                "compression_count": self.compression_count,
            }
            path = os.path.join(home, "vcc-debug.json")
            fd, tmp = tempfile.mkstemp(dir=home, prefix=".vcc-debug-", suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)
            os.replace(tmp, path)
        except Exception:
            pass

    # ── status ─────────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        status = super().get_status()
        status["engine"] = ENGINE_NAME
        status["summarizer"] = "algorithmic (no-LLM)"
        return status


def _coerce_float(value: Any, default: float) -> float:
    try:
        out = float(value)
        return out if 0.1 <= out <= 0.99 else default
    except (TypeError, ValueError):
        return default


def register(ctx: Any) -> None:
    """Entry point for the Hermes context-engine loader."""
    ctx.register_context_engine(VccEngine())
