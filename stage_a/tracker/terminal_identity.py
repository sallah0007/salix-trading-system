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

def terminal_notes(lookup_result, records: Iterable, scope=None) -> list:
    """Report strings (RETRIEVAL HINTS ONLY, never an identity-proof encoding: the proof is `resolve_terminal_identity(...).chain_facts/terminal_facts` recomputed from typed rows).
    Starts are typed: noncurrent rows with a survivor pointer, inside `scope=(era_id, instrument, timeframe)` when given, whose survivor has no CURRENT row in the same identity scope. The baseline
    lookup's own UNRESOLVED_CANONICAL_SURVIVOR error only GATES the report (it is not split or parsed for identities, so ids containing commas/colons cannot be lost). Informational: the
    lookup stays fail-closed."""
    recs = list(records)
    if not any(str(e).startswith("UNRESOLVED_CANONICAL_SURVIVOR:") for e in (getattr(lookup_result, "errors", ()) or ())):
        return []
    cur = {(r.feature_id, identity_scope(r)) for r in recs if r.is_current}
    out = []
    for r in sorted(recs, key=full_facts):                                  # deterministic order
        if r.is_current or not r.canonical_survivor or (scope is not None and identity_scope(r) != tuple(scope)):
            continue
        if (r.canonical_survivor, identity_scope(r)) in cur:
            continue                                                        # the narrow lookup resolves this one-hop current survivor itself
        t = resolve_terminal_identity(r, recs)
        out.append("TERMINAL_IDENTITY_HINT:%r>%r:%r:%s" % (t.start_id, t.terminal_id or "-", t.terminal_state or "-", t.status))
    return out
