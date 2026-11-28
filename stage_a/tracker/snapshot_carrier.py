"""R44: derive the Registry TRACKER_SNAPSHOT_MANIFEST (S4 p104-124) FROM the Core's owning resolved composition instead of hand-assembling it, then bind it (snapshot_binding).
Derived from Core records (never from the caller): instrument, query_asof, fence, per-timeframe resolved vintage, the selected parent per timeframe (canonical bar identity), provider/raw version/broker-UTC rule (recorded observation facts that must agree on ONE value).
Per-timeframe WATERMARK: a SOURCE-OWNED slot (`watermark_source`, callable timeframe -> int). No store source exists and none is invented; unbound => HELD (`PER_TIMEFRAME_WATERMARK_SOURCE_UNBOUND_HELD`). The Core journals the watermarks it was given and flags them supplied_unadmitted.
Fields no Core record carries (snapshot id, broker/UTC time identities, schema/calc-family version, quality/staleness, creation/effective/as-of identities, fence-read identity, enrichments) are EXPLICIT held inputs: missing/empty => refused, never defaulted. The result is a CANDIDATE manifest hash (no normative byte layout, D13) and authoritative=False."""
from ..errors import Refusal
from .registry_semantics import TrackerSnapshotManifest
from . import snapshot_binding as SB
WATERMARK_HELD = "PER_TIMEFRAME_WATERMARK_SOURCE_UNBOUND_HELD"
HELD_INPUTS = ("tracker_snapshot_id", "broker_server_time_identity", "utc_identity", "tracker_schema_calculation_family_version", "data_quality_missingness_staleness", "creation_effective_available_asof_identities", "fence_read_boundary_identity")
def resolve_and_bind(core, *, instrument, query_asof, fence, member_keys, parents_by_tf, watermark_source, timeframe, held_inputs, enrichment_ids=()):
    if not callable(watermark_source): raise Refusal("watermark_source", code=WATERMARK_HELD)
    if not (isinstance(held_inputs, dict) and set(held_inputs) == set(HELD_INPUTS) and all(isinstance(v, str) and v for v in held_inputs.values())): raise Refusal("held_inputs", code="SNAPSHOT_CARRIER_HELD_INPUTS_INCOMPLETE")
    if not isinstance(parents_by_tf, dict) or not parents_by_tf: raise Refusal("streams", code="SNAPSHOT_STREAMS_INVALID")
    wm = {}
    for tf in sorted(parents_by_tf):
        w = watermark_source(tf)
        if type(w) is not int or w < 0: raise Refusal(tf, code="SNAPSHOT_WATERMARK_SOURCE_RETURNED_NON_WATERMARK")
        wm[tf] = w
    out = core.resolve_sealed_snapshot(instrument, query_asof, fence, member_keys, parents_by_tf, wm)
    if out["state"] != "RESOLVED": return {"state": out["state"], "reason": out.get("reason", ""), "manifest": None, "bound": None, "resolved_manifest_hash": out.get("resolved_manifest_hash")}
    body = core.resolved_manifest(out["resolved_manifest_hash"]); ents = {e["timeframe"]: e for e in body["entries"]}
    if timeframe not in ents: raise Refusal(timeframe, code="SNAPSHOT_FIELD_DISAGREES_WITH_OWNING_OBSERVATIONS")
    vint = {e["vintage"] for e in ents.values()}
    if len(vint) != 1: raise Refusal("vintage", code="SNAPSHOT_COMPOSITION_NOT_SINGLE_VINTAGE_RESOLVED")
    rec = {}
    for e in ents.values():
        for c in e["candidates"]:
            f = core.observation_facts(c[0])
            if f is None: raise Refusal(c[0], code="SNAPSHOT_MEMBER_OBSERVATION_NOT_USABLE")
            for mf, of in SB.DERIVED_FROM_RECORDED_FACTS: rec.setdefault(mf, set()).add(f[of])
    if any(len(v) != 1 for v in rec.values()) or set(rec) != {m for m, _ in SB.DERIVED_FROM_RECORDED_FACTS}: raise Refusal("facts", code="SNAPSHOT_FIELD_DISAGREES_WITH_RECORDED_OBSERVATION_FACTS")
    m = TrackerSnapshotManifest(tracker_snapshot_id=held_inputs["tracker_snapshot_id"], instrument_id=body["instrument"], timeframe_or_event_class=timeframe, canonical_bar_or_event_identity=ents[timeframe]["parent_id"],
        broker_server_time_identity=held_inputs["broker_server_time_identity"], utc_identity=held_inputs["utc_identity"], broker_utc_rule_version=next(iter(rec["broker_utc_rule_version"])), source_provider_identity=next(iter(rec["source_provider_identity"])),
        raw_source_version=next(iter(rec["raw_source_version"])), tracker_schema_calculation_family_version=held_inputs["tracker_schema_calculation_family_version"], data_quality_missingness_staleness=held_inputs["data_quality_missingness_staleness"],
        creation_effective_available_asof_identities=held_inputs["creation_effective_available_asof_identities"], data_vintage_mode=next(iter(vint)), external_enrichment_ids=tuple(enrichment_ids), fence_read_boundary_identity=held_inputs["fence_read_boundary_identity"],
        query_asof=body["query_asof"], snapshot_fence_ts=body["fence"], timeframe_watermarks=tuple(sorted((tf, e["watermark"]) for tf, e in ents.items())))
    return {"state": "RESOLVED", "reason": "", "manifest": m, "bound": SB.bind_snapshot_manifest(core, m, out["resolved_manifest_hash"]), "resolved_manifest_hash": out["resolved_manifest_hash"]}
