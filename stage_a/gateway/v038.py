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
    """Exactly one final outcome per resolution identity; REQUEST_ID maps many-to-one; retries reuse, never re-evaluate."""
    def __init__(self):
        self._by_identity: Dict[FinalResolutionIdentity, object] = {}
        self._req_ids: Dict[str, FinalResolutionIdentity] = {}
        self.evaluations = 0
    def resolve(self, request_id: str, identity: FinalResolutionIdentity, evaluate):
        bound = self._req_ids.get(request_id)
        if bound is not None and bound != identity:
            raise Refusal(request_id, code="REQUEST_ID_REBOUND_TO_OTHER_IDENTITY")
        prior = self._by_identity.get(identity)
        if prior is not None:
            self._req_ids.setdefault(request_id, identity)
            return prior                                    # never fish for a different result
        self.evaluations += 1
        out = evaluate()
        self._by_identity[identity] = out
        self._req_ids[request_id] = identity
        return out
    def late_dependency_mutates(self, identity: FinalResolutionIdentity):
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
