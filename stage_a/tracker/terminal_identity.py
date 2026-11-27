"""Full-Tracker TERMINAL / TRANSITIVE canonical-identity resolution (Registry candidate s8; frozen Tracker core preserved). Identity-only and REPORT-ONLY.
Source-backed requirement: the Tracker returns the terminal canonical identity AND its governed state, including terminal REJECTED_INVALID / RETIRED / DISCARDED, never a false 'not found';
survivor resolution is transitive, acyclic and terminating. The accepted narrow Type1 semantics are UNCHANGED: `tracker_identity.search.identity_lookup` stays CURRENT-ONLY (one hop, current survivors
only) and noncurrent exacts remain review evidence. This module adds NO lifecycle authority and no state: it reads FeatureIdentity rows the one baseline store already holds.
NO terminal result authorizes a new claim, a resurrection (a noncurrent terminal never becomes current), a delivery or an automatic near-match substitution (`authorizes_*` are constants)."""
from dataclasses import dataclass
from typing import Iterable, Tuple

CURRENT_SURVIVOR, TERMINAL_NONCURRENT = "CURRENT_SURVIVOR", "TERMINAL_NONCURRENT"
CYCLE, ORPHAN, AMBIGUOUS = "SURVIVOR_CYCLE", "SURVIVOR_ORPHAN_DEAD_POINTER", "SURVIVOR_AMBIGUOUS_TERMINAL"
CROSS_SCOPE = "SURVIVOR_CROSS_SCOPE_LINK_UNPROVEN"

# IDENTITY SCOPE of a link = (era_id, instrument, timeframe). `FeatureIdentity.scope` is NOT part of it: that field is the lifecycle bucket (current_active / canonical_survivor_discarded ...),
# which legitimately differs between a retired pointer and its successor. A survivor pointer is a bare feature id with no scope of its own, so it can only be proven against rows in the
# POINTING record's identity scope; a same-id row in another era/instrument/timeframe is a different identity and is never a successor.
def identity_scope(r): return (r.era_id, r.instrument, r.timeframe)
def full_facts(r):
    """The immutable governed facts a terminal result is proven from (not an unqualified id string)."""
    return (r.feature_id, r.feature_version, r.definition_hash, r.graph_hash, r.era_id, r.instrument, r.timeframe, r.scope, str(r.lifecycle_state), bool(r.is_current), r.canonical_survivor or "")

@dataclass(frozen=True)
class TerminalIdentity:
    start_id: str
    status: str
    chain: Tuple[str, ...]            # feature ids from the start through the terminal (or through the last resolvable node)
    terminal_id: str                  # "" when unresolved (cycle / orphan / ambiguous / cross-scope)
    terminal_state: str               # governed lifecycle state of the terminal record; "" when unresolved
    terminal_is_current: bool
    chain_facts: Tuple[tuple, ...] = ()       # full_facts of every resolved hop (start..terminal): lets a reader re-verify the result
    terminal_facts: tuple = ()                # full_facts of the terminal record; () when unresolved
    authorizes_claim = False
    authorizes_resurrection = False
    authorizes_delivery = False
    authorizes_near_match_substitution = False

def resolve_terminal_identity(start, records: Iterable) -> TerminalIdentity:
    """Result is independent of input row order: candidates are filtered to the pointing record's identity scope, identical full-fact duplicates collapse, and ANY disagreement between
    remaining candidates (version/hash/state/currentness/survivor pointer) refuses as AMBIGUOUS instead of choosing the first row."""
    recs = list(records); node = start; chain = [start.feature_id]; facts = [full_facts(start)]; seen = {(start.feature_id, identity_scope(start))}
    def bad(status, extra):
        return TerminalIdentity(start.feature_id, status, tuple(chain) + extra, "", "", False, tuple(facts), ())
    for _ in range(len(recs) + 2):                                       # hard termination bound independent of the data
        if node.is_current or not node.canonical_survivor:
            return TerminalIdentity(start.feature_id, CURRENT_SURVIVOR if node.is_current else TERMINAL_NONCURRENT, tuple(chain),
                                    node.feature_id, str(node.lifecycle_state), bool(node.is_current), tuple(facts), full_facts(node))
        sid, sc = node.canonical_survivor, identity_scope(node)
        if (sid, sc) in seen:
            return bad(CYCLE, (sid,))
        same_id = [r for r in recs if r.feature_id == sid]
        cands = {full_facts(r): r for r in same_id if identity_scope(r) == sc}
        if not cands:
            return bad(CROSS_SCOPE if same_id else ORPHAN, (sid,))          # same id only in a foreign era/instrument/timeframe: linkage unproven, not a dead pointer and not a successor
        if len(cands) > 1:
            return bad(AMBIGUOUS, (sid,))                                   # never pick one of several candidates
        node = next(iter(cands.values())); chain.append(sid); facts.append(full_facts(node)); seen.add((sid, sc))
    return bad(CYCLE, ())

def subject_start_rows(subject, records: Iterable, normalizer) -> list:
    """The NONCURRENT rows that are exact matches of THIS lookup subject, re-derived from typed facts with the same matching rules the baseline lookup applies: the content-identity key
    RECOMPUTED from the subject's declared content (never supplied) for PRE_ID / content-bearing subjects, and the exact canonical key for CANONICAL_ID subjects. No diagnostic text is read,
    and an unrelated row in the same scope is never a start. Any recomputation problem returns [] (nothing is asserted about an unproven subject)."""
    from tracker_identity.content_identity import build_content_identity_key
    from tracker_identity.normalizer import normalize_subject
    from tracker_identity.search import _canonical_matches, _subject_key
    try:
        normalized, _ = normalize_subject(subject, normalizer)
    except ValueError:
        return []
    mode = str(subject.get("subject_mode", "CANONICAL_ID")).strip().upper() or "CANONICAL_ID"
    key = None
    if subject.get("candidate_content") is not None:
        key, errs = build_content_identity_key(subject["candidate_content"])
        if errs:
            key = None
    out = []
    for r in records:
        if r.is_current:
            continue
        by_content = key is not None and r.has_content_key and r.content_key_composite == key.composite
        by_canonical = mode == "CANONICAL_ID" and _canonical_matches(r, _subject_key(normalized))
        if by_content or by_canonical:
            out.append(r)
    return out

def subject_terminal_identities(subject, records: Iterable, normalizer, active_era_id=None, searched_scopes=None) -> Tuple[TerminalIdentity, ...]:
    """Typed, subject-bound terminal results (identity + governed state + full facts) for the lookup subject: one per matching noncurrent row, in a deterministic order. This is what the
    pipeline returns on its Outcome. Report-only: authorizes no claim, resurrection, delivery or near-match substitution, and the narrow lookup stays CURRENT-ONLY and fail-closed."""
    recs = list(records)
    ls = str(subject.get("lookup_era_scope", "ALL_ERAS")).strip().upper() or "ALL_ERAS"
    if ls not in ("ERA_1_ONLY", "ALL_ERAS"):
        return ()                                                       # invalid scope: nothing asserted
    if ls == "ERA_1_ONLY":
        if active_era_id != "ERA_1":
            return ()                                                   # unverified/unsupported active era: fail closed
        recs = [r for r in recs if r.era_id == active_era_id]            # the verified lookup's era bound, not all store rows
    if searched_scopes is not None:
        ss = set(searched_scopes); recs = [r for r in recs if r.scope in ss]   # rows outside the searched scopes are not evidence of anything
    starts = sorted(subject_start_rows(subject, recs, normalizer), key=full_facts)
    return tuple(resolve_terminal_identity(r, recs) for r in starts)
