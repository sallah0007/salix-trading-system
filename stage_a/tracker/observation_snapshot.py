"""R54: the OBSERVATION-TO-SNAPSHOT adapter (generic, candidate). It derives the snapshot members and per-timeframe parent candidates from the Core's OWN recorded observation receipts (`TrackerCore.observations_for`: recorded facts, availability and vintage; no caller-named member list) and hands them to the existing `snapshot_carrier.resolve_and_bind` (seal -> per-timeframe selection only among sealed members -> vintage from the sealed records -> candidate manifest bound with authoritative=False).
Ports it does NOT define (each HELD when unbound, never defaulted): `parent_complete(key, facts) -> bool` (the segmentation/completeness proof is `time_family.parent_complete` territory and no source supplies the rule), `watermark_source(timeframe) -> int` (carrier slot, unbound => PER_TIMEFRAME_WATERMARK_SOURCE_UNBOUND_HELD) and the carrier's explicit held inputs. The observation PAYLOAD is never decoded here: nothing in this path needs the byte layout (B01/D13), only the recorded fact NAMES and the Core's own availability/vintage records.
What is NOT proved: that the recorded facts are true (provider qualification), that a timeframe's parents are COMPLETE (supplied port), that the watermark is a real store watermark. Reference simulation only; no calendar, freshness threshold or encoding is invented."""
from ..errors import Refusal
from . import snapshot_carrier as SC
PORT_HELD = "OBSERVATION_SNAPSHOT_PARENT_COMPLETENESS_PORT_UNBOUND_HELD"
class ObservationSnapshotAdapter:
    def __init__(self, core, *, parent_complete=None, watermark_source=None):
        if core is None or not hasattr(core, "observations_for"): raise Refusal("core", code="OBSERVATION_SNAPSHOT_CORE_MISSING")
        for n, f in (("parent_complete", parent_complete), ("watermark_source", watermark_source)):
            if f is not None and not callable(f): raise Refusal(n, code="OBSERVATION_SNAPSHOT_PORT_INVALID")
        self._core, self._pc, self._wm = core, parent_complete, watermark_source
    def resolve(self, *, instrument, query_asof, fence, timeframe, held_inputs, enrichment_ids=()):
        if self._pc is None: raise Refusal("parent_complete", code=PORT_HELD)
        rows = self._core.observations_for(instrument)
        if not rows: return {"state": "HELD_NO_RECORDED_OBSERVATIONS", "reason": "ZERO_ROWS_IS_NOT_A_COMPLETED_SEARCH", "manifest": None, "bound": None, "resolved_manifest_hash": None}
        parents = {}
        for key, facts, avail, vint in rows:
            if avail >= fence: continue                                                                                             # the Core's half-open fence (availability < fence) excludes it from the seal: it is never offered as a parent candidate
            c = self._pc(key, facts)
            if type(c) is not bool: raise Refusal(key, code="OBSERVATION_SNAPSHOT_COMPLETENESS_NOT_BOOLEAN")                     # an unreadable proof is not "complete"
            parents.setdefault(facts["timeframe"], []).append((key, c))
        return SC.resolve_and_bind(self._core, instrument=instrument, query_asof=query_asof, fence=fence, member_keys=[r[0] for r in rows], parents_by_tf={tf: sorted(v) for tf, v in parents.items()},
                                   watermark_source=self._wm, timeframe=timeframe, held_inputs=held_inputs, enrichment_ids=enrichment_ids)
