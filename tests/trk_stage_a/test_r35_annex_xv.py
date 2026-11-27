"""Typed Annex V1.2 (13PE_pli3ZlFjjPdhHtWtLyyH2XdAv8XGA4FN0KGcIlA) XV END-TO-END ACCEPTANCE and XVI CROSS-CONSUMER CONSISTENCY against the repository SimulatedGateway + FW/ML receivers (candidate, simulation, NOT an external Gateway).
R36 CORRECTION OF THE R35 COVERAGE CLAIM: this file does NOT exercise every XV negative through both consumers. Exact coverage: (a) 13-field equality + XVI: FW receive_verified and ML build_row of the same outcome (test_fw_and_ml_receive... / test_xvi...);
(b) wrong version / wrong scope / hash mismatch / CATCHING_UP: FW receive_verified ONLY; missing required dependency: FW receive_verified, plus ML build_row only as the explicit excluded row; (c) the ML-only items covered are required-absence-as-explicit-excluded-row and EVENTUAL-not-substituted-for-ORIGINAL_AS_OBSERVED;
default/forward fill (non-outcome object refused), EVENTUAL-vs-ORIGINAL mixed-vintage refusal and the explicit-not-silent excluded row are covered by existing tests/trk_stage_a/test_boundaries.py lines 267-271 (ML.build_row), not here; feed-era equality is covered by test_r34_consumption_claim (claim path), not through build_row. The settlement test records LATE_VISIBILITY non-delivery and retry immutability; the SETTLEMENT_BREACH emitter is `SettlementBreachEvidence` below."""
import unittest
from stage_a.errors import Refusal
from stage_a.gateway import contracts as G
from stage_a.tracker import chain_status as C
from stage_a.fw import receiver as FWR
from stage_a.ml import receiver as MLR
from .test_boundaries import _gw, _entry, _health, _row, I, J, R, T, NONE_
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
XV_FIELDS = ("published_projection_bits", "logical_encoding_version", "published_projection_hash", "feature_version", "materialization_version", "step_index", "event_time", "available_asof", "chain_status_at_bind", "fit_generation_ref", "data_vintage_mode", "canonical_transition_ref", "bound_health_resolution_ref")
def both():
    g = _gw(); e = _entry(ver="f1"); out = g.resolve("r1", e, I, I, 3, 10, _health()); fw = FWR.receive_verified(out, e, I, I, T, g)
    row = MLR.build_row("row1", R("gen"), [e], [out], g, "ORIGINAL_AS_OBSERVED", NONE_, lambda o: NONE_, tables=g.t); return g, e, out, fw, row
