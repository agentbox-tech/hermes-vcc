#!/usr/bin/env python3
"""Structural-regime synthetic fixtures for hermes-vcc evals.

These probe STRUCTURAL regimes the extractor can silently fail in — each
fixture is built around one guard, cap, or absence of surface. Scores and
notes below are set from COMPILED output (run_pure), not from modelled
window arithmetic (skill rule: verify before blessing).

Measured engine behaviors the suite now pins:
  * the brief tail is verbatim, unclipped user text — guards (synthetic
    prefixes, XML strip, NON_GOAL, question skip, pref whitelist) protect
    the HEADER sections only; anything mid/late can still ride the tail,
    including fenced secrets.
  * preference extraction keeps ONE match per user block.
  * long whole user messages can become Session Goal lines verbatim.
  * USER_TEXT_CLIP=256 clips tail lines too — a fact planted past 256
    chars of a single turn is unrecoverable at fold.
  * previous_summary merge preserves prior goals/commits/prefs/files.
  * goal capture is length-based (language-blind); pref capture is
    English-whitelist-based (German and Arabic prefs never reach the
    header) — see bilingual-correction and arabic-workshop.

All personas, hosts, names and numbers are invented.

regenerate: python3 evals/gen_more_fixtures.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_fixtures as gf  # noqa: E402
import gen_human_fixtures as gh  # noqa: E402

PLAIN = [
    "Noted — continuing.",
    "That checks out.",
    "Working on it.",
    "Makes sense.",
    "Done — next step.",
]


def plain(msgs, i, prefix=None):
    msgs.append(gf.a((prefix + " " if prefix else "") + PLAIN[i % len(PLAIN)]))


# ────────────────────────────────────────────────────────────── research-web

def research_web():
    msgs, f = [], []
    gh.user(msgs, "Compare scheduler libraries for the fernpost ingest rewrite.",
            "I need benchmark numbers, not vibes.")
    f.append({"id": "goal-1", "category": "goal",
              "text": "Compare scheduler libraries for the fernpost ingest rewrite"})
    for i in range(1, 51):
        q = f"fernpost scheduler benchmark {'celery' if i % 2 else 'dask'} round {i}"
        msgs.append(gf.a("Searching.", [gf.call("web_search", {"query": q})]))
        hits = "\n".join(f"- fernrepo.example/lib/{h}-{i:03d}: notes and measured throughput"
                          for h in ("celery", "dask", "luigi"))
        msgs.append(gf.t("web_search", hits))
        if i % 3 == 0:
            msgs.append(gf.a("Pulling the top page.",
                             [gf.call("web_extract", {"url": f"https://fernrepo.example/lib/dask-{i:03d}"})]))
            msgs.append(gf.t("web_extract", "## Throughput\n" + gf.filler(60, "bench")))
        if i % 7 == 0:
            gh.user(msgs, f"Note CIT-{100 + i}: the article claims 41% faster on ingest-heavy load.")
        if i == 2:
            gh.user(msgs, "Early lead: fernrepo.example/early — looks promising.")
            f.append({"id": "url-early", "category": "read_file", "text": "fernsrepo.example/early",
                      "score": False, "note": "round 2 — URLs have no extractor; pre-brief-tail — measured drop"})
            f.append({"id": "cit-early", "category": "identifier", "text": "CIT-107",
                      "score": False, "note": "round 7 — pre-brief-tail — measured drop"})
        if i == 8:
            msgs.append(gf.a("Probing the endpoint.",
                             [gf.call("terminal", {"command": f"curl -s https://bench.example/{i}"})]))
            msgs.append(gf.t("terminal", gf.filler(40, "json")))
        if i % 12 == 0:
            msgs.append(gf.a("Saving notes.",
                             [gf.call("terminal", {"command": f'git commit -m "research notes {i // 12}"'})]))
            msgs.append(gf.t("terminal", f"[main {format(0xABCD0 + i, '07x')}] research notes"))
        if i == 44:
            msgs.append(gf.a("Suite check.", [gf.call("terminal", {"command": "pytest tests/ingest -q"})]))
            msgs.append(gf.t("terminal", "17 passed in 4.21s"))
        if i == 47:
            gh.user(msgs, "Always include the source URL next to every claim in the writeup.")
            f.append({"id": "pref-include", "category": "preference",
                      "text": "Always include the source URL next to every claim in the writeup",
                      "note": "whitelist 'always include' — survives header"})
            gh.user(msgs, "Always cite the failing benchmark with a CIT number.")
            f.append({"id": "pref-cite-gap", "category": "preference",
                      "text": "Always cite the failing benchmark with a CIT number",
                      "note": "'always cite' NOT on pref verb whitelist — no header entry; survives ONLY as verbatim tail (#1257)"})
        if i == 48:
            gh.user(msgs, "Best candidate so far: fernrepo.example/lib/dask-048, ref CIT-148.")
            f.append({"id": "url-late", "category": "read_file", "text": "fernsrepo.example/lib/dask-048",
                      "note": "late — verbatim brief tail"})
            f.append({"id": "cit-late", "category": "identifier", "text": "CIT-148",
                      "note": "late — verbatim brief tail"})
        plain(msgs, i)
    f.append({"id": "tracked-git", "category": "tracked_command",
              "text": 'git commit -m "research notes 1"',
              "note": "multi-name bucket: git survives alongside pytest"})
    f.append({"id": "tracked-pytest", "category": "tracked_command",
              "text": "pytest tests/ingest -q"})
    f.append({"id": "curl-untracked", "category": "tracked_command",
              "text": "curl -s https://bench.example/8", "score": False,
              "note": "curl not in track_commands — untracked, pre-tail — measured drop"})
    gf.dump("research-web", msgs, f, track_commands=["git", "pytest"],
            description="~50-round invented web-research session: URL/citation surfaces, multi-name tracked buckets.")


# ───────────────────────────────────────────────────────────── failure-chain

def failure_chain():
    msgs, f = [], []
    gh.user(msgs, "Fix the flaky nightly on the billing pipeline, whatever it takes.")
    f.append({"id": "goal-1", "category": "goal",
              "text": "Fix the flaky nightly on the billing pipeline, whatever it takes"})
    fails = {8: ("pytest tests/billing/e8 -q", "3 failed, 40 passed", "test_billing_overflow"),
             22: ("pytest tests/billing/e22 -q", "1 failed, 42 passed", "test_currency_round"),
             39: ("pytest tests/billing/e39 -q", "2 failed, 41 passed", "test_tax_join")}
    for i in range(1, 68):
        if i in fails:
            cmd, out, test = fails[i]
            msgs.append(gf.a("Running the suite.", [gf.call("terminal", {"command": cmd})]))
            msgs.append(gf.t("terminal", out + f"\nFAILED {test}"))
            msgs.append(gf.a(f"Red: {test} — investigating."))
            if i == 8:
                f.append({"id": "fail-tracked-e8", "category": "failed_command",
                         "text": "pytest tests/billing/e8 -q",
                         "note": "tracked bucket — COMMAND survives; bucket carries no pass/fail outcome"})
                f.append({"id": "failed-test-e8", "category": "blocker_volatile",
                         "text": "test_billing_overflow",
                         "note": "error identity is not extracted state — survives ONLY via assistant's 'Red:' line in tail"})
            if i == 22:
                f.append({"id": "fail-tracked-e22", "category": "failed_command",
                         "text": "pytest tests/billing/e22 -q",
                         "note": "tracked bucket keeps last 10 pytest calls incl. this failure"})
        elif i % 9 == 0:
            gh.user(msgs, gh.narr(i))
            msgs.append(gf.a("Attempting a fix.",
                             [gf.call("patch", {"path": "/home/dan/billing/nightly.py",
                                               "old_string": "x", "new_string": "y"})]))
            msgs.append(gf.t("patch", "patched nightly.py ok"))
        if i == 60:
            msgs.append(gf.a("Untracked late probe fails too.",
                             [gf.call("terminal", {"command": "make check-live"})]))
            msgs.append(gf.t("terminal", "Error: upstream timeout after 30s"))
            f.append({"id": "fail-late-untracked", "category": "failed_command",
                      "text": "make check-live",
                      "note": "untracked — survives ONLY because late; verbatim brief tail"})
        if i == 66:
            gh.user(msgs, "The tax join is still returning null rates for two tenants — that is the open blocker.")
            f.append({"id": "blocker-fresh", "category": "blocker",
                      "text": "The tax join is still returning null rates for two tenants — that is the open blocker.",
                      "note": "round 66 of 67 — also promoted to [Outstanding Context]"})
        plain(msgs, i)
    gf.dump("failure-chain", msgs, f, track_commands=["pytest"],
            description="~67-round escalating-failure session: command-vs-outcome retention split, fresh-only blockers.")


# ────────────────────────────────────────────────────────────── resume-seeded

RESUME_SEED = """[Session Goal]
- Port the ingest worker to Kafka.

