#!/usr/bin/env python3
"""Human-oriented synthetic fixtures for hermes-vcc evals.

Coding fixtures measure caps against tool-call structure. These measure what
compaction does to CONVERSATION: long emotional back-and-forth, few or zero
tool calls, durable content that is prose, commitments, names and dates
rather than files and commits. The engine's extractor is coding-shaped —
this suite is where that shows up honestly.

All personas and situations are invented (fixture policy: no real personal
details in repo content). Facts are planted as stand-alone lines because
that is what the extractors operate on:
  - goals        any substantive user line, FIRST block wins the head slots
  - preferences  verb whitelist — human-friendly variants on purpose:
                 "prefer …", "don't want", "please keep/avoid …"
  - blockers     LAST 20 blocks only, Capital-start, <=150 chars, plain line
                 (one line per block; [user] lines are prefixed verbatim)
  - identifiers  the REQ-style idiom [A-Z]{2,}-\\d+; ISO dates ride user
                 prose and survive only inside the brief tail — position,
                 not category, decides
  - names        NO extraction surface in v0 — recorded score=False so the
                 gap is documented, and so a future entity extractor gets
                 caught CHANGING these from loss to recall

regenerate: python3 evals/gen_human_fixtures.py
"""
import sys

import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_fixtures as gf  # noqa: E402

HOME = "/home/mika/apartment"  # invented persona "Mika"


def user(msgs, *paras):
    msgs.append(gf.u("\n\n".join(paras)))


def asst(msgs, i, n_sent=2):
    pool = [
        "What would it look like if that went well for you?",
        "Say more about the part that keeps coming back.",
        "That tracks — it makes sense you'd weigh it twice.",
        "What are you hoping they hear underneath the wording?",
        "Where does that leave you today?",
        "It sounds like the timing is doing half the work here.",
        "What would you do if nobody else's read mattered?",
        "Name the part you'd want settled first.",
        "How big is that number next to the whole picture?",
        "And what happens if you simply wait a week?",
    ]
    sents = [pool[(i + k) % len(pool)] for k in range(n_sent)]
    msgs.append(gf.a(" ".join(sents)))


def narr(i):
    """Generic first-person narrative bulk — plausible, weightless, invented."""
    pool = [
        "It keeps circling back to the same two things honestly.",
        "I went over the whole thread again last night.",
        "The paperwork side of it is quieter than I expected.",
        "People around me keep asking and I keep giving short answers.",
        "Some mornings it feels decided and some it doesn't.",
        "I keep drafting open tabs I never finish.",
        "The timing overlaps with everything else on the calendar.",
        "I asked two friends and got opposite answers.",
        "There's a small admin task I keep postponing every day.",
        "Most of it is fine day to day; it's the edges that fray.",
    ]
    return pool[i % len(pool)]


# ───────────────────────────────────────────────────────── email-draft (~55r)

