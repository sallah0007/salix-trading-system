"""Connected Contract V0.38 delivery-failure objects (read from the operative V0.38 document; see docs/a07 evidence).

STATUS: field-level conformance objects + pure rules for NON_DELIVERY_RESOLUTION, EXPECTED_DEPENDENCY_KEY, structured
OMISSIONS, RESOLUTION_VISIBILITY_WATERMARK, final-resolution identity, settlement delay and forensic classification.
NOT built here, because no source gives bytes: FINAL_RESOLUTION_HASH / PACKAGE_HASH canonical encoding (open item D13).
This is NOT a connection to a real Gateway; the resolver in contracts.py remains a simulation."""
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
        self._req_ids: Dict[str, FinalResolutionIdentity] = {}
        self._inflight = set()
        self.evaluations = 0
    def resolve(self, request_id: str, identity: FinalResolutionIdentity, evaluate):
        with self._lock:
            bound = self._req_ids.get(request_id)               # includes reservations held by in-flight evaluations
            if bound is not None and bound != identity:
                raise Refusal(request_id, code="REQUEST_ID_REBOUND_TO_OTHER_IDENTITY")
            if identity in self._by_identity:
                self._req_ids.setdefault(request_id, identity)
                return self._by_identity[identity]          # never fish for a different result
            if identity in self._inflight:
                raise Refusal(identity, code="REENTRANT_RESOLUTION")
            reserved_here = bound is None
            self._req_ids[request_id] = identity            # reserve BEFORE evaluating: nested calls cannot rebind it
            self._inflight.add(identity)
            try:
                self.evaluations += 1
                out = evaluate()
                if out is None:
                    raise Refusal(identity, code="EVALUATOR_RETURNED_NO_OUTCOME")
                self._by_identity[identity] = out
                return out
            except BaseException:
                if reserved_here:
                    self._req_ids.pop(request_id, None)     # failure policy: a failed call leaves no binding it created
                raise
            finally:
                self._inflight.discard(identity)
    def late_dependency_mutates(self, identity: FinalResolutionIdentity):
        with self._lock:
            if identity in self._by_identity:
                raise Refusal(identity, code="FINAL_WINDOW_IMMUTABLE")   # a late dependency may not re-resolve an expired window

H1_REQUIRED = ("CONSUMER_BINDING_ID", "CONSUMER_ID", "TARGET_CONSUMER", "REQUEST_ID", "BOUND_FEATURE_IDS_AND_VERSIONS",
               "BOUND_PAYLOAD_OR_PACKAGE_ID", "PACKAGE_CLASS", "PACKAGE_HASH", "PURPOSE", "TEMPORAL_CONTRACT_ID",
               "ELIGIBILITY_AS_OF_T", "SOURCE_VINTAGE_CAUSAL_POLICY_ID", "RESOLVER_POLICY_ID", "OMISSIONS_EXCLUSIONS_REASON_CODES",
               "FINAL_PACKAGE_HASH", "CREATED_TS", "ISSUER", "BOUND_HEALTH_RESOLUTION_REF", "BOUND_HEALTH_RESOLVED_AT")
def check_h1(fields: dict, decision_window: bool = True, consumer_is_ml: bool = False) -> None:
    """Field-PRESENCE check of the Connected Contract V0.37 H1 CONSUMER_BINDING list (as carried by V0.38). Byte encoding
    of PACKAGE_HASH / FINAL_PACKAGE_HASH is not defined by any source read (D13)."""
    need = list(H1_REQUIRED)
    if decision_window: need.append("RESOLUTION_VISIBILITY_WATERMARK")
    if consumer_is_ml: need += ["ML_MANIFEST_CLASS", "GENERATION_AUTHORITY_CLASS"]
    missing = [k for k in need if fields.get(k) is None]
    if missing:
        raise Refusal(",".join(missing), code="H1_FIELD_MISSING")
    if fields["ISSUER"] != "TRACKER_CONSUMER_GATEWAY":
        raise Refusal(fields["ISSUER"], code="BAD_ISSUER")
    if fields["PACKAGE_CLASS"] not in ("FW_PACKAGE", "ML_PACKAGE", "NEUTRAL_GOVERNED_PACKAGE"):
        raise Refusal(fields["PACKAGE_CLASS"], code="BAD_PACKAGE_CLASS")   # lane names are not PACKAGE_CLASS values (V0.38)

