"""Forward-Walk receiving CONTRACT (Annex §XIII). Existing connector only: Tracker -> Gateway -> FW. STATUS: validator over
Gateway Binding objects + lane classification; NOT a connection to the real FW. FW preserves the delivered entry exactly."""
from ..errors import Refusal
from ..gateway.contracts import Binding, NonDeliveryResolution, AbsenceApplied, DependencyEntry, REQUIRED
from ..schema import objects as O
from ..gateway.outcome_binding import check_dependency_outcome

def receive_verified(binding, expected: DependencyEntry, instrument_id: bytes, timeframe_id: bytes, tables, gateway, require_current=True):
    """The VERIFIED receiving path: the Gateway that issued the outcome is REQUIRED (no gateway -> refusal), so Binding, AbsenceApplied and NonDeliveryResolution are all checked against the
    stored immutable Gateway outcome. `receive(..., gateway=None)` is SHAPE-ONLY (no origin proof) and must not be presented as verified delivery."""
    if gateway is None:
        raise Refusal("verified receive needs the issuing Gateway", code="GATEWAY_REQUIRED_FOR_VERIFIED_RECEIVE")
    return receive(binding, expected, instrument_id, timeframe_id, tables, require_current, gateway)

def receive(binding, expected: DependencyEntry, instrument_id: bytes, timeframe_id: bytes, tables, require_current=True,
            gateway=None):
    if isinstance(binding, NonDeliveryResolution):
        check_dependency_outcome(binding, expected, gateway)                  # a forged/foreign non-delivery is rejected as such before it can mean anything
        raise Refusal(binding.reason, code="NON_DELIVERY")                    # settlement/non-delivery failure
    if isinstance(binding, AbsenceApplied):
        check_dependency_outcome(binding, expected, gateway) if expected.requirement_class != REQUIRED else None
        if expected.requirement_class == REQUIRED:
            raise Refusal("required dependency absent", code="REQUIRED_DEPENDENCY_ABSENT")
        return binding
    if not isinstance(binding, Binding):
        raise Refusal(type(binding).__name__, code="NOT_A_GATEWAY_BINDING")
    e = binding.entry
    if e.feature_version != expected.feature_version or e.feature_id != expected.feature_id:
        raise Refusal("version", code="WRONG_VERSION")
    if e.instrument_id != instrument_id or e.timeframe_id != timeframe_id:
        raise Refusal("scope", code="WRONG_SCOPE")
    if e.published_projection_name != expected.expected_projection:
        raise Refusal("projection", code="WRONG_PROJECTION")
    if O.delivered_hash(tables, e) != binding.delivered_feature_hash:
        raise Refusal("hash", code="HASH_MISMATCH")
    if require_current and e.chain_status_at_bind != "CURRENT":
        raise Refusal(e.chain_status_at_bind, code="CHAIN_STATUS_NOT_CURRENT")
    if e.canonical_transition_ref is None or e.bound_health_resolution_ref is None:
        raise Refusal("lineage", code="LINEAGE_MISSING")
    if gateway is not None and gateway.outcome(binding.request_id) is not binding:
        raise Refusal("not the stored Gateway binding", code="BINDING_NOT_FROM_GATEWAY")
    return binding        # exact preservation: same object, nothing re-derived
