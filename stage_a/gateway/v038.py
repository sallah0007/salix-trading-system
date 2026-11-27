"""Connected Contract V0.38 delivery-failure objects (read from the operative V0.38 document; see docs/a07 evidence).

STATUS: field-level conformance objects + pure rules for NON_DELIVERY_RESOLUTION, EXPECTED_DEPENDENCY_KEY, structured
OMISSIONS, RESOLUTION_VISIBILITY_WATERMARK, final-resolution identity, settlement delay and forensic classification.
NOT built here, because no source gives bytes: FINAL_RESOLUTION_HASH / PACKAGE_HASH canonical encoding (open item D13).
This is NOT a connection to a real Gateway; the resolver in contracts.py remains a simulation."""
import copy
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from ..errors import Refusal
from ..schema.encoding import Ref
from . import contracts as C

NOT_READY, REJECTED, AFTER_CUTOFF = "NOT_READY_REQUIRED_DEPENDENCY", "REJECTED_FAIL_CLOSED", "REQUEST_AFTER_CUTOFF"
NON_DELIVERY_STATUSES = (NOT_READY, REJECTED, AFTER_CUTOFF)          # V0.38: "the smallest status set"; SUPERSEDED is not one
GENUINE_LATE, SETTLEMENT_BREACH, RESOLVER_FAULT = "GENUINE_LATE", "SETTLEMENT_BREACH", "RESOLVER_FAULT"

# PROPOSED mapping (the source says only: missing/ineligible REQUIRED => NOT_READY "unless a stronger fail-closed
# authority reason applies"). Unknown reasons map to REJECTED_FAIL_CLOSED (fail closed on the unread).
_NOT_READY_REASONS = {"REQUIRED_DEPENDENCY_ABSENT", "NOT_AVAILABLE_BEFORE_FENCE", "LATE_VISIBILITY"}
def status_for_reason(reason: str) -> str:
    if reason in _NOT_READY_REASONS or reason.startswith("CHAIN_STATUS_NOT_CURRENT:"):
        return NOT_READY
    return REJECTED

@dataclass(frozen=True)
class ExpectedDependencyKey:
    """FEATURE_VERSION + expected EVENT_TIME or STEP_INDEX + DATA_VINTAGE_MODE + scope where not inherited."""
    feature_version: str; time_kind: str; time_value: int; data_vintage_mode: str; scope: Optional[Ref] = None
    def __post_init__(self):
        if self.time_kind not in ("EVENT_TIME", "STEP_INDEX"):
            raise Refusal(self.time_kind, code="BAD_EXPECTED_KEY_TIME_KIND")
        if not self.feature_version or not self.data_vintage_mode:
            raise Refusal("incomplete key", code="EXPECTED_KEY_INCOMPLETE")

@dataclass(frozen=True)
class StructuredOmission:
    """Minimum fields V0.38 requires for authority-bearing non-delivery evidence; free text alone is insufficient."""
    feature_id: bytes; feature_version: str; reason_code: str; expected_key: ExpectedDependencyKey
    observed_state: Optional[str] = None; observed_available_asof: Optional[int] = None; dependency_ref: Optional[Ref] = None
    def __post_init__(self):
        if not self.feature_id or not self.feature_version or not self.reason_code:
            raise Refusal("omission needs feature id/version/reason", code="OMISSION_NOT_STRUCTURED")
        if not isinstance(self.expected_key, ExpectedDependencyKey):
            raise Refusal("EXPECTED_DEPENDENCY_KEY required", code="OMISSION_NO_EXPECTED_KEY")
        if self.expected_key.feature_version != self.feature_version:
            raise Refusal("key/feature version mismatch", code="OMISSION_KEY_MISMATCH")

@dataclass(frozen=True)
class VisibilityWatermark:
    """Tracker status-log position + resolver-observed time. Resolver observation only; never widens the causal set."""
    status_log_position: int; observed_time: int

@dataclass(frozen=True)
class FinalResolutionIdentity:
    consumer_id: str; manifest_or_dataset_binding_id: Optional[str]; scope: str; window_fence_id: str

