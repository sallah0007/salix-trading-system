"""R26 CANDIDATE predicates for two registry clauses (Registry 1eZThdek..., read in R26; cited by section heading, no source text copied):
  (1) AUTHORITY-TRANSITION EVIDENCE TRUTH (registry sections at lines read as 'SIGNED_TRANSITION != VALID_TRANSITION'; test lines 'evidence-truth authority transition');
  (2) CAUSAL IMPUTATION / FITTED TRANSFORM FIREWALL (and its positive/negative control lines).
These are pure predicates plus a Core callpath (`TrackerCore.judge_transition_evidence` / `judge_transform`, consumed by `eligible_asof`). UNBOUND ADMISSIONS (source-owned, NOT invented here): which evidence store is 'authoritative' (the caller supplies the
index; a caller-supplied index is NOT an admitted authority), the governed freshness/watermark values, the fitting/holdout contract INSTANCES, the actor/principal admission. A signature/actor field is accepted ONLY as data and never contributes to validity."""
from dataclasses import dataclass
from typing import Tuple

VALID, INVALID, UNPROVABLE = "VALID", "INVALID", "UNPROVABLE"
@dataclass(frozen=True)
class EvidenceRecord:
    ref: str; subject: str; version_or_hash: str; instrument: str; timeframe: str; battery: str; vintage: str; dependencies: Tuple[str, ...]
    result: str; available_at: int; max_age: int; revoked: object; current: object; approval_state: object      # R27: NO defaults - revocation/currentness/approval must be stated explicitly by the evidence source
@dataclass(frozen=True)
class TransitionClaim:
    subject: str; version_or_hash: str; instrument: str; timeframe: str; battery: str; vintage: str; dependencies: Tuple[str, ...]; expected_result: str
    required_approval: str; evidence_refs: Tuple[str, ...]; signed_by: str = ""          # signed_by is recorded, never relied on
@dataclass(frozen=True)
class Verdict:
    status: str; reasons: Tuple[str, ...]
    def __bool__(self): raise TypeError("Verdict has no truthiness; compare .status")

def judge_transition_evidence(claim: TransitionClaim, index: dict, now: int) -> Verdict:
    """VALID only if EVERY referenced evidence record resolves, is current and unrevoked, fresh, and matches the claim on every dimension; at least one reference is required. Anything missing/unreadable is INVALID/UNPROVABLE (fail closed)."""
    if not isinstance(claim, TransitionClaim) or not isinstance(index, dict) or isinstance(now, bool) or not isinstance(now, int) or now < 0: return Verdict(UNPROVABLE, ("INPUT_INVALID",))
    if not claim.evidence_refs: return Verdict(INVALID, ("NO_EVIDENCE_REFERENCED",))                       # signed/authorized with no evidence is never valid
    if not all(isinstance(x, str) and x for x in (claim.subject, claim.version_or_hash, claim.instrument, claim.timeframe, claim.battery, claim.vintage, claim.expected_result, claim.required_approval)) \
            or not isinstance(claim.evidence_refs, tuple) or not all(isinstance(r, str) and r for r in claim.evidence_refs) or not isinstance(claim.dependencies, tuple) or not all(isinstance(d, str) and d for d in claim.dependencies):
        return Verdict(UNPROVABLE, ("CLAIM_MALFORMED",))
    bad = []
    for ref in claim.evidence_refs:
        e = index.get(ref)
        if not isinstance(e, EvidenceRecord): bad.append("EVIDENCE_MISSING:" + str(ref)); continue
        if e.ref != ref: bad.append("EVIDENCE_REF_MISMATCH:" + ref); continue
        if (not all(isinstance(x, str) and x for x in (e.subject, e.version_or_hash, e.instrument, e.timeframe, e.battery, e.vintage, e.result)) or not isinstance(e.dependencies, tuple) or not all(isinstance(d, str) for d in e.dependencies)
                or isinstance(e.available_at, bool) or not isinstance(e.available_at, int) or isinstance(e.max_age, bool) or not isinstance(e.max_age, int)
                or not isinstance(e.revoked, bool) or not isinstance(e.current, bool) or not (isinstance(e.approval_state, str) and e.approval_state)):
            bad.append("EVIDENCE_MALFORMED_OR_STATE_UNSTATED:" + ref); continue                    # unknown/unstated/mistyped states fail closed; nothing is inferred
        if e.revoked: bad.append("EVIDENCE_REVOKED:" + ref)
        if not e.current: bad.append("EVIDENCE_NOT_CURRENT:" + ref)
        if e.available_at > now or now - e.available_at > e.max_age or e.max_age <= 0: bad.append("EVIDENCE_STALE_OR_FUTURE:" + ref)
        for name, got, want in (("SUBJECT", e.subject, claim.subject), ("VERSION_OR_HASH", e.version_or_hash, claim.version_or_hash), ("INSTRUMENT", e.instrument, claim.instrument), ("TIMEFRAME", e.timeframe, claim.timeframe),
                                ("BATTERY", e.battery, claim.battery), ("VINTAGE", e.vintage, claim.vintage), ("DEPENDENCIES", tuple(e.dependencies), tuple(claim.dependencies)), ("RESULT", e.result, claim.expected_result),
                                ("APPROVAL", e.approval_state, claim.required_approval)):
            if got != want: bad.append("EVIDENCE_%s_MISMATCH:%s" % (name, ref))
    if bad: return Verdict(INVALID, tuple(bad))
    return Verdict(VALID, ())

