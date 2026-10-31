#!/usr/bin/env python3
"""Large-context synthetic fixtures for hermes-vcc evals.

All synthetic — the harness never reads live session data. Compaction only
earns its keep at bulk (hundreds of rounds, MB-scale transcripts) and the
cap ring-outs (brief tail, FILES_CAP, PREF_CAP, COMMITS_CAP, tracked-
command bucket) only collide at scale; the small fixtures cannot measure
them. Placement is arithmetic so every survival/loss is PREDICTED, not
hoped for:

  brief tail      ~200 rounds ≈ ~560 brief lines; cap keeps the last 120
                  → anything before ≈ round 157 leaves the transcript.
  PREF_CAP=10   header keeps the first ten (chronological); prefs #11+
                  planted before the brief tail are truly lost between the
                  scissors; #13 planted late rides only the tail.
  COMMITS_CAP   12 commits, keeps last 8 → stages 1..2 must ring out.
  tracked bucket 13 pytest invocations, keeps last 10 → #1..#3 ring out.
  FILES_CAP     patched mod_0NN: sorted head of header (mod_001..017) vs
                  brief tail (round > 157); mod_101 is mid → lost twice.

  big-refactor-100     ~200 rounds, ~600KB in — ONE compaction, all caps
                       colliding.
  chain-big-3rounds    three ~80-round segments compacted ITERATIVELY over
                       one engine fold — round-1 transcript is gone by
                       round 3; only section-merged facts survive. The regime
                       where LLM summarizers rewrite-drift and vcc cannot.

regenerate: python3 evals/gen_big_fixtures.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_fixtures as gf  # noqa: E402  (u/a/call/t/filler/mid/HERE)

BASE = "/home/rain/projects/billing/app"


def hexhash(i):
    return f"{(0x100ABCD + i * 7919) & 0xFFFFFFF:07x}"


def tool_round(i):
    p = f"{BASE}/mod_{i:03d}.py"
    if i % 2 == 0:
        gf.msgs.append(gf.a(f"Reading step {i}.", [gf.call("read_file", {"path": p})]))
        gf.msgs.append(gf.t("read_file", f"# mod_{i:03d}\nclass Step:\n" + gf.filler(25, "src")))
    else:
        gf.msgs.append(gf.a(f"Patching step {i}.",
                             [gf.call("patch", {"path": p, "old_string": "x", "new_string": "y"})]))
        gf.msgs.append(gf.t("patch", f"patched mod_{i:03d}.py ok"))


def commit_round(k):
    gf.msgs.append(gf.a(f"Committing stage {k}.",
                         [gf.call("terminal", {"command": f'git commit -m "billing stage {k}"'})]))
    gf.msgs.append(gf.t("terminal", f"[main {hexhash(k)}] billing stage {k}\n 3 files changed"))


def pytest_round(tag, output="22 passed"):
    gf.msgs.append(gf.a(f"Suite run {tag}.",
                         [gf.call("terminal", {"command": f"pytest tests/billing/r{tag:02d}.py -q"})]))
    gf.msgs.append(gf.t("terminal", f"{output} in {0.5 + tag * 0.01:.2f}s"))


# (text, round) — chronological; all texts use the engine's pref verb
# whitelist (always use|run|keep|write|prefix|include|append|set...,
# never use|write|send|run|deploy|delete...) so PREF_CAP pressure is what
# we measure, not pattern coverage. #11/#12 land past the cap mid-session.
PREFS = [
    ("Always prefix commit messages with billing:", 2),
    ("Never write files under legacy without asking.", 4),
    ("Always run the pytest suite before publishing a stage.", 6),
    ("Never send raw invoice payloads.", 8),
    ("Always write docs/runbook.md when endpoints change.", 10),
    ("Never use bare except in scheduler code.", 12),
    ("Always run p95 benchmarks before and after each stage.", 14),
    ("Never deploy the cron unit without a rollback one-liner.", 16),
    ("Always keep migrations reversible for two releases.", 18),
    ("Never run the live deploy before the dry-run passes.", 20),
    ("Always include a breadcrumbs comment at cut points.", 90),   # #11 → cap-trimmed
    ("Always set the timezone flag on scheduler jobs.", 110),       # #12 → cap-trimmed
    ("Always append a changelog entry per release.", 195),           # #13 → brief tail
]
PYTEST_ROUNDS = [3, 20, 37, 54, 71, 88, 105, 122, 139, 156, 173, 186, 197]


def big_refactor():
    gf.msgs, f = [], []
    R = 200
    gf.msgs.append(gf.u("Refactor the billing scheduler so it processes invoices in streams "
                        "and keep the public API stable across the whole migration."))
    f.append({"id": "goal-1", "category": "goal",
              "text": "Refactor the billing scheduler so it processes invoices in streams"})
    pref_at = {r: PREFS[i] for i, (_, r) in enumerate(PREFS) for _ in [i]}
    for r in range(R):
        if r in pref_at:
            n = [pr[1] for pr in PREFS].index(r) + 1
            gf.msgs.append(gf.u(PREFS[n - 1][0]))
            if n <= 10:
                f.append({"id": f"pref-{n}", "category": "preference", "text": PREFS[n - 1][0],
                         "note": "within PREF_CAP — must survive header"})
            elif n in (11, 12):
                f.append({"id": f"pref-{n}", "category": "preference", "text": PREFS[n - 1][0],
                         "score": False, "note": "past PREF_CAP, pre-brief-tail — measured drop"})
            elif n == 13:
                f.append({"id": "pref-13", "category": "preference", "text": PREFS[12][0],
                         "note": "past PREF_CAP but late — survives via brief tail"})
        elif r == 3:
            gf.msgs.append(gf.a("Early probe fails hard.",
                                [gf.call("terminal", {"command": "python -m compileall app -q"})]))
            gf.msgs.append(gf.t("terminal", "SyntaxError: invalid syntax (app/mod_003.py, line 12)\ncompilation stopped"))
            f.append({"id": "fail-early", "category": "failed_command",
                      "text": "python -m compileall app -q", "score": False,
                      "note": "measured drop: round 3 — untracked + past brief tail"})
            gf.msgs.append(gf.a("The scheduler import crashes on mod_003 — blocking everything."))
            f.append({"id": "blocker-early", "category": "blocker_volatile",
                      "text": "crashes on mod_003", "score": False,
                      "note": "measured drop: deep blocker — fresh-only policy"})
        elif r == 5:
            gf.msgs.append(gf.u("The compliance ticket REQ-1000 covers the audit trail requirement."))
            f.append({"id": "ident-early", "category": "identifier", "text": "REQ-1000",
                      "score": False, "note": "measured drop: pre-brief-tail"})
        elif r == 195:
            pass  # pref-13 handled above by pref_at
        tool_round(r)
        if r in PYTEST_ROUNDS:
            n = PYTEST_ROUNDS.index(r) + 1
            pytest_round(r, "1 failed, 21 passed" if r == 197 else "22 passed")
            if n in (11, 12):
                f.append({"id": f"pytest-{n}", "category": "tracked_command",
                         "text": f"pytest tests/billing/r{r:02d}.py",
                         "note": f"invocation #{n} of 13 — inside last-10 bucket"})
        if r % 15 == 14:
            commit_round(r // 15 + 1)
        if r == 197:
            gf.msgs.append(gf.a("The suite still fails on timezone rounding in the final stage — that is the open blocker."))
            f.append({"id": "blocker-late", "category": "blocker",
                      "text": "still fails on timezone rounding"})
        if r == 199:
            gf.msgs.append(gf.u("Close out ticket REQ-2000 when the suite is fully green."))
            f.append({"id": "ident-late", "category": "identifier", "text": "REQ-2000"})
    # ring-out diagnostics — score=False records MEASURED drops with intent;
    # header lists basenames only, so fact texts are basenames too.
    for k in (1, 2):
        f.append({"id": f"commit-{k}", "category": "commit", "text": f"billing stage {k}",
                  "hash": hexhash(k), "score": False,
                  "note": "measured drop: COMMITS_CAP=8 keeps stages 6..13"})
    f.append({"id": "commit-9", "category": "commit", "text": "billing stage 9",
              "hash": hexhash(9), "note": "invocation #9 of 13 — survives header cap"})
    f.append({"id": "pytest-1", "category": "tracked_command", "text": "pytest tests/billing/r03.py",
              "score": False, "note": "measured drop: bucket keeps last 10 of 13"})
    f.append({"id": "mod-head", "category": "modified_file", "text": "mod_001.py",
              "note": "header keeps chronology head (basenames); survives"})
    f.append({"id": "mod-mid", "category": "modified_file", "text": "mod_101.py",
              "score": False, "note": "measured drop: past header head AND pre-brief-tail"})
    f.append({"id": "mod-tail", "category": "modified_file", "text": "mod_199.py",
              "note": "late — brief tail (full path there; basename matches)"})
    gf.dump("big-refactor-100", gf.msgs, f, track_commands=["pytest"],
            description="~200-round synthetic refactor (~600KB): all caps colliding; placements arithmetic-predicted.")


# ─────────────────────────────────────────────────────────── chain-big-3rounds

def chain_segment(rnd):
    """~80-round synthetic segment. Files block-prefixed by round so sorted
    order == round order: round-1 files ride the merged header head."""
    gf.msgs.append(gf.u({
        1: "Migrate the legacy document converter to the streaming pipeline.",
        2: "Now the focus: add OCR fallback for scanned documents.",
        3: "Finally, cut over the batch API to the streaming converter.",
    }[rnd]))
    for i in range((rnd - 1) * 80, rnd * 80 - 4):  # 76 file rounds
        tool_round(i)
    pytest_round(40 + rnd)
    commit_round(rnd)
    if rnd == 1:
        # whitelist verb ("never remove") so pref extraction is not the
        # variable — iterative-fold survival is
        gf.msgs.append(gf.u("Never remove public endpoints during the chain."))
        gf.msgs.append(gf.a("First stage complete; OCR fallback queued for round two."))
    elif rnd == 2:
        gf.msgs.append(gf.a("Second stage committed; batch API cutover queued for round three."))
    else:
        gf.msgs.append(gf.a("The final stage still fails on nested-quote escaping — open blocker at handoff."))


def chain_big_3rounds():
    segs, facts = [], []
    goals = {
        1: "Migrate the legacy document converter to the streaming pipeline.",
        2: "Now the focus: add OCR fallback for scanned documents.",
        3: "Finally, cut over the batch API to the streaming converter.",
    }
    gf.msgs = []
    mark = 0  # compaction folds only the NEW tail since the last fold
    for rnd in (1, 2, 3):
        chain_segment(rnd)
        segs.append(gf.msgs[mark:])
        mark = len(gf.msgs)
        facts.append({"id": f"goal-r{rnd}", "category": "goal",
                      "text": goals[rnd][:60], "round": rnd})
        facts.append({"id": f"commit-r{rnd}", "category": "commit",
                      "text": f"billing stage {rnd}", "hash": hexhash(rnd), "round": rnd})
        facts.append({"id": f"pytest-r{rnd}", "category": "tracked_command",
                      "text": f"pytest tests/billing/r{40 + rnd}.py", "round": rnd})
    facts.append({"id": "mod-r1", "category": "modified_file", "text": "mod_001.py", "round": 1,
                  "note": "prev-first merge keeps round-1 files at the header head (basenames)"})
    facts.append({"id": "mod-r3", "category": "modified_file", "text": "mod_235.py", "round": 3,
                  "note": "late round-3 patch — brief tail of the final fold"})
    facts.append({"id": "pref-r1", "category": "preference",
                  "text": "Never remove public endpoints during the chain", "round": 1,
                  "note": "whitelist-matched pref planted round 1 — tests survival across two folds"})
    facts.append({"id": "blocker-r3", "category": "blocker",
                  "text": "still fails on nested-quote escaping", "round": 3})
    fx = {"name": "chain-big-3rounds",
          "description": "3×~76-round synthetic segments compacted ITERATIVELY; scoring the final fold — "
                       "round-1 transcript is gone, only merged sections survive.",
          "rounds": segs, "track_commands": ["pytest"], "facts": facts}
    path = os.path.join(gf.HERE, fx["name"] + ".json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(fx, fh, indent=2, ensure_ascii=False)
    print(f"wrote {path} ({sum(len(s) for s in segs)} msgs across 3 rounds, {len(facts)} facts)")


if __name__ == "__main__":
    gf.ROW[0] = 5000
    big_refactor()
    chain_big_3rounds()
