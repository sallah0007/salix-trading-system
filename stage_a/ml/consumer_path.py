"""R43: the ML consumer-side INTEGRATION over the SAME objects the Tracker path produced (Gateway outcome + its final-resolution store), not a pile of unit-tested helpers.
One call, `MLConsumerPath.consume`, drives in order, each step on the real public candidate objects and each refusing/holding rather than inferring:
  1. `DatasetAuthority.request_binding`: the dataset manifest is linked to the consumer binding ONLY for an ML outcome the SAME Gateway and the SAME final store issued (reverse H1 link; no forward CONSUMER_BINDING field, no CBID == manifest-binding forcing);
  2. `receiver.build_row`: the Gateway-issued outcome is re-verified by the consumer (exact owned entry, hash re-derived, vintage, issued-by-this-gateway); a required non-delivery EXCLUDES the row (no consumption follows);
  3. the revoked-ancestry gate over the DECLARED union must be CLEAR (unknown/revoked => BLOCKED);
  4. the writer/finalizer facade `correlate` must be VERIFIED_AGAINST_REGISTRY for the named generation manifest (recorded write + granted finalize);
  5. the request snapshot is ISSUED by the generation registry (refuses an ineligible/revoked generation);
  6. all six joins are checked against the REAL registries' indexes (binding->manifest reverse index, manifest hash index, the issued snapshot) with the caller's join record, plus cross-object coherence (J1 binding id == the issued identity's binding id; J4/J5/snapshot name one generation).
The result is ALWAYS `qualified=False` and lists `held` inputs (principal grants, J2 catalog, J3 Health service, J6 exposure ledger instances, native ML forward fields): source-owned inputs stay exactly held. Grants here are whatever the caller's registries were built with (test labels in tests); nothing is appointed."""
from dataclasses import dataclass
from ..errors import Refusal
from . import receiver as MLR, six_joins as SJ
def _s(x): return isinstance(x, str) and bool(x)
@dataclass(frozen=True)
class MLConsumption:
    row: object
    binding_health: object
    gate: object
    generation: object
    snapshot: object
    joins: object
    blockers: tuple
    held: tuple
    qualified: bool = False
    @property
    def usable_for_simulation(self): return not self.blockers
HELD = ("ML_PRINCIPAL_GRANTS_ARE_CALLER_SUPPLIED_NOT_APPOINTED", "J2_CATALOG_SNAPSHOT_INSTANCE_IF_NOT_SUPPLIED", "J3_BIND_TIME_HEALTH_SERVICE_INSTANCE", "J6_EXPOSURE_LEDGER_INSTANCE", "DATASET_TO_GENERATION_KEY_NOT_SOURCE_DEFINED", "NATIVE_ML_FORWARD_CONSUMER_BINDING_FIELD_NOT_YET_NATIVE")
class MLConsumerPath:
    def __init__(self, *, gateway, final_store, authority, generations, writer, tables):
        if any(x is None for x in (gateway, final_store, authority, generations, writer, tables)): raise Refusal("ports", code="ML_CONSUMER_PATH_PORT_MISSING")
        self._g, self._f, self._a, self._gr, self._w, self._t = gateway, final_store, authority, generations, writer, tables
    def consume(self, caller, dataset_manifest, entry, outcome, request_id, *, row_id, generation_ref, generation_manifest_id, event, request_start_ts, joins, fence, vintage_mode="ORIGINAL_AS_OBSERVED", eligibility_reason, exclusion_reason_for_missing, catalog_snapshot=None, family_map=None, hypothesis_family_id=None):
        bh = self._a.request_binding(caller, dataset_manifest, outcome, gateway=self._g, final_store=self._f, request_id=request_id)           # refuses foreign / forged / unissued / re-linked
        row = MLR.build_row(row_id, generation_ref, [entry], [outcome], self._g, vintage_mode, eligibility_reason, exclusion_reason_for_missing, tables=self._t, expected_request_ids={(entry.feature_id, entry.feature_version): getattr(outcome, "request_id", None)})
        if not row.included: return MLConsumption(row, bh, None, None, None, None, ("ROW_EXCLUDED_REQUIRED_DEPENDENCY_NOT_DELIVERED",), HELD)
        if bh is None: return MLConsumption(row, None, None, None, None, None, ("NO_DATASET_BINDING_LINK",), HELD)
        blockers = []
        if self._a._d.is_revoked(dataset_manifest.dataset_manifest_id): blockers.append("DATASET_REVOKED")                    # the ancestry gate looks at ANCESTORS; the consumed dataset itself being revoked is checked here
        gate = self._a.gate(dataset_manifest.dataset_manifest_id)
        if gate["verdict"] != "CLEAR": blockers.append("DATASET_ANCESTRY_" + gate["verdict"])
        corr = self._w.correlate(generation_manifest_id)
        if corr["status"] != "VERIFIED_AGAINST_REGISTRY": blockers.append("GENERATION_" + corr["status"])
        snap = None
        try: snap = self._gr.snapshot(request_id, event, generation_manifest_id, request_start_ts)
        except Refusal as e: blockers.append("SNAPSHOT_" + e.code)
        jr = None
        if isinstance(joins, dict) and isinstance(joins.get("J1_DATASET_MANIFEST"), dict) and joins["J1_DATASET_MANIFEST"].get("binding_id") != bh["binding_id"]: blockers.append("J1_BINDING_ID_NOT_THE_ISSUED_IDENTITYS")
        else:
            consumed = {(b.entry.feature_id.hex(), b.entry.feature_version) for b in row.bindings} | {(a.feature_id.hex(), a.feature_version) for a in row.absence_applied}
            jr = SJ.check_six_joins(joins, self._gr, fence=fence, consumed_features=consumed, catalog_snapshot=catalog_snapshot, request_snapshot=snap, dataset_manifests=self._a._d.manifest_index(), binding_to_manifest=self._a._d.binding_index(), consumer_binding_id=bh["binding_id"], family_map=family_map, hypothesis_family_id=hypothesis_family_id)
            blockers += ["JOINS_" + c + "_" + s for c, s, _ in jr.correlation if s in (SJ.MISMATCH, SJ.MISSING)] + ["JOIN_" + j + "_" + s for j, s, _ in jr.statuses if s in (SJ.MISMATCH, SJ.MISSING)]
        return MLConsumption(row, bh, gate, corr, snap, jr, tuple(blockers), HELD)
