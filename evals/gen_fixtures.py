#!/usr/bin/env python3
"""Generate the eval fixtures (committed as static JSON next to this file).

Fixtures are synthetic Hermes OpenAI-format transcripts with planted facts:
each fact is echoed in the fixture's `facts` list with its category, so the
scorer never has to guess what should have survived. regenerate with:

    python3 evals/gen_fixtures.py
"""
import json
import os

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
os.makedirs(HERE, exist_ok=True)
ROW = [1000]


def mid():
    ROW[0] += 1
    return ROW[0]


def u(text):
    return {"role": "user", "content": text, "_row_id": mid()}


def a(text=None, calls=None):
    m = {"role": "assistant", "_row_id": mid()}
    if text:
        m["content"] = text
    if calls:
        m["tool_calls"] = calls
    return m


def call(name, args, cid=None):
    return {"id": cid or f"call_{mid()}", "type": "function",
            "function": {"name": name, "arguments": json.dumps(args)}}


def t(name, content):
    return {"role": "tool", "tool_name": name, "content": content, "_row_id": mid()}


def filler(n_lines, tag="out"):
    """Realistic bulk so reduction % measures something real: many-line tool outputs."""
    return "\n".join(f"{tag} line {i:04d}: "
                     "returning buffered data from the worker pool for review and archival"
                     for i in range(n_lines))