def to_v038(nd: "C.NonDeliveryResolution", identity: FinalResolutionIdentity, key: ExpectedDependencyKey, wm: VisibilityWatermark,
            target_consumer: str, causal_policy_id: str, resolver_policy_id: str, temporal_contract_id: str, created_ts: int,
            observed_state: Optional[str] = None, observed_asof: Optional[int] = None) -> NonDeliveryResolutionV038:
    om = StructuredOmission(nd.feature_id, nd.feature_version, nd.reason, key, observed_state, observed_asof)
    return NonDeliveryResolutionV038(nd.request_id, identity, status_for_reason(nd.reason), target_consumer, nd.fence,
                                     causal_policy_id, resolver_policy_id, temporal_contract_id, wm, (om,), (nd.reason,), created_ts)

# ---- BOTH (R11): one request, two consumers -> two separate packages, bindings and final resolutions -------------------------
BOTH_LANES = ("FORWARD_WALK", "MACHINE_LEARNING")
BOTH_DISTINCT_FIELDS = ("CONSUMER_ID", "CONSUMER_BINDING_ID", "BOUND_PAYLOAD_OR_PACKAGE_ID", "PACKAGE_HASH", "FINAL_PACKAGE_HASH")
_LANE_PACKAGE_CLASS = {"FORWARD_WALK": "FW_PACKAGE", "MACHINE_LEARNING": "ML_PACKAGE"}

def check_both_separation(fw: dict, ml: dict) -> None:
    """Companion D02 (supporting proposal, not authority): BOTH = separate FW and ML package/binding identities and hashes.
    Each lane is H1-checked on its own (ML with its ML-only fields); the lanes must carry distinct values for every identity field and
    the lane-correct PACKAGE_CLASS; a shared value in any field is refused (one lane's package can never stand in for the other's).
    Hash BYTE ENCODING is still undefined (D13): this compares claimed values for inequality only; it does not recompute them."""
    check_h1(fw, consumer_is_ml=False)
    check_h1(ml, consumer_is_ml=True)
    for f in BOTH_DISTINCT_FIELDS:
        if fw[f] == ml[f]:
            raise Refusal("%s=%r" % (f, fw[f]), code="BOTH_LANES_SHARE_IDENTITY_FIELD")
    for lane, rec in (("FORWARD_WALK", fw), ("MACHINE_LEARNING", ml)):
        if rec["PACKAGE_CLASS"] != _LANE_PACKAGE_CLASS[lane]:
            raise Refusal("%s:%s" % (lane, rec["PACKAGE_CLASS"]), code="BOTH_LANE_PACKAGE_CLASS_MISMATCH")
        if rec["TARGET_CONSUMER"] not in (lane, "BOTH"):
            raise Refusal("%s:%s" % (lane, rec["TARGET_CONSUMER"]), code="BOTH_LANE_TARGET_MISMATCH")
    if fw["REQUEST_ID"] != ml["REQUEST_ID"]:
        raise Refusal("request", code="BOTH_LANES_DIFFERENT_REQUEST")

def resolve_both(store: FinalResolutionStore, request_id: str, fw_identity: FinalResolutionIdentity, ml_identity: FinalResolutionIdentity,
                 evaluate_fw, evaluate_ml) -> dict:
    """Resolve each lane independently (per-consumer failure separation). The lane-qualified request key lets one REQUEST_ID own two
    identities without tripping REQUEST_ID_REBOUND (the lane suffix is this implementation's choice; an OPEN source decision).
    A lane failure is returned as that lane's refusal and never alters or blocks the other lane's stored outcome."""
    if fw_identity.consumer_id == ml_identity.consumer_id or fw_identity == ml_identity:
        raise Refusal(request_id, code="BOTH_LANES_SHARE_RESOLUTION_IDENTITY")
    out = {}
    for lane, ident, ev in (("FORWARD_WALK", fw_identity, evaluate_fw), ("MACHINE_LEARNING", ml_identity, evaluate_ml)):
        try:
            out[lane] = ("RESOLVED", store.resolve("%s#%s" % (request_id, lane), ident, ev))
        except Refusal as e:
            out[lane] = ("REFUSED", e.code)
    return out