@dataclass(frozen=True)
class NonDeliveryResolutionV038:
    request_id: str; identity: FinalResolutionIdentity; status: str; target_consumer: str; eligibility_as_of_t: int
    causal_policy_id: str; resolver_policy_id: str; temporal_contract_id: str; watermark: VisibilityWatermark
    omissions: Tuple[StructuredOmission, ...]; reason_codes: Tuple[str, ...]; created_ts: int
    issuer: str = "TRACKER_CONSUMER_GATEWAY"
    bound_health_resolution_ref: Optional[Ref] = None; bound_health_resolved_at: Optional[int] = None
    def __post_init__(self):
        if self.status not in NON_DELIVERY_STATUSES:
            raise Refusal(self.status, code="BAD_NON_DELIVERY_STATUS")
        if self.issuer != "TRACKER_CONSUMER_GATEWAY":
            raise Refusal(self.issuer, code="BAD_ISSUER")
        if self.status == NOT_READY and not self.omissions:
            raise Refusal("NOT_READY needs structured OMISSIONS", code="NOT_READY_WITHOUT_OMISSIONS")
        if (self.bound_health_resolution_ref is None) != (self.bound_health_resolved_at is None):
            raise Refusal("health ref/time travel together", code="HEALTH_PAIR")

def check_settlement(fence: int, settlement_delay: int, certified_max_visibility_lag: Optional[int], resolution_time: int) -> int:
    """Final resolution occurs at fence + SETTLEMENT_DELAY; delay must cover the certified max lag; unknown => fail closed.
    Returns the resolver observation time. Eligibility is still AVAILABLE_ASOF < fence only (the delay never widens it)."""
    if certified_max_visibility_lag is None:
        raise Refusal("certified visibility bound unavailable", code="SETTLEMENT_BOUND_UNAVAILABLE")
    if settlement_delay < certified_max_visibility_lag:
        raise Refusal("SETTLEMENT_DELAY below certified lag", code="SETTLEMENT_DELAY_TOO_SMALL")
    if resolution_time < fence + settlement_delay:
        raise Refusal("resolution before settlement point", code="RESOLUTION_BEFORE_SETTLEMENT")
    return fence + settlement_delay

def classify_late(available_asof: int, fence: int, publish_log_position: int, watermark: VisibilityWatermark,
                  omitted_by_resolver: bool = True) -> str:
    """V0.38 FORENSIC CLASSIFICATION."""
    if available_asof >= fence:
        return GENUINE_LATE
    if publish_log_position > watermark.status_log_position:
        return SETTLEMENT_BREACH
    if omitted_by_resolver:
        return RESOLVER_FAULT
    raise Refusal("pre-fence, visible at watermark, not omitted: not a late dependency", code="NOT_LATE")