def dump(name, messages, facts, track_commands=None, previous_summary=None, description=""):
    fx = {"name": name, "description": description, "messages": messages, "facts": facts}
    if track_commands:
        fx["track_commands"] = track_commands
    if previous_summary:
        fx["previous_summary"] = previous_summary
    path = os.path.join(HERE, name + ".json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(fx, fh, indent=2, ensure_ascii=False)
    print(f"wrote {path} ({len(messages)} msgs, {len(facts)} facts)")


# ──────────────────────────────────────────────────────────── coding-session

def coding_session():
    msgs, f = [], []
    msgs.append(u("Port the OAuth refresh flow into the authgate service and make the existing tests pass."))
    f.append({"id": "goal-1", "category": "goal",
              "text": "Port the OAuth refresh flow into the authgate service"})
    msgs.append(a("I'll map the refresh flow first.",
                 [call("read_file", {"path": "/home/rain/projects/authgate/src/refresh.py"})]))
    msgs.append(t("read_file", "def refresh_token(session):\n    token = session.get('token')\n" + filler(180, "src")))
    f.append({"id": "read-1", "category": "read_file", "text": "src/refresh.py"})
    msgs.append(u("Always use four-space indentation in YAML configs."))
    f.append({"id": "pref-1", "category": "preference",
              "text": "Always use four-space indentation in YAML configs"})
    msgs.append(u("Never push directly to main."))
    f.append({"id": "pref-2", "category": "preference", "text": "Never push directly to main"})
    msgs.append(a("Patching the refresh path.",
                 [call("patch", {"path": "/home/rain/projects/authgate/src/refresh.py",
                                 "old_string": "x", "new_string": "y"})]))
    msgs.append(t("patch", "ok"))
    f.append({"id": "mod-1", "category": "modified_file", "text": "src/refresh.py"})
    msgs.append(a("Writing the client.", [call("write_file", {
        "path": "/home/rain/projects/authgate/src/token_client.py", "content": "..."})]))
    msgs.append(t("write_file", "ok"))
    f.append({"id": "mod-2", "category": "modified_file", "text": "src/token_client.py"})
    msgs.append(a("Capturing the runbook.", [call("write_file", {
        "path": "/home/rain/projects/authgate/docs/runbook.md", "content": "..."})]))
    msgs.append(t("write_file", "ok"))
    f.append({"id": "created-1", "category": "created_file", "text": "docs/runbook.md"})
    msgs.append(a("Committing.",
                 [call("terminal", {"command": 'git add -A && git commit -m "fix token refresh race in middleware"'})]))
    msgs.append(t("terminal", "[main 7c1f40a] fix token refresh race in middleware\n 2 files changed"))
    f.append({"id": "commit-1", "category": "commit",
              "text": "fix token refresh race in middleware", "hash": "7c1f40a"})
    msgs.append(a("Running tests.", [call("terminal", {"command": "pytest tests/test_refresh.py -q"})]))
    msgs.append(t("terminal", "FAILED tests/test_refresh.py::test_race - AssertionError: stale token returned\n1 failed in 0.41s"))
    f.append({"id": "fail-1", "category": "failed_command", "text": "pytest tests/test_refresh.py"})
    msgs.append(a("The refresh middleware still fails the race test — need to serialize the refresh call."))
    f.append({"id": "blocker-1", "category": "blocker", "text": "still fails the race test"})
    msgs.append(u("Leave the trace ID REQ-4471 in the final report."))
    f.append({"id": "ident-1", "category": "identifier", "text": "REQ-4471"})
    long_text = ("Before we continue, note that the compliance reviewer asked for a full audit trail of every "
                 "token mutation in this service, and they will cross-check against ledger exports from the "
                 "billing side later this week, so keep the churn visible. The ticket they filed is REQ-9902.")
    msgs.append(u(long_text))
    f.append({"id": "ident-clipped", "category": "identifier", "text": "REQ-9902",
              "note": "past USER_TEXT_CLIP=256 — known v0 gap"})
    msgs.append(u("Actually, switch to python-jose for the decode step."))
    f.append({"id": "scope-1", "category": "scope_change",
              "text": "switch to python-jose for the decode step"})
    msgs.append(a("Reading the decoder.", [call("read_file", {"path": "/home/rain/projects/authgate/src/decode.py"})]))
    msgs.append(t("read_file", "def decode(jwt): ..."))
    msgs.append(u("Add retry with exponential backoff to the token refresh client."))
    f.append({"id": "goal-2", "category": "goal",
              "text": "Add retry with exponential backoff to the token refresh client"})
    msgs.append(a("Patching decoder.",
                 [call("patch", {"path": "/home/rain/projects/authgate/src/decode.py",
                                 "old_string": "a", "new_string": "b"})]))
    msgs.append(t("patch", "ok"))
    f.append({"id": "mod-3", "category": "modified_file", "text": "src/decode.py"})
    msgs.append(a("Full suite.", [call("terminal", {"command": "pytest tests/test_refresh.py tests/test_decode.py -q"})]))
    msgs.append(t("terminal", "5 passed in 1.02s"))
    f.append({"id": "tracked-1", "category": "tracked_command",
              "text": "pytest tests/test_refresh.py tests/test_decode.py"})
    msgs.append(u("ok"))
    msgs.append(a("Done: retry with backoff is in, full suite green."))
    dump("coding-session", msgs, f, track_commands=["pytest"],
         description="Happy-path coding session: goals, prefs, files, commit, one failure, scope change.")


# ──────────────────────────────────────────────────────────── error-recovery

def error_recovery():
    msgs, f = [], []
    msgs.append(u("Debug why the nightly deploy job crashes on pxl every Sunday."))
    f.append({"id": "goal-1", "category": "goal", "text": "Debug why the nightly deploy job crashes"})
    msgs.append(a("Reproducing.", [call("terminal", {"command": "systemctl --user status deploy-nightly"})]))
    msgs.append(t("terminal", "× deploy-nightly.service - failed with result 'exit-code'"))
    msgs.append(a("The unit fails before the upload step — the token file is missing at run time, so the job cannot authenticate."))
    f.append({"id": "blocker-deep", "category": "blocker_volatile",
              "text": "the token file is missing at run time",
              "note": "deep blocker: Outstanding Context is fresh-only (last 20 blocks)"})
    for i in range(6):
        msgs.append(a(f"Probing step {i}.", [call("terminal", {"command": f"journalctl -u deploy-nightly | tail -{i + 5}"})]))
        msgs.append(t("terminal", "-- logs slice --\n" + filler(35, "journal")))
    msgs.append(a("Failing again.", [call("terminal", {"command": "bash scripts/deploy.sh --dry-run"})]))
    msgs.append(t("terminal", "error: could not lock config file /home/rain/.gitconfig: Permission denied"))
    f.append({"id": "fail-1", "category": "failed_command", "text": "bash scripts/deploy.sh --dry-run"})
    msgs.append(a("Deploy dry-run still fails on the gitconfig lock — that is the blocker to fix."))
    f.append({"id": "blocker-1", "category": "blocker", "text": "still fails on the gitconfig lock"})
    msgs.append(u("Fix it by owning the file mode in the install step."))
    f.append({"id": "goal-2", "category": "goal", "text": "Fix it by owning the file mode in the install step"})
    msgs.append(a("Fix applied.", [call("patch", {"path": "/home/rain/services/deploy-nightly/install.sh",
                                                   "old_string": "x", "new_string": "y"})]))
    msgs.append(t("patch", "ok"))
    f.append({"id": "mod-1", "category": "modified_file", "text": "services/deploy-nightly/install.sh"})
    msgs.append(a("Committing.", [call("terminal", {"command": 'git commit -m "own gitconfig mode in install step"'})]))
    msgs.append(t("terminal", "[main e9b21cc] own gitconfig mode in install step"))
    f.append({"id": "commit-1", "category": "commit", "text": "own gitconfig mode in install step", "hash": "e9b21cc"})
    dump("error-recovery", msgs, f, track_commands=["deploy.sh"],
         description="Error-recovery session: deep blocker (expected drop) + late blocker + failed command + fix.")


# ──────────────────────────────────────────────────────────── preference-heavy

def preference_heavy():
    msgs, f = [], []
    prefs = [
        "Always use four-space indentation in YAML configs.",
        "Never push directly to main.",
        "Always cite line numbers in review comments.",
        "Never use emoji in commit messages.",
        "Always run pytest before declaring done.",
        "Never edit files under vendor without asking.",
        "Always keep changelog entries dated ISO 8601.",
        "Never log tokens or api keys.",
        "Always prefix branch names with feature or fix.",
        "Never delete archived sessions.",
        "Always squash merge small PRs.",
        "Never commit lockfiles by hand.",
    ]
    msgs.append(u("Review the pull request for the exporter rewrite and list every issue you find."))
    f.append({"id": "goal-1", "category": "goal", "text": "Review the pull request for the exporter rewrite"})
    for i, p in enumerate(prefs, 1):
        msgs.append(a(f"Noted, preference {i} registered in my working notes."))
        msgs.append(u(p))
        cat = "preference"
        f.append({"id": f"pref-{i}", "category": cat, "text": p.rstrip(".")})
    msgs.append(a("Review complete: two naming issues and one missing test."))
    dump("preference-heavy", msgs, f,
         description="12 preferences: PREF_CAP=10 trims the header — pref-11/12 survive only as [user] brief lines.")


# ──────────────────────────────────────────────────────────── multi-compact-chain

PREV_SUMMARY = """[Session Goal]
- Rewrite the legacy parser to stream input instead of slurping files

[Files And Changes]
- Modified: legacy/parser.py

[Commits]
- a1b2c3d: add streaming parser core

[User Preferences]
- Always cite line numbers in review comments

[Outstanding Context]
- Parser fails on multi-line strings

---

Compacted turns remain searchable with session_search — query() to search this session's history, or session_id + around_message_id to scroll the full text around any #id reference below. Do not redo work already completed.
"""


def multi_compact_chain():
    msgs, f = [], []
    f.append({"id": "prev-goal", "category": "goal", "text": "Rewrite the legacy parser to stream input",
              "note": "from previous_summary — cumulative merge must keep it"})
    f.append({"id": "prev-commit", "category": "commit", "text": "add streaming parser core", "hash": "a1b2c3d"})
    f.append({"id": "prev-pref", "category": "preference", "text": "Always cite line numbers in review comments"})
    f.append({"id": "prev-blocker", "category": "blocker_volatile", "text": "Parser fails on multi-line strings",
              "note": "Outstanding Context is fresh-only; prev blocker drops by design"})
    msgs.append(u("Keep going on the parser work: add chunked read support now."))
    f.append({"id": "goal-1", "category": "goal", "text": "add chunked read support now"})
    msgs.append(a("Extending.", [call("patch", {"path": "/home/rain/projects/legacy/legacy/parser.py",
                                                 "old_string": "x", "new_string": "y"})]))
    msgs.append(t("patch", "ok"))
    f.append({"id": "mod-prev", "category": "modified_file", "text": "legacy/parser.py",
              "note": "modified in previous compaction; merge must carry it"})
    msgs.append(a("New file for chunking.", [call("write_file", {
        "path": "/home/rain/projects/legacy/legacy/chunks.py", "content": "..."})]))
    msgs.append(t("write_file", "ok"))
    f.append({"id": "mod-1", "category": "modified_file", "text": "legacy/chunks.py"})
    msgs.append(a("Committing.", [call("terminal", {"command": 'git commit -m "chunked read for streaming parser"'})]))
    msgs.append(t("terminal", "[main 4f7aa10] chunked read for streaming parser"))
    f.append({"id": "commit-1", "category": "commit", "text": "chunked read for streaming parser", "hash": "4f7aa10"})
    msgs.append(a("Chunked read still fails the fuzz corpus on nested quotes — needs an escape state."))
    f.append({"id": "blocker-1", "category": "blocker", "text": "still fails the fuzz corpus"})
    dump("multi-compact-chain", msgs, f, previous_summary=PREV_SUMMARY,
         description="Second compaction over a previous_summary: cumulative header merge + volatile Outstanding Context.")


# ──────────────────────────────────────────────────────────── long-cap-session

def long_cap_session():
    msgs, f = [], []
    msgs.append(u("Refactor the billing scheduler pipeline end to end without changing its public contract."))
    f.append({"id": "goal-1", "category": "goal", "text": "Refactor the billing scheduler pipeline end to end"})
    msgs.append(u("Always prefix commit messages with billing: when touching this module."))
    f.append({"id": "pref-early", "category": "preference",
              "text": "Always prefix commit messages with billing"})
    msgs.append(a("Early probe fails.", [call("terminal", {"command": "pytest tests/billing/early_crash.py -q"})]))
    msgs.append(t("terminal", "FAILED tests/billing/early_crash.py::test_import - ModuleNotFoundError"))
    f.append({"id": "fail-early", "category": "failed_command", "text": "pytest tests/billing/early_crash.py",
              "note": "early command: past the brief tail cap; survives via Tracked Commands tail retention"})
    # ~75 rounds × 2 brief lines > BRIEF_MAX_LINES_DEFAULT=120 → tail wins.
    for i in range(75):
        p = f"/home/rain/projects/billing/mod/step_{i:03d}.py"
        if i % 2 == 0:
            msgs.append(a(f"Reading step {i}.", [call("read_file", {"path": p})]))
            msgs.append(t("read_file", f"# step {i}\nclass Step:\n" + filler(60, "mod")))
        else:
            msgs.append(a(f"Patching step {i}.", [call("patch", {"path": p, "old_string": "x", "new_string": "y"})]))
            msgs.append(t("patch", "ok"))
            if i == 21:
                f.append({"id": "mod-mid", "category": "modified_file", "text": "mod/step_021.py",
                         "note": "past FILES_CAP=10 in the header (sorted head keeps step_001..019); survives only via its brief tail line"})
    msgs.append(u("Publish the final refactor as one commit when the suite is green."))
    f.append({"id": "goal-2", "category": "goal",
              "text": "Publish the final refactor as one commit when the suite is green"})
    msgs.append(a("Committing.", [call("terminal", {"command": 'git commit -m "billing: pipeline refactor batch"'})]))
    msgs.append(t("terminal", "[main 81c0ffe] billing: pipeline refactor batch"))
    f.append({"id": "commit-1", "category": "commit",
              "text": "billing: pipeline refactor batch", "hash": "81c0ffe"})
    msgs.append(a("The scheduler tests still fail on timezone rounding in step_044 — that is the open blocker."))
    f.append({"id": "blocker-1", "category": "blocker", "text": "still fail on timezone rounding"})
    dump("long-cap-session", msgs, f, track_commands=["pytest"],
         description="~155 brief lines > cap 120: tail facts survive; early brief facts drop; header-capped files ride the sorted head.")


if __name__ == "__main__":
    ROW[0] = 1000
    coding_session()
    error_recovery()
    preference_heavy()
    multi_compact_chain()
    long_cap_session()
