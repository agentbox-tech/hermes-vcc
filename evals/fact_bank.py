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
    round: Optional[int] = None      # chain fixtures: which compaction round planted it

    @property
    def weight(self) -> int:
        return WEIGHTS.get(self.category, 1)


def norm(text: str) -> str:
    # language-neutral matching: casefold (folds ß->ss), collapse whitespace,
    # drop Arabic diacritics/tatweel so planted and rendered forms meet.
    text = re.sub(r"[\u064B-\u0652\u0670\u0640]", "", text)
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
    for req in ("name", "facts"):
        if req not in fx:
            raise ValueError(f"{path}: missing key {req!r}")
    if "messages" not in fx and not fx.get("rounds"):
        raise ValueError(f"{path}: needs 'messages' or non-empty 'rounds'")
    for f in fx["facts"]:
        if f.get("category") not in WEIGHTS:
            raise ValueError(f"{path}: fact {f.get('id')} has unknown category {f.get('category')!r}")
    return fx


def parse_facts(fx: Dict[str, Any]) -> List[Fact]:
    return [Fact(id=f["id"], category=f["category"], text=f["text"],
                 hash=f.get("hash"), score=f.get("score", True), note=f.get("note", ""),
                 round=f.get("round"))
            for f in fx["facts"]]


def score(facts: List[Fact], summary_text: str) -> Dict[str, Any]:
    """Weighted recall + per-category (+ per-round, chain fixtures) breakdown."""
    scored = [f for f in facts if f.score]
    total_w = sum(f.weight for f in scored) or 1
    got_w = 0
    misses: List[Dict[str, str]] = []
    per_cat: Dict[str, List[bool]] = {}
    per_round: Dict[int, List[bool]] = {}
    for f in scored:
        hit = recalled(f, summary_text)
        per_cat.setdefault(f.category, []).append(hit)
        if f.round is not None:
            per_round.setdefault(f.round, []).append(hit)
        if hit:
            got_w += f.weight
        else:
            misses.append({"id": f.id, "category": f.category,
                          "known_gap": f.id in KNOWN_GAP_IDS, "text": f.text[:80]})
    cats = {c: {"n": len(h), "recalled": sum(h),
                "recall": round(sum(h) / len(h), 3)} for c, h in per_cat.items()}
    rounds = {str(r): {"n": len(h), "recalled": sum(h),
                       "recall": round(sum(h) / len(h), 3)} for r, h in sorted(per_round.items())}
    out = {
        "recall": round(got_w / total_w, 4),
        "earned_weight": got_w,
        "total_weight": total_w,
        "facts": len(scored),
        "misses": misses,
        "categories": cats,
    }
    if rounds:
        out["rounds"] = rounds
    return out


# SYNTHETIC-ONLY POLICY (Rain, 2026-10-31): the harness never consumes live
# session transcripts. Ground truth = facts planted by gen_fixtures.py /
# gen_big_fixtures.py, matched by the symmetric checker above. Live-session
# economics are measured by scripts/replay_eval.py (replay gate), which
# reports sizes/latency only — never fact claims about real conversations.
