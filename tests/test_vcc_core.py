"""Pure-logic tables for vcc_core (no disk, no hermes imports, no wall clock)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "engine"))

import vcc_core as vcc  # noqa: E402


def msg(role, content=None, _id=None, tool_calls=None, tool_name=None):
    m = {"role": role, "content": content}
    if _id is not None:
        m["_row_id"] = _id
    if tool_calls:
        m["tool_calls"] = tool_calls
    if tool_name:
        m["tool_name"] = tool_name
    return m


def tc(call_id, name, arguments):
    return {"id": call_id, "type": "function",
            "function": {"name": name, "arguments": arguments}}


# ── clip / clip_sentence: pure string-in/verdict-out ──────────────────

@pytest.mark.parametrize("text,max_len,expected", [
    ("short", 10, "short"),
    ("a" * 50, 20, "a" * 20),
    ("word " * 10, 12, "word word"),      # word boundary above 60%
    ("no spaces here at all", 10, "no spaces"),  # fallback hard cut
])
def test_clip(text, max_len, expected):
    assert vcc.clip(text, max_len) == expected


@pytest.mark.parametrize("text,max_len,suffix_ok", [
    ("Do the thing. Then more text follows here", 20, "Do the thing."),
    ("No terminator at all keeps clipping", 12, False),
])
def test_clip_sentence(text, max_len, suffix_ok):
    out = vcc.clip_sentence(text, max_len)
    if suffix_ok:
        assert out == suffix_ok
    else:
        assert len(out) <= max_len


# ── noise filtering ─────────────────────────────────────────────────────

@pytest.mark.parametrize("content,kept", [
    ("[System: compacted]", False),
    ("[CONTEXT COMPACTION — REFERENCE ONLY] blah", False),
    ("Cronjob Response: did the thing", False),
    ("real user request here", True),
    ("   ", False),
    ("<memory-context>hint</memory-context>", False),          # wrapper-only → empty
    ("<memory-context>hint</memory-context> real ask", True),
])
def test_synthetic_user_rows(content, kept):
    blocks = vcc.filter_noise(vcc.normalize([msg("user", content, _id=1)]))
    assert bool(blocks) is kept


def test_noise_tools_dropped():
    blocks = vcc.normalize([
        msg("assistant", "", tool_calls=[tc("c1", "todo_list", "{}")]),
        msg("tool", "[]", tool_name="todo_list", _id=2),
    ])
    assert vcc.filter_noise(blocks) == []


# ── goals ───────────────────────────────────────────────────────────────

def test_first_user_message_is_the_goal():
    out = vcc.extract_goals(vcc.normalize([msg("user", "Fix the auth bug in login", _id=1)]))
    assert out == ["Fix the auth bug in login"]


def test_scope_change_detected():
    blocks = vcc.normalize([
        msg("user", "Build the dashboard widget", _id=1),
        msg("assistant", "Working on it.", _id=2),
        msg("user", "actually instead make it a CLI tool", _id=3),
    ])
    goals = vcc.extract_goals(blocks)
    assert "[Scope change]" in goals
    assert any("CLI tool" in g for g in goals)


@pytest.mark.parametrize("content", ["ok", "thanks!", "y", "hey"])
def test_short_noise_never_a_goal(content):
    assert vcc.extract_goals(vcc.normalize([msg("user", content, _id=1)])) == []


def test_template_signal_truncates():
    blocks = vcc.normalize([msg("user", "Review the PR\nFor each issue:\nRead it in full", _id=1)])
    goals = vcc.extract_goals(blocks)
    assert goals and not any("Read it in full" in g for g in goals)


# ── preferences ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("line,captured", [
    ("Always run tests before committing", True),
    ("Never send email on my behalf", True),
    ("Prefer dense messages", True),
    ("What time is it?", False),          # question
    ("I pushed the change", False),       # no preference construction
])
def test_preference_patterns(line, captured):
    prefs = vcc.extract_preferences(vcc.normalize([msg("user", line, _id=1)]))
    assert bool(prefs) is captured


def test_one_pref_per_block():
    blocks = vcc.normalize([msg("user", "Always use tabs. Never use spaces.", _id=1)])
    assert len(vcc.extract_preferences(blocks)) == 1


# ── files ─────────────────────────────────────────────────────────────────

def test_file_categories_and_prefix_trim():
    blocks = vcc.normalize([
        msg("assistant", "", tool_calls=[tc("c1", "read_file", '{"path":"/home/rain/app/src/auth/a.ts"}')]),
        msg("assistant", "", tool_calls=[tc("c2", "write_file", '{"path":"/home/rain/app/src/util/b.ts","content":"x"}')]),
        msg("assistant", "", tool_calls=[tc("c3", "patch", '{"path":"/home/rain/app/src/util/c.ts"}')]),
    ])
    act = vcc.extract_files(blocks)
    assert act["read"] == {"auth/a.ts"}
    assert act["modified"] == {"util/b.ts", "util/c.ts"}
    # pi semantics: write_file lands in modified AND created, then dedup
    # (created -= modified) empties created; it survives only via hook
    # fileOps, which the v1 host seam does not provide.
    assert act["created"] == set()


def test_modified_supersedes_created():
    blocks = vcc.normalize([
        msg("assistant", "", tool_calls=[tc("c1", "write_file", '{"path":"/x/y.py","content":"a"}')]),
    ])
    act = vcc.extract_files(blocks)
    lines = vcc.format_file_activity(act)
    assert any(l.startswith("Modified:") for l in lines)
    assert not any(l.startswith("Created:") for l in lines)


# ── commits ───────────────────────────────────────────────────────────────

def test_commit_single_quote_and_hash():
    blocks = vcc.normalize([
        msg("assistant", "", tool_calls=[tc("c1", "terminal",
            '{"command":"git commit -m \'fix(auth): refresh token\'"}')]),
        msg("tool", "[master 4125d3f] fix(auth): refresh token", tool_name="terminal", _id=2),
    ])
    commits = vcc.extract_commits(blocks)
    assert commits == [("4125d3f", "fix(auth): refresh token")]
    assert vcc.format_commits(commits) == ["4125d3f: fix(auth): refresh token"]


def test_non_commit_bash_ignored():
    blocks = vcc.normalize([
        msg("assistant", "", tool_calls=[tc("c1", "terminal", '{"command":"git status"}')]),
    ])
    assert vcc.extract_commits(blocks) == []


# ── outstanding context ───────────────────────────────────────────────────

def test_blocker_detected_only_recent_and_like_sentences():
    blocks = vcc.normalize([
        msg("assistant", "The lint check is still failing on line 42 here", _id=1),
        msg("assistant", "All good, tests pass.", _id=2),
    ])
    out = vcc.extract_outstanding_context(blocks)
    assert len(out) == 1
    assert "lint" in out[0]


# ── tracked commands ──────────────────────────────────────────────────────

def test_tracked_commands_bucket_and_touch():
    blocks = vcc.normalize([
        msg("assistant", "", tool_calls=[tc("c1", "terminal", '{"command":"ssh box0 uptime"}')]),
        msg("assistant", "", tool_calls=[tc("c2", "terminal", '{"command":"kubectl get pods"}')]),
        msg("assistant", "", tool_calls=[tc("c3", "terminal", '{"command":"ssh box0 free -m"}')]),
    ])
    buckets = vcc.extract_tracked_commands(blocks, ["ssh", "kubectl"])
    assert len(buckets["ssh"]) == 2
    lines = vcc.format_tracked_commands(buckets)
    assert any(line.startswith("ssh:") for line in lines)


def test_tracked_off_by_default():
    blocks = vcc.normalize([
        msg("assistant", "", tool_calls=[tc("c1", "terminal", '{"command":"ssh box0"}')]),
    ])
    assert vcc.extract_tracked_commands(blocks, []) == {}


# ── refs / refs fail-closed ──────────────────────────────────────────────

def test_refs_use_row_ids_and_missing_id_renders_no_ref():
    blocks = vcc.normalize([
        msg("user", "do the thing", _id=42),
        msg("user", "no id here"),
    ])
    lines = vcc.build_brief_lines(vcc.filter_noise(blocks))
    assert "(#42)" in lines[0]
    assert "#" not in lines[1]


# ── format / caps / merge ────────────────────────────────────────────────

def test_cap_brief_head_omission_marker():
    text = "\n".join(f"line {i}" for i in range(130))
    out = vcc.cap_brief(text, 120)
    assert out.startswith("...(10 earlier lines omitted)")
    assert out.endswith("line 129")


def test_cap_items_head_and_tail():
    items = [str(i) for i in range(15)]
    assert vcc.cap_items(items, 10).endswith("(+5 more)")
    assert vcc.cap_items(items, 10, ", ", "tail").startswith("(+5 earlier) 5")


def test_merge_dedups_goals_and_survives_wrap():
    prev = "[Session Goal]\n- First goal item\n\n---\n\n[user] old ask\n\n" + vcc.RECALL_NOTE
    fresh = "[Session Goal]\n- First goal item\n- Second goal\n\n---\n\n[user] newer ask"
    merged = vcc.merge_sections(prev, fresh)
    assert merged.count("- First goal item") == 1
    assert "- Second goal" in merged
    assert merged.count("session_search") == 1  # note stripped then re-added once


def test_merge_volatile_outstanding_fresh_only():
    prev = "[Outstanding Context]\n- Old lint failure persists here"
    fresh = "[Outstanding Context]\n- New blocker remains broken"
    merged = vcc.merge_sections(prev, fresh)
    assert "Old lint" not in merged and "New blocker" in merged


def test_files_union_across_merge():
    prev = "[Files And Changes]\n- Modified: a.py, b.py"
    fresh = "[Files And Changes]\n- Modified: b.py, c.py"
    merged = vcc.merge_sections(prev, fresh)
    assert "a.py" in merged and "c.py" in merged


# ── compile end-to-end ────────────────────────────────────────────────────

def test_compile_pure_noise_is_empty_fail_closed():
    turns = [msg("user", "[System: compacted]", _id=1), msg("user", "ok", _id=2)]
    assert vcc.compile_summary(turns) == ""


def test_compile_structure_and_note():
    turns = [
        msg("user", "Fix the auth bug in login flow", _id=101),
        msg("assistant", "Root cause: token refresh missing.", _id=102,
            tool_calls=[tc("c1", "terminal", '{"command":"git commit -m \'fix: token\'"}')]),
        msg("tool", "[main abc1234] fix: token", tool_name="terminal", _id=103),
    ]
    out = vcc.compile_summary(turns)
    assert out.startswith("[Session Goal]")
    assert "abc1234: fix: token" in out
    assert out.count("session_search") == 1
    assert "SUMMARY_PREFIX" not in out  # engine adds host prefix, core never does


def test_compile_repeated_merge_does_not_stack_note():
    turns = [msg("user", "Fix the auth bug please", _id=1)]
    s1 = vcc.compile_summary(turns)
    s2 = vcc.compile_summary(turns, s1)
    s3 = vcc.compile_summary(turns, s2)
    assert s3.count("session_search") == 1


# ── determinism: pure function, same bytes ───────────────────────────────

def test_compile_is_deterministic():
    turns = [
        msg("user", "Build a widget and deploy it", _id=1),
        msg("assistant", "Working.", _id=2,
            tool_calls=[tc("c1", "write_file", '{"path":"/home/rain/w/x.py","content":"print()"}')]),
        msg("tool", "ok", tool_name="write_file", _id=3),
        msg("user", "Always run the linter first", _id=4),
    ]
    assert vcc.compile_summary(turns) == vcc.compile_summary(turns)
