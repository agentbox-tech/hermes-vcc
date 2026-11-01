#!/usr/bin/env python3
"""Human-stress fixtures — the shapes a household box must not drop.

Coverage rule (Rain 2026-11-01, after the human-case gap review): the
suite covered facts SAID; these stress facts that REPEAT, CHANGE STATE,
expire, arrive SECOND-HAND, or carry CONSEQUENCE. Failure modes here are
harm, not inconvenience, so several facts are deliberately planted where no
current extractor can reach them — those counted misses are the evidence
for the amendment lane (board 197).

  safety-diet            allergy + dose facts embedded in prose (EN/DE/TR)
  three-day-state-chain  Mahnung → payment → closure across three folds;
                         deadlines that EXPIRE vs deadlines that stay live
  roster-recurring       recurrence semantics (jeden Dienstag / standing)
                         + person-keyed care roster with a swap revision
  quote-forwards         second-hand speech (> Maya schrieb: …) that the
                         bullet/NON_GOAL guards actively eat today
  vent-then-ask          40 low-fact emotional blocks, one buried request
                         and a remember-don't-fix instruction

All persons, places, amounts, medicines and situations are invented.

regenerate: python3 evals/gen_human_stress_fixtures.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_fixtures as gf  # noqa: E402
import gen_human_fixtures as gh  # noqa: E402
from gen_human2_fixtures import plain, measure_and_annotate  # noqa: E402


def pad(msgs, start=4, end=110):
    for i in range(start, end):
        msgs.append(gf.u(gh.narr(i)))
        plain(msgs, i)


def _chain(name, path, edges):
    """Reshape a dumped single-shot fixture into iterative-fold rounds."""
    fx = json.load(open(path))
    m = fx.pop("messages")
    fx["rounds"] = [m[a:b] for a, b in edges]
    json.dump(fx, open(path, "w"), indent=2, ensure_ascii=False)
    return [len(r) for r in fx["rounds"]]


def safety_diet():
    msgs, f = [], []
    gh.user(msgs, "Hilf mir beim Wochenplan fürs Essen — für die ganze Familie und den Besuch am Samstag.")
    f.append({"id": "goal-diet", "category": "goal",
              "text": "Hilf mir beim Wochenplan fürs Essen"})
    safety = [
        ("Wichtig: Sevim ist allergisch gegen Erdnüsse — nichts mit Erdnüssen oder Erdnussöl auf den Tisch.",
         "allergy-peanut", "Sevim ist allergisch gegen Erdnüsse"),
        ("Mia darf ihr Asthmaspray nehmen: zwei Hübe morgens, zwei abends, vor dem Schlafengehen.",
         "dose-spray", "zwei Hübe morgens, zwei abends"),
        ("Kaya isst vegetarisch, darauf bitte bei allem achten, was für Samstag geplant ist.",
         "kaya-vegetarisch", "Kaya isst vegetarisch"),
        ("Atıştırmalık olarak cevizli kurabiye yapmayalım, Sevim'in alerjisi çok ciddi.",
         "allergy-tr", "Sevim'in alerjisi çok ciddi"),
    ]
    for line, fid, note in safety:
        msgs.append(gf.u(line))
        plain(msgs, len(msgs))
        f.append({"id": fid, "category": "preference", "text": line,
                  "note": "safety-critical — " + note})
    msgs.append(gf.u("Der Wochenplan soll drei Mahlzeiten pro Tag haben, wechselnde Rezepte, nicht zu aufwendig."))
    plain(msgs, 8)
    pad(msgs, 9, 110)
    msgs.append(gf.u("Nochmal, damit es sicher notiert ist: keine Nüsse bei Sevim, Spray 2x morgens 2x abends, Kaya vegetarisch."))
    f.append({"id": "safety-restated", "category": "preference",
              "text": "keine Nüsse bei Sevim"})
    return msgs, f


def three_day_state_chain():
    day1 = []
    gh.user(day1, "Samstag, 31.10. — die Mahnung der Stadtwerke ist gekommen, 347,50 Euro, Zahlungsziel 07.11., Referenz MAH-2261-88.")
    plain(day1, 1)
    day2 = [
        gf.u("Sonntag, 01.11. — die Rechnung ist jetzt bezahlt, per Überweisung, BNZ beilag 55-409-2."),
        gf.a("Notiert."),
    ]
    day2_pad = []
    for i in range(2, 60):
        day2_pad.append(gf.u(gh.narr(i)))
        plain(day2_pad, i)
    day3 = []
    day3.append(gf.u("Zahlung bestätigt, Akte geschlossen. Neue Frist für den Einspruch: 2026-11-28."))
    f_ = [
        {"id": "mahnung-betrag", "category": "identifier",
         "text": "347,50 Euro",
         "note": "locale-formatted amount, deep day-1 — survival measures fold carry of amounts"},
        {"id": "mahnung-ref", "category": "identifier", "text": "MAH-2261-88"},
        {"id": "zahlung-getaetigt", "category": "scope_change",
         "text": "die Rechnung ist jetzt bezahlt",
         "note": "STATE transition — no state semantics in v0; counted miss expected"},
        {"id": "ebeleg-nr", "category": "identifier", "text": "55-409-2"},
        {"id": "einspruch-frist", "category": "identifier", "text": "2026-11-28"},
        {"id": "altedeadline-expired", "category": "identifier",
         "text": "07.11.",
         "note": "EXPIRED deadline — v0 keeps it salient next to live ones; temporal validity gap"},
    ]
    msgs = day1 + day2 + day2_pad + day3
    return msgs, f_


def roster_recurring():
    msgs, f = [], []
    gh.user(msgs, "Unser Wochenritual und die Betreuung — bitte alles festhalten, mehrsprachig wie bei uns üblich.")
    f.append({"id": "goal-roster", "category": "goal",
              "text": "Wochenritual und die Betreuung"})
    entries = [
        ("Jeden Dienstag ist Müll rausstellen, in geraden Wochen auch die Papiertonne.", "recur-trash"),
        ("Stehende Termine: donnerstags 9 Uhr Standup, immer mit Kaffee danach.", "recur-standup"),
        ("Mia wird am Mittwoch von Opa abgeholt, 15:30 Uhr, bitte Regenjacke einpacken.", "roster-mia-mittwoch"),
        ("Παρακαλώ θύμισε τη Σέβιμ να πάρει τα φάρμακα της Τετάρτη στις 8.", "sevim-meds-wed"),
    ]
    for line, fid in entries * 3:
        msgs.append(gf.u(line))
        plain(msgs, len(msgs))
    first_ids = [
        {"id": "roster-mia-mittwoch", "category": "identifier",
         "text": "Mia wird am Mittwoch von Opa abgeholt"},
        {"id": "recur-standup", "category": "preference",
         "text": "Stehende Termine: donnerstags 9 Uhr Standup",
         "note": "recurrence semantics — 'stehende/jeden' match no extractor; counted miss expected"},
        {"id": "sevim-meds-wed", "category": "preference",
         "text": "να πάρει τα φάρμακα της Τετάρτη στις 8",
         "note": "Greek care note — no extractor for the language yet"},
    ]
    f.extend(first_ids)
    pad(msgs, len(msgs), len(msgs) + 60)
    msgs.append(gf.u("Tausch in der Betreuung: Opa holt Mia am Donnerstag ab, nicht Mittwoch — der Mittwoch fällt aus."))
    f.append({"id": "roster-swap", "category": "scope_change",
              "text": "Opa holt Mia am Donnerstag ab, nicht Mittwoch",
              "note": "supersession — both days will remain recalled (no chains)"})
    return msgs, f


def quote_forwards():
    msgs, f = [], []
    gh.user(msgs, "Ich leite euch die Nachrichten weiter, die ich so kriege — bitte alles zuordnen und merken.")
    f.append({"id": "goal-forward", "category": "goal",
              "text": "alles zuordnen und merken"})
    quotes = [
        "> Maya schrieb: Der Schlüssel liegt im Briefkasten, Code 4471, nicht verlieren.",
        "> Tom leitete weiter: Der Handwerker kommt Dienstag zwischen 8 und 12, einen Werkstattschlüssel braucht er nicht.",
        "> Weitergeleitet von Kaya: esse Samstag doch Fisch, mein Vater bringt welchen mit.",
        "> Nachricht von Sevim: Bitte die Mahnung NICHT bezahlen bevor die Rechnung da ist, nur die Originalrechnung, nicht die erste Kopie.",
    ]
    for k in range(3):
        for q in quotes:
            msgs.append(gf.u(q))
            plain(msgs, k * 4 + len(msgs) // 4 % 5)
    f.append({"id": "fwd-code", "category": "identifier", "text": "Code 4471",
              "note": "inside a quote-forward block — guards eat '>' openers; only tail can carry"})
    f.append({"id": "fwd-safety", "category": "blocker",
              "text": "die Mahnung NICHT bezahlen bevor die Rechnung da ist",
              "note": "second-hand SAFETY instruction — attribution AND content must survive; counted miss expected"})
    f.append({"id": "fwd-handwerker", "category": "identifier",
              "text": "Dienstag zwischen 8 und 12"})
    pad(msgs, 20, 110)
    msgs.append(gf.u("Falls wichtig: der Code ist auch am Freitag noch 4471, gleich wie im Briefkasten."))
    f.append({"id": "code-echo", "category": "identifier", "text": "4471"})
    return msgs, f


def vent_then_ask():
    msgs, f = [], []
    feelings = [
        "Heute war einfach einer dieser Tage, weißt du?",
        "Alles fühlt sich gerade nach zu viel an, ehrlich.",
        "Ich habe schon wieder alles auf morgen verschoben.",
        "Manchmal denke ich, ich organiséiere nur noch Chaos.",
        "Es ist nicht dramatisch, nur anstrengend, immer weiter.",
        "Alle erwarten was und ich sitz hier mit zu wenig Kaffee.",
        "Weißt du dieses Gefühl, wenn die Post Angst macht?",
        "Ich will heute gar nicht viel, nur raus hier irgendwie.",
    ]
    for k in range(5):
        for line in feelings:
            msgs.append(gf.u(line))
    msgs.append(gf.u("Ich will gar nicht, dass du das reparierst — ich will nur, dass du weißt, "
                     "dass ich nächste Woche den Brief vom Amt öffnen und beantworten muss, "
                     "Frist Mitte November,und dass ich dabei deine Hilfe will, Sanftmut zuerst."))
    f.append({"id": "remember-not-fix", "category": "preference",
              "text": "Ich will gar nicht, dass du das reparierst",
              "note": "remember-don't-fix instruction — no extractor shape; counted miss expected"})
    f.append({"id": "brief-amt-task", "category": "goal",
              "text": "den Brief vom Amt öffnen und beantworten muss"})
    f.append({"id": "frist-mitte-nov", "category": "identifier",
              "text": "Frist Mitte November",
              "note": "fuzzy deadline — no numeric form, identifier idioms all exact"})
    pad(msgs, 2, 110)
    msgs.append(gf.u("Danke fürs Zuhören. Der Brief: Frist ist der 14.11. geworden."))
    f.append({"id": "frist-exact", "category": "identifier", "text": "14.11."})
    return msgs, f


BUILDERS = [
    ("safety-diet", safety_diet, None),
    ("three-day-state-chain", three_day_state_chain, [(0, 2), (2, 62), (62, None)]),
    ("roster-recurring", roster_recurring, None),
    ("quote-forwards", quote_forwards, None),
    ("vent-then-ask", vent_then_ask, None),
]


if __name__ == "__main__":
    for name, builder, edges in BUILDERS:
        msgs, facts = builder()
        gf.dump(name, msgs, facts, track_commands=["pytest"])
        if edges:
            path = f"{gf.HERE}/{name}.json"
            r = _chain(name, path, [(a, b if b is not None else len(msgs)) for a, b in edges])
            print(f"  -> chain: rounds={r}")
        det, misses = measure_and_annotate(name)
        print(f"{name:22s} facts={len(facts):2d} deterministic={det} "
              f"misses={len(misses)} ({','.join(misses[:4])}{'…' if len(misses) > 4 else ''})")
