"""Generic bounded Health EVIDENCE adapters over records this repository already produces (Typed Annex XVII: Health supplies evidence only; MasterHealth V3 B0 is the SOLE operative envelope: no competing schema, no second Health authority; Build Plan 14/14A subject list).
Each adapter returns a `HealthObservation`: a subject KIND, the FACTS read from the existing record (counts, statuses, reason codes, hashes), the exact source-record reference, and `held_slots` naming every B0 envelope field that remains SOURCE-OWNED and UNBOUND
(HEALTH_PROFILE_*, HEALTH_POLICY_*, CRITICAL_SET_*, REASON_CODE registry, producer identity/signature, thresholds, expectation state). An observation never carries a HEALTHY/NOT_HEALTHY verdict: mapping facts to a state needs a governed policy (thresholds are DEFERRED by the source),
so `state_for(obs, policy)` applies a SUPPLIED policy callable and labels the result CALLER_POLICY_UNADMITTED; with no policy the state is UNKNOWN (never HEALTHY). Facts are read, never fabricated: an absent record yields `facts=None`/UNKNOWN, not an empty healthy reading.
These adapters are not a Health service, emit nothing to a Health authority and change no status."""
from dataclasses import dataclass
from typing import Optional
from ..errors import Refusal
B0_HELD_SLOTS = ("HEALTH_PROFILE_ID/VERSION", "HEALTH_POLICY_ID/VERSION", "CRITICAL_SET_ID/VERSION", "REASON_CODE registry", "PRODUCER_ID/VERSION", "PRODUCER_SIGNATURE_OR_INTEGRITY_BINDING", "thresholds", "EXPECTATION_STATE")
KINDS = ("MATERIALIZATION_ROW", "SCHEDULER_RESOURCE_STATE", "GATEWAY_BINDING_NON_DELIVERY", "FW_RETURNS", "ML_GENERATION_AND_CLAIMS", "QUANT_MANIFEST_PROFILE", "FIT_GENERATION", "REPLAY_BACKLOG", "ML_FW_AUGMENTED", "COORDINATION_HANDOFF", "READ_PATH_REVOCATION_CURRENTNESS", "VERSION_RELATIONSHIP")
STATES = ("HEALTHY", "NOT_HEALTHY", "UNKNOWN")

@dataclass(frozen=True)
class HealthObservation:
    kind: str; facts: Optional[dict]; source_ref: str; held_slots: tuple = B0_HELD_SLOTS; admitted: bool = False
    subject: Optional[tuple] = None      # R36: ((field, value), ...) the record's OWN subject binding (Typed Annex XVII 616-662: feature/version/instrument/timeframe/materialization evidence fields); None = the record carries none
    scope: str = "UNSCOPED"              # "SUBJECT" (facts about one feature subject, bound by `subject`) | "GLOBAL:<name>" (declared global statistics, never attributed to a feature automatically) | "UNSCOPED" (no declared scope: attributed to nothing)

def from_verification_result(res, source_ref: str) -> HealthObservation:
    from ..tracker.verification.verification_result import VerificationResult, split_levels, result_is_self_consistent
    if not isinstance(res, VerificationResult): return HealthObservation("MATERIALIZATION_ROW", None, source_ref)
    l1, l2 = split_levels(res)
    return HealthObservation("MATERIALIZATION_ROW", {"status": res.status, "scope": res.scope, "l1": l1, "l2": l2, "failed_checks": tuple(sorted(n for n, ok in res.checks if not ok)), "reasons": tuple(res.reasons), "result_hash": res.result_hash, "self_consistent": result_is_self_consistent(res)}, source_ref, subject=tuple(res.subject), scope="SUBJECT")

def from_reverify_pass(core, pass_id: str) -> HealthObservation:
    p = core.reverify_pass(pass_id)
    if p is None: return HealthObservation("SCHEDULER_RESOURCE_STATE", None, "reverify_pass:" + str(pass_id))
    items = p["items"]; by = {}
    for it in items: by[it[2]] = by.get(it[2], 0) + 1                       # outcome is the third element (subject, trigger, outcome, ...)
    return HealthObservation("SCHEDULER_RESOURCE_STATE", {"at": p["at"], "max_items": p["max_items"], "items": len(items), "by_outcome": dict(sorted(by.items())), "skipped": sum(v for k, v in by.items() if k.startswith("SKIPPED"))}, "reverify_pass:" + pass_id, scope="GLOBAL:REVERIFY_PASS")

