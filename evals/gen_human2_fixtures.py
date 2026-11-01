#!/usr/bin/env python3
"""Human-genre eval fixtures, batch 2 — nine conversation shapes aimed at
proven missing surfaces. This generator SELF-MEASURES: after composing each
fixture it compiles the pure path, runs the real checker per fact, and
rewrites score + surface into the fixture JSON. Facts therefore record what
survived, never what a guess predicted.

Fixtures (surface probed in parens):
  multiparty-plan    turn ownership — vcc has user/assistant only
  advice-session     assistant-authored durable content — no extractor
  relative-dates     deictic dates — ISO absolute only
  commitment-ledger  promises + retraction — supersession again
  topic-interleave   three threads over ~90 rounds — scope collapse
  currency-units     German notation €2.300 / 47,50 — verbatim-preserved,
                     unparsed; locale-drift is a baseline-run probe
  name-alias         one person, three labels — zero entity extractor
  qa-pairs           tutoring — question-guard drops half the exchange
  voice-noise        transcript garbage — length-based capture swallows the
                     umms into the header along with the fact

All persons, addresses, amounts and situations are invented.

regenerate: python3 evals/gen_human2_fixtures.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "engine"))
import fact_bank            # noqa: E402
import gen_fixtures as gf  # noqa: E402
import gen_human_fixtures as gh  # noqa: E402
import run_eval            # noqa: E402

PLAIN = ["Noted — continuing.", "Makes sense.", "Right.", "Okay — go on.", "Got it."]


def plain(msgs, i):
    msgs.append(gf.a(PLAIN[i % len(PLAIN)]))


# ───────────────────────────────────────────────────────────── multiparty-plan

def multiparty_plan():
    msgs, f = [], []
    gh.user(msgs, "Let's sort the rooftop get-together for the crew — figure out who brings what.",
            "I'll relay whatever people tell me.")
    f.append({"id": "goal-1", "category": "goal",
              "text": "Let's sort the rooftop get-together for the crew"})
    relay = [
        "Tom says he brings the grill and two bags of charcoal.",
        "Maya texted: she can host, rooftop is her place at Beispielweg 7.",
        "Jonas says he has to work Saturday, he'll drop by Sunday instead.",
        "Tom says he already texted the plus-ones to come.",
        "Maya says music is sorted, she brings the speaker.",
        "Petra says she'll bring two salads, one vegan.",
        "Jonas asks if Sunday lunch works better than dinner.",
        "Tom says charcoal is 12 euros at the corner shop.",
        "Maya says her neighbors need to be told by Thursday.",
        "Petra offers cold drinks, asks how many liters.",
    ]
    for i, line in enumerate(relay * 4, start=2):
        msgs.append(gf.u(line))
        msgs.append(gf.a("Logged." if i % 2 else "Added to the list."))
        plain(msgs, i)
    msgs.append(gf.u("Round two of the relay, people repeating themselves now."))
    for k in range(60):
        msgs.append(gf.u(gh.narr(k)))
        plain(msgs, k)
    msgs.append(gf.u("Maya confirms: Saturday 2026-11-14 at 16:00, her place, Beispielweg 7."))
    f.append({"id": "attribution-maya-host", "category": "identifier",
              "text": "Beispielweg 7"})
    f.append({"id": "attribution-jonas-sunday", "category": "identifier",
              "text": "Jonas says he has to work Saturday, he'll drop by Sunday instead."})
    f.append({"id": "attribution-tom-grill", "category": "identifier",
              "text": "Tom says he brings the grill"})
    msgs.append(gf.u("Okay let's lock it in as the final plan."))
    return msgs, f


# ─────────────────────────────────────────────────────────────── advice-session

def advice_session():
    msgs, f = [], []
    gh.user(msgs, "I have three exams in six weeks and I keep freezing up. How should I structure my study?",
            "Be specific — I want something I can follow.")
    f.append({"id": "goal-1", "category": "goal",
              "text": "I have three exams in six weeks and I keep freezing up"})
    msgs.append(gf.a("Split the six weeks into three two-week blocks, one subject each, "
                     "with a final week of mixed recall tests. Study in 40-minute blocks "
                     "with 10-minute breaks, and every evening write a half-page summary "
                     "of the day from memory."))
    f.append({"id": "advice-structure", "category": "preference",
              "text": "Split the six weeks into three two-week blocks, one subject each"})
    for i in range(4, 112):
        gh.user(msgs, gh.narr(i))
        plain(msgs, i)
        if i == 12:
            msgs.append(gf.a("Second rule that matters: never reread passively — "
                             "every session ends with closed-book recall."))
            f.append({"id": "advice-recall-rule", "category": "preference",
                      "text": "never reread passively"})
        if i == 25:
            gh.user(msgs, "The freezing is worst in the mornings.")
            msgs.append(gf.a("Then move the hardest subject to the evening this week and "
                             "start mornings with ten easy flashcards to warm up."))
    msgs.append(gf.a("Reminder of your plan: subject A by 2026-11-15, subject B by 2026-11-29, "
                     "mixed recall after that."))
    f.append({"id": "advice-dates", "category": "identifier",
              "text": "subject A by 2026-11-15"})
    msgs.append(gf.u("Great — that's exactly what I needed."))
    return msgs, f


# ────────────────────────────────────────────────────────────── relative-dates

def relative_dates():
    msgs, f = [], []
    gh.user(msgs, "Track my errands this fortnight — I'll say the dates the way people say them.")
    f.append({"id": "goal-1", "category": "goal",
              "text": "Track my errands this fortnight"})
    deictic = [
        ("The visa appointment is next Thursday.", "visa-next-thursday"),
        ("The paperwork is due in two weeks.", "paperwork-two-weeks"),
        ("The plumber comes the day after tomorrow.", "plumber-day-after"),
        ("I hand in the tax forms in ten days.", "tax-ten-days"),
        ("Mum's birthday is this coming Wednesday.", "mum-wednesday"),
    ]
    for i, (line, fid) in enumerate(deictic, start=2):
        msgs.append(gf.u(line))
        msgs.append(gf.a("Noted."))
        plain(msgs, i)
        f.append({"id": fid, "category": "identifier", "text": line})
        if i == 3:
            msgs.append(gf.u("Actually the visa appointment moved to the Monday after."))
            f.append({"id": "visa-moved", "category": "scope_change",
                      "text": "Actually the visa appointment moved to the Monday after."})
    for i in range(8, 112):
        gh.user(msgs, gh.narr(i))
        plain(msgs, i)
    msgs.append(gf.u("To restate with real dates: visa appointment 2026-11-16, paperwork due 2026-11-20."))
    f.append({"id": "visa-abs", "category": "identifier", "text": "2026-11-16"})
    f.append({"id": "paperwork-abs", "category": "identifier", "text": "2026-11-20"})
    msgs.append(gf.u("And plumber 2026-11-03, that's locked."))
    f.append({"id": "plumber-abs", "category": "identifier", "text": "2026-11-03"})
    return msgs, f


# ───────────────────────────────────────────────────────────── commitment-ledger

def commitment_ledger():
    msgs, f = [], []
    gh.user(msgs, "Help me keep track of what I promised people this month.")
    f.append({"id": "goal-1", "category": "goal",
              "text": "Help me keep track of what I promised people this month"})
    promises = [
        ("I promise to call the landlord by Monday.", "promise-landlord", "preference"),
        ("I said I'd help Kaya move on Saturday.", "promise-kaya", "preference"),
        ("I promised the office a demo before the 10th.", "promise-demo", "preference"),
    ]
    for line, fid, cat in promises:
        msgs.append(gf.u(line))
        plain(msgs, len(msgs))
        f.append({"id": fid, "category": cat, "text": line})
    for i in range(8, 112):
        gh.user(msgs, gh.narr(i))
        plain(msgs, i)
        if i == 20:
            msgs.append(gf.u("Actually, Saturday won't work with Kaya — I promised Sunday instead."))
            f.append({"id": "kaya-retract", "category": "scope_change",
                      "text": "Actually, Saturday won't work with Kaya — I promised Sunday instead."})
        if i == 44:
            msgs.append(gf.u("The demo slipped — it's now promised for the 19th."))
            f.append({"id": "demo-moved", "category": "scope_change",
                      "text": "it's now promised for the 19th"})
    msgs.append(gf.u("List me back everything I owe whom."))
    return msgs, f


# ────────────────────────────────────────────────────────────── topic-interleave

def topic_interleave():
    msgs, f = [], []
    threads = {
        "visa": ("Renew my visa before it lapses on 2026-12-01.", "visa-lapse-2026-12-01"),
        "noise": ("The neighbor's workshop noise after 22:00 has to stop — file the complaint.",
                  "noise-complaint-22"),
        "gift": ("Plan the anniversary gift for the exhibition opening.", "gift-exhibition-opening"),
    }
    msgs.append(gf.u(threads["visa"][0]))
    msgs.append(gf.u(threads["noise"][0]))
    msgs.append(gf.u(threads["gift"][0]))
    for key, (text, fid) in threads.items():
        f.append({"id": "goal-" + key, "category": "goal", "text": text.split(" —")[0][:70]})
    picks = [("visa", "The embassy needs the income proof PDF."),
             ("noise", "Their name on the register is Wehrlein, top floor."),
             ("gift", "Budget stays under 400."),
             ("visa", "Appointment slot opens 2026-11-05."),
             ("noise", "Landlord already knows, he backs the complaint."),
             ("gift", "Textile archive, not candles."),
             ("visa", "Old number B4-88210 must be cited in the form."),
             ("noise", "Recording from last Tuesday is 71 dB at 22:40."),
             ("gift", "Card reads simply: zehn Jahre.")]
    for i, (key, line) in enumerate(picks * 8):
        msgs.append(gf.u(line))
        plain(msgs, i)
        if i == 0:
            msgs.append(gf.u("Topical note to remember for later: the visa income proof comes from last quarter."))
            f.append({"id": "visa-proof-mid", "category": "identifier",
                      "text": "the visa income proof comes from last quarter"})
    msgs.append(gf.u("Scope change: drop the noise complaint for now, focus visa and gift."))
    f.append({"id": "scope-drop-noise", "category": "scope_change",
              "text": "drop the noise complaint for now, focus visa and gift"})
    msgs.append(gf.u("B4-88210 — don't lose that number."))
    f.append({"id": "visa-num-late", "category": "identifier", "text": "B4-88210"})
    msgs.append(gf.u("Gift card stays kurz und gut: zehn Jahre."))
    f.append({"id": "gift-text-late", "category": "identifier",
              "text": "zehn Jahre"})
    msgs.append(gf.u("What's still open in each thread?"))
    return msgs, f


# ──────────────────────────────────────────────────────────────── currency-units

def currency_units():
    """German notation canonical (Rain 2026-11-01): €2.300, comma decimals.
    An English-locale lookalike is planted as a deliberate ambiguity trap —
    2.300 (two thousand three hundred) vs 2,300 (two point three) are
    different numbers; the engine must preserve both verbatim and parse neither."""
    msgs, f = [], []
    gh.user(msgs, "Hilf mir, das Budget für die Werkstatt-Sanierung aufzustellen.",
            "Beträge bitte in deutscher Schreibweise.")
    f.append({"id": "goal-1", "category": "goal",
              "text": "Hilf mir, das Budget für die Werkstatt-Sanierung aufzustellen"})
    msgs.append(gf.u("Kernbudget sind €2.300, Werkzeug €47,50 extra, Anlieferung €180."))
    f.append({"id": "eur-de", "category": "identifier", "text": "€2.300"})
    f.append({"id": "cents-de", "category": "identifier", "text": "€47,50"})
    msgs.append(gf.a("Notiert — Kernbudget 2.300 Euro."))
    for i in range(4, 112):
        if i % 5 == 0:
            msgs.append(gf.u(gh.narr(i)))
        plain(msgs, i)
        if i == 10:
            msgs.append(gf.u("Der US-Lieferant schickt 2,300 USD — achtung, das ist NOT die Eurozahl."))
            f.append({"id": "usd-trap", "category": "identifier", "text": "2,300 USD"})
        if i == 22:
            msgs.append(gf.u("Actually, kürze das Kernbudget auf €1.900."))
            f.append({"id": "budget-cut", "category": "scope_change",
                      "text": "kürze das Kernbudget"})
            f.append({"id": "eur-new", "category": "identifier", "text": "€1.900"})
    msgs.append(gf.u("Gesamtbudget €1.900 plus Anlieferung €180 ist final."))
    f.append({"id": "eur-final", "category": "identifier", "text": "€1.900 plus Anlieferung €180"})
    return msgs, f


# ─────────────────────────────────────────────────────────────────── name-alias

def name_alias():
    msgs, f = [], []
    gh.user(msgs, "Help me follow up on the people from the design agency visit last week.")
    f.append({"id": "goal-1", "category": "goal",
              "text": "Help me follow up on the people from the design agency visit last week"})
    refs = [
        "Katja from Studio Nordberg liked the color study.",
        "K. sent a calendar link for Thursday.",
        "the woman from the agency asked for the pricing sheet by Friday",
        "Katja mentioned a second intro at the content studio on 2026-11-12",
        "K. confirmed the logo revision call.",
    ]
    for i, line in enumerate(refs, start=2):
        msgs.append(gf.u(line))
        plain(msgs, i)
    f.append({"id": "alias-full", "category": "identifier", "text": "Katja from Studio Nordberg"})
    f.append({"id": "alias-initial", "category": "identifier", "text": "K. sent a calendar link"})
    f.append({"id": "alias-descriptor", "category": "identifier",
              "text": "the woman from the agency asked for the pricing sheet"})
    for i in range(8, 112):
        gh.user(msgs, gh.narr(i))
        plain(msgs, i)
    msgs.append(gf.u("Katja, K., the woman from the agency — all the same person, mind you."))
    f.append({"id": "alias-merge-late", "category": "identifier",
              "text": "Katja, K., the woman from the agency"})
    msgs.append(gf.u("Draft the thank-you note to her, deadline Friday."))
    return msgs, f


# ───────────────────────────────────────────────────────────────────── qa-pairs

def qa_pairs():
    msgs, f = [], []
    gh.user(msgs, "Tutor me on Roman history — rapid fire, you ask, I answer, correct me.")
    f.append({"id": "goal-1", "category": "goal",
              "text": "Tutor me on Roman history"})
    qa = [
        ("Who founded Rome according to legend?", "Romulus, 753 BC"),
        ("What year did the Republic fall?", "27 BC, Augustus"),
        ("Name the river Caesar crossed.", "Rubicon, 49 BC"),
        ("What ended the Punic Wars?", "Rome destroyed Carthage, 146 BC"),
        ("Who was the last of the seven kings?", "Tarquinius Superbus"),
    ]
    for i, (q, a) in enumerate(qa * 2):
        msgs.append(gf.a(q))
        msgs.append(gf.u(a))
        msgs.append(gf.a("Right." if i % 2 else "Correct, moving on."))
    f.append({"id": "qa-answer-early", "category": "identifier", "text": "Romulus, 753 BC"})
    f.append({"id": "qa-question-early", "category": "identifier",
              "text": "Who founded Rome according to legend?"})
    f.append({"id": "qa-answer-late", "category": "identifier",
              "text": "Tarquinius Superbus"})
    for i in range(len(qa) * 2, len(qa) * 2 + 80):
        plain(msgs, i)
    msgs.append(gf.u("Recap round winner: you got the Rubicon one right twice."))
    return msgs, f


# ─────────────────────────────────────────────────────────────────── voice-noise

def voice_noise():
    msgs, f = [], []
    gh.user(msgs, "umm yeah so umm — I need to, like, reorder the Zahnspange thing for mia, "
                  "it was the umm blue one I think, with the extra pads? sorry, messy voice note.",
            "and umm tell me when you got it")
    f.append({"id": "goal-noisy", "category": "goal",
              "text": "I need to, like, reorder the Zahnspange thing for mia"})
    for i in range(3, 112):
        msgs.append(gf.u(("umm " * (i % 3 + 1)) + ("yeah " * (i % 4 + 1))
                         + gh.narr(i).lower()))
        plain(msgs, i)
        if i == 9:
            msgs.append(gf.u("wait no umm correction — it's the green one, not blue. order number umm 44-77-9."))
            f.append({"id": "voice-correction", "category": "scope_change",
                      "text": "it's the green one, not blue"})
            f.append({"id": "voice-order-no", "category": "identifier", "text": "44-77-9"})
    msgs.append(gf.u("also umm, the full thing I never sent was that the courier must arrive before 08:30 "
                     "and the gate code is T9-4410 and umm the pads are size M, sorry the message keeps going "
                     "and going and then ends after the wall like always."))
    f.append({"id": "voice-gate-code", "category": "identifier", "text": "T9-4410"})
    msgs.append(gf.a("Got it — reorder the green one, 44-77-9."))
    return msgs, f


# ────────────────────────────────────────────────── build → dump → MEASURE loop

BUILDERS = [
    ("multiparty-plan", multiparty_plan),
    ("advice-session", advice_session),
    ("relative-dates", relative_dates),
    ("commitment-ledger", commitment_ledger),
    ("topic-interleave", topic_interleave),
    ("currency-units", currency_units),
    ("name-alias", name_alias),
    ("qa-pairs", qa_pairs),
    ("voice-noise", voice_noise),
]


def measure_and_annotate(name):
    """Compile the pure path, score every fact with the real checker, and
    annotate the SURFACE into the fixture JSON. score stays the EXPECTATION
    (what a compacted mind should still know) — never rewritten to match
    measurement, or the gate would measure its own annotations. Expectation-
    true facts that were measured dropped are the signal: they print as
    misses and the blessed floor pins the honest retention number."""
    path = os.path.join(HERE, "fixtures", name + ".json")
    fx = fact_bank.load_fixture(path)
    texts = set()
    for _ in range(2):
        texts.add(run_eval.run_pure(fx)[0])
    deterministic = len(texts) == 1
    text = texts.pop()
    hdr = fact_bank.norm(text.split("\n---\n")[0])
    misses = []
    for fact in fx["facts"]:
        rec = fact_bank.recalled(fact_bank.Fact(**{k: v for k, v in fact.items()
                                                   if k in ("id", "category", "text", "hash", "score", "note")}), text)
        fact["score"] = bool(fact.get("score", True))
        base = fact.get("note", "").split(" | MEASURED")[0]
        surface = ("header" if fact_bank.norm(fact["text"]) in hdr
                   else "verbatim tail" if rec else "pre-tail, no matching extractor")
        fact["note"] = (base + " | MEASURED: " + ("survives via " if rec else "DROPPED (known gap) — ")
                        + surface).strip(" |")
        if fact["score"] and not rec:
            misses.append(fact["id"])
    with open(path, "w") as fh:
        json.dump(fx, fh, ensure_ascii=False, indent=1)
    return deterministic, misses


if __name__ == "__main__":
    for name, builder in BUILDERS:
        msgs, facts = builder()
        gf.dump(name, msgs, facts, track_commands=["pytest"])
        det, misses = measure_and_annotate(name)
        fx = fact_bank.load_fixture(os.path.join(HERE, "fixtures", name + ".json"))
        exp = sum(1 for x in fx["facts"] if x.get("score", True))
        print(f"{name:20s} facts={len(fx['facts']):2d} expect_keep={exp:2d} "
              f"deterministic={det} measured_misses={','.join(misses) or '-'}")
