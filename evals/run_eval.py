#!/usr/bin/env python3
"""Fact-retention eval for hermes-vcc (Grist task 72).

Scores how many weighted ground-truth facts survive compaction, with the
same symmetric checker over three candidate producers:

  pure     vcc_core.compile_summary — no host imports, fully offline
  engine   VccEngine._generate_summary — the shipped engine path (host redaction
           + summary prefix), requires the Hermes tree importable
  baseline host ContextCompressor._generate_summary — the built-in LLM pipeline
           (opt-in --baseline; one aux call per fixture ROUND — chain
           fixtures fold iteratively over one instance — live config)

Facts come only from fixtures (planted by gen_fixtures.py / gen_big_fixtures.py
and annotated with where each should survive). The harness never reads live
session transcripts — that is a deliberate policy (Rain, 2026-10-31); live
size/latency economics are measured separately by scripts/replay_eval.py.

Determinism is asserted on pure+engine (byte-identical re-run). focus_topic
is probed as a documented v0 no-op. --gate compares recall/reduction against
evals/gate.json floors; --bless rewrites the floors from measured values.

Usage (pxl):
    ~/.hermes/hermes-agent/venv/bin/python evals/run_eval.py            # pure+engine over fixtures
    ~/.hermes/hermes-agent/venv/bin/python evals/run_eval.py --baseline # + LLM baseline
    ~/.hermes/hermes-agent/venv/bin/python evals/run_eval.py --gate     # regression gate
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
AGENT = os.environ.get("HERMES_AGENT_DIR", os.path.expanduser("~/.hermes/hermes-agent"))
GATE_PATH = os.path.join(HERE, "gate.json")

sys.path.insert(0, HERE)          # fact_bank
sys.path.insert(0, os.path.join(REPO, "engine"))  # vcc_core (pure module)

# Engine/baseline import the hermes tree; a bare `python` on PATH may be a
# different toolchain without ruamel — re-exec under the pinned venv.
try:
    import ruamel.yaml  # noqa: F401
except ModuleNotFoundError:
    _sp = os.path.expanduser("~/.hermes/hermes-agent/venv/lib/python3.11/site-packages")
    _venv = os.path.expanduser("~/.hermes/hermes-agent/venv/bin/python")
    _pp = os.environ.get("PYTHONPATH")
    if os.path.isdir(_sp) and (_sp not in sys.path) and not (_pp and _sp in _pp):
        # relocatable venv bootstrap can miss its generation prefix under load
        os.environ["PYTHONPATH"] = _sp + (os.pathsep + _pp if _pp else "")
        os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)] + sys.argv[1:])

import fact_bank  # noqa: E402
import vcc_core  # noqa: E402


def _segments(fx):
    """A fixture is either one transcript or an ordered list of `rounds`
    segments compacted ITERATIVELY (chain fixtures)."""
    return fx.get("rounds") or [fx["messages"]]


def input_chars(messages) -> int:
    total = 0
    for m in messages:
        if not isinstance(m, dict):
            continue
        c = m.get("content")
        total += len(c) if isinstance(c, str) else len(json.dumps(c, default=str))
        for call in m.get("tool_calls") or []:
            args = ((call or {}).get("function") or {}).get("arguments")
            total += len(args) if isinstance(args, str) else len(json.dumps(args, default=str))
    return total


# ──────────────────────────────────────────────────────────────── producers

def run_pure(fx):
    opts = vcc_core.VccOptions(
        brief_max_lines=fx.get("brief_max_lines") or vcc_core.BRIEF_MAX_LINES_DEFAULT,
        track_commands=tuple(fx.get("track_commands") or ()),)
    outs = []
    for _ in range(2):
        prev = fx.get("previous_summary")
        for seg in _segments(fx):
            prev = vcc_core.compile_summary(list(seg), prev, opts) or prev
        outs.append(prev or "")
    return outs[0], outs[0] == outs[1]


_engine_mod = None


def get_engine():
    """Load engine/__init__.py directly: same class the host loader would
    produce, minus the isolation-host round-trip (the eval process already
    runs the host tree read-only from a trusted repo checkout)."""
    global _engine_mod
    if _engine_mod is not None:
        return _engine_mod.VccEngine(model="m")
    sys.path.insert(0, AGENT)
    import importlib.util
    eng_dir = os.path.join(REPO, "engine")
    last_exc = None
    for _ in range(2):  # one retry: import flaky under device memory pressure
        spec = importlib.util.spec_from_file_location(
            "vcc_engine_under_eval", os.path.join(eng_dir, "__init__.py"),
            submodule_search_locations=[eng_dir])
        mod = importlib.util.module_from_spec(spec)
        sys.modules["vcc_engine_under_eval"] = mod  # required for `from . import`
        try:
            spec.loader.exec_module(mod)
            _engine_mod = mod
            return mod.VccEngine(model="m")
        except Exception as exc:
            sys.modules.pop("vcc_engine_under_eval", None)
            last_exc = exc
    raise last_exc


def run_engine(fx):
    outs = []
    for _ in range(2):
        e = get_engine()
        e.update_model(model="m", context_length=256000)
        if fx.get("brief_max_lines") or fx.get("track_commands"):
            e._vcc_options = vcc_core.VccOptions(
                brief_max_lines=fx.get("brief_max_lines") or vcc_core.BRIEF_MAX_LINES_DEFAULT,
                track_commands=tuple(fx.get("track_commands") or ()))
        if fx.get("previous_summary"):
            e._previous_summary = fx["previous_summary"]
        text = ""
        for seg in _segments(fx):
            text = e._generate_summary(list(seg)) or text
        outs.append(text or "")
    return outs[0], outs[0] == outs[1]


def focus_probe(fx):
    """v0 stance: focus_topic is accepted but unused (no LLM to steer).
    True == confirmed no-op (byte-identical to the unfocused summary)."""
    a = get_engine(); a.update_model(model="m", context_length=256000)
    b = get_engine(); b.update_model(model="m", context_length=256000)
    plain = focused = ""
    for seg in _segments(fx):
        plain = a._generate_summary(list(seg)) or plain
        focused = b._generate_summary(list(seg), focus_topic="token refresh retry") or focused
    return plain == focused


def baseline_runtime():
    """Live main-model route from pxl config; None when unavailable."""
    sys.path.insert(0, AGENT)
    try:
        from hermes_cli.config import load_config
        cfg = load_config() or {}
        m = cfg.get("model") or {}
        provider = m.get("provider") or ""
        prov = (cfg.get("providers") or {}).get(provider) or {}
        base_url = m.get("base_url") or prov.get("api") or ""
        api_key = m.get("api_key") or prov.get("api_key") or ""
        model = m.get("default") or prov.get("default_model") or ""
        if not (model and base_url and api_key):
            return None
        return {"model": model, "provider": provider, "base_url": base_url,
                "api_key": api_key, "api_mode": m.get("api_mode") or "chat_completions",
                "context_length": int(prov.get("context_length") or 256000)}
    except Exception as exc:
        if os.environ.get("VCC_EVAL_DEBUG"):
            import traceback
            traceback.print_exc()
            import sysconfig
            print("sys.path:", sys.path)
            print("sp:", sysconfig.get_paths()["purelib"])
        print(f"  (baseline config unavailable: {exc})")
        return None


def run_baseline(fx, rt):
    """Built-in pipeline on the same transcript. For chain fixtures this
    folds over ONE compressor instance — each round sees the prior round's
    LLM summary, exactly the host's iterative-compaction contract (this is
    where rewrite-drift shows up)."""
    from agent.context_compressor import ContextCompressor
    c = ContextCompressor(model=rt["model"], provider=rt["provider"],
                          base_url=rt["base_url"], api_key=rt["api_key"],
                          api_mode=rt["api_mode"], config_context_length=rt["context_length"],
                          quiet_mode=True)
    text = ""
    for seg in _segments(fx):
        out = c._generate_summary(list(seg))
        if not out:
            raise RuntimeError(f"baseline produced nothing: {getattr(c, '_last_summary_error', '?')}")
        text = out
    return text


# ─────────────────────────────────────────────────────────────────── report

def eval_fixture(fx, paths, rt):
    facts = fact_bank.parse_facts(fx)
    in_chars = sum(input_chars(seg) for seg in _segments(fx))
    rounds = len(_segments(fx))
    row = {"name": fx["name"], "facts": len([f for f in facts if f.score]),
           "rounds": rounds, "paths": {}}
    for path in paths:
        try:
            if path == "pure":
                text, det = run_pure(fx)
            elif path == "engine":
                text, det = run_engine(fx)
            elif path == "baseline":
                text, det = run_baseline(fx, rt), None
            else:
                raise ValueError(path)
        except Exception as exc:
            if os.environ.get("VCC_EVAL_DEBUG"):
                import traceback
                traceback.print_exc()
            row["paths"][path] = {"error": f"{type(exc).__name__}: {exc}"[:200]}
            continue
        sc = fact_bank.score(facts, text)
        sc.update({"summary_chars": len(text),
                   "reduction": round(1 - len(text) / max(1, in_chars), 4),
                   "deterministic": det})
        row["paths"][path] = sc
    if "engine" in paths and "pure" in paths and not row["paths"].get("engine", {}).get("error"):
        row["focus_noop"] = focus_probe(fx)
    return row


def print_row(row):
    r = f", {row['rounds']} rounds" if row.get("rounds", 1) > 1 else ""
    print(f"\n── {row['name']} ({row['facts']} scored facts{r})")
    for path, sc in row["paths"].items():
        if "error" in sc:
            print(f"   {path:8s} ERROR {sc['error']}")
            continue
        det = "-" if sc["deterministic"] is None else ("OK" if sc["deterministic"] else "NONDET")
        print(f"   {path:8s} recall={sc['recall']*100:5.1f}%  reduction={sc['reduction']*100:5.1f}%  "
              f"({sc['summary_chars']}c)  determinism={det}")
        for cat, c in sorted(sc["categories"].items()):
            flag = "" if c["recalled"] == c["n"] else ("  <- known gap" if all(
                m["known_gap"] for m in sc["misses"] if m["category"] == cat) else "")
            print(f"            {cat:18s} {c['recalled']}/{c['n']}{flag}")
        for m in sc["misses"]:
            tag = " [known gap]" if m["known_gap"] else ""
            print(f"            MISS {m['id']:14s} ({m['category']}){tag} {m['text']}")
    if "focus_noop" in row:
        print(f"   focus_topic no-op probe: {'CONFIRMED' if row['focus_noop'] else 'STEERS?!'}")


# ───────────────────────────────────────────────────────────────────── main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", default=os.path.join(HERE, "fixtures"))
    ap.add_argument("--baseline", action="store_true", help="also score the built-in LLM pipeline")
    ap.add_argument("--gate", action="store_true", help="fail on gate.json floor violations")
    ap.add_argument("--bless", action="store_true", help="rewrite gate.json from measured values")
    ap.add_argument("--json", help="write full results JSON here")
    args = ap.parse_args()

    paths = ["pure", "engine"] + (["baseline"] if args.baseline else [])
    rt = baseline_runtime() if args.baseline else None
    if args.baseline and not rt:
        print("baseline requested but live route unavailable — skipping baseline")
        paths = [p for p in paths if p != "baseline"]

    fx_names = sorted(f for f in os.listdir(args.fixtures) if f.endswith(".json"))
    fixtures = [fact_bank.load_fixture(os.path.join(args.fixtures, f)) for f in fx_names]
    results = [eval_fixture(fx, paths, rt) for fx in fixtures]
    for r in results:
        print_row(r)

    ok = True
    if args.gate or args.bless:
        gate = {"floors": {}}
        for r in results:
            for path, sc in r["paths"].items():
                if "error" in sc or path == "baseline":
                    continue
                key = f"{r['name']}:{path}"
                if args.bless:
                    gate["floors"][key] = {"recall": round(sc["recall"] - 0.02, 3),
                                           "reduction": round(sc["reduction"] - 0.02, 3)}
                else:
                    prev = json.load(open(GATE_PATH)).get("floors", {}).get(key) if os.path.exists(GATE_PATH) else None
                    if prev is None:
                        print(f"GATE: no floor for {key} (run --bless)"); ok = False; continue
                    for metric in ("recall", "reduction"):
                        if sc[metric] < prev[metric]:
                            print(f"GATE FAIL {key}: {metric} {sc[metric]:.3f} < floor {prev[metric]:.3f}")
                            ok = False
                    if sc["deterministic"] is False:
                        print(f"GATE FAIL {key}: non-deterministic output"); ok = False
        if args.bless:
            gate["note"] = "floors = measured recall/reduction minus 0.02; re-bless only with a stated reason in the commit message"
            with open(GATE_PATH, "w") as fh:
                json.dump(gate, fh, indent=2)
            print(f"wrote {GATE_PATH} ({len(gate['floors'])} floors)")

    if args.json:
        with open(args.json, "w") as fh:
            json.dump(results, fh, indent=2)
        print(f"\nwrote {args.json}")

    print("\nEVAL:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
