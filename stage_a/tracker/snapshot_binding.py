"""R38: bind a Registry `TrackerSnapshotManifest` (p105-124) to its OWNING observations: the Core's journaled resolved-snapshot composition (sealed observation members -> per-timeframe resolution; `TrackerCore.resolve_sealed_snapshot` / `resolved_manifest`). The manifest is accepted as bound ONLY IF every field the Core actually holds agrees EXACTLY: instrument, query_asof, fence, the per-timeframe watermark set (same timeframes, same values; no timeframe left unmatched either way), and the vintage the sealed records carry (equal to `data_vintage_mode` for every entry; the Core's vintage label vocabulary is not source-mapped, so an unequal label REFUSES, never guessed). A mixed-vintage or unresolved composition refuses.
Fields the Core does NOT hold (provider identity, raw source version, broker/UTC rule, calendar identity, quality, creation/effective identities, enrichment ids, fence read identity ...) are listed in `unbound_fields` as SUPPLIED-NOT-DERIVED: this binder does not pretend to derive them. `authoritative` is always False (the manifest byte layout/hash is a labelled candidate; no admission). Clears no gate."""
from dataclasses import dataclass, fields as dc_fields
from ..errors import Refusal
from .registry_semantics import TrackerSnapshotManifest
HELD_FIELDS = ("broker_server_time_identity", "utc_identity", "broker_utc_rule_version", "source_provider_identity", "raw_source_version", "tracker_schema_calculation_family_version", "data_quality_missingness_staleness", "creation_effective_available_asof_identities", "external_enrichment_ids", "fence_read_boundary_identity", "canonical_bar_or_event_identity", "tracker_snapshot_id")
@dataclass(frozen=True)
class BoundSnapshot:
    manifest_hash: str; resolved_manifest_hash: str; base_seal_hash: str; unbound_fields: tuple; authoritative: bool = False
def bind_snapshot_manifest(core, manifest, resolved_manifest_hash) -> BoundSnapshot:
    if not isinstance(manifest, TrackerSnapshotManifest) or not isinstance(resolved_manifest_hash, str) or not resolved_manifest_hash: raise Refusal("manifest", code="SNAPSHOT_BINDING_INPUT_INVALID")
    manifest.validate(); body = core.resolved_manifest(resolved_manifest_hash)
    if body is None: raise Refusal(resolved_manifest_hash, code="SNAPSHOT_RESOLVED_MANIFEST_NOT_IN_CORE")
    if body.get("mixed_policy") is not None or body.get("state") in (None, "UNRESOLVED_HELD"): raise Refusal(str(body.get("state")), code="SNAPSHOT_COMPOSITION_NOT_SINGLE_VINTAGE_RESOLVED")
    if body["instrument"] != manifest.instrument_id: raise Refusal("instrument", code="SNAPSHOT_FIELD_DISAGREES_WITH_OWNING_OBSERVATIONS")
    if (body["query_asof"], body["fence"]) != (manifest.query_asof, manifest.snapshot_fence_ts): raise Refusal("asof/fence", code="SNAPSHOT_FIELD_DISAGREES_WITH_OWNING_OBSERVATIONS")
    ents = {e["timeframe"]: e for e in body["entries"]}; wm = dict(manifest.timeframe_watermarks)
    if set(ents) != set(wm): raise Refusal(",".join(sorted(set(ents) ^ set(wm))), code="SNAPSHOT_TIMEFRAME_SET_DISAGREES")
    for tf, e in ents.items():
        if e["watermark"] != wm[tf]: raise Refusal(tf, code="SNAPSHOT_WATERMARK_DISAGREES_WITH_OWNING_RESOLUTION")
        if e["vintage"] != manifest.data_vintage_mode: raise Refusal(tf, code="SNAPSHOT_VINTAGE_LABEL_NOT_COMPARABLE_HELD")
    return BoundSnapshot(manifest.manifest_hash(), resolved_manifest_hash, body["base_seal_hash"], tuple(f for f in HELD_FIELDS))