class FinalResolutionStore:
    """Exactly one final outcome per resolution identity; REQUEST_ID maps many-to-one; retries reuse, never re-evaluate.

    BOUNDED CONTRACT (until a qualified provider supplies atomicity, D10): single PROCESS only. Within one process the
    check/evaluate/store sequence is serialised by one lock, a re-entrant call for an identity already being evaluated is refused
    (it would otherwise recurse or double-evaluate), the request id is RESERVED for the identity before evaluation (nested or concurrent calls with the same request id and another identity are refused; a failed call releases only a reservation it created), an evaluator that raises stores nothing (the identity stays unresolved and a
    later call may evaluate again), and an evaluator that returns None is refused (None cannot be told apart from 'no outcome').
    Nothing here protects against two processes or a restart: the map is in memory. That is an unresolved provider decision."""
    def __init__(self):
        import threading
        self._lock = threading.RLock()
        self._by_identity: Dict[FinalResolutionIdentity, object] = {}
        self._req_ids: Dict[tuple, FinalResolutionIdentity] = {}      # key = (consumer_id, request_id): H1 REQUEST_ID is consumer-local
        self._inflight = set()
        self.evaluations = 0
    def resolve(self, request_id: str, identity: FinalResolutionIdentity, evaluate):
        with self._lock:
            rk = (identity.consumer_id, request_id)
            bound = self._req_ids.get(rk)               # includes reservations held by in-flight evaluations
            if bound is not None and bound != identity:
                raise Refusal(request_id, code="REQUEST_ID_REBOUND_TO_OTHER_IDENTITY")
            if identity in self._by_identity:
                self._req_ids.setdefault(rk, identity)
                return copy.deepcopy(self._by_identity[identity])          # never fish for a different result; a detached copy, so a caller mutation cannot rewrite the final outcome
            if identity in self._inflight:
                raise Refusal(identity, code="REENTRANT_RESOLUTION")
            reserved_here = bound is None
            self._req_ids[rk] = identity            # reserve BEFORE evaluating: nested calls cannot rebind it
            self._inflight.add(identity)
            try:
                self.evaluations += 1
                out = evaluate()
                if out is None:
                    raise Refusal(identity, code="EVALUATOR_RETURNED_NO_OUTCOME")
                self._by_identity[identity] = copy.deepcopy(out)      # R35: the evaluator's object is NOT aliased into the immutable final store
                return copy.deepcopy(self._by_identity[identity])
            except BaseException:
                if reserved_here:
                    self._req_ids.pop(rk, None)     # failure policy: a failed call leaves no binding it created
                raise
            finally:
                self._inflight.discard(identity)
    def outcome_for(self, identity: FinalResolutionIdentity):
        with self._lock: o = self._by_identity.get(identity); return None if o is None else copy.deepcopy(o)
    def identity_of(self, consumer_id: str, request_id: str):
        with self._lock: return self._req_ids.get((consumer_id, request_id))
    def late_dependency_mutates(self, identity: FinalResolutionIdentity):
        with self._lock:
            if identity in self._by_identity:
                raise Refusal(identity, code="FINAL_WINDOW_IMMUTABLE")   # a late dependency may not re-resolve an expired window

H1_REQUIRED = ("CONSUMER_BINDING_ID", "CONSUMER_ID", "TARGET_CONSUMER", "REQUEST_ID", "BOUND_FEATURE_IDS_AND_VERSIONS",
               "BOUND_PAYLOAD_OR_PACKAGE_ID", "PACKAGE_CLASS", "PACKAGE_HASH", "PURPOSE", "TEMPORAL_CONTRACT_ID",
               "ELIGIBILITY_AS_OF_T", "SOURCE_VINTAGE_CAUSAL_POLICY_ID", "RESOLVER_POLICY_ID", "OMISSIONS_EXCLUSIONS_REASON_CODES",
               "FINAL_PACKAGE_HASH", "CREATED_TS", "ISSUER", "BOUND_HEALTH_RESOLUTION_REF", "BOUND_HEALTH_RESOLVED_AT")
ML_MANIFEST_CLASSES = ("OFFICIAL_ML_TRAINING_MANIFEST", "ML_SIMULATION_MANIFEST", "RESEARCH_MANIFEST")      # Contract V0.38 T-ML (Composer Contract section 11 classes)
GENERATION_AUTHORITY_CLASSES = ("ML_STANDALONE", "ML_FW_AUGMENTED")                                              # Contract V0.38 T-ML (ML Core)
def h1_is_ml(fields: dict) -> bool:
    """ML applicability is DERIVED from the bound consumer/package classes, never from a caller flag: CONSUMER_ID == ML or PACKAGE_CLASS == ML_PACKAGE."""
    return fields.get("CONSUMER_ID") == "ML" or fields.get("PACKAGE_CLASS") == "ML_PACKAGE"
