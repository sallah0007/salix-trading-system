"""Non-transitive speculation (Annex V1.2 §A; Q21). Effective speculative depth > 1 over the dependency closure fails
closed BEFORE a candidate exists."""
from dataclasses import dataclass
from typing import Tuple
from ..errors import Refusal

CANONICAL_ONLY, ONE_HOP = "CANONICAL_ONLY", "ONE_HOP_NON_SPECULATIVE_SOURCE_STAGE"

@dataclass(frozen=True)
class StagedCandidate:
    candidate_id: str
    input_speculation_class: str
    transitive_speculation_depth: int
    staged_inputs: Tuple[str, ...] = ()        # ids of staged candidates used as inputs
    all_content_inputs_publishable: bool = True

def admit(candidate: StagedCandidate, known: dict):
    """known: candidate_id -> StagedCandidate (already admitted). Raises Refusal; returns candidate."""
    c = candidate
    if c.transitive_speculation_depth not in (0, 1):
        raise Refusal("depth must be 0 or 1", code="DEPTH_OUT_OF_RANGE")
    if c.input_speculation_class not in (CANONICAL_ONLY, ONE_HOP):
        raise Refusal(c.input_speculation_class, code="UNKNOWN_SPECULATION_CLASS")
    if c.input_speculation_class == CANONICAL_ONLY and c.staged_inputs:
        raise Refusal("CANONICAL_ONLY cannot reference staged inputs", code="STAGED_INPUT_UNDECLARED")
    if c.input_speculation_class == ONE_HOP and not c.staged_inputs:
        raise Refusal("ONE_HOP without a staged input", code="ONE_HOP_NO_INPUT")
    for sid in c.staged_inputs:
        src = known.get(sid)
        if src is None:
            raise Refusal(sid, code="STAGED_INPUT_UNKNOWN")           # fail closed on the unread
        if src.transitive_speculation_depth != 0 or not src.all_content_inputs_publishable:
            raise Refusal(sid, code="SPECULATIVE_SOURCE_NOT_ELIGIBLE")
    if c.staged_inputs and c.transitive_speculation_depth != 1:
        raise Refusal("a candidate consuming a staged input is itself depth 1", code="DEPTH_UNDERSTATED")
    if c.candidate_id in known:
        raise Refusal(c.candidate_id, code="DUPLICATE_CANDIDATE")
    return c

def effective_depth(candidate_id, known):
    """Independent recomputation over the closure (cycle-safe): used to cross-check declared depth."""
    seen = set()
    def go(i):
        if i in seen: raise Refusal(i, code="CYCLE")
        seen.add(i)
        c = known[i]
        d = max([go(s) for s in c.staged_inputs], default=-1) + 1 if c.staged_inputs else 0
        seen.discard(i)
        return d
    return go(candidate_id)
