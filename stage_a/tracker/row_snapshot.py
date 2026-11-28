"""R53 per-ROW consumption against a resolved Core snapshot composition (Registry p101-102 per-timeframe resolved vintage/watermark, no false simultaneity; p121-123 no independent latest-value query, MIXED_VINTAGE invalid, half-open fence available_asof < SNAPSHOT_FENCE_TS).
`row_snapshot_blockers(snapshot, delivered)` checks ONE delivered row entry (`DeliveredFeatureEntry`, issued by the Gateway) against the Core's own journaled resolved composition (`core.resolved_manifest`): single-vintage RESOLVED; instrument and timeframe are members of that composition; the row's data_vintage_mode equals the per-timeframe resolved vintage; the row's AVAILABLE_ASOF is strictly before the snapshot fence (half-open) and not after that timeframe's recorded watermark (visibility reading: a value is visible only if available_asof <= watermark; CANDIDATE reading).
The label relations row id bytes <-> instrument/timeframe LABELS are SUPPLIED ports (`instrument_of`, `timeframe_of`): unbound or unmapped => HELD blocker, never a guessed equality. The per-timeframe watermark VALUES are whatever the Core journaled (supplied_unadmitted: no store source for them is appointed). Returns a tuple of blocker codes; () means none found, which authorizes nothing."""
HELD_PORT = "ROW_SNAPSHOT_LABEL_PORT_UNBOUND_HELD"
def row_snapshot_blockers(snapshot, delivered):
    if isinstance(snapshot, dict) and snapshot.get("core") is not None and snapshot.get("resolved_manifest_hash") is None: return ("ROW_SNAPSHOT_RESOLVED_MANIFEST_ABSENT_HELD",)      # an UNRESOLVED / mixed-vintage composition has no resolved manifest to consume
    if not (isinstance(snapshot, dict) and snapshot.get("core") is not None and isinstance(snapshot.get("resolved_manifest_hash"), str) and snapshot["resolved_manifest_hash"]): return ("ROW_SNAPSHOT_INPUT_INVALID",)
    try: body = snapshot["core"].resolved_manifest(snapshot["resolved_manifest_hash"])
    except Exception: body = None
    if not isinstance(body, dict): return ("ROW_SNAPSHOT_RESOLVED_MANIFEST_ABSENT_HELD",)
    if body.get("state") != "RESOLVED" or body.get("mixed_policy") is not None or not body.get("entries"): return ("ROW_SNAPSHOT_NOT_SINGLE_VINTAGE_RESOLVED",)
    ents = {e["timeframe"]: e for e in body["entries"]}; out = []
    iof, tof = snapshot.get("instrument_of"), snapshot.get("timeframe_of")
    if not (callable(iof) and callable(tof)): return (HELD_PORT,)
    try: ins, tf = iof(delivered.instrument_id), tof(delivered.timeframe_id)
    except Exception: return (HELD_PORT,)
    if ins is None or tf is None: return (HELD_PORT,)
    if ins != body["instrument"]: out.append("ROW_SNAPSHOT_INSTRUMENT_NOT_IN_COMPOSITION")
    e = ents.get(tf)
    if e is None: out.append("ROW_SNAPSHOT_TIMEFRAME_NOT_IN_COMPOSITION"); return tuple(out)
    if delivered.data_vintage_mode != e["vintage"]: out.append("ROW_SNAPSHOT_VINTAGE_DIFFERS_FROM_TIMEFRAME_RESOLUTION")
    if not delivered.available_asof < body["fence"]: out.append("ROW_SNAPSHOT_AVAILABLE_ASOF_NOT_BEFORE_FENCE")
    if delivered.available_asof > e["watermark"]: out.append("ROW_SNAPSHOT_AVAILABLE_ASOF_AFTER_TIMEFRAME_WATERMARK")
    return tuple(out)
