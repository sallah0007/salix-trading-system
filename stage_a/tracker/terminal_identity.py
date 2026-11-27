"""Full-Tracker TERMINAL / TRANSITIVE canonical-identity resolution (Registry candidate s8; frozen Tracker core preserved). Identity-only and REPORT-ONLY.
Source-backed requirement: the Tracker returns the terminal canonical identity AND its governed state, including terminal REJECTED_INVALID / RETIRED / DISCARDED, never a false 'not found';
survivor resolution is transitive, acyclic and terminating. The accepted narrow Type1 semantics are UNCHANGED: `tracker_identity.search.identity_lookup` stays CURRENT-ONLY (one hop, current survivors
only) and noncurrent exacts remain review evidence. This module adds NO lifecycle authority and no state: it reads FeatureIdentity rows the one baseline store already holds.
NO terminal result authorizes a new claim, a resurrection (a noncurrent terminal never becomes current), a delivery or an automatic near-match substitution (`authorizes_*` are constants)."""
from dataclasses import dataclass
from typing import Iterable, Tuple

CURRENT_SURVIVOR, TERMINAL_NONCURRENT = "CURRENT_SURVIVOR", "TERMINAL_NONCURRENT"
CYCLE, ORPHAN, AMBIGUOUS = "SURVIVOR_CYCLE", "SURVIVOR_ORPHAN_DEAD_POINTER", "SURVIVOR_AMBIGUOUS_TERMINAL"

@dataclass(frozen=True)
class TerminalIdentity:
    start_id: str
    status: str
    chain: Tuple[str, ...]            # feature ids from the start through the terminal (or through the last resolvable node)
    terminal_id: str                  # "" when unresolved (cycle / orphan / ambiguous)
    terminal_state: str               # governed lifecycle state of the terminal record; "" when unresolved
    terminal_is_current: bool
    authorizes_claim = False
    authorizes_resurrection = False
    authorizes_delivery = False
    authorizes_near_match_substitution = False

def resolve_terminal_identity(start, records: Iterable) -> TerminalIdentity:
    recs = list(records); node = start; chain = [start.feature_id]; seen = {start.feature_id}
    for _ in range(len(recs) + 2):                                       # hard termination bound independent of the data
        if node.is_current or not node.canonical_survivor:
            return TerminalIdentity(start.feature_id, CURRENT_SURVIVOR if node.is_current else TERMINAL_NONCURRENT, tuple(chain),
                                    node.feature_id, str(node.lifecycle_state), bool(node.is_current))
        sid = node.canonical_survivor
        if sid in seen:
            return TerminalIdentity(start.feature_id, CYCLE, tuple(chain) + (sid,), "", "", False)
        cands = [r for r in recs if r.feature_id == sid]
        if not cands:
            return TerminalIdentity(start.feature_id, ORPHAN, tuple(chain) + (sid,), "", "", False)
        if len({(r.feature_version, r.definition_hash, r.graph_hash, r.lifecycle_state, r.is_current) for r in cands}) > 1:
            return TerminalIdentity(start.feature_id, AMBIGUOUS, tuple(chain) + (sid,), "", "", False)    # never pick one of several candidates
        node = cands[0]; chain.append(sid); seen.add(sid)
    return TerminalIdentity(start.feature_id, CYCLE, tuple(chain), "", "", False)

def terminal_notes(lookup_result, records: Iterable) -> list:
    """Report strings for the pipeline failure list. Starts are the noncurrent rows whose named survivor the baseline lookup itself reported unresolved (UNRESOLVED_CANONICAL_SURVIVOR:<ids>
    in its errors; the lookup result carries no match list when incomplete). Terminal identity AND state are reported; informational only, the lookup stays fail-closed."""
    recs = list(records); ids = set()
    for e in getattr(lookup_result, "errors", ()) or ():
        if e.startswith("UNRESOLVED_CANONICAL_SURVIVOR:"):
            ids.update(x for x in e.split(":", 1)[1].split(",") if x)
    out = []
    for r in recs:
        if not r.is_current and r.canonical_survivor in ids:
            t = resolve_terminal_identity(r, recs)
            out.append("TERMINAL_IDENTITY:%s>%s:%s:%s" % (t.start_id, t.terminal_id or "-", t.terminal_state or "-", t.status))
    return out
