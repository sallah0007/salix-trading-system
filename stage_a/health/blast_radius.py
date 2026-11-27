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

def upstream_incomplete(consumer_features: Iterable[bytes], failed: bytes, feature_deps: Dict[bytes, Tuple[bytes, ...]], unread: Iterable[bytes]) -> bool:
    """CONSUMER-SPECIFIC incompleteness (OB2 / Q12 / M4): walks only the features the consumer's own closure transitively depends on. A feature that is listed unread, or whose
    own lineage was never supplied (absent from feature_deps), makes THIS consumer undetermined; unread lineage elsewhere does not. The failed subject itself is not 'unread'."""
    unread, seen, stack = set(unread), set(), list(consumer_features)
    while stack:
        n = stack.pop()
        if n in seen or n == failed:
            continue
        seen.add(n)
        if n in unread or n not in feature_deps:
            return True
        stack.extend(feature_deps[n])
    return False

def blast_radius(failed: bytes, consumers: Dict[str, object], feature_deps: Dict[bytes, Tuple[bytes, ...]], closure_contains_target,
                 unread_features: Iterable[bytes] = (), closure_features=None) -> Dict[str, CarriedUpstreamImpact]:
    """closure_contains_target(manifest, feature, consumers) -> bool and closure_features(manifest, consumers) -> set are INJECTED (Health must not import FW/ML: architecture
    rule Q18-Q20); both must raise Refusal for unread or misbound ancestry (fw.lanes versions do). The caller is NOT assumed to validate: a consumer whose key differs from
    its own manifest_id is UNDETERMINED. With closure_features supplied, feature-lineage incompleteness is judged per consumer over its own closure (an empty, fully resolved
    closure is never contaminated by an unrelated unread branch). Without it, the conservative GLOBAL rule applies (any incompleteness anywhere -> undetermined): safe but over-blocking, named."""
    if not isinstance(failed, bytes) or not failed:
        raise Refusal(repr(failed), code="FAILED_SUBJECT_NOT_AN_IDENTITY")
    affected, features_incomplete = downstream_features(failed, feature_deps, unread_features)
    out = {}
    for cid in sorted(consumers):
        m = consumers[cid]
        if getattr(m, "manifest_id", cid) != cid:
            out[cid] = CarriedUpstreamImpact(cid, UNDETERMINED, failed, (), "CONSUMER_KEY_MISMATCH"); continue
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
        else:
            incomplete = features_incomplete
            if closure_features is not None:
                try:
                    incomplete = upstream_incomplete(closure_features(m, consumers), failed, feature_deps, unread_features)
                except Refusal as e:
                    out[cid] = CarriedUpstreamImpact(cid, UNDETERMINED, failed, (), e.code); continue
            out[cid] = CarriedUpstreamImpact(cid, UNDETERMINED, failed, (), "FEATURE_LINEAGE_INCOMPLETE") if incomplete else CarriedUpstreamImpact(cid, UNAFFECTED, failed)
    return out

def must_block(impact: CarriedUpstreamImpact) -> bool:
    """OB2: only a PROVEN dependency may block. Unrelated and undetermined consumers are not blocked by this evidence alone."""
    return impact.verdict == AFFECTED

def consumer_use(impact: CarriedUpstreamImpact, required: bool) -> str:
    """Applies existing rules; chooses no new recovery policy. Build Plan 13.1: unknown REQUIRED ancestry fails closed; 14A/OB2: a proven-independent branch stays
    unaffected. AFFECTED -> block; UNAFFECTED -> allow; UNDETERMINED + REQUIRED use -> refuse (unproven independence), reason kept; UNDETERMINED + non-required use ->
    NO_SOURCE_RULE (no source read states the consequence; the case is named, not decided). Never a global quarantine, never a local-state copy."""
    if impact.verdict == AFFECTED:
        return "BLOCK_PROVEN_DEPENDENCY"
    if impact.verdict == UNAFFECTED:
        return "ALLOW_PROVEN_INDEPENDENT"
    return "REFUSE_UNPROVEN_INDEPENDENCE" if required else "NO_SOURCE_RULE_UNDETERMINED_NON_REQUIRED_USE"