class XV(unittest.TestCase):
    def test_fw_and_ml_receive_exactly_the_published_values_for_all_thirteen_fields_and_ml_adds_its_three(self):
        g, e, out, fw, row = both(); pub = g.rows[(I, "f1", I, I)][0]; ent = fw.entry; ml_ent = row.bindings[0].entry
        for f in ("published_projection_bits", "logical_encoding_version", "published_projection_hash", "feature_version", "materialization_version", "step_index", "event_time", "available_asof", "fit_generation_ref", "data_vintage_mode", "canonical_transition_ref"):
            self.assertEqual(getattr(ent, f), getattr(pub, f), f); self.assertEqual(getattr(ml_ent, f), getattr(pub, f), f)
        self.assertEqual((ent.chain_status_at_bind, ent.bound_health_resolution_ref), (C.CURRENT, R("hl")))                                  # resolved by the Gateway at the fence / from the bound Health snapshot
        self.assertEqual((ml_ent.chain_status_at_bind, ml_ent.bound_health_resolution_ref), (ent.chain_status_at_bind, ent.bound_health_resolution_ref))
        self.assertTrue(set(XV_FIELDS) <= {f for f in ent.__dataclass_fields__})
        self.assertEqual((row.generation_binding_ref, row.row_eligibility_reason, row.row_exclusion_reason, row.included), (R("gen"), NONE_, None, True))   # ML-only: GENERATION_BINDING_REF, ROW_ELIGIBILITY_REASON, ROW_EXCLUSION_REASON
    def test_xvi_equivalent_scope_gives_fw_and_ml_identical_bits_hash_and_lineage(self):
        g, e, out, fw, row = both(); a, b = fw.entry, row.bindings[0].entry
        self.assertEqual((a.published_projection_bits, a.published_projection_hash, a.canonical_transition_ref, fw.delivered_feature_hash), (b.published_projection_bits, b.published_projection_hash, b.canonical_transition_ref, row.bindings[0].delivered_feature_hash))
    def test_the_required_negatives_each_fail_closed_on_both_consumers(self):
        g = _gw(); e = _entry(ver="f1"); out = g.resolve("r1", e, I, I, 3, 10, _health())
        self.assertEqual(code(FWR.receive_verified, out, _entry(ver="f2"), I, I, T, g), "WRONG_VERSION")                                         # wrong version
        self.assertEqual(code(FWR.receive_verified, out, e, J, I, T, g), "WRONG_SCOPE")                                                           # wrong scope
        miss = g.resolve("r2", _entry(fid=J, ver="f1"), I, I, 3, 10, _health()); self.assertEqual(code(FWR.receive_verified, miss, _entry(fid=J, ver="f1"), I, I, T, g), "NON_DELIVERY")   # missing required dependency
        import dataclasses; bad = dataclasses.replace(out, delivered_feature_hash=b"\x00" * 32); self.assertIsNotNone(code(FWR.receive_verified, bad, e, I, I, T, g))               # hash mismatch (and not the stored Gateway object)
        cu = _gw(status=C.CATCHING_UP); o2 = cu.resolve("r1", e, I, I, 3, 10, _health()); self.assertEqual(o2.reason, "CHAIN_STATUS_NOT_CURRENT:CATCHING_UP"); self.assertEqual(code(FWR.receive_verified, o2, e, I, I, T, cu), "NON_DELIVERY")   # CATCHING_UP where CURRENT required
    def test_correction_after_bind_keeps_the_old_binding_and_adds_later_lineage_and_a_settlement_breach_is_immutable_evidence(self):
        g = _gw(); e = _entry(ver="f1"); b = g.resolve("r1", e, I, I, 3, 10, _health()); g.note_correction_after_bind("r1", R("fix"))
        self.assertIs(g.outcome("r1"), b); self.assertEqual(g.later_lineage("r1"), (R("fix"),)); self.assertIs(FWR.receive_verified(b, e, I, I, T, g), b)             # old binding preserved, later lineage beside it
        late = _gw(avail=4, visible=12); nd = late.resolve("r1", e, I, I, 3, 10, _health()); self.assertEqual(nd.reason, "LATE_VISIBILITY"); self.assertIs(late.resolve("r1", e, I, I, 3, 10, _health()), nd)   # settlement/visibility breach: stored, immutable on retry
    def test_ml_only_negatives_no_silent_row_drop_no_default_fill_and_no_vintage_substitution(self):
        g = _gw(); e = _entry(ver="f1"); out = g.resolve("r1", e, I, I, 3, 10, _health()); miss = g.resolve("r2", _entry(fid=J, ver="f1"), I, I, 3, 10, _health())
        r = MLR.build_row("rowX", R("gen"), [_entry(fid=J, ver="f1")], [miss], g, "ORIGINAL_AS_OBSERVED", NONE_, lambda o: ("ENUM", "REASON", "REQUIRED_ABSENT"), tables=g.t)
        self.assertEqual((r.included, r.row_exclusion_reason, r.bindings), (False, ("ENUM", "REASON", "REQUIRED_ABSENT"), ()))                      # a required absence yields an EXPLICIT excluded row with its reason, never a silent drop or a filled row
        ev = _gw(vint="EVENTUAL"); o = ev.resolve("r1", e, I, I, 3, 10, _health(), data_vintage_mode="ORIGINAL_AS_OBSERVED"); self.assertEqual(o.reason, "DATA_VINTAGE_MODE_MISMATCH")    # EVENTUAL never substitutes for ORIGINAL_AS_OBSERVED
class SettlementBreachEvidence(unittest.TestCase):
    """R36: the V0.38 forensic classification has an actual emitter and callpath: `SimulatedGateway.record_late_evidence` -> immutable evidence beside the stored outcome -> Health adapter facts. The governed SETTLEMENT_DELAY / certified lag remain a HELD slot."""
    def test_pre_fence_data_visible_after_the_watermark_is_recorded_as_a_settlement_breach_beside_an_unchanged_outcome(self):
        from stage_a.gateway import v038 as V
        from stage_a.health import adapters as AD
        g = _gw(); e = _entry(ver="f1"); b = g.resolve("r1", e, I, I, 3, 10, _health()); wm = V.VisibilityWatermark(50, 12)
        ev = g.record_late_evidence("r1", 9, 51, wm); self.assertEqual((ev.classification, ev.fence, ev.watermark_position), (V.SETTLEMENT_BREACH, 10, 50))
        self.assertIs(g.outcome("r1"), b); self.assertIs(FWR.receive_verified(b, e, I, I, T, g), b)                                  # the bound outcome is NOT rewritten
        self.assertEqual(g.record_late_evidence("r1", 9, 51, wm), ev); self.assertEqual(g.late_evidence("r1"), (ev,))                       # idempotent
        self.assertEqual(g.record_late_evidence("r1", 10, 99, wm).classification, V.GENUINE_LATE); self.assertEqual(g.record_late_evidence("r1", 9, 50, wm).classification, V.RESOLVER_FAULT)
        self.assertEqual(code(g.record_late_evidence, "r1", 9, 50, wm, omitted_by_resolver=False), "NOT_LATE"); self.assertEqual(code(g.record_late_evidence, "nope", 9, 51, wm), "NO_OUTCOME_TO_ANNOTATE")
        self.assertEqual(code(g.record_late_evidence, "r1", 9, 51, (50, 12)), "LATE_EVIDENCE_INPUT_INVALID")
        o = AD.from_gateway_late_evidence(g); self.assertEqual(o.facts, {"late_evidence": 3, "by_classification": {"GENUINE_LATE": 1, "RESOLVER_FAULT": 1, "SETTLEMENT_BREACH": 1}}); self.assertEqual((o.scope, o.admitted), ("GLOBAL:GATEWAY_LATE_EVIDENCE", False))
if __name__ == "__main__": unittest.main()