def email_draft():
    msgs, f = [], []
    user(msgs, "Write a firm but friendly email to my landlord about the deposit.",
         "He says part of it went to repainting; the move-out checklist says otherwise.")
    f.append({"id": "goal-1", "category": "goal",
              "text": "Write a firm but friendly email to my landlord about the deposit"})
    msgs.append(gf.a("I can draft that. What tone and length are you aiming for?"))
    msgs.append(gf.a("Drafting now."))
    for i in range(3):
        msgs.append(gf.a("Writing the draft.",
                         [gf.call("write_file" if i == 0 else "patch",
                                  {"path": f"{HOME}/draft_to_landlord.md"})]))
        msgs.append(gf.t("write_file", "Dear Herr Vogel,\n\n"
                         + "\n\n".join(f"Draft paragraph {p:02d}: {narr(i * 10 + p)}"
                                       for p in range(18))
                         + "\n\nKind regards,\nMika"))
        user(msgs, narr(i + 3))
        asst(msgs, i + 1)
    user(msgs, "Please keep it under 150 words.")
    user(msgs, "Never include the word eviction anywhere in it.")
    f.append({"id": "pref-tone", "category": "preference",
              "text": "Please keep it under 150 words"})
    f.append({"id": "pref-eviction", "category": "preference",
              "text": "Never include the word eviction anywhere in it.",
              "note": "own block — extraction is one-pref-per-block; bundled second prefs are dropped"})
    msgs.append(gf.a("Shorter, and the hard word stays out."))
    user(msgs, "My deadline for a reply is 2026-11-20.")
    f.append({"id": "ident-deadline-early", "category": "identifier",
              "text": "2026-11-20", "score": False,
              "note": "round ~6, long past USER_TEXT_CLIP window by fold time"})
    user(msgs, "The heating ticket from last winter still isn't fixed and I don't want to lose that leverage."
               " It's listed as ticket HT-4410 in the portal.")
    f.append({"id": "volatile-heating", "category": "blocker_volatile",
              "text": "The heating ticket from last winter still isn't fixed and I don't want to lose that leverage.",
              "score": False,
              "note": "measured SURVIVOR-in-header despite early placement — 'don't want' hit the pref "
                    "whitelist, so the whole message rode into Preferences (prefs smuggle operational "
                    "facts). unscored: survival is accidental (whitelist), not the fresh-only path probed"})
    f.append({"id": "ident-ticket", "category": "identifier", "text": "HT-4410",
              "score": False,
              "note": "measured survivor-in-header via the same pref-smuggle clip (200c span reaches it)"})
    msgs.append(gf.a("Noted — the heating history is worth one calm line, not a paragraph."))
    for i in range(4, 44):
        msgs.append(gf.a("Revising.",
                         [gf.call("patch", {"path": f"{HOME}/draft_to_landlord.md",
                                           "old_string": "x", "new_string": "y"})]))
        msgs.append(gf.t("patch", "patched draft_to_landlord.md ok\n" + narr(i)))
        user(msgs, narr(i))
        if i == 30:
            # deliberate two-pref block (two LINES, one message): extraction
            # takes one pref per user block, so the second line is dropped
            msgs.append(gf.u("Always keep emoji out of it.\nNever send follow-ups before Friday."))
            f.append({"id": "pref-emoji", "category": "preference",
                      "text": "Always keep emoji out of it.",
                      "note": "first line of its block — extracted to header (whitelist 'always keep')"})
            f.append({"id": "pref-followups", "category": "preference",
                      "text": "Never send follow-ups before Friday.",
                      "score": False,
                      "note": "second LINE of a two-pref block — NOT extracted to header "
                            "(one-pref-per-block rule); survives only verbatim in the brief "
                            "tail, so at bulk past the tail cut it would drop. score=False "
                            "flags the structural fragility, measured: present here at tail."})
        asst(msgs, i)
    msgs.append(gf.a("The portal still rejects attachments over 5 MB, so the photos won't go through."))
    f.append({"id": "blocker-portal", "category": "blocker",
              "text": "The portal still rejects attachments over 5 MB, so the photos won't go through."})
    user(msgs, "Always add my partner to any cc on apartment threads.")
    f.append({"id": "pref-cc", "category": "preference",
              "text": "Always add my partner to any cc on apartment threads",
              "note": "late — also rides the brief tail"})
    asst(msgs, 44)
    user(msgs, "Actually, let's switch the ask to the maintenance deposit instead.")
    f.append({"id": "scope-1", "category": "scope_change",
              "text": "Actually, let's switch the ask to the maintenance deposit instead.",
              "note": "last scope line — lands under [Scope change]"})
    msgs.append(gf.a("Rewriting the ask around the maintenance deposit."))
    user(msgs, "Send it to Herr Vogel.",
            "Reply by 2026-12-04 if I don't confirm first.")
    f.append({"id": "name-vogel", "category": "identifier", "text": "Herr Vogel",
              "score": False,
              "note": "person name — v0 has no entity extractor; MEASURED survivor in the brief "
                    "tail (late 'Send it to Herr Vogel' rides verbatim); not guaranteed by extraction"})
    f.append({"id": "ident-newdeadline", "category": "identifier", "text": "2026-12-04",
              "note": "late — brief tail carries it verbatim"})
    gf.dump("email-draft", msgs, f,
            description="~55-round invented email-drafting session (landlord deposit); prose+files, tone prefs, late scope pivot.")


# ──────────────────────────────────────────────────────── conflict-talk (~90r)

