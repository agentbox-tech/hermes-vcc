"""Algorithmic compaction core — port of pi-vcc (https://github.com/sting8k/pi-vcc, MIT).

Pure string/data processing over OpenAI-format Hermes messages: normalize -> noise
filter -> section extraction -> brief transcript -> format -> merge-with-previous.
No LLM calls, no filesystem, no Hermes imports (the engine in __init__.py wires
this to the host and applies host redaction first). Retuned from pi's message shape
(bashExecution/toolResult) to Hermes OpenAI shape (assistant.tool_calls + role=tool),
with pi tool names replaced by Hermes ones.

#N refs in rendered output are DB message ids (fail-closed: a message without an
id renders no ref), so the host's session_search scroll consumes them directly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

# ──────────────────────────────────────────────────────────────────── tuning

BRIEF_MAX_LINES_DEFAULT = 120
WRAP_WIDTH = 120
GOAL_CAP = 8
PREF_CAP = 10
FILES_CAP = 10
COMMITS_CAP = 8
OUTSTANDING_CAP = 5
USER_TEXT_CLIP = 256
ASSISTANT_HEAD_WORDS = 80
ASSISTANT_TAIL_WORDS = 120

RECALL_NOTE = (
    "Compacted turns remain searchable with session_search — query() to search "
    "this session's history, or session_id + around_message_id to scroll the "
    "full text around any #id reference below. Do not redo work already completed."
)

SEPARATOR = "\n\n---\n\n"
HEADER_NAMES = (
    "Session Goal",
    "Files And Changes",
    "Commits",
    "Tracked Commands",
    "Outstanding Context",
    "User Preferences",
)

# ──────────────────────────────────────────────────────── hermes tool maps

# pi's bashExecution becomes role="tool" in Hermes; command text lives in the
# assistant tool_call arguments. Names are matched case-insensitively.
BASH_TOOLS = {"terminal", "execute_code"}
FILE_READ_TOOLS = {"read_file"}
FILE_WRITE_TOOLS = {"write_file", "patch"}
FILE_CREATE_TOOLS = {"write_file"}
NOISE_TOOLS = {"todo_list", "tool_search", "clarify", "text_to_speech"}

# Synthetic user rows the host injects mid-conversation: never goals/preferences.
# The engine overrides this with the host's canonical tuple when importable.
DEFAULT_SYNTHETIC_USER_PREFIXES = (
    "[System:", "[CONTEXT", "[PRIOR CONTEXT", "[IMPORTANT: Background",
    "[Your active task list", "[Planning state preserved", "[ASYNC DELEGATION",
    "[OUT-OF-BAND", "Cronjob Response:",
)

# Wrapper blocks injected into user messages whose content is background data,
# not user intent. <memory-context> is Hermes-specific (memory provider injection).
_XML_BLOCK_RE = re.compile(
    r"<(memory-context|system-reminder|ide_opened_file|command-message|system_note)"
    r"[^>]*>[\s\S]*?</\1>",
)

# ───────────────────────────────────────────────────────────── content utils


def _text_of(content: Any) -> str:
    if not content:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    return ""


def _image_types(content: Any) -> List[str]:
    if not isinstance(content, list):
        return []
    return [
        str(part.get("mime_type") or part.get("mimeType") or "image")
        for part in content
        if isinstance(part, dict) and part.get("type") == "image"
    ]


def clip(text: str, max_len: int = 200) -> str:
    if len(text) <= max_len:
        return text
    cut = text.rfind(" ", 0, max_len)
    end = cut if cut > max_len * 0.6 else max_len
    return text[:end]


def clip_sentence(text: str, max_len: int = 200) -> str:
    if len(text) <= max_len:
        return text
    matches = list(re.finditer(r"[.!?](?:\s|$)", text[:max_len]))
    if matches:
        end = matches[-1].end()
        if end >= max_len * 0.5:
            return text[:end].rstrip()
    return clip(text, max_len)


def non_empty_lines(text: str) -> List[str]:
    return [line.strip() for line in text.split("\n") if line.strip()]


def clean_user_text(text: str) -> str:
    return _XML_BLOCK_RE.sub("", text).strip()


_STOP_WORDS = frozenset("""
a an the is are was were be been being have has had do does did will would could
should may might shall can need must to of in for on with at by from as into
through during before after above below between under over and but or nor not so
yet both either neither each every all any few more most other some such no that
this these those it its i me my we our you your he him his she her they them
their who which what if then than when where how just also
""".split())


def truncate_words(text: str, limit: int) -> str:
    """Truncate to `limit` non-stopword words (whitespace tokenizer; CJK falls back to raw clip)."""
    flat = re.sub(r"\s+", " ", text).strip()
    words = flat.split(" ")
    if len(words) <= limit:
        return flat
    count, out = 0, []
    for word in words:
        if re.search(r"[A-Za-z0-9\u00c0-\uffff]", word) \
                and word.lower().strip(".,;:!?\"'`()[]{}") not in _STOP_WORDS:
            count += 1
            if count > limit:
                return " ".join(out).rstrip() + "…(truncated)"
        out.append(word)
    return flat


# ───────────────────────────────────────────────────────────────── normalize


@dataclass
class Block:
    kind: str  # user | assistant | tool_call | tool_result
    text: str = ""
    name: str = ""
    args: Dict[str, Any] = field(default_factory=dict)
    source_id: Optional[int] = None  # DB message id -> (#N) refs


def _tool_call_name(call: Any) -> str:
    if not isinstance(call, dict):
        return ""
    fn = call.get("function")
    if isinstance(fn, dict):
        return str(fn.get("name") or "")
    return str(call.get("name") or "")


def _tool_call_args(call: Any) -> Dict[str, Any]:
    if not isinstance(call, dict):
        return {}
    fn = call.get("function")
    raw = fn.get("arguments") if isinstance(fn, dict) else call.get("arguments")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            import json
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {"_raw": raw}
        except (ValueError, TypeError):
            return {"_raw": raw}
    return {}


def normalize(messages: List[Dict[str, Any]]) -> List[Block]:
    blocks: List[Block] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        # Host stamps DB ids as _row_id after persistence; id/`#N` refs read
        # it first so refs are consumable by session_search even pre-sanitize.
        msg_id = msg.get("_row_id", msg.get("id"))
        msg_id = int(msg_id) if isinstance(msg_id, int) or (
            isinstance(msg_id, str) and msg_id.isdigit()) else None
        if role == "user":
            text = _text_of(msg.get("content"))
            blocks.append(Block("user", text=text, source_id=msg_id))
            for mime in _image_types(msg.get("content")):
                blocks.append(Block("user", text=f"[image: {mime}]", source_id=msg_id))
        elif role == "assistant":
            text = _text_of(msg.get("content"))
            if text.strip():
                blocks.append(Block("assistant", text=text, source_id=msg_id))
            for call in msg.get("tool_calls") or []:
                blocks.append(Block(
                    "tool_call", name=_tool_call_name(call),
                    args=_tool_call_args(call), source_id=msg_id))
        elif role == "tool":
            name = str(msg.get("tool_name") or "")
            blocks.append(Block(
                "tool_result", text=_text_of(msg.get("content")),
                name=name, source_id=msg_id))
    return blocks


def filter_noise(blocks: List[Block],
                synthetic_prefixes: Tuple[str, ...] = DEFAULT_SYNTHETIC_USER_PREFIXES) -> List[Block]:
    out: List[Block] = []
    for b in blocks:
        if b.kind == "tool_call" and b.name.lower() in NOISE_TOOLS:
            continue
        if b.kind == "tool_result" and b.name.lower() in NOISE_TOOLS:
            continue
        if b.kind == "user":
            stripped = clean_user_text(b.text)
            if not stripped:
                continue
            if stripped.lstrip().startswith(synthetic_prefixes):
                continue
            if _NOISE_SHORT_RE.match(stripped):
                continue  # bare acknowledgments carry no transcript signal
            out.append(Block("user", text=stripped, source_id=b.source_id))
            continue
        out.append(b)
    return out


# ──────────────────────────────────────────────────────────────── extractors

_GOAL_TASK_RE = re.compile(
    r"\b(fix|implement|add|create|build|refactor|debug|investigate|update|remove|"
    r"delete|migrate|deploy|test|write|set up|port|install|configure)\b", re.I)
_GOAL_SCOPE_RE = re.compile(
    r"\b(instead|actually|change of plan|forget that|new task|switch to|now I want|"
    r"pivot|let'?s do|stop .* and)\b", re.I)
_NOISE_SHORT_RE = re.compile(
    r"^(ok|yes|no|sure|yeah|yep|go|hi|hey|thx|thanks|y|n|k)\s*[.!?]*$", re.I)
_NON_GOAL_RE = re.compile(
    r"^\s*[\[│├└─╭╰]|```|^\s*(function |const |let |var |import |export |class )|"
    r"^(https?:|file:|/[A-Za-z])|^\s*For each\b")
_TEMPLATE_SIGNAL_RE = re.compile(
    r"^\s*(For each\b|Do NOT implement\b|Analyze and propose\b|Output:\s*$)", re.I)

_MAX_GOAL_CHARS = 200


def _is_substantive_goal(text: str) -> bool:
    t = text.strip()
    if not (5 < len(t) <= _MAX_GOAL_CHARS):
        return False
    return not _NOISE_SHORT_RE.match(t) and not _NON_GOAL_RE.search(t)


def extract_goals(blocks: List[Block]) -> List[str]:
    goals: List[str] = []
    latest_scope: Optional[List[str]] = None
    for b in blocks:
        if b.kind != "user":
            continue
        lines = non_empty_lines(b.text)
        idx = next((i for i, l in enumerate(lines) if _TEMPLATE_SIGNAL_RE.match(l)), None)
        if idx is not None:
            lines = lines[:idx]
        lines = [re.sub(r"^\s*(?:[-*+]|\d+\.)\s+", "", l)
                 for l in lines if _is_substantive_goal(l)]
        lines = [l for l in lines if len(l) > 5]
        if not lines:
            continue
        if not goals:
            goals.extend(lines[:6])
            continue
        leading = b.text[:200]
        if _GOAL_SCOPE_RE.search(leading):
            latest_scope = [clip(l, _MAX_GOAL_CHARS) for l in lines[:3]]
        elif _GOAL_TASK_RE.search(leading) and len(lines[0]) > 15:
            latest_scope = [clip(l, _MAX_GOAL_CHARS) for l in lines[:2]]
    if latest_scope:
        goals.append("[Scope change]")
        goals.extend(latest_scope)
    return goals[:GOAL_CAP]


_PREF_PATTERNS = [
    re.compile(r"\bprefer(?:s|red|ring)?\s+\w", re.I),
    re.compile(r"\bdon'?t want\b", re.I),
    re.compile(r"\balways (?:use|do|run|prefer|keep|make|format|write|add|set|put|"
               r"prefix|start|include|append|respond|reply)\b", re.I),
    re.compile(r"\bnever (?:use|do|run|push|commit|write|ignore|add|set|put|remove|"
               r"delete|include|deploy|send|email)\b", re.I),
    re.compile(r"\bplease (?:use|avoid|keep|make|don'?t|do not|format|write)\b", re.I),
    re.compile(r"\b(?:style|format|language|naming)\s*[:=]\s*\S", re.I),
]


def extract_preferences(blocks: List[Block]) -> List[str]:
    prefs: List[str] = []
    seen: Set[str] = set()
    for b in blocks:
        if b.kind != "user":
            continue
        per_block = 0
        for line in non_empty_lines(b.text):
            if not (5 <= len(line) <= 200):
                continue
            if line.endswith("?") or "?..." in line:
                continue
            if not any(p.search(line) for p in _PREF_PATTERNS):
                continue
            clipped = clip(line, 200)
            key = clipped.lower()
            if key in seen:
                continue
            seen.add(key)
            prefs.append(clipped)
            per_block += 1
            if per_block >= 1:
                break
    return prefs[:PREF_CAP]


def dedup_prefs_against_goals(prefs: List[str], goals: List[str]) -> List[str]:
    goal_set = {g.strip().lower() for g in goals}
    return [p for p in prefs if p.strip().lower() not in goal_set]


_BLOCKER_RE = re.compile(
    r"\b(fail(?:ed|s|ure|ing)?|broken|cannot|can't|won't work|does not work|"
    r"doesn't work|still (?:broken|failing|wrong)|blocked|blocker|"
    r"not (?:fixed|resolved|working)|crash(?:es|ed|ing)?)\b", re.I)


def extract_outstanding_context(blocks: List[Block]) -> List[str]:
    items: List[str] = []
    for b in blocks[-20:]:
        if b.kind not in ("assistant", "user"):
            continue
        for line in non_empty_lines(b.text):
            if not _BLOCKER_RE.search(line) or len(line) < 15:
                continue
            if re.match(r"^\s*[-*+>]\s", line) or re.match(r"^\s*\(", line):
                continue
            if not re.match(r"^\s*[\"'`*_]?[A-Z`]", line):
                continue
            clipped = f"[user] {clip_sentence(line, 150)}" if b.kind == "user" else clip_sentence(line, 150)
            if clipped not in items:
                items.append(clipped)
            break
    return items[:OUTSTANDING_CAP]


def _extract_path(args: Dict[str, Any]) -> str:
    for key in ("path", "file", "file_path", "target", "oldPath", "path_match"):
        val = args.get(key)
        if isinstance(val, str) and val:
            return val
    return ""


def _longest_common_dir_prefix(paths: List[str]) -> str:
    abs_paths = [p for p in paths if p.startswith("/")]
    if len(abs_paths) < 2:
        return ""
    split = [p.split("/") for p in abs_paths]
    min_len = min(len(s) for s in split)
    i = 0
    while i < min_len - 1:
        seg = split[0][i]
        if not all(s[i] == seg for s in split):
            break
        i += 1
    if i < 2:
        return ""
    return "/".join(split[0][:i]) + "/"


def extract_files(blocks: List[Block]) -> Dict[str, Set[str]]:
    act: Dict[str, Set[str]] = {"read": set(), "modified": set(), "created": set()}
    for b in blocks:
        if b.kind != "tool_call":
            continue
        path = _extract_path(b.args)
        if not path:
            continue
        name = b.name.lower()
        if name in FILE_READ_TOOLS:
            act["read"].add(path)
        if name in FILE_WRITE_TOOLS:
            act["modified"].add(path)
        if name in FILE_CREATE_TOOLS:
            act["created"].add(path)
    for path in act["modified"]:
        act["created"].discard(path)
    prefix = _longest_common_dir_prefix([*act["read"], *act["modified"], *act["created"]])
    if prefix:
        for cat in act.values():
            trimmed = {p[len(prefix):] if p.startswith(prefix) else p for p in cat}
            cat.clear()
            cat.update(trimmed)
    return act


def format_file_activity(act: Dict[str, Set[str]]) -> List[str]:
    def cap(items: List[str]) -> str:
        if len(items) <= FILES_CAP:
            return ", ".join(items)
        return ", ".join(items[:FILES_CAP]) + f" (+{len(items) - FILES_CAP} more)"
    lines = []
    for cat, label in (("modified", "Modified"), ("created", "Created"), ("read", "Read")):
        if act[cat]:
            lines.append(f"{label}: {cap(sorted(act[cat]))}")
    return lines


_COMMIT_MSG_RE = re.compile(
    r"git\s+commit[^\n]*?-m\s+(?:\"((?:[^\"\\]|\\.)*)\"|'((?:[^'\\]|\\.)*)')")
_HEREDOC_OPEN_RE = re.compile(r"(?<![\w)])<<-?\s*[\"']?([A-Za-z_]\w*)[\"']?")


def _command_of(b: Block) -> str:
    cmd = b.args.get("command") or b.args.get("code") or ""
    return cmd if isinstance(cmd, str) else ""


def extract_commits(blocks: List[Block]) -> List[Tuple[Optional[str], str]]:
    commits: List[Tuple[Optional[str], str]] = []
    for i, b in enumerate(blocks):
        if b.kind != "tool_call" or b.name.lower() not in BASH_TOOLS:
            continue
        cmd = _command_of(b)
        if not re.search(r"\bgit\s+commit\b", cmd):
            continue
        m = _COMMIT_MSG_RE.search(cmd)
        if not m:
            continue
        raw = next((g for g in m.groups() if g is not None), "")
        message = raw.replace('\\"', '"').replace("\\'", "'").split("\n")[0].strip()
        if not message and raw:
            # heredoc: git commit -m "$(cat <<EOF ... )" — first body line
            h = _HEREDOC_OPEN_RE.search(cmd[m.end() - 10:])
            if h:
                delim = h.group(1)
                rest = cmd[m.end():]
                for line in rest.split("\n"):
                    trimmed = line.strip().lstrip("\t")
                    if trimmed == delim:
                        break
                    if trimmed:
                        message = trimmed
                        break
        if not message:
            continue
        hash_: Optional[str] = None
        for j in range(i + 1, min(len(blocks), i + 4)):
            r = blocks[j]
            if r.kind != "tool_result":
                continue
            mm = (re.search(r"\[\S+\s+([0-9a-f]{7,12})\]", r.text)
                  or re.search(r"\b([0-9a-f]{7,12})\b", r.text))
            if mm:
                hash_ = mm.group(1)
                break
        key = f"{hash_ or ''}::{message}"
        if not any(f"{h or ''}::{msg}" == key for h, msg in commits):
            commits.append((hash_, message))
    return commits


def format_commits(commits: List[Tuple[Optional[str], str]]) -> List[str]:
    return [f"{h}: {msg}" if h else msg for h, msg in commits[-COMMITS_CAP:]]


_TRACKED_COMMANDS_PER_NAME = 10
_TRACKED_SEP = " ;; "


def _command_name(cmd: str) -> str:
    """First word past sudo/env/VAR= prefixes — the tracked bucket name."""
    tokens = cmd.strip().split()
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in ("sudo", "env", "doas"):
            i += 1
            continue
        if re.match(r"^[A-Za-z_]\w*=", t):
            i += 1
            continue
        return t
    return ""


def extract_tracked_commands(blocks: List[Block], track_commands: List[str]) -> Dict[str, List[str]]:
    if not track_commands:
        return {}
    buckets: Dict[str, List[str]] = {}
    for b in blocks:
        if b.kind != "tool_call" or b.name.lower() not in BASH_TOOLS:
            continue
        cmd = _command_of(b).strip()
        if not cmd:
            continue
        name = _command_name(cmd)
        if name not in track_commands and not any(
                cmd.startswith(t) or name == t for t in track_commands):
            continue
        bucket = buckets.setdefault(name, [])
        entry = clip(cmd, 240)
        if entry in bucket:
            bucket.remove(entry)
        bucket.append(entry)  # touch-on-dup: most recent last
        if len(bucket) > _TRACKED_COMMANDS_PER_NAME:
            del bucket[0]
    return buckets


def format_tracked_commands(buckets: Dict[str, List[str]]) -> List[str]:
    return [f"{name}: {_TRACKED_SEP.join(cmds)}" for name, cmds in buckets.items() if cmds]


# ──────────────────────────────────────────────────────────────────── brief


def _ref(b: Block) -> str:
    return f" (#{b.source_id})" if b.source_id is not None else ""


def build_brief_lines(blocks: List[Block]) -> List[str]:
    """Chronological brief transcript; each tool call one line with a (#id) ref."""
    lines: List[str] = []
    for b in blocks:
        if b.kind == "user":
            text = clip(re.sub(r"\s+", " ", b.text).strip(), USER_TEXT_CLIP)
            if text:
                lines.append(f"[user] {text}{_ref(b)}")
        elif b.kind == "assistant":
            text = truncate_words(b.text, ASSISTANT_HEAD_WORDS + ASSISTANT_TAIL_WORDS)
            if text:
                lines.append(f"[assistant] {text}{_ref(b)}")
        elif b.kind == "tool_call":
            cmd = _command_of(b) if b.name.lower() in BASH_TOOLS else ""
            path = _extract_path(b.args)
            target = clip(cmd or path, 200) if (cmd or path) else ""
            suffix = f" \"{target}\"" if target else ""
            lines.append(f"* {b.name}{suffix}{_ref(b)}")
    return lines


# ─────────────────────────────────────────────────────────────────── format


def wrap_long_lines(text: str, max_chars: int = WRAP_WIDTH) -> str:
    out: List[str] = []
    for line in text.split("\n"):
        if len(line) <= max_chars:
            out.append(line)
            continue
        indent_m = re.match(r"^\s*(?:[-*]\s+|\d+\.\s+)?", line)
        indent = indent_m.group(0) if indent_m else ""
        cont = " " * min(len(indent), 8) if indent else ""
        remaining = line
        prefix = ""
        while len(prefix) + len(remaining) > max_chars:
            avail = max(20, max_chars - len(prefix))
            cut = remaining.rfind(" ", 0, avail)
            if cut < avail * 0.5:
                cut = avail
            out.append(prefix + remaining[:cut].rstrip())
            remaining = remaining[cut:].lstrip()
            prefix = cont
        if remaining:
            out.append(prefix + remaining)
    return "\n".join(out)


def cap_items(items: List[str], limit: int, join_with: str = ", ", keep: str = "head") -> str:
    if len(items) <= limit:
        return join_with.join(items)
    over = len(items) - limit
    if keep == "tail":
        return f"(+{over} earlier) " + join_with.join(items[-limit:])
    return join_with.join(items[:limit]) + f" (+{over} more)"


def strip_cap_marker(text: str) -> str:
    return re.sub(r"^\s*\(\+\d+ earlier\)\s*", "",
                  re.sub(r"\s*\(\+\d+ (?:more|earlier)\)\s*$", "", text))


def cap_brief(text: str, max_lines: int = BRIEF_MAX_LINES_DEFAULT) -> str:
    lines = text.split("\n")
    if len(lines) <= max_lines:
        return text
    omitted = len(lines) - max_lines
    kept = lines[-max_lines:]
    first_header = next((i for i, l in enumerate(kept) if re.match(r"^\[.+\]", l)), None)
    if first_header is not None and first_header > 0:
        omitted += first_header
        kept = kept[first_header:]
    return f"...({omitted} earlier lines omitted)\n\n" + "\n".join(kept)


def section(title: str, items: List[str]) -> str:
    if not items:
        return ""
    return f"[{title}]\n" + "\n".join(f"- {item}" for item in items)


def format_summary(sections: Dict[str, List[str]], brief: str,
                  cap_brief_transcript: bool = True) -> str:
    header_parts = [section(name, sections.get(name, [])) for name in HEADER_NAMES]
    header_parts = [h for h in header_parts if h]
    parts = []
    if header_parts:
        parts.append("\n\n".join(header_parts))
    if brief:
        parts.append(cap_brief(brief) if cap_brief_transcript else brief)
    if not parts:
        return ""
    return wrap_long_lines(SEPARATOR.join(parts))


# ───────────────────────────────────────────────────────────── merge-previous


def section_of(text: str, header: str) -> str:
    tag = f"[{header}]"
    start = text.find(tag)
    if start < 0:
        return ""
    after = text[start:]
    candidates = [i for i in (after.find(f"[{h}]") for h in HEADER_NAMES if h != header) if i > 0]
    sep = after.find(SEPARATOR)
    if sep > 0:
        candidates.append(sep)
    end = min(candidates) if candidates else len(after)
    return after[:end].strip()


def brief_of(text: str) -> str:
    idx = text.find(SEPARATOR)
    return text[idx + len(SEPARATOR):].strip() if idx >= 0 else ""


def _strip_recall_note(text: str) -> str:
    pattern = r"\n*(?:---\n+)?" + r"\s+".join(re.escape(w) for w in RECALL_NOTE.split()) + r"\n*"
    return re.sub(pattern, "\n\n", text).rstrip()


def _merge_categorized(categories: List[str], prev: str, fresh: str,
                      split_on: str, touch_on_dup: bool = False) -> Dict[str, List[str]]:
    merged: Dict[str, List[str]] = {c: [] for c in categories}
    seen: Dict[str, Set[str]] = {c: set() for c in categories}
    for text in (prev, fresh):
        for line in text.split("\n"):
            for cat in categories:
                prefix = f"- {cat}: "
                if not line.startswith(prefix):
                    continue
                rest = strip_cap_marker(line[len(prefix):])
                for item in rest.split(split_on):
                    item = item.strip()
                    if not item:
                        continue
                    if item in seen[cat]:
                        if touch_on_dup:
                            merged[cat].remove(item)
                        else:
                            continue
                    seen[cat].add(item)
                    merged[cat].append(item)
    return merged


def _discover_categories(text: str) -> List[str]:
    seen: List[str] = []
    for line in text.split("\n"):
        m = re.match(r"^- ([^:]+): ", line)
        if m and m.group(1) not in seen:
            seen.append(m.group(1))
    return seen


def merge_sections(prev: str, fresh: str) -> str:
    """Merge a previous summary with a fresh one: per-section dedup + re-cap."""
    merged_headers: List[str] = []
    for header in HEADER_NAMES:
        fresh_sec = section_of(fresh, header)
        # prev went through wrap_long_lines — rejoin continuation lines first.
        prev_sec = re.sub(r"\n[ \t]+(?=\S)", " ", section_of(prev, header))
        if header == "Outstanding Context":  # volatile: fresh only
            merged = fresh_sec
        elif not prev_sec:
            merged = fresh_sec
        elif not fresh_sec:
            merged = prev_sec
        elif header == "Files And Changes":
            cats = ["Modified", "Created", "Read"]
            merged_map = _merge_categorized(cats, prev_sec, fresh_sec, ", ")
            merged_map["Modified"] = [p for p in merged_map["Modified"]]
            mod_set = set(merged_map["Modified"])
            merged_map["Created"] = [p for p in merged_map["Created"] if p not in mod_set]
            lines = [f"- {cat}: {cap_items(merged_map[cat], FILES_CAP)}"
                     for cat in cats if merged_map[cat]]
            merged = f"[{header}]\n" + "\n".join(lines) if lines else ""
        elif header == "Tracked Commands":
            prev_cats = _discover_categories(prev_sec)
            cats = prev_cats + [c for c in _discover_categories(fresh_sec) if c not in prev_cats]
            merged_map = _merge_categorized(cats, prev_sec, fresh_sec, _TRACKED_SEP,
                                            touch_on_dup=True)
            lines = ["- {}: {}".format(cat, cap_items(merged_map[cat], _TRACKED_COMMANDS_PER_NAME,
                                                      _TRACKED_SEP, "tail"))
                     for cat in cats if merged_map[cat]]
            merged = f"[{header}]\n" + "\n".join(lines) if lines else ""
        else:  # Session Goal, Commits, User Preferences: line-level dedup + tail cap
            prev_lines = [l for l in prev_sec.split("\n") if l.startswith("- ")]
            fresh_lines = [l for l in fresh_sec.split("\n") if l.startswith("- ")]
            combined = list(dict.fromkeys(prev_lines + fresh_lines))
            cap = 8 if header in ("Session Goal", "Commits") else 15
            capped = combined[-cap:] if len(combined) > cap else combined
            if capped:
                merged = f"[{header}]\n" + "\n".join(capped)
            else:
                merged = ""
        if merged:
            merged_headers.append(merged)

    prev_brief, fresh_brief = brief_of(prev), brief_of(fresh)
    merged_brief = ""
    if prev_brief or fresh_brief:
        fresh_lines = fresh_brief.count("\n") + 1 if fresh_brief else 0
        budget = max(0, BRIEF_MAX_LINES_DEFAULT - fresh_lines)
        prev_tail = cap_brief(prev_brief, budget) if prev_brief and budget else ""
        merged_brief = f"{prev_tail}\n\n{fresh_brief}" if prev_tail else cap_brief(fresh_brief)

    parts = []
    if merged_headers:
        parts.append("\n\n".join(merged_headers))
    if merged_brief:
        parts.append(merged_brief)
    return SEPARATOR.join(parts)


# ──────────────────────────────────────────────────────────────────── compile

@dataclass
class VccOptions:
    brief_max_lines: int = BRIEF_MAX_LINES_DEFAULT
    track_commands: Tuple[str, ...] = ()
    synthetic_user_prefixes: Tuple[str, ...] = DEFAULT_SYNTHETIC_USER_PREFIXES


def compile_summary(messages: List[Dict[str, Any]], previous_summary: Optional[str] = None,
                    options: Optional[VccOptions] = None) -> str:
    """Compact `messages` into the structured summary body (no SUMMARY_PREFIX —
    the engine wraps). Returns "" when nothing could be extracted (fail-closed:
    the host then routes its deterministic fallback)."""
    opts = options or VccOptions()
    blocks = filter_noise(normalize(messages), opts.synthetic_user_prefixes)
    if not blocks:
        return ""

    goals = extract_goals(blocks)
    prefs = dedup_prefs_against_goals(extract_preferences(blocks), goals)
    sections_map = {
        "Session Goal": goals,
        "Files And Changes": format_file_activity(extract_files(blocks)),
        "Commits": format_commits(extract_commits(blocks)),
        "Tracked Commands": format_tracked_commands(
            extract_tracked_commands(blocks, list(opts.track_commands))),
        "Outstanding Context": extract_outstanding_context(blocks),
        "User Preferences": prefs,
    }
    brief = "\n".join(cap_brief_lines(build_brief_lines(blocks), opts.brief_max_lines))
    fresh = format_summary(sections_map, brief, cap_brief_transcript=False)
    if not fresh:
        return ""

    if previous_summary:
        merged = merge_sections(_strip_recall_note(previous_summary), fresh)
    else:
        merged = fresh
    if not merged:
        return ""
    return wrap_long_lines(merged + SEPARATOR + RECALL_NOTE)


def cap_brief_lines(lines: List[str], max_lines: int) -> List[str]:
    return lines[-max_lines:] if len(lines) > max_lines else lines