def from_final_store(store) -> HealthObservation:
    out = store.outcomes(); by = {}
    for ident, o in out:
        k = type(o).__name__ + (":" + o.reason if type(o).__name__ == "NonDeliveryResolution" else ""); by[k] = by.get(k, 0) + 1
    return HealthObservation("GATEWAY_BINDING_NON_DELIVERY", {"windows": len(out), "by_outcome": dict(sorted(by.items()))}, "final_resolution_store", scope="GLOBAL:FINAL_RESOLUTION_STORE")

def from_gateway_late_evidence(gateway) -> HealthObservation:
    """Immutable late/settlement evidence the Gateway recorded beside stored outcomes (V0.38 forensic classification). Facts only: counts by classification; a SETTLEMENT_BREACH is evidence, the Health verdict needs the unbound policy."""
    ev = gateway.all_late_evidence(); by = {}
    for e in ev: by[e.classification] = by.get(e.classification, 0) + 1
    return HealthObservation("GATEWAY_BINDING_NON_DELIVERY", {"late_evidence": len(ev), "by_classification": dict(sorted(by.items()))}, "gateway_late_evidence", scope="GLOBAL:GATEWAY_LATE_EVIDENCE")

def from_fw_association(assoc) -> HealthObservation:
    rets = assoc.all_returns(); by = {}
    for r in rets: by[r.return_class] = by.get(r.return_class, 0) + 1
    return HealthObservation("FW_RETURNS", {"returns": len(rets), "by_class": dict(sorted(by.items())), "payload_fields": "HELD_UNBOUND"}, "fw_association", scope="GLOBAL:FW_ASSOCIATION")

def from_claim_ledger(claims, registry_correlations: dict = None) -> HealthObservation:
    cs = claims.claims(); corr = dict(registry_correlations or {})
    return HealthObservation("ML_GENERATION_AND_CLAIMS", {"claims": len(cs), "authority_bearing": sum(1 for c in cs if c.authority_bearing), "writer_correlations": {k: v for k, v in sorted(corr.items())}}, "claim_ledger", scope="GLOBAL:CLAIM_LEDGER")

def _subject(feature_key, **extra):
    return tuple([("expect_scope_key", feature_key.key())] + sorted(extra.items()))

def from_accepted_manifest(readback) -> HealthObservation:
    """QUANT_MANIFEST_PROFILE (Build Plan 14): facts about the ACCEPTED manifest read back AS FOUND (`tracker.accepted_manifest.read_accepted_manifest`, hashes recomputed independently). SUBJECT-scoped to that feature key/version; no verdict."""
    d = readback.manifest.data; fk = readback.feature_key
    return HealthObservation("QUANT_MANIFEST_PROFILE", {"manifest_hash": readback.manifest_hash, "accepted_seq": readback.accepted_seq, "inputs": len(d.get("inputs", ())), "nodes": len(d.get("nodes", ())), "fit_refs": len(d.get("fit_refs", ())), "declared_opcodes": len(d.get("declared_opcodes", ())), "declared_capabilities": len(d.get("declared_capabilities", ()))},
                             "accepted_manifest:" + fk, subject=(("expect_scope_key", fk), ("record_manifest_hash", readback.manifest_hash)), scope="SUBJECT")

def from_relationship_reference(ref) -> HealthObservation:
    """R38: facts about a `relationship_store.RelationshipReference` (state/class/claim_allowed/reason + the exact record id). SUBJECT-scoped to the (predecessor, successor) pair. No verdict and NO delivery fact: the reference carries none."""
    from ..tracker.relationship_store import RelationshipReference
    if not isinstance(ref, RelationshipReference): return HealthObservation("VERSION_RELATIONSHIP", None, "relationship_reference:unreadable")
    return HealthObservation("VERSION_RELATIONSHIP", {"state": ref.state, "class": ref.relationship_class, "claim_allowed": ref.claim_allowed, "reason": ref.reason, "record_id": ref.record_id, "schema_version": ref.schema_version, "store_head_seq": ref.store_head_seq},
                             "relationship:%s->%s@%s" % (ref.predecessor, ref.successor, ref.schema_version), subject=(("predecessor", ref.predecessor), ("successor", ref.successor)), scope="SUBJECT")

def from_registry_integrity(report) -> HealthObservation:
    """R40: FACTS about a `registry_integrity.IntegrityReport` (per-check states + overall). SUBJECT-scoped; no verdict, no status mapping; an unreadable report yields facts=None."""
    from ..tracker.registry_integrity import IntegrityReport
    if not isinstance(report, IntegrityReport): return HealthObservation("REGISTRY_INTEGRITY", None, "registry_integrity:unreadable")
    return HealthObservation("REGISTRY_INTEGRITY", {"overall": report.overall, "findings": [(f.check, f.state, f.code) for f in report.findings]}, "registry_integrity:%s" % report.subject, subject=(("subject", report.subject),), scope="SUBJECT")

