"""Fact model + symmetric scoring for hermes-vcc evals (Grist 72).

A fixture carries a list of planted facts extracted from the FULL transcript
(ground truth). Every candidate summary — vcc pure-compile, vcc engine, or
the baseline LLM summary — is scored with the SAME checker, so neither side
gets a parsing advantage (pi-vcc benchmark methodology, adapted).

Matching is normalized substring, not embeddings:
  * whitespace collapsed, casefolded
  * path facts tolerate the engine's common-directory-prefix trim by also
    matching the trailing two path segments
  * commit facts require BOTH the short hash and the subject when a hash is
    known — the pair is the durable unit

Weights follow pi-vcc's "losing an error state hurts more than losing an
ls" doctrine, re-cut for Hermes tool shapes.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

WEIGHTS: Dict[str, int] = {
    "failed_command": 6,   # error state is the most critical to carry forward
    "commit": 5,           # durable history; the handoff record of done-work
    "modified_file": 4,
    "goal": 4,
    "scope_change": 4,
    "preference": 4,
    "blocker": 4,
    "blocker_volatile": 4, # deep/early blocker: drop is EXPECTED (fresh-only policy)
    "created_file": 3,
    "tracked_command": 2,
    "identifier": 2,
    "read_file": 1,
}

PATH_CATS = {"modified_file", "created_file", "read_file"}

# Facts whose loss is a documented v0 behavior; they are scored (so the floor
# is measured, not hoped for) but flagged in the report as known gaps.
KNOWN_GAP_IDS = {
    # user text beyond USER_TEXT_CLIP: the identifier sits past the 256-char
    # user-line clip, so it cannot appear in the brief.
    "ident-clipped",
}


@dataclass
class Fact:
    id: str
    category: str
    text: str
    hash: Optional[str] = None       # commit facts: short hash paired with subject
    score: bool = True               # False = diagnostic only (not in recall)
    note: str = ""

    @property
    def weight(self) -> int:
        return WEIGHTS.get(self.category, 1)


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _path_recalled(path: str, hay: str) -> bool:
    p = norm(path)
    if p in hay:
        return True
    parts = [s for s in path.split("/") if s]
    if len(parts) >= 2:
        return "/".join(parts[-2:]).casefold() in hay
    return parts and parts[-1].casefold() in hay


def recalled(fact: Fact, summary_text: str) -> bool:
    hay = norm(summary_text)
    if fact.category == "commit":
        subject_ok = norm(fact.text) in hay
        if fact.hash:
            return subject_ok and norm(fact.hash) in hay
        return subject_ok
    if fact.category in PATH_CATS:
        return _path_recalled(fact.text, hay)
    # commands/identifiers/free text: substring; commands render inside the
    # brief quoted, so compare on the normalized substring directly.
    return norm(fact.text) in hay


def load_fixture(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        fx = json.load(fh)
    for req in ("name", "messages", "facts"):
        if req not in fx:
            raise ValueError(f"{path}: missing key {req!r}")
    for f in fx["facts"]:
        if f.get("category") not in WEIGHTS:
            raise ValueError(f"{path}: fact {f.get('id')} has unknown category {f.get('category')!r}")
    return fx


def parse_facts(fx: Dict[str, Any]) -> List[Fact]:
    return [Fact(id=f["id"], category=f["category"], text=f["text"],
                 hash=f.get("hash"), score=f.get("score", True), note=f.get("note", ""))
            for f in fx["facts"]]


def score(facts: List[Fact], summary_text: str) -> Dict[str, Any]:
    """Weighted recall + per-category breakdown over scored facts."""
    scored = [f for f in facts if f.score]
    total_w = sum(f.weight for f in scored) or 1
    got_w = 0
    misses: List[Dict[str, str]] = []
    per_cat: Dict[str, List[bool]] = {}
    for f in scored:
        hit = recalled(f, summary_text)
        per_cat.setdefault(f.category, []).append(hit)
        if hit:
            got_w += f.weight
        else:
            misses.append({"id": f.id, "category": f.category,
                          "known_gap": f.id in KNOWN_GAP_IDS, "text": f.text[:80]})
    cats = {c: {"n": len(h), "recalled": sum(h),
                "recall": round(sum(h) / len(h), 3)} for c, h in per_cat.items()}
    return {
        "recall": round(got_w / total_w, 4),
        "earned_weight": got_w,
        "total_weight": total_w,
        "facts": len(scored),
        "misses": misses,
        "categories": cats,
    }


# ───────────────────────────────── real-session symmetric extractor (--real)
# Deliberately generic text-level extraction over raw OpenAI-format messages:
# the same strings the engine extracts, parsed independently, matched as
# substrings against any candidate summary.

_COMMIT_RE = re.compile(r"git\s+commit[^\n]*?-m\s+\"((?:[^\"\\]|\\.)*)\"")
_FAIL_RE = re.compile(r"\b(FAILED|error:|Traceback|fatal:)\b", re.I)


def extract_real_facts(messages: List[Dict[str, Any]], cap_per_cat: int = 20) -> List[Fact]:
    """Ground-truth facts from a raw session transcript (no engine code)."""
    buckets: Dict[str, List[Fact]] = {c: [] for c in
        ("modified_file", "created_file", "read_file", "commit", "failed_command")}
    n = 0
    for i, m in enumerate(messages):
        if not isinstance(m, dict):
            continue
        n += 1
        if m.get("role") == "assistant":
            for call in m.get("tool_calls") or []:
                fn = (call or {}).get("function") or {}
                name = str(fn.get("name") or "").lower()
                raw = fn.get("arguments")
                try:
                    args = json.loads(raw) if isinstance(raw, str) else (raw or {})
                except ValueError:
                    args = {}
                if not isinstance(args, dict):
                    args = {}
                path = args.get("path") or args.get("file_path") or ""
                if not isinstance(path, str) or not path:
                    continue
                cat = None
                if name == "read_file":
                    cat = "read_file"
                elif name in ("patch",):
                    cat = "modified_file"
                elif name == "write_file":
                    cat = "created_file"
                if cat and len(buckets[cat]) < cap_per_cat:
                    buckets[cat].append(Fact(f"real-{cat}-{n}", cat, path))
            for call in m.get("tool_calls") or []:
                fn = (call or {}).get("function") or {}
                if str(fn.get("name") or "").lower() not in ("terminal", "execute_code"):
                    continue
                raw = fn.get("arguments")
                try:
                    args = json.loads(raw) if isinstance(raw, str) else (raw or {})
                except ValueError:
                    args = {}
                cmd = str((args or {}).get("command") or (args or {}).get("code") or "")
                cm = _COMMIT_RE.search(cmd)
                if cm and len(buckets["commit"]) < cap_per_cat:
                    subject = cm.group(1).replace('\\"', '"').split("\n")[0].strip()
                    h = None
                    for j in range(i + 1, min(len(messages), i + 4)):
                        nxt = messages[j]
                        if isinstance(nxt, dict) and nxt.get("role") == "tool":
                            hm = re.search(r"\[\S+\s+([0-9a-f]{7,12})\]", str(nxt.get("content") or ""))
                            if hm:
                                h = hm.group(1)
                                break
                    if subject:
                        buckets["commit"].append(Fact(f"real-commit-{n}", "commit", subject[:60], hash=h))
        if m.get("role") == "tool" and _FAIL_RE.search(str(m.get("content") or "")):
            j = i - 1
            while j >= 0:
                pj = messages[j]
                if isinstance(pj, dict) and pj.get("role") == "assistant" and pj.get("tool_calls"):
                    call = pj["tool_calls"][0]
                    fn = (call or {}).get("function") or {}
                    if str(fn.get("name") or "").lower() in ("terminal", "execute_code"):
                        raw = fn.get("arguments")
                        try:
                            args = json.loads(raw) if isinstance(raw, str) else (raw or {})
                        except ValueError:
                            args = {}
                        cmd = str((args or {}).get("command") or (args or {}).get("code") or "").strip()
                        if cmd and len(buckets["failed_command"]) < cap_per_cat:
                            buckets["failed_command"].append(
                                Fact(f"real-fail-{i}", "failed_command", cmd[:40]))
                    break
                j -= 1
    out: List[Fact] = []
    for b in buckets.values():
        out.extend(b)
    return out
