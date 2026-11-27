"""R27 Build Plan s13A: the ONE owner of the DeliveredFeatureEntry (frozen Typed Annex V1.2 section XII; hash coverage in the Annex hash section). The object is `schema.objects.DeliveredFeatureEntry` (exact Annex field list/order;
no shortened or consumer-specific variant). FW `receive`/ML `build_row` consume it READ-ONLY through `verify_delivered`; they never construct it. Semantic hash composition is independently re-derived in `schema.independent.delivered_hash`
(field selection/order/presence), sharing only primitive writers. The Gateway (`SimulatedGateway.resolve`) constructs entries ONLY via `build_delivered_entry`. Real Gateway/Contract integration, hash byte-domain admission: unchanged inputs."""
from ..errors import Refusal
from ..schema import objects as O

DeliveredFeatureEntry = O.DeliveredFeatureEntry
ANNEX_XII_FIELDS = ("feature_id", "feature_version", "quant_manifest_hash", "instrument_id", "timeframe_id", "materialization_version", "step_index", "event_time", "logical_encoding_version",
                    "published_projection_name", "published_projection_bits", "published_projection_hash", "fit_generation_ref", "data_vintage_mode", "available_asof", "chain_status_at_bind",
                    "source_or_causal_policy_ref", "bound_health_resolution_ref", "bound_health_resolved_at", "canonical_transition_ref", "omissions_exclusions_reason_codes")

def build_delivered_entry(row, chain_status: str, health_ref, health_resolved_at: int, omissions=()) -> DeliveredFeatureEntry:
    """The only constructor path. Every field is taken from the published row or the bind-time inputs; nothing is omitted or reinterpreted."""
    return O.DeliveredFeatureEntry(
        feature_id=row.feature_id, feature_version=row.feature_version, quant_manifest_hash=row.quant_manifest_hash, instrument_id=row.instrument_id, timeframe_id=row.timeframe_id,
        materialization_version=row.materialization_version, step_index=row.step_index, event_time=row.event_time, logical_encoding_version=row.logical_encoding_version,
        published_projection_name=row.published_projection_name, published_projection_bits=row.published_projection_bits, published_projection_hash=row.published_projection_hash,
        fit_generation_ref=row.fit_generation_ref, data_vintage_mode=row.data_vintage_mode, available_asof=row.available_asof, chain_status_at_bind=chain_status,
        source_or_causal_policy_ref=row.source_or_causal_policy_ref, bound_health_resolution_ref=health_ref, bound_health_resolved_at=health_resolved_at,
        canonical_transition_ref=row.canonical_transition_ref, omissions_exclusions_reason_codes=tuple(omissions))

def verify_delivered(tables, entry, claimed_hash: bytes) -> None:
    """Read-only consumer check: exact schema type (no look-alike), complete Annex field set, hash recomputed over the canonical encodings."""
    if type(entry) is not DeliveredFeatureEntry: raise Refusal(type(entry).__name__, code="NOT_THE_FROZEN_DELIVERED_ENTRY")
    if tuple(entry.__dataclass_fields__) != ANNEX_XII_FIELDS: raise Refusal("field set", code="DELIVERED_ENTRY_FIELDS_DIFFER_FROM_ANNEX")
    if O.delivered_hash(tables, entry) != claimed_hash: raise Refusal("hash", code="HASH_MISMATCH")
