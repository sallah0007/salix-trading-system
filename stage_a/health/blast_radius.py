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

def upstream_lineage_defect(consumer_features: Iterable[bytes], failed: bytes, feature_deps: Dict[bytes, Tuple[bytes, ...]], unread: Iterable[bytes]) -> Optional[str]:
    """CONSUMER-SPECIFIC lineage proof (OB2 / Q12 / M4): walks only the features the consumer's own closure transitively depends on and returns None only when that upstream
    lineage is fully read AND acyclic. FEATURE_LINEAGE_INCOMPLETE: a feature is listed unread or its own lineage was never supplied. FEATURE_LINEAGE_CYCLIC: the reachable lineage
    contains a cycle (invalid for a DAG-certified feature graph; independence cannot be proven over it). The failed subject itself is a proof endpoint, not 'unread'."""
    unread = set(unread); state = {}                                         # 1 = on stack, 2 = done
    for root in consumer_features:
        if root == failed or state.get(root) == 2:
            continue
        if root in unread or root not in feature_deps:
            return "FEATURE_LINEAGE_INCOMPLETE"
        state[root] = 1; stack = [(root, iter(feature_deps[root]))]
        while stack:
            n, it = stack[-1]
            c = next(it, None)
            if c is None:
                state[n] = 2; stack.pop(); continue
            if c == failed or state.get(c) == 2:
                continue
            if state.get(c) == 1:
                return "FEATURE_LINEAGE_CYCLIC"
            if c in unread or c not in feature_deps:
                return "FEATURE_LINEAGE_INCOMPLETE"
            state[c] = 1; stack.append((c, iter(feature_deps[c])))
    return None

def blast_radius(failed: bytes, consumers: Dict[str, object], feature_deps: Dict[bytes, Tuple[bytes, ...]], closure_contains_target, closure_features=None,
                 unread_features: Iterable[bytes] = ()) -> Dict[str, CarriedUpstreamImpact]:
    """closure_contains_target(manifest, feature, consumers) -> bool and closure_features(manifest, consumers) -> set are BOTH REQUIRED (omitted -> Refusal CLOSURE_PROOF_ADAPTER_REQUIRED, never a silent global default) and INJECTED (Health must not import FW/ML:
    architecture rule Q18-Q20); both must raise Refusal for unread or misbound ancestry (fw.lanes versions do). There is NO fallback: R18's optional probe kept the global
    over-blocking default. The caller is NOT assumed to validate: a consumer whose key differs from its own manifest_id is UNDETERMINED; a probe that is not callable is refused.
    Incompleteness and cycles are judged per consumer over its own closure (an empty, fully resolved closure is never contaminated by an unrelated branch)."""
    if not isinstance(failed, bytes) or not failed:
        raise Refusal(repr(failed), code="FAILED_SUBJECT_NOT_AN_IDENTITY")
    if not callable(closure_contains_target) or not callable(closure_features):
        raise Refusal("closure probes", code="CLOSURE_PROOF_ADAPTER_REQUIRED")
    affected, _ = downstream_features(failed, feature_deps, unread_features)
    out = {}
    for cid in sorted(consumers):
        m = consumers[cid]
        if getattr(m, "manifest_id", cid) != cid:
            out[cid] = CarriedUpstreamImpact(cid, UNDETERMINED, failed, (), "CONSUMER_KEY_MISMATCH"); continue
        proven, unread, reason = [], False, ""
        for f in sorted(affected):
            try:
                if closure_contains_target(m, f, consumers):
                    proven.append(f)
            except Refusal as e:                              # DERIVED_FROM_UNRESOLVED / DERIVATION_CYCLE / GRAPH_KEY_MISMATCH: ancestry unread
                unread = True; reason = e.code
        if proven:
            out[cid] = CarriedUpstreamImpact(cid, AFFECTED, failed, tuple(proven), "closure contains failed subject or a dependent")
        elif unread:
            out[cid] = CarriedUpstreamImpact(cid, UNDETERMINED, failed, (), reason)
        else:
            try:
                defect = upstream_lineage_defect(closure_features(m, consumers), failed, feature_deps, unread_features)
            except Refusal as e:
                out[cid] = CarriedUpstreamImpact(cid, UNDETERMINED, failed, (), e.code); continue
            out[cid] = CarriedUpstreamImpact(cid, UNDETERMINED, failed, (), defect) if defect else CarriedUpstreamImpact(cid, UNAFFECTED, failed)
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
