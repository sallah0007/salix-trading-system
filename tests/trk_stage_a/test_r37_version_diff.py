"""R37: FEATURE_VERSION_RELATIONSHIP diff engine + ledger (Registry p137-165, p322)."""
import unittest
from stage_a.errors import Refusal
from stage_a.tracker import version_diff as VD, version_relationship as VR
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
PAIRS = (("formula", "DEFINITION_SEMANTICS"), ("avail_rule", "CAUSAL_TIME"), ("source_path", "PROVENANCE_SOURCE"), ("instrument_set", "SCOPE_ELIGIBILITY_DEFINITION"), ("fit_window", "FITTED_LEARNED_STATE"))
S = VD.DiffSchema("DS1", tuple(f for f, _ in PAIRS), PAIRS)
BASE = {"formula": "f1", "avail_rule": "a1", "source_path": "p1", "instrument_set": "XAU", "fit_window": "w1"}
def rel(**chg): return VD.compute(S, "F@1", BASE, "F@2", dict(BASE, **chg))
class Diff(unittest.TestCase):
    def test_each_dimension_yields_its_source_class_and_changed_fields_are_exactly_the_differing_admitted_fields(self):
        r = rel(source_path="p2"); self.assertEqual((r.state, r.relationship_class, r.changed_fields), (VD.COMPUTED, VD.PROVENANCE_CHANGE, ("source_path",)))
        self.assertEqual(rel(instrument_set="XAU,EUR").relationship_class, VD.SCOPE_CHANGE)
        for f, v in (("formula", "f2"), ("avail_rule", "a2"), ("fit_window", "w2")): self.assertEqual(rel(**{f: v}).relationship_class, VD.MATERIAL_ALTERNATIVE, f)         # unexplained semantic change, no defect evidence
        self.assertEqual(rel(source_path="p2", instrument_set="E").relationship_class, None); self.assertEqual(rel(source_path="p2", instrument_set="E").reason, "COMBINATION_NOT_DEFINED_HELD")      # not invented
        same = rel(); self.assertEqual((same.relationship_class, same.reason, same.changed_fields), (None, "NO_CHANGED_FIELDS_NO_CLASS_DEFINED", ()))
    def test_correction_needs_verified_defect_evidence_and_every_semantic_change_attributable(self):
        ver = lambda refs: refs == ("EV1",); kw = dict(defect_verifier=ver, defect_evidence_refs=("EV1",))
        c = VD.compute(S, "F@1", BASE, "F@2", dict(BASE, formula="f2"), attributable_fields=("formula",), **kw); self.assertEqual((c.relationship_class, c.evidence_refs), (VD.CORRECTION, ("EV1",)))
        for name, k in (("unattributed extra semantic change", dict(attributable_fields=("formula",), **kw)), ("evidence not verified", dict(attributable_fields=("formula", "avail_rule"), defect_verifier=lambda r: False, defect_evidence_refs=("EV1",))), ("verifier returns truthy non-True", dict(attributable_fields=("formula", "avail_rule"), defect_verifier=lambda r: "yes", defect_evidence_refs=("EV1",))), ("no verifier", dict(attributable_fields=("formula", "avail_rule"))), ("no evidence refs", dict(attributable_fields=("formula", "avail_rule"), defect_verifier=ver))):
            r = VD.compute(S, "F@1", BASE, "F@2", dict(BASE, formula="f2", avail_rule="a2"), **k); self.assertEqual(r.relationship_class, VD.MATERIAL_ALTERNATIVE, name)
        self.assertEqual(VD.compute(S, "F@1", BASE, "F@2", dict(BASE, formula="f2", avail_rule="a2"), attributable_fields=("formula", "avail_rule"), **kw).relationship_class, VD.CORRECTION)      # positive control
    def test_unverifiable_history_is_uncomputable_never_correction_and_attempt_identity_does_not_change_the_result(self):
        r = VD.compute(S, "F@1", dict(BASE, formula=VD.UNVERIFIABLE), "F@2", dict(BASE, formula="f2"), defect_verifier=lambda x: True, defect_evidence_refs=("EV",), attributable_fields=("formula",)); self.assertEqual((r.state, r.relationship_class), (VR.UNCOMPUTABLE, None))
        a = VD.compute(S, "F@1", dict(BASE, attempt_identity="A1"), "F@2", dict(BASE, source_path="p2", attempt_identity="A9")); b = rel(source_path="p2"); self.assertEqual((a.relationship_class, a.changed_fields, a.record_id), (b.relationship_class, b.changed_fields, b.record_id))
    def test_schema_defects_are_raised_never_skipped_and_the_engine_cannot_invent_a_category(self):
        for k, c in ((dict(predecessor=dict(BASE, extra="x")), "SCHEMA_MISMATCH"), (dict(predecessor={k: v for k, v in BASE.items() if k != "formula"}), "SCHEMA_MISMATCH")):
            self.assertEqual(code(lambda **kw: VD.compute(S, "A", kw.get("predecessor", BASE), "B", BASE), **k), c)
        for bad, c in ((VD.DiffSchema("D", ("a", "b"), (("a", "DEFINITION_SEMANTICS"),)), "DIFF_PARTITION_INCOMPLETE"), (VD.DiffSchema("D", ("a",), (("a", "DEFINITION_SEMANTICS"), ("a", "CAUSAL_TIME"))), "DIFF_PARTITION_NOT_DISJOINT"), (VD.DiffSchema("D", ("a",), (("a", "NEW_CATEGORY"),)), "UNKNOWN_DIMENSION"), (VD.DiffSchema("D", ("attempt_identity",), (("attempt_identity", "PROVENANCE_SOURCE"),)), "ATTEMPT_IDENTITY_IN_DIFF")):
            self.assertEqual(code(VD.compute, bad, "A", {}, "B", {}), c)
        self.assertEqual(code(VD.compute, S, "A", BASE, "A", BASE), "RELATIONSHIP_IDS_INVALID")
