#!/usr/bin/env python3
"""Diff two `run_eval.py --json` outputs: report per-fixture recall deltas.

Campaign tool: run before a change, run after, diff — a change must move
something measurable or be reported as behavior-preserving.

usage: python evals/diff_eval.py before.json after.json [--path engine]
"""
import argparse
import json
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--path", default="engine")
    args = ap.parse_args()
    b = {e["name"]: e["paths"][args.path]["recall"] for e in json.load(open(args.before))}
    a = {e["name"]: e["paths"][args.path]["recall"] for e in json.load(open(args.after))}
    moved = changed = 0
    for name in sorted(set(b) | set(a)):
        rb, ra = b.get(name), a.get(name)
        if rb is None:
            print(f"NEW  {name:32s} {ra:.1%}")
            continue
        if ra is None:
            print(f"GONE {name}")
            continue
        d = ra - rb
        if abs(d) < 1e-9:
            changed += 1
            continue
        moved += 1
        print(f"{'UP  ' if d > 0 else 'DOWN'} {name:32s} {rb:6.1%} -> {ra:6.1%}  ({d:+.1%})")
    print(f"-- {moved} fixture(s) moved, {changed} unchanged "
          f"({sum(1 for n in set(b) & set(a) if a[n] < b[n])} regressions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