def check_h1(fields: dict, decision_window: bool = True) -> None:
    """Field-PRESENCE check of the Connected Contract V0.37 H1 CONSUMER_BINDING list (as carried by V0.38). ML_MANIFEST_CLASS / GENERATION_AUTHORITY_CLASS are REQUIRED WHEN CONSUMER_ID = ML (H1); applicability is derived from the
    record (`h1_is_ml`) and cannot be waived by a caller flag (R29). Values must come from the source vocabularies; whether they are the classes of the ACTUAL bound manifest/generation is a source-owned binding checked by
    `check_h1_ml_binding` (T-ML: applicability and classes derive from the bound manifest and generation, never from the receiver). Byte encoding of PACKAGE_HASH / FINAL_PACKAGE_HASH is not defined by any source read (D13)."""
    need = list(H1_REQUIRED)
    if decision_window: need.append("RESOLUTION_VISIBILITY_WATERMARK")
    ml = h1_is_ml(fields)
    if ml: need += ["ML_MANIFEST_CLASS", "GENERATION_AUTHORITY_CLASS"]
    missing = [k for k in need if fields.get(k) is None]
    if missing:
        raise Refusal(",".join(missing), code="H1_FIELD_MISSING")
    if fields["ISSUER"] != "TRACKER_CONSUMER_GATEWAY":
        raise Refusal(fields["ISSUER"], code="BAD_ISSUER")
    if fields["PACKAGE_CLASS"] not in ("FW_PACKAGE", "ML_PACKAGE", "NEUTRAL_GOVERNED_PACKAGE"):
        raise Refusal(fields["PACKAGE_CLASS"], code="BAD_PACKAGE_CLASS")   # lane names are not PACKAGE_CLASS values (V0.38)
    if (fields["CONSUMER_ID"] == "FW" and fields["PACKAGE_CLASS"] == "ML_PACKAGE") or (fields["CONSUMER_ID"] == "ML" and fields["PACKAGE_CLASS"] == "FW_PACKAGE"):
        raise Refusal("%s/%s" % (fields["CONSUMER_ID"], fields["PACKAGE_CLASS"]), code="H1_CONSUMER_PACKAGE_CLASS_MISMATCH")      # ML_PACKAGE != FW_PACKAGE; one binding, one consumer
    if ml:
        if fields["ML_MANIFEST_CLASS"] not in ML_MANIFEST_CLASSES: raise Refusal(str(fields["ML_MANIFEST_CLASS"]), code="H1_ML_MANIFEST_CLASS_UNKNOWN")
        if fields["GENERATION_AUTHORITY_CLASS"] not in GENERATION_AUTHORITY_CLASSES: raise Refusal(str(fields["GENERATION_AUTHORITY_CLASS"]), code="H1_GENERATION_AUTHORITY_CLASS_UNKNOWN")

def check_h1_ml_binding(fields: dict, bound_manifest_class, bound_generation_authority_class) -> None:
    """The source-owned part: the classes carried in H1 must equal those of the ACTUAL bound ML manifest / generation, supplied by their owner. Without that owner input the H1 classes are only vocabulary-valid, not verified
    (an exact held slot; nothing is inferred)."""
    check_h1(fields)
    if not h1_is_ml(fields): raise Refusal("not an ML binding", code="H1_NOT_ML")
    if (fields["ML_MANIFEST_CLASS"], fields["GENERATION_AUTHORITY_CLASS"]) != (bound_manifest_class, bound_generation_authority_class): raise Refusal("H1 ML classes differ from the bound manifest/generation", code="H1_ML_CLASSES_NOT_THE_BOUND_ONES")

def to_v038(nd: "C.NonDeliveryResolution", identity: FinalResolutionIdentity, key: ExpectedDependencyKey, wm: VisibilityWatermark,
            target_consumer: str, causal_policy_id: str, resolver_policy_id: str, temporal_contract_id: str, created_ts: int,
            observed_state: Optional[str] = None, observed_asof: Optional[int] = None) -> NonDeliveryResolutionV038:
    om = StructuredOmission(nd.feature_id, nd.feature_version, nd.reason, key, observed_state, observed_asof)
    return NonDeliveryResolutionV038(nd.request_id, identity, status_for_reason(nd.reason), target_consumer, nd.fence,
                                     causal_policy_id, resolver_policy_id, temporal_contract_id, wm, (om,), (nd.reason,), created_ts)