class Ledger(unittest.TestCase):
    def test_one_record_per_schema_version_history_is_immutable_replay_pins_the_id_and_uncomputed_blocks_only_the_claim(self):
        L = VD.RelationshipLedger(); self.assertEqual(L.successor_claim("F@1", "F@2", "DS1"), {"claim": "FAIL_CLOSED", "state": VR.UNCOMPUTED, "existing_version_deliverable": True, "record_id": None})
        r1 = L.append(rel(source_path="p2")); self.assertIs(L.append(rel(source_path="p2")), r1); self.assertEqual(code(L.append, VD.compute(S, "F@1", BASE, "F@2", dict(BASE, instrument_set="E"))), "RELATIONSHIP_IMMUTABLE_PER_SCHEMA_VERSION")
        c = L.successor_claim("F@1", "F@2", "DS1"); self.assertEqual((c["claim"], c["class"], c["record_id"]), ("REFERENCE_RECORD", VD.PROVENANCE_CHANGE, r1.record_id))
        S2 = VD.DiffSchema("DS2", S.admitted, S.pairs); r2 = L.append(VD.compute(S2, "F@1", BASE, "F@2", dict(BASE, formula="f2"))); self.assertEqual(L.pinned(r1.record_id), r1); self.assertEqual(L.current("F@1", "F@2", "DS2"), r2); self.assertEqual(L.current("F@1", "F@2", "DS1"), r1)      # old record intact
        self.assertEqual(L.successor_claim("F@1", "F@2", "DS3")["claim"], "FAIL_CLOSED"); self.assertTrue(L.successor_claim("F@1", "F@2", "DS3")["existing_version_deliverable"])
        un = L.append(VD.compute(S, "G@1", dict(BASE, formula=VD.UNVERIFIABLE), "G@2", BASE)); self.assertEqual(L.successor_claim("G@1", "G@2", "DS1")["state"], VR.UNCOMPUTABLE); self.assertEqual(L.successor_claim("G@1", "G@2", "DS1")["claim"], "FAIL_CLOSED")
if __name__ == "__main__": unittest.main()
