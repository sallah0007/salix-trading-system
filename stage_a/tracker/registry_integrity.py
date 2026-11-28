"""R40: the GENERIC integrated REGISTRY INTEGRITY CHECKER (Registry 377; DecisionContext 140-151 for quarantine/restoration) over the ACTUAL objects: `registry_entry.RegistryEntry`, the ONE `LifecycleFramework` journal, `relationship_store.RelationshipStore`, the B19 `EvidenceResolver`. The source owner supplies admission/currentness/revocation INSTANCES; this module supplies mechanics only and creates no second lifecycle or Health authority and no status mapping.
Each check yields a typed finding: OK / UNKNOWN / NOT_LIVE_SAFE (never "healthy"). Overall = NOT_LIVE_SAFE if any finding is, else UNKNOWN if any is, else CHECKS_PASS_FACTS_ONLY (which is still `authoritative=False`: it asserts no Health, status or gate).
  entry_integrity      : subject/version/creation-request/origin are non-empty, the entry's DISPOSITION_HISTORY equals the lifecycle journal's history RE-DERIVED now (an entry that carries a disposition the journal lacks is NOT_LIVE_SAFE), and the CREATION_REQUEST_ID is confirmed by the SUPPLIED `creation_request_known(creation_request_id, subject)` against the actual intake record (unbound => UNKNOWN; False => NOT_LIVE_SAFE);
  survivor_chain       : the survivor pointers resolve transitively, acyclically and terminating; the terminal survivor must be live in its owning journal (`owner_check`), else NOT_LIVE_SAFE; a refused chain (cycle, too long) is NOT_LIVE_SAFE;
  relationship         : for a survivor pointer, the relationship reference under the CURRENT diff schema must allow the claim (the store re-runs the compute path); uncomputed/held => UNKNOWN; mismatch/owner-not-live/uncomputable => NOT_LIVE_SAFE; no pointer => OK (nothing to relate);
  load_bearing_evidence: the supplied TransitionClaim must bind EXACTLY this subject/version and exactly the entry's TEST_EVIDENCE_REFS; the B19 resolver resolves AND re-resolves at use time (`use`); VALID needed; INVALID => NOT_LIVE_SAFE; UNPROVABLE => UNKNOWN; no refs, no claim or an unbound resolver => UNKNOWN;
  evidence_admission   : a store with no admission (`admission is None`, as every candidate store here) => UNKNOWN: a ref is never health.
`quarantine_decision` : SAFE QUARANTINE never waits for optional context metadata; RESTORATION stays HELD without governed metadata AND a VALID evidence report."""
from dataclasses import dataclass
from ..errors import Refusal
from . import registry_semantics as RSM
from .evidence_truth import VALID, INVALID, UNPROVABLE
OK, UNKNOWN, NOT_LIVE_SAFE = "OK", "UNKNOWN", "NOT_LIVE_SAFE"
@dataclass(frozen=True)
class Finding: check: str; state: str; code: str
@dataclass(frozen=True)
class IntegrityReport:
    subject: str; findings: tuple; overall: str; authoritative: bool = False
