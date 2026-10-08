#!/usr/bin/env python3
"""Offline replay gate: run the vcc engine over real session transcripts from
the live state.db (read-only) and report reduction %, alternation violations,
and determinism. Never mutates the DB or the running agent.

Usage (pxl):
    HERMES_HOME=~/.hermes ~/.hermes/hermes-agent/venv/bin/python scripts/replay_eval.py [--min-msgs 150] [--sessions 3]
"""
import argparse
import logging
import os
import sys

logging.basicConfig(level=logging.WARNING)
HERMES = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
AGENT = os.environ.get("HERMES_AGENT_DIR", os.path.expanduser("~/.hermes/hermes-agent"))
sys.path.insert(0, AGENT)


def visible_roles(msgs):
    return [m.get("role") for m in msgs
            if m.get("role") != "tool" and not (m.get("role") == "assistant" and m.get("tool_calls"))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-msgs", type=int, default=150)
    ap.add_argument("--sessions", type=int, default=3)
    args = ap.parse_args()

    from hermes_state import SessionDB
    from plugins.context_engine import find_engine_dir, _load_engine_from_dir

    d = find_engine_dir("hermes-vcc")
    if not d:
        print("FAIL: engine not discovered"); return 1
    db = SessionDB()
    rows = db._conn.execute(
        "SELECT session_id FROM messages WHERE active=1 GROUP BY session_id "
        "HAVING COUNT(*)>=? ORDER BY MAX(timestamp) DESC LIMIT ?",
        (args.min_msgs, args.sessions)).fetchall()
    if not rows:
        print("FAIL: no sessions with >=%d msgs" % args.min_msgs); return 1

    failures = 0
    for (sid,) in rows:
        msgs = db.get_messages(sid)
        def run():
            e = _load_engine_from_dir(find_engine_dir("hermes-vcc"))
            e.update_model(model="m", context_length=256000)
            return e.compress(list(msgs), current_tokens=int(sum(len(str(m.get('content') or '')) for m in msgs) / 3.2))
        o1, o2 = run(), run()
        b1 = "".join(str(m.get("content") or "") for m in o1)
        b2 = "".join(str(m.get("content") or "") for m in o2)
        vis = visible_roles(o1)
        viol = sum(1 for i in range(len(vis) - 1) if vis[i] == vis[i + 1])
        cb = sum(len(str(m.get("content") or "")) for m in msgs)
        det = "OK" if b1 == b2 else "NON-DETERMINISTIC"
        ok = viol == 0 and b1 == b2
        failures += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'} {sid[:16]}: {len(msgs)}->{len(o1)} msgs, "
              f"{100*(1-len(b1)/cb):.1f}% reduction, alternation_violations={viol}, determinism={det}")
    print("REPLAY:", "ALL PASS" if failures == 0 else f"{failures} FAILED")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