# ---- BOTH: one request, two consumers -> two separate packages, bindings and final resolutions -------------------------------
# Connected Contract V0.37 H1: CONSUMER_ID = FW | ML | other authorized consumer; PACKAGE_CLASS = FW_PACKAGE | ML_PACKAGE | NEUTRAL...;
# REQUEST_ID is a consumer-local reference; TARGET_CONSUMER comes from the request context. Companion D02 (supporting proposal): BOTH = separate
# FW/ML package and binding ids and hashes.
BOTH_LANES = {"FW": {"PACKAGE_CLASS": "FW_PACKAGE", "ML": False}, "ML": {"PACKAGE_CLASS": "ML_PACKAGE", "ML": True}}
BOTH_DISTINCT_FIELDS = ("CONSUMER_BINDING_ID", "BOUND_PAYLOAD_OR_PACKAGE_ID", "PACKAGE_HASH", "FINAL_PACKAGE_HASH")

def check_both_separation(fw: dict, ml: dict) -> None:
    """Each record is H1-checked for ITS lane (ML with ML-only fields), must carry that lane's source-defined CONSUMER_ID ('FW'/'ML') and
    PACKAGE_CLASS, TARGET_CONSUMER == 'BOTH' (target comes from the request context), and the two must differ in every identity field.
    Swapped, unknown or arbitrary consumer labels are refused. Hash BYTE ENCODING is undefined (D13): inequality of claimed values only."""
    for lane, rec in (("FW", fw), ("ML", ml)):
        if rec.get("CONSUMER_ID") != lane:                          # lane identity first (exact lane code), then the H1 check whose ML applicability is derived from the record
            raise Refusal("%s:%r" % (lane, rec.get("CONSUMER_ID")), code="BOTH_LANE_CONSUMER_ID_WRONG")
        if rec.get("PACKAGE_CLASS") != BOTH_LANES[lane]["PACKAGE_CLASS"]:
            raise Refusal("%s:%s" % (lane, rec.get("PACKAGE_CLASS")), code="BOTH_LANE_PACKAGE_CLASS_MISMATCH")
        check_h1(rec)
        if rec["TARGET_CONSUMER"] != "BOTH":
            raise Refusal("%s:%s" % (lane, rec["TARGET_CONSUMER"]), code="BOTH_LANE_TARGET_NOT_BOTH")
    for f in BOTH_DISTINCT_FIELDS:
        if fw[f] == ml[f]:
            raise Refusal("%s=%r" % (f, fw[f]), code="BOTH_LANES_SHARE_IDENTITY_FIELD")

def check_binding_matches_identity(h1: dict, identity: FinalResolutionIdentity) -> None:
    """The checked binding and the resolution identity must agree: same consumer, and the same manifest/dataset binding id when the binding carries one."""
    if identity.consumer_id != h1["CONSUMER_ID"]:
        raise Refusal("%r!=%r" % (identity.consumer_id, h1["CONSUMER_ID"]), code="IDENTITY_CONSUMER_DIFFERS_FROM_BINDING")
    b = h1.get("MANIFEST_OR_DATASET_BINDING_ID")
    if b is not None and identity.manifest_or_dataset_binding_id != b:
        raise Refusal("%r!=%r" % (identity.manifest_or_dataset_binding_id, b), code="IDENTITY_BINDING_DIFFERS_FROM_BINDING")

def resolve_both(store: FinalResolutionStore, fw_h1: dict, ml_h1: dict, fw_identity: FinalResolutionIdentity,
                 ml_identity: FinalResolutionIdentity, evaluate_fw, evaluate_ml) -> dict:
    """Pair-validate first (a pair defect refuses BOTH lanes before any evaluation), then resolve each lane independently under its own
    consumer-local (consumer_id, REQUEST_ID) key through the ordinary store path: no alias namespace, no request-key suffix. A lane's
    failure is returned as that lane's refusal and never alters or blocks the other lane's stored outcome."""
    check_both_separation(fw_h1, ml_h1)
    check_binding_matches_identity(fw_h1, fw_identity)
    check_binding_matches_identity(ml_h1, ml_identity)
    out = {}
    for lane, h1, ident, ev in (("FW", fw_h1, fw_identity, evaluate_fw), ("ML", ml_h1, ml_identity, evaluate_ml)):
        try:
            out[lane] = ("RESOLVED", store.resolve(h1["REQUEST_ID"], ident, ev))
        except Refusal as e:
            out[lane] = ("REFUSED", e.code)
    return out
