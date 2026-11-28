"""R43: the ML consumer-side INTEGRATION over the SAME objects the Tracker path produced (Gateway outcome + its final-resolution store), not a pile of unit-tested helpers.
One call, `MLConsumerPath.consume`, drives in order, each step on the real public candidate objects and each refusing/holding rather than inferring:
  1. `DatasetAuthority.request_binding`: the dataset manifest is linked to the consumer binding ONLY for an ML outcome the SAME Gateway and the SAME final store issued (reverse H1 link; no forward CONSUMER_BINDING field, no CBID == manifest-binding forcing);
  2. `receiver.build_row`: the Gateway-issued outcome is re-verified by the consumer (exact owned entry, hash re-derived, vintage, issued-by-this-gateway); a required non-delivery EXCLUDES the row (no consumption follows);
  3. the revoked-ancestry gate over the DECLARED union must be CLEAR (unknown/revoked => BLOCKED);
  4. the writer/finalizer facade `correlate` must be VERIFIED_AGAINST_REGISTRY for the named generation manifest (recorded write + granted finalize);
  5. the request snapshot is ISSUED by the generation registry (refuses an ineligible/revoked generation);
  6. all six joins are checked against the REAL registries' indexes (binding->manifest reverse index, manifest hash index, the issued snapshot) with the caller's join record, plus cross-object coherence (J1 binding id == the issued identity's binding id; J4/J5/snapshot name one generation).
  7. Health (R49): a `health` supplier (health.impact_supplier) derives the carried-upstream impact for THIS consumer from the governed ConsumerManifest closure; requiredness comes from the entry, never from the caller; a required use with no supplier is BLOCKED; non-required unknown is only named.
The result is ALWAYS `qualified=False` and lists `held` inputs (principal grants, J2 catalog, J3 Health service, J6 exposure ledger instances, native ML forward fields): source-owned inputs stay exactly held. Grants here are whatever the caller's registries were built with (test labels in tests); nothing is appointed."""
from dataclasses import dataclass
from ..errors import Refusal
from . import receiver as MLR, six_joins as SJ
from ..gateway.contracts import REQUIRED
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
    def consume(self, caller, dataset_manifest, entry, outcome, request_id, *, row_id, generation_ref, generation_manifest_id, event, request_start_ts, joins, fence, vintage_mode="ORIGINAL_AS_OBSERVED", eligibility_reason, exclusion_reason_for_missing, catalog_snapshot=None, family_map=None, hypothesis_family_id=None, health=None, feature_view=None, snapshot=None):
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
        if snapshot is not None:                                                                          # R53: each consumed ROW against the Core's resolved per-timeframe composition (row_snapshot)
            from ..tracker.row_snapshot import row_snapshot_blockers
            for b in row.bindings: blockers += list(row_snapshot_blockers(snapshot, b.entry))
        held = HELD
        if feature_view is not None:                                                                      # R53: the Tracker REGISTRY section 14 thirteen duties over the registered view that this consumption reads
            blockers += self._view_blockers(feature_view, entry, row)
        else: held = held + ("TRACKER_ML_FEATURE_VIEW_NOT_SUPPLIED",)
        required = getattr(entry, "requirement_class", None) == REQUIRED
        if health is None:
            if required: blockers.append("HEALTH_IMPACT_NOT_EVALUATED_FOR_REQUIRED_USE")          # a required use is never allowed by omission (R49)
            else: held = HELD + ("HEALTH_CARRIED_UPSTREAM_IMPACT_NOT_EVALUATED",)
        else:
            use, _imp = health.decide(dataset_manifest.dataset_manifest_id, "ML", entry)         # CANDIDATE relation: the ML consumer manifest id is the consumed dataset manifest id (unbound otherwise)
            if use == "BLOCK_PROVEN_DEPENDENCY": blockers.append("HEALTH_PROVEN_DEPENDENCY_ON_FAILED_SUBJECT")
            elif use == "REFUSE_UNPROVEN_INDEPENDENCE": blockers.append("HEALTH_REQUIRED_ANCESTRY_UNPROVEN:" + str(getattr(_imp, "reason", "")))
            elif use.startswith("REFUSE_"): blockers.append("HEALTH_" + use)
            elif use.startswith("NO_SOURCE_RULE"): held = HELD + ("HEALTH_NO_SOURCE_RULE_UNDETERMINED_NON_REQUIRED_USE",)       # named, not decided
        return MLConsumption(row, bh, gate, corr, snap, jr, tuple(blockers), held)

    def _view_blockers(self, fv, entry, row):
        """`fv` = {"store": FeatureViewStore, "manifest_id": str, "resolvers": {evaluate keyword resolvers}, "symbol_of": callable(feature_id bytes) -> declared symbol | None}. Every non-PASS duty blocks (FAIL and HELD alike: an unbound duty is never a pass); a consumed feature
        must be one the registered view declares (exact symbol + version through the SUPPLIED subject-bound `symbol_of`; unmapped => blocked, never guessed), and the actual consumed ROW (via the supplied `row_of_transition` bridge from the delivered entry's canonical transition ref) must be one of the view's declared rows; without the bridge the row relation is HELD. Satisfying the duties authorizes nothing (p351)."""
        from . import tracker_ml_contract as TM
        if not isinstance(fv, dict) or any(k not in fv for k in ("store", "manifest_id", "resolvers", "symbol_of")): return ["TRACKER_ML_VIEW_INPUT_INVALID"]
        m = fv["store"].get(fv["manifest_id"])
        if m is None: return ["TRACKER_ML_VIEW_NOT_REGISTERED"]
        out = ["TRACKER_ML_DUTY_%s_%s" % (p, st) for p, (_n, st, _d) in TM.evaluate(m, store=fv["store"], **fv["resolvers"])["duties"].items() if st != TM.PASS]
        declared = {(f[0], f[1]) for f in m.features}; view_rows = set(m.rows); bridge = fv.get("row_of_transition")
        for b in row.bindings:
            sym = fv["symbol_of"](b.entry.feature_id) if callable(fv["symbol_of"]) else None
            if sym is None: out.append("CONSUMED_FEATURE_SYMBOL_UNMAPPED_HELD"); continue
            if (sym, b.entry.feature_version) not in declared: out.append("CONSUMED_FEATURE_NOT_DECLARED_IN_VIEW"); continue
            # exact consumed ROW: the delivered entry carries the canonical transition ref of the row the Gateway served (RowPublication's committed origin). The SUPPLIED subject-bound `row_of_transition(ref)` must read that record back and
            # return (row_content_hash, materialization_version, step_index); the row-content hash is NOT compared with the delivered-feature hash (different domains). No bridge / unresolved (e.g. a legacy feature-version row) => explicit HELD, never a pass.
            try: got = None if bridge is None else bridge(b.entry.canonical_transition_ref)
            except Exception: got = None
            if not (isinstance(got, tuple) and len(got) == 3): out.append("CONSUMED_ROW_NOT_BOUND_TO_VIEW_HELD"); continue
            h, mv, step = got
            if mv != b.entry.materialization_version or step != b.entry.step_index: out.append("CONSUMED_ROW_DIFFERS_FROM_DELIVERED_ENTRY")
            elif (sym, h) not in view_rows: out.append("CONSUMED_ROW_NOT_IN_VIEW")
        return out
