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

def _xref(tables, r):
    if r is None: return None
    if r.ref_type not in tables.ref_types: raise Refusal(r.ref_type, code="REF_TYPE_NOT_IN_SUPPLIED_TABLE")
    return (tables.ref_types[r.ref_type], r.target_id, r.target_version, r.target_hash)

def _enum(tables, name, sym):
    t = tables.enums.get(name)
    if t is None or sym not in t: raise Refusal("%s:%r" % (name, sym), code="ENUM_SYMBOL_NOT_IN_SUPPLIED_TABLE")
    return t[sym]

def independent_view(tables, entry) -> dict:
    """Plain-data view of the entry for the INDEPENDENT composition (refs -> (type code, id, version, hash|None); enum symbols -> codes from the SUPPLIED table; nothing is numbered here)."""
    d = {f: getattr(entry, f) for f in ANNEX_XII_FIELDS}
    for f in ("fit_generation_ref", "source_or_causal_policy_ref", "bound_health_resolution_ref", "canonical_transition_ref"): d[f] = _xref(tables, d[f])
    d["data_vintage_mode"] = _enum(tables, "DATA_VINTAGE_MODE", d["data_vintage_mode"]); d["chain_status_at_bind"] = _enum(tables, "CHAIN_STATUS", d["chain_status_at_bind"])
    om = []
    for v in d["omissions_exclusions_reason_codes"]:
        if not (isinstance(v, tuple) and v): raise Refusal("omission tag", code="OMISSION_MALFORMED")
        om.append(("ENUM", v[1], _enum(tables, v[1], v[2])) if v[0] == "ENUM" and len(v) == 3 else ("REF", _xref(tables, v[1])) if v[0] == "REF" and len(v) == 2 else (_ for _ in ()).throw(Refusal("omission tag", code="OMISSION_MALFORMED")))
    d["omissions_exclusions_reason_codes"] = om
    return d

def verify_delivered(tables, entry, claimed_hash: bytes) -> None:
    """Read-only consumer check: exact schema type (no look-alike), complete Annex field set, and the hash RE-DERIVED by the independent composition (schema.independent: its own field order/presence/width rules, not the
    producer's `objects.delivered_hash`). Any refusal from the independent side (range/presence/unknown code) is a refusal here; disagreement with the claimed hash is HASH_MISMATCH."""
    if type(entry) is not DeliveredFeatureEntry: raise Refusal(type(entry).__name__, code="NOT_THE_FROZEN_DELIVERED_ENTRY")
    if tuple(entry.__dataclass_fields__) != ANNEX_XII_FIELDS: raise Refusal("field set", code="DELIVERED_ENTRY_FIELDS_DIFFER_FROM_ANNEX")
    from ..schema import independent as X
    try: h = X.delivered_hash(independent_view(tables, entry), tables.enums)
    except (ValueError, TypeError, KeyError, AttributeError) as e: raise Refusal(str(e), code="DELIVERED_ENTRY_NOT_INDEPENDENTLY_COMPOSABLE")
    if h != claimed_hash: raise Refusal("hash", code="HASH_MISMATCH")
