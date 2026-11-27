"""Blast radius (Build Plan 14A R1 + OB2): derived from governed dependency/consumption lineage and exact bindings, NOT by copying an upstream subject's
status into a downstream local status. Pure structural traversal over SUPPLIED, already-validated lineage. No Health profile, threshold or registry is
needed or used (those are D17/D18 and stay out).
Output is CARRIED-UPSTREAM IMPACT evidence per consumer; it never sets a LOCAL_STATE and never contains a health state.
Verdicts: AFFECTED_PROVEN_DEPENDENCY (a lineage path from the failed subject to the consumer was found), NOT_AFFECTED_NO_PROVEN_DEPENDENCY (the whole lineage
was read and no path exists: OB2 says this consumer must not be blocked), UNDETERMINED_LINEAGE_UNREAD (lineage could not be fully read: absence of a found
path is NOT absence of a dependency; the result is neither 'affected' nor 'unaffected').
EXACT MISSING SEMANTIC RULE (not invented): what action an UNDETERMINED consumer must receive (block / deliver / review). This module only classifies it."""
from dataclasses import dataclass
from typing import Dict, Tuple, Iterable, Optional
from ..errors import Refusal

AFFECTED = "AFFECTED_PROVEN_DEPENDENCY"
UNAFFECTED = "NOT_AFFECTED_NO_PROVEN_DEPENDENCY"
UNDETERMINED = "UNDETERMINED_LINEAGE_UNREAD"

@dataclass(frozen=True)
class CarriedUpstreamImpact:
    consumer_id: str
    verdict: str
    failed_subject: bytes
    via: Tuple[bytes, ...] = ()            # failed subject plus downstream features through which the dependency was proven
    reason: str = ""

def downstream_features(failed: bytes, feature_deps: Dict[bytes, Tuple[bytes, ...]], unread_features: Iterable[bytes] = ()):
    """Transitive dependents of `failed`. feature_deps maps feature -> the features it depends on (governed lineage). Returns (affected_set, undetermined_set):
    a feature listed as unread, or absent from feature_deps while referenced as a dependency target, makes lineage incomplete."""
    unread = set(unread_features)
    dependents: Dict[bytes, set] = {}
    for f, deps in feature_deps.items():
        for d in deps:
            dependents.setdefault(d, set()).add(f)
    affected, frontier, incomplete = {failed}, [failed], bool(unread)
    while frontier:
        cur = frontier.pop()
        for f in dependents.get(cur, ()):
            if f not in affected:
                affected.add(f); frontier.append(f)
    for d in {x for deps in feature_deps.values() for x in deps}:
        if d not in feature_deps and d != failed:
            incomplete = True                                  # a dependency target whose own lineage was never supplied
    return affected, incomplete

def blast_radius(failed: bytes, consumers: Dict[str, object], feature_deps: Dict[bytes, Tuple[bytes, ...]], closure_contains_target,
                 unread_features: Iterable[bytes] = ()) -> Dict[str, CarriedUpstreamImpact]:
    """closure_contains_target(manifest, feature, consumers) -> bool is INJECTED (Health must not import FW/ML: architecture rule Q18-Q20); it must raise
    Refusal for unread ancestry (fw.lanes.closure_contains_target does)."""
    if not isinstance(failed, bytes) or not failed:
        raise Refusal(repr(failed), code="FAILED_SUBJECT_NOT_AN_IDENTITY")
    affected, features_incomplete = downstream_features(failed, feature_deps, unread_features)
    out = {}
    for cid in sorted(consumers):
        m = consumers[cid]
        proven, unread = [], False
        for f in sorted(affected):
            try:
                if closure_contains_target(m, f, consumers):
                    proven.append(f)
            except Refusal as e:                              # DERIVED_FROM_UNRESOLVED / DERIVATION_CYCLE: ancestry unread
                unread = True; reason = e.code
        if proven:
            out[cid] = CarriedUpstreamImpact(cid, AFFECTED, failed, tuple(proven), "closure contains failed subject or a dependent")
        elif unread:
            out[cid] = CarriedUpstreamImpact(cid, UNDETERMINED, failed, (), reason)
        elif features_incomplete:
            out[cid] = CarriedUpstreamImpact(cid, UNDETERMINED, failed, (), "FEATURE_LINEAGE_INCOMPLETE")
        else:
            out[cid] = CarriedUpstreamImpact(cid, UNAFFECTED, failed)
    return out

def must_block(impact: CarriedUpstreamImpact) -> bool:
    """OB2: only a PROVEN dependency may block. Unrelated and undetermined consumers are not blocked by this evidence alone."""
    return impact.verdict == AFFECTED
