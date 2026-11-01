#!/usr/bin/env python3
"""Multilingual eval fixtures — genre × language matrix.

Coverage rule: every human-genre shape must exist in more than English, and
at least one TECHNICAL session must be multilingual (native instructions
around an English toolchain — the actual AgentBox usage shape). Languages:
EN + DE AR ES UK SV FI ZH JA KO (+TR). The engine's pattern lists are
English today, so these fixtures mostly MEASURE A COVERAGE MAP OF THE GAP
before the multilingual extraction layer ships; scores are expectations,
misses are the map. CJK also probes structural walls (clip_sentence has no
。！？ awareness, truncate_words degrades to raw clip). Self-measured via
gen_human2.

  commitment-ledger-{de,ar,es,uk,sv,fi,zh,ja,ko}   promises + revisions +
                                                    deictic dates per language
  coding-session-multilingual                       nine native intents, seven
                                                    native blockers, EN toolchain
  cjk-punctuation-probe                             。 boundaries past USER_TEXT_CLIP
  relative-dates-{de,tr}  multiparty-plan-de  advice-session-de
  name-alias-ar  voice-noise-de  topic-interleave-mix  coding-session-de

All persons, places, amounts and situations are invented.

regenerate: python3 evals/gen_multilingual_fixtures.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_fixtures as gf  # noqa: E402
import gen_human_fixtures as gh  # noqa: E402
from gen_human2_fixtures import plain, measure_and_annotate  # noqa: E402


def pad(msgs, start=6, end=110):
    for i in range(start, end):
        msgs.append(gf.u(gh.narr(i)))
        plain(msgs, i)


def commitment_ledger_de():
    msgs, f = [], []
    gh.user(msgs, "Hilf mir, was ich diesen Monat zugesagt habe, im Blick zu behalten.")
    f.append({"id": "goal-de", "category": "goal",
              "text": "Hilf mir, was ich diesen Monat zugesagt habe, im Blick zu behalten"})
    lines = [
        ("Ich verspreche, den Vermieter bis Montag anzurufen.", "promise-vermieter"),
        ("Ich habe Kaya gesagt, dass ich ihr am Samstag beim Umzug helfe.", "promise-kaya"),
        ("Ich habe dem Büro eine Demo vor dem 10. versprochen.", "promise-demo"),
    ]
    for line, fid in lines:
        msgs.append(gf.u(line))
        plain(msgs, len(msgs))
        f.append({"id": fid, "category": "preference", "text": line})
    pad(msgs, 8)
    msgs.append(gf.u("Eigentlich passt Samstag nicht mit Kaya — ich habe ihr Sonntag versprochen."))
    f.append({"id": "kaya-revision-de", "category": "scope_change",
              "text": "Eigentlich passt Samstag nicht mit Kaya"})
    msgs.append(gf.u("Festhalten: die Demo ist jetzt fest für den 19."))
    f.append({"id": "demo-fixed-de", "category": "identifier", "text": "die Demo ist jetzt fest für den 19."})
    msgs.append(gf.u("Was habe ich wem noch schuldig?"))
    return msgs, f


def commitment_ledger_ar():
    msgs, f = [], []
    gh.user(msgs, "ساعدني أتذكر كل ما قطعته على نفسي هذا الشهر.")
    f.append({"id": "goal-ar", "category": "goal",
              "text": "ساعدني أتذكر كل ما قطعته على نفسي هذا الشهر"})
    lines = [
        ("أعدك بالاتصال بصاحب المنزل قبل الأحد.", "promise-sahib"),
        ("وعدت كايا بالمساعدة في النقل يوم السبت.", "promise-kaia-ar"),
    ]
    for line, fid in lines:
        msgs.append(gf.u(line))
        plain(msgs, len(msgs))
        f.append({"id": fid, "category": "preference", "text": line})
    pad(msgs, 8)
    msgs.append(gf.u("في الواقع، السبت لا يناسب كايا — أعدتها يوم الأحد."))
    f.append({"id": "kaia-revision-ar", "category": "scope_change",
              "text": "السبت لا يناسب كايا"})
    msgs.append(gf.u("قيد: العرض التقديمي أصبح رسمياً في 19."))
    f.append({"id": "demo-fixed-ar", "category": "identifier",
              "text": "العرض التقديمي أصبح رسمياً في 19"})
    msgs.append(gf.u("ماذا بقي في الذمة؟"))
    return msgs, f


def relative_dates_de():
    msgs, f = [], []
    gh.user(msgs, "Notiere meine Termine diese zwei Wochen — Daten wie man sie sagt.")
    f.append({"id": "goal-de", "category": "goal",
              "text": "Notiere meine Termine diese zwei Wochen"})
    deictic = [
        ("Der Amtstermin ist nächste Woche Donnerstag.", "termin-naechste-woche"),
        ("Die Unterlagen sind in zwei Wochen fällig.", "unterlagen-zwei-wochen"),
        ("Der Klempner kommt übermorgen.", "klempner-uebermorgen"),
    ]
    for i, (line, fid) in enumerate(deictic, start=2):
        msgs.append(gf.u(line))
        msgs.append(gf.a("Notiert."))
        plain(msgs, i)
        f.append({"id": fid, "category": "identifier", "text": line})
        if i == 2:
            msgs.append(gf.u("Eigentlich wurde der Amtstermin auf den Montag danach verschoben."))
            f.append({"id": "termin-moved-de", "category": "scope_change",
                      "text": "Eigentlich wurde der Amtstermin auf den Montag danach verschoben"})
    pad(msgs, 6, 110)
    msgs.append(gf.u("Nochmal mit echten Daten: Amtstermin 2026-11-16, Unterlagen 2026-11-20."))
    f.append({"id": "termin-abs-de", "category": "identifier", "text": "2026-11-16"})
    f.append({"id": "unterlagen-abs-de", "category": "identifier", "text": "2026-11-20"})
    return msgs, f


def relative_dates_tr():
    msgs, f = [], []
    gh.user(msgs, "Randevularımı iki hafta boyunca not et — tarihleri söylendiği gibi.")
    f.append({"id": "goal-tr", "category": "goal",
              "text": "Randevularımı iki hafta boyunca not et"})
    deictic = [
        ("Vize randevusu haftaya perşembe.", "randevu-haftaya"),
        ("Evraklar iki hafta içinde teslim.", "evraklar-iki-hafta"),
        ("Tesisatçı ertesi gün geliyor.", "tesisatci-ertesi-gun"),
    ]
    for i, (line, fid) in enumerate(deictic, start=2):
        msgs.append(gf.u(line))
        msgs.append(gf.a("Not aldım."))
        plain(msgs, i)
        f.append({"id": fid, "category": "identifier", "text": line})
    pad(msgs, 6, 110)
    msgs.append(gf.u("Gerçek tarihlerle: randevu 2026-11-16, evrak teslim 2026-11-20."))
    f.append({"id": "randevu-abs-tr", "category": "identifier", "text": "randevu 2026-11-16"})
    return msgs, f


def multiparty_plan_de():
    msgs, f = [], []
    gh.user(msgs, "Dachterrunden für die Crew planen — wer bringt was, sagtet mir alle Bescheid.")
    f.append({"id": "goal-de", "category": "goal",
              "text": "Dachterrunden für die Crew planen"})
    relay = [
        "Tom sagt, er bringt den Grill und zwei Säcke Kohle.",
        "Maya schreibt: sie kann hosten, ihre Wohnung ist Beispielweg 7.",
        "Jonas sagt, er muss Samstag arbeiten, er kommt Sonntag vorbei.",
        "Petra bietet zwei Salate an, einer vegan.",
    ]
    for i, line in enumerate(relay * 4, start=2):
        msgs.append(gf.u(line))
        msgs.append(gf.a("Eingetragen."))
        plain(msgs, i)
    pad(msgs, len(msgs), len(msgs) + 40)
    msgs.append(gf.u("Maya bestätigt: Samstag 2026-11-14 um 16:00, Beispielweg 7."))
    f.append({"id": "confirm-de", "category": "identifier",
              "text": "Maya bestätigt: Samstag 2026-11-14 um 16:00, Beispielweg 7"})
    f.append({"id": "tom-grill-de", "category": "identifier",
              "text": "Tom sagt, er bringt den Grill"})
    return msgs, f


def advice_session_de():
    msgs, f = [], []
    gh.user(msgs, "Ich habe drei Prüfungen in sechs Wochen und kriege immer Panik. Wie soll ich lernen?",
            "Konkret bitte, damit ich es durchziehen kann.")
    f.append({"id": "goal-de", "category": "goal",
              "text": "Ich habe drei Prüfungen in sechs Wochen und kriege immer Panik"})
    msgs.append(gf.a("Drei Blöcke zu zwei Wochen, ein Fach pro Block. Lerne in "
                     "40-Minuten-Einheiten mit zehn Minuten Pause, und schreibe abends "
                     "eine halbe Seite aus dem Kopf."))
    f.append({"id": "advice-de-struktur", "category": "preference",
              "text": "Drei Blöcke zu zwei Wochen, ein Fach pro Block"})
    pad(msgs, 5, 110)
    msgs.append(gf.u("Das Panik ist morgens am schlimmsten."))
    msgs.append(gf.a("Dann schiebe das schwerste Fach auf den Abend und beginne den "
                     "Morgen mit zehn leichten Karten zum Aufwärmen."))
    f.append({"id": "advice-de-morgen", "category": "preference",
              "text": "Morgen mit zehn leichten Karten zum Aufwärmen"})
    return msgs, f


def name_alias_ar():
    msgs, f = [], []
    gh.user(msgs, "ساعدني في متابعة أشخاص قابلتهم الأسبوع الماضي من الاستوديو.")
    f.append({"id": "goal-ar", "category": "goal",
              "text": "ساعدني في متابعة أشخاص قابلتهم الأسبوع الماضي من الاستوديو"})
    refs = [
        "ليلى من استوديو الشمال أعجبتها دراسة الألوان.",
        "ل. أرسلت رابط تقويم ليوم الخميس.",
        "المرأة من الاستوديو طلبت قائمة الأسعار قبل الجمعة.",
    ]
    for i, line in enumerate(refs, start=2):
        msgs.append(gf.u(line))
        plain(msgs, i)
        f.append({"id": ["alias-full-ar", "alias-initial-ar", "alias-desc-ar"][i - 2],
                  "category": "identifier", "text": line})
    pad(msgs, 6, 110)
    msgs.append(gf.u("ليلى، ل.، المرأة من الاستوديو — كلهم نفس الشخص."))
    f.append({"id": "alias-merge-ar", "category": "identifier",
              "text": "ليلى، ل.، المرأة من الاستوديو"})
    msgs.append(gf.u("اكتب لها رسالة شكر، الموعد الجمعة، على layla@example.de"))
    f.append({"id": "email-late-ar", "category": "identifier", "text": "layla@example.de"})
    return msgs, f


def voice_noise_de():
    msgs, f = [], []
    gh.user(msgs, "ähm ja also — ich soll, quasi, die Zahnspange für Mia nachbestellen, "
                  "ähm die blaue glaub ich, mit den extra Pads? sorry, Sprachnachricht.",
            "und sag Bescheid, ähm, wenn du's hast.")
    f.append({"id": "goal-de-noisy", "category": "goal",
              "text": "ich soll, quasi, die Zahnspange für Mia nachbestellen"})
    pad(msgs, 3, 110)
    msgs.insert(4, gf.u("warte nein, ähm, Korrektur — es ist die grüne, nicht die blaue. "
                        "Bestellnummer ähm 44-77-9."))
    f.append({"id": "voice-corr-de", "category": "scope_change",
              "text": "es ist die grüne, nicht die blaue"})
    f.append({"id": "voice-num-de", "category": "identifier", "text": "44-77-9"})
    msgs.append(gf.u("außerdem ähm, was ich nie abgeschickt hatte: der Kurier muss vor 08:30 da sein "
                     "und der Code fürs Tor ist T9-4410 und ähm die Pads sind Größe M, sorry die "
                     "Nachricht wird einfach länger und länger und endet dann hinter der Wand."))
    f.append({"id": "voice-gate-de", "category": "identifier", "text": "T9-4410"})
    msgs.append(gf.a("Alles klar — die grüne, 44-77-9."))
    return msgs, f


def topic_interleave_mix():
    msgs, f = [], []
    threads = [
        ("visa", "Renew my visa before it lapses on 2026-12-01.", "goal-en"),
        ("noise", "Der Lärm der Werkstatt nach 22 Uhr muss aufhören — ich reiche die Beschwerde ein.", "goal-de"),
        ("gift", "خطط لهدية الذكرى السنوية لحفل الافتتاح.", "goal-ar"),
        ("kargo", "Kargo cuma gününe kadar gelmeli, takip numarası K-33-21.", "goal-tr"),
    ]
    for _, line, fid in threads:
        msgs.append(gf.u(line))
        f.append({"id": fid, "category": "goal", "text": line.split(" —")[0][:70]})
    notes = [
        "The embassy needs the income proof PDF.",
        "Mieter heißt Wehrlein, oberstes Stockwerk.",
        "الميزانية تبقى تحت 400.",
        "Etiket bedeli 45 Euro'yu geçmesin.",
    ]
    for k in range(8):
        for i, line in enumerate(notes):
            msgs.append(gf.u(line))
            plain(msgs, k * 4 + i)
    msgs.append(gf.u("Scope change: die Beschwerde pausiert, fokussiert Visa, Geschenk und Kargo."))
    f.append({"id": "scope-mix", "category": "scope_change",
              "text": "fokussiert Visa, Geschenk und Kargo"})
    f.append({"id": "note-ar", "category": "identifier", "text": "الميزانية تبقى تحت 400"})
    f.append({"id": "note-tr", "category": "identifier", "text": "takip numarası K-33-21"})
    f.append({"id": "note-de", "category": "identifier", "text": "Mieter heißt Wehrlein"})
    return msgs, f


def coding_session_de():
    """Multilingual TECHNICAL session: German intent, English toolchain."""
    msgs, f = [], []
    gh.user(msgs, "Refaktoriere den Billing-Scheduler und deploye den api-gateway danach.")
    f.append({"id": "goal-de-tech", "category": "goal",
              "text": "Refaktoriere den Billing-Scheduler und deploye den api-gateway danach",
              "note": "German task verbs not on _GOAL_TASK_RE — headline multilingual gap"})
    for i in range(2, 60):
        msgs.append(gf.a("Weiter.", [gf.call("read_file", {"path": f"/home/jonas/billing/sched_{i:02d}.py"})]))
        msgs.append(gf.t("read_file", gf.filler(25, "code")))
        if i % 4 == 0:
            msgs.append(gf.a("Ändere was.",
                             [gf.call("patch", {"path": "/home/jonas/billing/scheduler.py",
                                               "old_string": "x", "new_string": "y"})]))
            msgs.append(gf.t("patch", "patched ok"))
        if i % 9 == 0:
            msgs.append(gf.a("Testlauf.", [gf.call("terminal", {"command": "pytest tests/billing -q"})]))
            msgs.append(gf.t("terminal", "40 passed in 3.9s" if i > 30 else "3 failed, 37 passed"))
        if i == 33:
            msgs.append(gf.u("Der Test schlägt fehl, die Währungsumrechnung ist kaputt."))
            f.append({"id": "blocker-de-tech", "category": "blocker",
                      "text": "die Währungsumrechnung ist kaputt",
                      "note": "German blocker words unmached by _BLOCKER_RE — multilingual gap"})
        if i == 55:
            msgs.append(gf.a("Fix steht.",
                             [gf.call("terminal", {"command": 'git commit -m "billing fx fix stage 1"'})]))
            msgs.append(gf.t("terminal", f"[main {format(0xACCE0 + i, '07x')}] billing fx fix stage 1"))
            f.append({"id": "commit-tech", "category": "commit",
                      "text": "billing fx fix stage 1", "hash": format(0xACCE0 + 55, "07x")})
    msgs.append(gf.u("Nochmal auf Englisch zur Sicherheit: refactor the billing scheduler, "
                     "then deploy the api-gateway."))
    f.append({"id": "goal-restated-en", "category": "goal",
              "text": "refactor the billing scheduler",
              "note": "late English restatement — the task verbs do match here; shows the gap is "
                     "the German verbs, not the intent"})
    return msgs, f


def _ledger_lang(prefix, goal, promises, revision, rev_fid, deictic,
                 deictic_fids, late_abs, facts_extra):
    """Shared shape: commitments + revision + deictic dates + late absolute
    restatement + identifier email, authored natively per language."""
    msgs, f = [], []
    msgs.append(gf.u(goal))
    f.append({"id": "goal-" + prefix, "category": "goal", "text": goal.rstrip(".?!")})
    for line, fid in promises:
        msgs.append(gf.u(line))
        plain(msgs, len(msgs))
        f.append({"id": fid, "category": "preference", "text": line})
    pad(msgs, 8)
    msgs.append(gf.u(revision))
    f.append({"id": rev_fid, "category": "scope_change", "text": revision})
    for line, fid in deictic:
        msgs.append(gf.u(line))
        plain(msgs, len(msgs))
        f.append({"id": fid, "category": "identifier", "text": line})
    msgs.append(gf.u(late_abs))
    f.append({"id": "abs-late-" + prefix, "category": "identifier", "text": late_abs[-40:]})
    for line, fid, cat in facts_extra:
        msgs.append(gf.u(line))
        f.append({"id": fid, "category": cat, "text": line})
    return msgs, f


def commitment_ledger_es():
    return _ledger_lang(
        "es",
        "Ayúdame a llevar la cuenta de lo que prometí este mes.",
        [("Prometo llamar al casero antes del lunes.", "promise-casero"),
         ("Le dije a Kaya que la ayudo a mudarse el sábado.", "promise-kaya-es")],
        "En realidad el sábado no va con Kaya — le prometí el domingo.", "kaya-rev-es",
        [("La cita en la oficina es el jueves que viene.", "cita-jueves"),
         ("Los papeles vencen en dos semanas.", "papeles-dos-semanas")],
        ["cita-jueves-fid", "papeles-fid"],
        "Con fechas reales: cita 2026-11-16, papeles 2026-11-20.",
        [("Kaya lo escribe tarde, responde a kaya@ejemplo.es.", "kaya-email-es", "identifier")])


def commitment_ledger_uk():
    return _ledger_lang(
        "uk",
        "Допоможи мені запам'ятати всі обіцянки цього місяця.",
        [("Я обіцяю зателефонувати орендодавцю до понеділка.", "promise-orendodar"),
         ("Я пообіцяв Каяї допомогти з переїздом у суботу.", "promise-kaya-uk")],
        "Насправді субота не підходить Каяї — я пообіцяв неділю.", "kaya-rev-uk",
        [("Візова зустріч наступного четверга.", "zurestcha-chetver"),
         ("Документи потрібні за два тижні.", "dokumenti-dva-tyzhni")],
        ["zurestcha-fid", "dokumenti-fid"],
        "Точні дати: зустріч 2026-11-16, документи 2026-11-20.",
        [("Кая пише пізно — відповідай на kaya@example.ua.", "kaya-email-uk", "identifier")])


def commitment_ledger_sv():
    return _ledger_lang(
        "sv",
        "Hjälp mig hålla koll på allt jag lovat den här månaden.",
        [("Jag lovar att ringa värden före måndag.", "promis-varden"),
         ("Jag sa till Kaya att jag hjälper henne flytta på lördag.", "promis-kaya-sv")],
        "Egentligen funkar inte lördag för Kaya — jag lovade i stället söndag.", "kaya-rev-sv",
        [("Myndighetsmötet är nästa torsdag.", "motet-nasta-torsdag"),
         ("Pappererna ska in om två veckor.", "papper-tva-veckor")],
        ["motet-fid", "papper-fid"],
        "Med riktiga datum: möte 2026-11-16, papper 2026-11-20.",
        [("Kaya skriver sent — svara på kaya@example.se.", "kaya-email-sv", "identifier")])


def commitment_ledger_fi():
    return _ledger_lang(
        "fi",
        "Auta minua muistamaan mitä olen luvannut tässä kuussa.",
        [("Lupaan soittaa isännälle ennen maanantaita.", "lupaus-isanta"),
         ("Sanoin Kayalle auttavani muutossa lauantaina.", "lupaus-kaya-fi")],
        "Oikeastaan lauantai ei käy Kayalle — lupasinkin sunnuntain.", "kaya-rev-fi",
        [("Virastotapaaminen on ensi torstaina.", "tapaaminen-ensi-torstai"),
         ("Asiakirjat erääntyvät kahdessa viikossa.", "asiakirjat-kahdessa")],
        ["tapaaminen-fid", "asiakirjat-fid"],
        "Todelliset päivät: tapaaminen 2026-11-16, asiakirjat 2026-11-20.",
        [("Kaya kirjoittaa myöhään — vastaa osoitteeseen kaya@example.fi.", "kaya-email-fi", "identifier")])


def coding_session_multilingual():
    """Multilingual technical work — native intents across six languages
    around an English toolchain; English toolchain facts must survive while
    non-English verbs expose the pattern gap per language."""
    msgs, f = [], []
    intents = [
        ("Refactoriza el scheduler de facturación.", "intent-es"),
        ("Рефакторі планувальник billing.", "intent-uk"),
        ("Refaktorera schemaläggaren för fakturering.", "intent-sv"),
        ("Uudelleenkirjoita laskutuksen ajastin.", "intent-fi"),
        ("عدّل مجدولة الفوترة وأصلح البوابة.", "intent-ar"),
        ("Refaktoriere den Billing-Scheduler.", "intent-de"),
        ("重构计费调度器。", "intent-zh"),
        ("請求スケジューラをリファクタリングして。", "intent-ja"),
        ("결제 스케줄러를 리팩터링해줘.", "intent-ko"),
    ]
    blockers = [
        ("El test falla, la conversión de moneda está rota.", "blocker-es"),
        ("Тест не проходить, конвертація валюти зламана.", "blocker-uk"),
        ("Testet slår fel, valutakonverteringen är trasig.", "blocker-sv"),
        ("Testi epäonnistuu, valuutan muunnos on rikki.", "blocker-fi"),
        ("测试挂了，汇率转换坏了。", "blocker-zh"),
        ("テストが落ちる、通貨変換が壊れている。", "blocker-ja"),
        ("테스트 실패, 통화 변환이 깨졌어.", "blocker-ko"),
        ("El test falla: INT-9912 en rojo.", "blocker-es-id"),
    ]
    for i in range(2, 60):
        if i % 2 == 0 and i // 2 - 1 < len(intents):
            line, fid = intents[i // 2 - 1]
            msgs.append(gf.u(line))
            f.append({"id": fid, "category": "goal", "text": line.rstrip(".?!")})
        msgs.append(gf.a("Continuing.",
                         [gf.call("patch", {"path": "/home/mila/billing/scheduler.py",
                                           "old_string": "x", "new_string": "y"})]))
        msgs.append(gf.t("patch", "patched ok"))
        if i % 9 == 0:
            msgs.append(gf.a("Run.", [gf.call("terminal", {"command": "pytest tests/billing -q"})]))
            msgs.append(gf.t("terminal", "3 failed, 37 passed" if i < 45 else "40 passed in 4.1s"))
        if i % 7 == 0 and blockers:
            line, fid = blockers.pop(0)
            msgs.append(gf.u(line))
            f.append({"id": fid, "category": "blocker", "text": line})
    msgs.append(gf.a("Committed.", [gf.call("terminal", {"command": 'git commit -m "billing fx multiblock"'})]))
    msgs.append(gf.t("terminal", f"[main {format(0xBEEF0, '07x')}] billing fx multiblock"))
    f.append({"id": "commit-en", "category": "commit",
              "text": "billing fx multiblock", "hash": format(0xBEEF0, "07x")})
    msgs.append(gf.u("To restate for the log: refactor billing scheduler, fix currency conversion, deploy gateway."))
    f.append({"id": "restated-en", "category": "goal",
              "text": "refactor billing scheduler, fix currency conversion, deploy gateway",
              "note": "late English restatement — control for the six native intents"})
    return msgs, f


def commitment_ledger_zh():
    return _ledger_lang(
        "zh",
        "帮我记下这个月答应别人的所有事。",
        [("我答应周一之前给房东打电话。", "promise-fangdong"),
         ("我跟凯娅说周六帮她搬家。", "promise-kaiya")],
        "其实周六凯娅不行 — 我改口答应周日了。", "kaya-rev-zh",
        [("下周四要去大使馆。", "dashi-xiazhou"),
         ("材料两周内交。", "cailiao-liangzhou")],
        ["dashi-fid", "cailiao-fid"],
        "用确切日期再说一遍：2026-11-16 大使馆，2026-11-20 交材料。",
        [("凯娅回信 kaya@example.cn。", "kaya-email-zh", "identifier")])


def commitment_ledger_ja():
    return _ledger_lang(
        "ja",
        "今月約束したことをすべて記録するのを手伝ってください。",
        [("月曜までに大家に電話すると約束した。", "promise-oya"),
         ("土曜にカヤの引っ越しを手伝うと言った。", "promise-kaya-ja")],
        "実は土曜はカヤに合わない — 日曜に約束し直した。", "kaya-rev-ja",
        [("官庁の予約は来週木曜。", "yoyaku-raishu"),
         ("書類は2週間以内。", "shorui-shuukan")],
        ["yoyaku-fid", "shorui-fid"],
        "正確な日付で: 予約 2026-11-16、書類 2026-11-20。",
        [("カヤへの返信は kaya@example.jp に。", "kaya-email-ja", "identifier")])


def commitment_ledger_ko():
    return _ledger_lang(
        "ko",
        "이번 달에 약속한 모든 것을 기억하도록 도와줘.",
        [("월요일까지 집주인에게 전화하기로 약속했어.", "promise-jipju"),
         ("토요일에 카야 이사 돕는다고 했어.", "promise-kaya-ko")],
        "사실 토요일은 카야가 안 돼 — 일요일로 약속을 바꿨어.", "kaya-rev-ko",
        [("관공서 예약은 다음 주 목요일이야.", "yeyak-daeumju"),
         ("서류는 2주 안에 내야 해.", "seoryu-2ju")],
        ["yeyak-fid", "seoryu-fid"],
        "정확한 날짜로: 예약 2026-11-16, 서류 2026-11-20.",
        [("카야 답장은 kaya@example.kr로 보내줘.", "kaya-email-ko", "identifier")])


def cjk_punctuation_probe():
    """clip_sentence breaks on [.!?] only — 。！？ are invisible to it, and
    truncate_words' word tokenizer degrades to raw clip for CJK. A long CJK
    turn ending in an ASCII id past the wall pins both behaviors."""
    msgs, f = [], []
    long_cjk = ("재개발 관련 서류를 준비하고 번역본도 확인해야 한다는 이야기를 여러 번 했는데 "
                * 4) + "요약하면 마감은 다음 주이고 참조 번호 INT-9950입니다。"
    msgs.append(gf.u("总结我的搬家待办事项，涉及租房、运输和押金。"))
    f.append({"id": "goal-zh-cjk", "category": "goal",
              "text": "总结我的搬家待办事项，涉及租房、运输和押金"})
    msgs.append(gf.u(long_cjk))
    f.append({"id": "cjk-past-clip", "category": "identifier", "text": "INT-9950",
              "note": "ASCII id at the far end of a CJK turn — clip_sentence now snaps "
                     "at 。 boundaries (was English-punctuation-blind)"})
    msgs.append(gf.u("要約すると引っ越しは 2026-11-20 に確定。"))
    f.append({"id": "cjk-date-ja", "category": "identifier", "text": "2026-11-20"})
    msgs.append(gf.a("Noted."))
    return msgs, f


BUILDERS = [
    ("commitment-ledger-de", commitment_ledger_de),
    ("commitment-ledger-ar", commitment_ledger_ar),
    ("commitment-ledger-es", commitment_ledger_es),
    ("commitment-ledger-uk", commitment_ledger_uk),
    ("commitment-ledger-sv", commitment_ledger_sv),
    ("commitment-ledger-fi", commitment_ledger_fi),
    ("commitment-ledger-zh", commitment_ledger_zh),
    ("commitment-ledger-ja", commitment_ledger_ja),
    ("commitment-ledger-ko", commitment_ledger_ko),
    ("cjk-punctuation-probe", cjk_punctuation_probe),
    ("coding-session-multilingual", coding_session_multilingual),
    ("relative-dates-de", relative_dates_de),
    ("relative-dates-tr", relative_dates_tr),
    ("multiparty-plan-de", multiparty_plan_de),
    ("advice-session-de", advice_session_de),
    ("name-alias-ar", name_alias_ar),
    ("voice-noise-de", voice_noise_de),
    ("topic-interleave-mix", topic_interleave_mix),
    ("coding-session-de", coding_session_de),
]


if __name__ == "__main__":
    for name, builder in BUILDERS:
        msgs, facts = builder()
        gf.dump(name, msgs, facts, track_commands=["pytest"])
        det, misses = measure_and_annotate(name)
        print(f"{name:22s} facts={len(facts):2d} deterministic={det} "
              f"misses={len(misses)} ({','.join(misses[:4])}{'…' if len(misses) > 4 else ''})")