def from_fit_generation_check(feature_key, manifest_fit_refs, accepted_generations) -> HealthObservation:
    """FIT_GENERATION: runs the existing `check_fit_refs` over the manifest's fit references and the SUPPLIED accepted generations; facts = the refs and the exact refusal code (or OK). SUBJECT-scoped."""
    from ..composer.expression.fit_generation import check_fit_refs
    try: check_fit_refs(manifest_fit_refs, accepted_generations); res = "OK"
    except Refusal as e: res = e.code
    return HealthObservation("FIT_GENERATION", {"refs": len(manifest_fit_refs), "accepted_generations": len(accepted_generations), "result": res}, "fit_generation_check:" + feature_key.key(), subject=_subject(feature_key), scope="SUBJECT")

def from_replay_backlog(feature_key, journal, applied_seq) -> HealthObservation:
    """REPLAY_BACKLOG: journal head sequence vs the SUPPLIED applied sequence of a consumer/projection. backlog = head - applied (negative = applied ahead of the journal = a defect, reported as is)."""
    recs = journal.read_from(1); head = recs[-1].seq if recs else 0
    return HealthObservation("REPLAY_BACKLOG", {"head_seq": head, "applied_seq": applied_seq, "backlog": head - applied_seq}, "journal:" + feature_key.namespace(), subject=_subject(feature_key), scope="SUBJECT")

def from_augmented_checks(checks) -> HealthObservation:
    """ML_FW_AUGMENTED bindings (MasterHealthV3 G): counts of `ml.receiver.AugmentedCheck` results by lane and by whether the rebind was verified against an actually issued Gateway binding."""
    by = {}
    for c in checks: k = "%s:%s" % (c.lane, "VERIFIED" if c.rebind_verified else "UNVERIFIED"); by[k] = by.get(k, 0) + 1
    return HealthObservation("ML_FW_AUGMENTED", {"checks": len(checks), "by_lane_and_verification": dict(sorted(by.items()))}, "ml_fw_augmented", scope="GLOBAL:ML_FW_AUGMENTED")

def from_journal_handoff(journal, namespace: str) -> HealthObservation:
    """COORDINATION_HANDOFF (durable coordination): record kinds, head sequence and legacy (pre-R34, no materialization binding) accepted bodies in one journal namespace, read AS FOUND."""
    from ..replay import replay
    recs = journal.read_from(1); by = {}
    for r in recs: by[r.kind] = by.get(r.kind, 0) + 1
    try: legacy = sum(1 for v in replay(namespace, recs).values() if v.legacy_binding_absent)
    except Refusal as e: return HealthObservation("COORDINATION_HANDOFF", {"head_seq": recs[-1].seq if recs else 0, "by_kind": dict(sorted(by.items())), "replay": e.code}, "journal:" + namespace, scope="GLOBAL:JOURNAL:" + namespace)
    return HealthObservation("COORDINATION_HANDOFF", {"head_seq": recs[-1].seq if recs else 0, "by_kind": dict(sorted(by.items())), "legacy_accepted": legacy, "replay": "OK"}, "journal:" + namespace, scope="GLOBAL:JOURNAL:" + namespace)

def from_revocation_ledgers(datasets=None, generations=None) -> HealthObservation:
    """READ_PATH_REVOCATION_CURRENTNESS: size and last timestamp of the dataset revocation ledger and the generation lifecycle ledger a read path consults. An empty ledger is a fact (0), never 'currently clean'."""
    dl = list(datasets._ledger) if datasets is not None else None; gl = list(generations.ledger()) if generations is not None else None
    return HealthObservation("READ_PATH_REVOCATION_CURRENTNESS", {"dataset_revocations": None if dl is None else len(dl), "dataset_last_ts": None if not dl else dl[-1][1], "generation_ledger": None if gl is None else len(gl)}, "revocation_ledgers", scope="GLOBAL:REVOCATION_LEDGERS")

def state_for(obs: HealthObservation, policy=None):
    """(state, label). No policy -> UNKNOWN. A supplied policy must return exactly HEALTHY / NOT_HEALTHY / UNKNOWN; anything else refuses. An observation without facts is UNKNOWN whatever the policy says."""
    if not isinstance(obs, HealthObservation): raise Refusal("obs", code="NOT_A_HEALTH_OBSERVATION")
    if obs.facts is None or policy is None: return "UNKNOWN", ("NO_FACTS" if obs.facts is None else "NO_POLICY_SUPPLIED")
    st = policy(obs.facts)
    if st not in STATES or type(st) is not str: raise Refusal(repr(st), code="HEALTH_POLICY_RESULT_INVALID")
    return st, "CALLER_POLICY_UNADMITTED"