def conflict_talk():
    msgs, f = [], []
    user(msgs, "Help me think through the argument with my flatmate about the studio space.",
         "He books it by habit and I stop asking.")
    f.append({"id": "goal-1", "category": "goal",
              "text": "Help me think through the argument with my flatmate about the studio space"})
    msgs.append(gf.a("Okay. What does a fair week of studio time look like to you?"))
    for i in range(1, 88):
        if i == 10:
            user(msgs, "I'd prefer a quiet conversation over a group call.")
            user(msgs, "I don't want an apology out of anyone, I want the calendar to work.")
            f.append({"id": "pref-quiet", "category": "preference",
                      "text": "I'd prefer a quiet conversation over a group call."})
            f.append({"id": "pref-apology", "category": "preference",
                      "text": "I don't want an apology out of anyone, I want the calendar to work.",
                      "note": "separate block — one-pref-per-block rule drops a bundled second"})
        elif i == 20:
            user(msgs, "Please keep Ines out of it.",
                 "She hasn't answered my last message and that silence is the part I can't fix.")
            f.append({"id": "pref-ines", "category": "preference",
                      "text": "Please keep Ines out of it.",
                      "note": "whitelist 'please keep'; header survivor"})
            f.append({"id": "volatile-silence", "category": "blocker_volatile",
                      "text": "She hasn't answered my last message and that silence is the part I can't fix.",
                      "score": False, "note": "round 20 — outside last-20-block scan; expected drop"})
            f.append({"id": "name-ines", "category": "identifier", "text": "Ines",
                      "score": False,
                      "note": "no entity extractor, but MEASURED survivor-in-header — embedded in the "
                            "extracted pref 'Please keep Ines out of it' (name rides the pref clause)"})
        elif i == 60:
            user(msgs, "Marek keeps copying everyone on the lease group and it reopens the fight.")
            f.append({"id": "name-marek", "category": "identifier", "text": "Marek",
                      "score": False,
                      "note": "no entity extractor; MEASURED survivor in the brief tail (round 60 of 87 "
                            "still inside the tail window) — would drop at greater bulk"})
        elif i == 84:
            user(msgs, "I always keep Sunday mornings unplanned, so propose that slot.")
            f.append({"id": "pref-sunday", "category": "preference",
                      "text": "I always keep Sunday mornings unplanned, so propose that slot.",
                      "note": "late — header + tail"})
        elif i == 86:
            user(msgs, "The shared calendar invite still won't work and that is the open issue.")
            f.append({"id": "blocker-calendar", "category": "blocker",
                      "text": "The shared calendar invite still won't work and that is the open issue.",
                      "note": "late — inside last-20-block scan"})
        elif i == 87:
            user(msgs, "Let's write the talking points for Thursday 2026-11-08.")
            f.append({"id": "ident-meetdate", "category": "identifier",
                      "text": "2026-11-08", "note": "late — brief tail"})
        user(msgs, narr(i))
        asst(msgs, i, n_sent=3)
    gf.dump("conflict-talk", msgs, f,
            description="~90-round zero-tool mediation conversation (invented flatmate dispute); names vs extractors, fresh-only blockers.")


# ────────────────────────────────────────────────────── life-decision (~120r)

def life_decision():
    msgs, f = [], []
    user(msgs, "I'm deciding whether to move to Lisbon for the research fellowship.",
         "Two years, his contract is here, and the fellowship may not knock twice.")
    f.append({"id": "goal-1", "category": "goal",
              "text": "I'm deciding whether to move to Lisbon for the research fellowship"})
    msgs.append(gf.a("What does each version of the next two years feel like when you say it out loud?"))
    for i in range(1, 118):
        if i == 8:
            user(msgs, "Rent there runs 1150 euro, and the stipend barely clears it with the visa fees."
                      " My application number is FP-7781.")
            f.append({"id": "ident-app-early", "category": "identifier", "text": "FP-7781",
                      "score": False, "note": "round 8 — REQ-idiom id planted early; pre-tail drop"})
            f.append({"id": "volatile-insurance", "category": "blocker_volatile",
                      "text": "The insurance transfer still doesn't work online and the office only opens after nine.",
                      "score": False, "note": "early — outside the last-20-block scan"})
            msgs.append(gf.a("The insurance office window is annoying but small next to the ship-question."))
        elif i == 30:
            user(msgs, "Please keep the budget under 1600 euro per month, all in.")
            f.append({"id": "pref-budget", "category": "preference",
                      "text": "Please keep the budget under 1600 euro per month, all in."})
        elif i == 55:
            user(msgs, "Never send me drafts on Sundays; that's when I stop thinking clearly.")
            f.append({"id": "pref-sunday", "category": "preference",
                      "text": "Never send me drafts on Sundays; that's when I stop thinking clearly."})
        elif i == 80:
            user(msgs, "Always include my partner in lease decisions, even the small ones.")
            f.append({"id": "pref-partner", "category": "preference",
                      "text": "Always include my partner in lease decisions, even the small ones."})
        elif i == 100:
            user(msgs, "The visa portal is still blocked for new appointment requests.")
            f.append({"id": "blocker-visa", "category": "blocker",
                      "text": "The visa portal is still blocked for new appointment requests.",
                      "note": "round 100 of 118 — inside last-20 scan at fold"})
        elif i == 112:
            user(msgs, "Reference number for the housing allowance is HA-90210.")
            f.append({"id": "ident-allow", "category": "identifier", "text": "HA-90210",
                      "note": "late REQ-idiom id — survives if inside tail window"})
        elif i == 116:
            user(msgs, "Actually, the plan now is to defer the move and stay one more year.")
            f.append({"id": "scope-1", "category": "scope_change",
                      "text": "Actually, the plan now is to defer the move and stay one more year.",
                      "note": "last scope line — [Scope change] section"})
        user(msgs, narr(i))
        asst(msgs, i, n_sent=3)
    gf.dump("life-decision", msgs, f,
            description="~118-round invented major-decision conversation (Lisbon fellowship); prose-only, late ids, defer-pivot.")


if __name__ == "__main__":
    email_draft()
    conflict_talk()
    life_decision()