def valid_until(claim: TransitionClaim, index: dict):
    """Last instant the referenced evidence is fresh (min over refs of available_at + max_age); None if any ref is unresolved/malformed. Used at USE time, not only when the verdict was made."""
    ends = []
    for r in claim.evidence_refs:
        e = index.get(r)
        if not isinstance(e, EvidenceRecord) or isinstance(e.available_at, bool) or not isinstance(e.available_at, int) or isinstance(e.max_age, bool) or not isinstance(e.max_age, int): return None
        ends.append(e.available_at + e.max_age)
    return min(ends) if ends else None

KINDS = ("INTERPOLATION", "IMPUTATION", "FILL", "SCALER", "LEARNED_TRANSFORM")
@dataclass(frozen=True)
class TransformSpec:
    kind: str; direction: str            # CAUSAL | BACKWARD | FUTURE | CENTERED
    version: str; fit_window_end: int; fit_permitted_until: int; asof: int; lineage_ref: str; missingness_observable: bool; provenance_ref: str
def judge_transform(spec: TransformSpec) -> Verdict:
    """A transform may enter a prospective/LIVE_SAFE view only if causal, versioned, fitted on information permitted by its fitting/holdout contract (fit_permitted_until is the CONTRACT INSTANCE supplied by the caller), lineage-bound, and missingness stays observable with provenance."""
    r = []
    if not isinstance(spec, TransformSpec): return Verdict(UNPROVABLE, ("INPUT_INVALID",))
    if spec.kind not in KINDS: r.append("KIND_UNKNOWN")
    if spec.direction != "CAUSAL": r.append("NOT_CAUSAL:" + str(spec.direction))
    if not (isinstance(spec.version, str) and spec.version): r.append("NOT_VERSIONED")
    ints = [spec.fit_window_end, spec.fit_permitted_until, spec.asof]
    if any(isinstance(x, bool) or not isinstance(x, int) for x in ints): return Verdict(UNPROVABLE, tuple(r) + ("TIME_INPUT_INVALID",))
    if spec.fit_window_end > spec.fit_permitted_until: r.append("FITTED_ON_FORBIDDEN_INFORMATION")
    if spec.fit_window_end >= spec.asof: r.append("FIT_NOT_BEFORE_ASOF")
    if not (isinstance(spec.lineage_ref, str) and spec.lineage_ref): r.append("LINEAGE_MISSING")
    if spec.missingness_observable is not True or not (isinstance(spec.provenance_ref, str) and spec.provenance_ref): r.append("MISSINGNESS_ERASED_OR_UNPROVENANCED")
    return Verdict(INVALID, tuple(r)) if r else Verdict(VALID, ())