def _f(check, state, code=""): return Finding(check, state, code)
def check_registry_entry(entry, *, lifecycle, relationships=None, schema_version=None, survivor_pointers=None, owner_check=None, evidence_resolver=None, evidence_claim=None, evidence_pins=None, now=None, watermark=None, creation_request_known=None):
    from .registry_entry import RegistryEntry
    if not isinstance(entry, RegistryEntry): raise Refusal("entry", code="REGISTRY_INTEGRITY_INPUT_INVALID")
    out = []; subj = entry.subject
    # entry integrity (history re-derived from the single lifecycle journal)
    if not (subj and entry.origin in RSM.ORIGINS and entry.creation_request_id): out.append(_f("entry_integrity", NOT_LIVE_SAFE, "ENTRY_FIELDS_INVALID"))
    elif lifecycle is None or not hasattr(lifecycle, "history"): out.append(_f("entry_integrity", UNKNOWN, "LIFECYCLE_SOURCE_UNBOUND"))
    elif tuple(entry.disposition_history) != lifecycle.history(subj): out.append(_f("entry_integrity", NOT_LIVE_SAFE, "DISPOSITION_HISTORY_DIFFERS_FROM_LIFECYCLE_JOURNAL"))
    elif not callable(creation_request_known): out.append(_f("entry_integrity", UNKNOWN, "CREATION_REQUEST_SOURCE_UNBOUND"))
    else:
        try: known = creation_request_known(entry.creation_request_id, subj)
        except Refusal: known = None
        out.append(_f("entry_integrity", OK if known is True else UNKNOWN if known is None else NOT_LIVE_SAFE, "" if known is True else "CREATION_REQUEST_UNRESOLVED" if known is None else "CREATION_REQUEST_NOT_ASSOCIATED_WITH_SUBJECT"))
    # survivor chain
    ptr = dict(survivor_pointers or {})
    try: chain = RSM.resolve_survivor_chain(ptr, subj)
    except Refusal as e: chain = None; out.append(_f("survivor_chain", NOT_LIVE_SAFE, e.code))
    if chain is not None:
        if chain != entry.survivor_chain: out.append(_f("survivor_chain", NOT_LIVE_SAFE, "ENTRY_SURVIVOR_CHAIN_DIFFERS_FROM_POINTERS"))
        elif len(chain) == 1: out.append(_f("survivor_chain", OK))
        elif not callable(owner_check): out.append(_f("survivor_chain", UNKNOWN, "OWNER_CHECK_UNBOUND"))
        else: out.append(_f("survivor_chain", OK if owner_check(chain[-1]) is True else NOT_LIVE_SAFE, "" if owner_check(chain[-1]) is True else "SURVIVOR_NOT_LIVE_IN_OWNING_JOURNAL"))
    # relationship (current diff-schema conformance + computability)
    nxt = ptr.get(subj)
    if nxt is None: out.append(_f("relationship", OK, "NO_SURVIVOR_POINTER"))
    elif relationships is None or schema_version is None: out.append(_f("relationship", UNKNOWN, "RELATIONSHIP_STORE_OR_SCHEMA_UNBOUND"))
    else:
        r = relationships.successor_reference(subj, nxt, schema_version)
        if r.claim_allowed: out.append(_f("relationship", OK))
        elif r.state == "OWNER_NOT_RESOLVED" or r.reason in ("RECORD_DOES_NOT_MATCH_RECOMPUTATION", "HISTORICAL_CONTENT_UNVERIFIABLE_ROUTE_MATERIAL_ALTERNATIVE_TREATMENT") or r.state == "RELATIONSHIP_UNCOMPUTABLE": out.append(_f("relationship", NOT_LIVE_SAFE, r.reason or r.state))
        else: out.append(_f("relationship", UNKNOWN, r.reason or r.state))
    # load-bearing evidence (B19 resolve + use-time re-resolve)
    if not entry.test_evidence_refs: out.append(_f("load_bearing_evidence", UNKNOWN, "NO_EVIDENCE_REFS_ON_ENTRY"))
    elif evidence_resolver is None or evidence_claim is None or evidence_pins is None or now is None or watermark is None: out.append(_f("load_bearing_evidence", UNKNOWN, "EVIDENCE_RESOLVER_OR_CLAIM_UNBOUND"))
    elif evidence_claim.subject != subj or tuple(evidence_claim.evidence_refs) != tuple(entry.test_evidence_refs): out.append(_f("load_bearing_evidence", NOT_LIVE_SAFE, "EVIDENCE_CLAIM_DOES_NOT_BIND_ENTRY"))
    else:
        rc = evidence_resolver.resolve(evidence_claim, evidence_pins, now, watermark)
        if rc.status == VALID:
            try: evidence_resolver.use(rc, evidence_claim, evidence_pins, now, watermark); out.append(_f("load_bearing_evidence", OK))
            except Refusal as e: out.append(_f("load_bearing_evidence", NOT_LIVE_SAFE, e.code))
        else: out.append(_f("load_bearing_evidence", NOT_LIVE_SAFE if rc.status == INVALID else UNKNOWN, ",".join(rc.reasons) or rc.status))
        out.append(_f("evidence_admission", OK if getattr(evidence_resolver._s, "admission", None) is not None else UNKNOWN, "" if getattr(evidence_resolver._s, "admission", None) is not None else "EVIDENCE_STORE_NOT_ADMITTED_HELD"))
    states = [f.state for f in out]; overall = NOT_LIVE_SAFE if NOT_LIVE_SAFE in states else UNKNOWN if UNKNOWN in states else "CHECKS_PASS_FACTS_ONLY"
    return IntegrityReport(subj, tuple(out), overall)
def quarantine_decision(report, context_metadata=None):
    """Safe quarantine does NOT wait for optional context metadata (DecisionContext 140-151); restoration is HELD without governed metadata and a passing integrity report. Facts only; the lifecycle journal remains the only authority for any transition."""
    if not isinstance(report, IntegrityReport): raise Refusal("report", code="REGISTRY_INTEGRITY_INPUT_INVALID")
    q = "PERMITTED_NOT_WAITING_FOR_CONTEXT_METADATA" if report.overall != "CHECKS_PASS_FACTS_ONLY" else "NOT_INDICATED"
    r = "HELD_MISSING_GOVERNED_METADATA" if not context_metadata else "HELD_INTEGRITY_NOT_PASSING" if report.overall != "CHECKS_PASS_FACTS_ONLY" else "METADATA_AND_CHECKS_PRESENT_TRANSITION_STILL_NEEDS_LIFECYCLE_AUTHORITY"
    return {"quarantine": q, "restoration": r}