[User Preferences]
- Always run the contract suite before merging.

[Commits]
- a1b2c3d: pin kafka client

[Files And Changes]
- Modified: worker.py
"""


def resume_seeded():
    msgs, f = [], []
    gh.user(msgs, "Picking up where we left off — Kafka port. First, the DLQ design: dead-letter topics for parse failures.",
            "DLQ-2200 is the ticket.")
    f.append({"id": "goal-new", "category": "goal",
              "text": "Picking up where we left off — Kafka port."})
    f.append({"id": "dlq-2200", "category": "identifier", "text": "DLQ-2200",
              "note": "survives twice: whole first message became a Session Goal line AND the tail"})
    for i in range(2, 12):
        gh.user(msgs, gh.narr(i))
        msgs.append(gf.a("Working on it.",
                         [gf.call("patch", {"path": "/home/ivn/ingest/worker.py",
                                           "old_string": "x", "new_string": "y"})]))
        msgs.append(gf.t("patch", f"patched worker.py ok (round {i})"))
        plain(msgs, i)
    gh.user(msgs, "[CONTEXT COMPACTION — REFERENCE ONLY] The staging host staging-7.example stays flaky.")
    f.append({"id": "guard-synth", "category": "identifier", "text": "staging-7.example",
              "score": False,
              "note": "synthetic-prefix guard: whole block dropped before extraction — measured absent"})
    gh.user(msgs, "Reference the flaky host staging-8.example in the runbook notes.",
            "<memory-context>secret token ZL-555 ignored</memory-context>")
    f.append({"id": "guard-xml", "category": "identifier", "text": "ZL-555",
              "score": False, "note": "XML block stripped by _XML_BLOCK_RE before extraction — measured absent"})
    f.append({"id": "plain-late", "category": "identifier", "text": "staging-8.example",
              "note": "non-guarded part of same message — late, brief tail"})
    f.append({"id": "prev-goal", "category": "goal", "text": "Port the ingest worker to Kafka.",
              "note": "seeded previous_summary — merge keeps prior goals first"})
    f.append({"id": "prev-commit", "category": "commit", "text": "pin kafka client",
              "hash": "a1b2c3d", "note": "seeded commit: hash AND subject survive the merge"})
    f.append({"id": "prev-pref", "category": "preference",
              "text": "Always run the contract suite before merging.",
              "note": "seeded whitelist pref — header merge retains"})
    f.append({"id": "prev-file", "category": "modified_file", "text": "worker.py",
              "note": "seeded file merged ahead of new patches"})
    gf.dump("resume-seeded", msgs, f, previous_summary=RESUME_SEED,
            description="host-resume shape: seeded previous_summary + guard blocks; tests merge integrity + drop guards.")


# ─────────────────────────────────────────────────────────── noise-adversarial

def noise_adversarial():
    msgs, f = [], []
    msgs.append(gf.u("Review the auth module and fix the token refresh retry loop in gateway.py."))
    f.append({"id": "goal-1", "category": "goal",
              "text": "Review the auth module and fix the token refresh retry loop in gateway.py"})
    msgs.append(gf.a("Ok — auth module, refresh retry. Any style rules?"))
    msgs.append(gf.u("ok"))                                     # bare ack — dropped
    msgs.append(gf.u("What about REQ-3000?"))               # question
    f.append({"id": "q-ident", "category": "identifier", "text": "REQ-3000",
              "note": "question turn: NON_GOAL '^What' kept it out of goals header — but the verbatim tail still carries it"})
    msgs.append(gf.u("Style notes:\n\n| module | rule |\n|---|---|\n| gateway | always use utc timestamps |\n| api | never put pii in logs |"))
    f.append({"id": "pref-in-table", "category": "preference",
              "text": "always use utc timestamps",
              "note": "pref regex is .search() — whitelist text in a table cell IS extracted (whole row stored)"})
    f.append({"id": "pref-in-table2", "category": "preference",
              "text": "never put pii in logs", "score": False,
              "note": "SECOND pref in the same user block — extraction keeps one match per block; row dropped (measured)"})
    msgs.append(gf.u("Reference impl:\n```python\ndef retry():\n    # always use jittered backoff\n    token = \"s3cr3t-abc123\"\n```"))
    f.append({"id": "pref-in-fence", "category": "preference",
              "text": "always use jittered backoff",
              "note": "whitelist pref buried in a code fence — extracted; fence-blind, comment marker kept"})
    f.append({"id": "secret-in-fence", "category": "identifier", "text": "s3cr3t-abc123",
              "note": "SECURITY NOTE: fences do not shield content — verbatim tail carries the secret until tail rollover"})
    msgs.append(gf.u("/non-goal-leading-slash-line should never become a goal"))
    f.append({"id": "slash-nongoal", "category": "goal",
              "text": "/non-goal-leading-slash-line",
              "note": "NON_GOAL guard kept it out of goals header; verbatim tail still carries the line"})
    for i in range(6, 30):
        msgs.append(gf.a("Continuing.",
                         [gf.call("read_file", {"path": f"/home/omar/auth/gateway_{i:02d}.py"})]))
        msgs.append(gf.t("read_file", gf.filler(30, "src")))
        plain(msgs, i)
    msgs.append(gf.u(("Long instruction that keeps going to probe the USER_TEXT_CLIP=256 wall, " * 5)
                     + "and REQ-5000 sits past it."))
    f.append({"id": "ident-past-clip", "category": "identifier", "text": "REQ-5000",
              "score": False,
              "note": "past USER_TEXT_CLIP=256 within one turn — clipped at fold; unrecoverable from header AND tail (measured: tail line cut mid-sentence at the wall)"})
    gf.dump("noise-adversarial", msgs, f,
            description="~30-round adversarial formatting: fences, tables, guards, questions, past-clip probe.")


# ─────────────────────────────────────────────────────── bilingual-correction

def bilingual_correction():
    msgs, f = [], []
    gh.user(msgs, "Help me plan the kitchen renovation budget.",
            "Ich möchte alles in einem Rutsch durchgehen.")
    f.append({"id": "goal-1", "category": "goal",
              "text": "Help me plan the kitchen renovation budget"})
    f.append({"id": "goal-de", "category": "goal",
              "text": "Ich möchte alles in einem Rutsch durchgehen.",
              "note": "goal capture is length-based, language-blind — German second line became a Session Goal verbatim"})
    msgs.append(gf.u("Benutze immer Celsius und nie Fahrenheit."))
    f.append({"id": "pref-de-gap", "category": "preference",
              "text": "Benutze immer Celsius und nie Fahrenheit",
              "note": "German pref: pref verbs are English-only — no header entry ever; survives ONLY as verbatim tail"})
    gh.user(msgs, "Always use metric units in the plan.")
    f.append({"id": "pref-en", "category": "preference",
              "text": "Always use metric units in the plan"})
    gh.user(msgs, "The working budget is 1800 euro.")
    f.append({"id": "budget-stale", "category": "identifier", "text": "1800",
              "note": "SUPERSEDED value still recalled: verbatim tail + the correction line itself quotes 1800 — engine has no supersession surface (amendment design exhibit, board 197)"})
    for i in range(12, 50):
        gh.user(msgs, gh.narr(i) + (" Alles gut soweit." if i % 5 == 0 else ""))
        plain(msgs, i)
        if i == 30:
            gh.user(msgs, "Actually, make the budget 1600 instead of 1800.")
            f.append({"id": "correction", "category": "scope_change",
                      "text": "Actually, make the budget 1600 instead of 1800.",
                      "note": "'Actually' scope marker + 'make' whitelist — survives as scope/goal AND tail"})
            f.append({"id": "budget-fixed", "category": "identifier", "text": "1600"})
        if i == 40:
            gh.user(msgs, "Fertig braucht es einen Termin bis zum 15.12.2026.")
            f.append({"id": "date-de", "category": "identifier", "text": "15.12.2026",
                      "note": "German date idiom unmached in header (ISO pattern only) — survives via verbatim tail"})
        if i == 48:
            gh.user(msgs, "Confirm the appointment by 2026-12-15.")
            f.append({"id": "date-iso-late", "category": "identifier", "text": "2026-12-15",
                      "note": "ISO date, late — brief tail verbatim"})
    gf.dump("bilingual-correction", msgs, f,
            description="~50-round DE/EN session with numeric supersession: stale-fact persistence + language coverage gaps.")


# ────────────────────────────────────────────────────────────── arabic-workshop

def arabic_workshop():
    """Mixed-script session: agent chats in Arabic while workshopping
    German business emails. Invented persona Layla, invented
    client, invented amounts."""
    msgs, f = [], []
    msgs.append(gf.u("أحتاج مساعدتك في صياغة عرض سعر للعميل الألماني بخصوص تجديد المطبخ."))
    f.append({"id": "goal-ar", "category": "goal",
              "text": "أحتاج مساعدتك في صياغة عرض سعر للعميل الألماني بخصوص تجديد المطبخ",
              "note": "goal capture is length-based — full Arabic request becomes a Session Goal verbatim"})
    msgs.append(gf.a("Of course — let's draft the quote."))
    msgs.append(gf.u("تمام"))                                   # bare Arabic ack
    msgs.append(gf.u("دائماً حافظ على نبرة رسمية وودودة في رسائل العميل."))
    f.append({"id": "pref-ar-gap", "category": "preference",
              "text": "دائماً حافظ على نبرة رسمية وودودة في رسائل العميل",
              "note": "Arabic pref: whitelist is English-only — zero header coverage; survives ONLY as verbatim tail"})
    for i in range(4, 34):
        if i % 4 == 0:
            msgs.append(gf.u("حسناً، لنكمل الصياغة."))
            msgs.append(gf.a("Refining the draft."))
        if i == 9:
            msgs.append(gf.u("vielen Dank für Ihre Anfrage zum Angebot 4711 — bitte bestätigen Sie den Termin."))
            f.append({"id": "de-snippet", "category": "identifier", "text": "4711",
                      "score": False, "note": "mid-session German email body: refs inside unparsed prose — pre-brief-tail measured drop"})
        if i == 15:
            msgs.append(gf.u("المبلغ ٤٧١١ يورو يشمل التركيب."))
            f.append({"id": "arabic-indic", "category": "identifier", "text": "٤٧١١",
                      "score": False,
                      "note": "Arabic-Indic digits: all ID idioms are ASCII — unrecoverable once pre-tail (measured drop)"})
        if i % 6 == 0:
            msgs.append(gf.a("Draft v2.", [gf.call("write_file", {"path": "/home/layla/angebote/angebot.txt"})]))
            msgs.append(gf.t("write_file", gf.filler(35, "angebot")))
        plain(msgs, i)
    msgs.append(gf.u("في الواقع، المبلغ النهائي 5200 وليس 4711."))
    f.append({"id": "ar-correction", "category": "identifier", "text": "5200",
              "note": "Arabic-worded correction: no English scope marker — no scope section; survives via verbatim tail"})
    msgs.append(gf.a("Noted — final amount 5200."))
    msgs.append(gf.u("أرسل المسودة إلى layla@example.de بعد المراجعة."))
    f.append({"id": "email-ar-turn", "category": "identifier", "text": "layla@example.de",
              "note": "EMAIL_RE is ASCII — email inside Arabic turn still extracted/tailed"})
    msgs.append(gf.u("الموعد المقترح ١٥ ديسمبر ٢٠٢٦ صباحاً."))
    f.append({"id": "arabic-month", "category": "identifier", "text": "١٥ ديسمبر ٢٠٢٦",
              "note": "Arabic month name + Arabic-Indic digits — no idiom matches; survives ONLY verbatim tail"})
    gf.dump("arabic-workshop", msgs, f,
            description="~35-round Arabic-narration session workshopping a German client email; language coverage map.")


if __name__ == "__main__":
    research_web()
    failure_chain()
    resume_seeded()
    noise_adversarial()
    bilingual_correction()
    arabic_workshop()
