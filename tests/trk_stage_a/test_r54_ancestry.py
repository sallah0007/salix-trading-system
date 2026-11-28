"""R54 ancestry: whole-ancestry completeness is bound to a SOURCE-BACKED closure (ml/closure candidate) through an EXPLICIT resolver. Two package strings are never correlated by intake; the narrow fit-reference currency is separate.
Candidate/SIM only: the completeness witness stays unadmitted, nothing here admits, qualifies or clears a gate."""
import dataclasses, unittest
from stage_a.ml import closure as CL
from stage_a.tracker.quant_intake_adapter import AncestryBinding, admit
from tracker_component import report as R
from .fixtures import Rig, package, momentum_manifest, SIM_CONF

FITS = {1: "a" * 64, 2: "b" * 64}
FR = [{"generation": 2, "ref_hash": "b" * 64}]

def N(i): return CL.ClosureNode(i, "NODE", "v1", "src:" + i)
def E(p, c, cls): return CL.ClosureEdge(p, c, cls, "ev:" + p + c, True)
def record(edges=None, nodes=("FEAT", "MODEL", "GEN", "FIT2"), **k):
    d = dict(closure_id="C1", subject_id="FEAT", subject_type="FEATURE", subject_version_or_hash="h", policy_id="P", policy_version="1", policy_hash="ph",
             nodes=tuple(N(n) for n in nodes),
             edges=tuple(edges if edges is not None else (E("MODEL", "FEAT", "LEARNED_DERIVED_MODEL_EDGE"), E("GEN", "MODEL", "MODEL_GENERATION_INPUT_EDGE"), E("FIT2", "GEN", "FITTED_TRANSFORM_EDGE"))),
             unresolved_edges=(), unknown_edge_types=(), missing_required_edges=(), closure_complete=True, fw_taint_present=False, fw_taint_source_ids=(),
             ml_fw_augmented_ancestry_present=False, admission_input_verdict="PASS", research_exposure_flags=(), computed_ts=5,
             resolver_id="R", resolver_version="1", resolver_hash="rh", final_closure_hash="fh")
    d.update(k); return CL.ClosureRecord(**d)
def binding(rec=None, **k):
    d = dict(record=rec or record(), subject_node="FEAT", upstream_model_node="MODEL", upstream_generation_node="GEN", fit_ref_nodes={2: "FIT2"}); d.update(k); return AncestryBinding(**d)

def run(resolver, fit_refs=FR):
    rig = Rig(fits=FITS, ancestry_resolver=resolver); p = package(momentum_manifest(fit_refs=fit_refs)); rig.issue(p); o = rig.pipe.run(p)
    R.verify_report(o.report); return rig, o
def anc(o): return o.report["ANCESTRY_COMPLETENESS"]
def adm_of(resolver, fit_refs=FR, bo=None):
    p = package(momentum_manifest(fit_refs=fit_refs)); 
    if bo is not None: p = dataclasses.replace(p, build_output=bo)
    return admit(p, accepted_fit_generations=FITS, conformance=SIM_CONF, ancestry_resolver=resolver)

class GenuineRelation(unittest.TestCase):
    def test_bound_closure_is_candidate_pass_and_accepts(self):
        rig, o = run(lambda *a: binding()); self.assertTrue(o.accepted_ok, o.failures); self.assertEqual(anc(o), "PASS")
    def test_no_fit_refs_needs_no_ancestry(self):
        rig = Rig(); p = package(); rig.issue(p); o = rig.pipe.run(p); self.assertTrue(o.accepted_ok); self.assertEqual(anc(o), "PASS")

class HeldUnknown(unittest.TestCase):
    def test_no_resolver_is_unknown_not_pass(self):
        rig, o = run(None); self.assertFalse(o.accepted_ok); self.assertEqual(anc(o), "UNKNOWN")
    def test_resolver_returns_nothing_is_unknown(self):
        rig, o = run(lambda *a: None); self.assertFalse(o.accepted_ok); self.assertEqual(anc(o), "UNKNOWN")
    def test_unknown_never_reaches_registry(self):
        rig, o = run(None); self.assertNotEqual(o.report["INTAKE_VERDICT"], "ACCEPT_FOR_REGISTRY")

class FailClosed(unittest.TestCase):
    def fails(self, b, code):
        rig, o = run(lambda *a: b); self.assertFalse(o.accepted_ok); self.assertEqual(anc(o), "FAIL"); self.assertTrue(any(code in c for _, c in o.failures), o.failures)
    def test_foreign_generation_not_in_closure(self):
        self.fails(binding(upstream_generation_node="FOREIGN-GEN"), "UPSTREAM_ID_NOT_IN_CLOSURE")
    def test_foreign_model_not_in_closure(self):
        self.fails(binding(upstream_model_node="FOREIGN-MODEL"), "UPSTREAM_ID_NOT_IN_CLOSURE")
    def test_closure_for_another_subject(self):
        self.fails(binding(subject_node="OTHER"), "ANCESTRY_CLOSURE_FOR_ANOTHER_SUBJECT")
    def test_fit_reference_not_in_closure(self):
        self.fails(binding(record(nodes=("FEAT", "MODEL", "GEN", "FIT2"), edges=(E("MODEL", "FEAT", "LEARNED_DERIVED_MODEL_EDGE"), E("GEN", "MODEL", "MODEL_GENERATION_INPUT_EDGE")))), "FIT_REFERENCE_NOT_IN_CLOSURE")
    def test_fit_reference_generation_unmapped(self):
        self.fails(binding(fit_ref_nodes={}), "FIT_REFERENCE_NOT_IN_CLOSURE")
    def test_unknown_edge_class_fails_closed_derivation(self):
        self.fails(binding(record(edges=(E("MODEL", "FEAT", "LEARNED_DERIVED_MODEL_EDGE"), E("GEN", "MODEL", "UNKNOWN"), E("FIT2", "GEN", "FITTED_TRANSFORM_EDGE")))), "ANCESTRY_CLOSURE_NOT_PASS")
    def test_unresolved_edges_fail_closed_derivation(self):
        self.fails(binding(record(unresolved_edges=("e?",))), "ANCESTRY_CLOSURE_NOT_PASS")
    def test_closure_complete_false_fails(self):
        self.fails(binding(record(closure_complete=False)), "ANCESTRY_CLOSURE_NOT_PASS")
    def test_no_learned_edge_to_upstream_ids(self):
        self.fails(binding(record(edges=(E("MODEL", "FEAT", "FEATURE_DEPENDENCY"), E("GEN", "MODEL", "FEATURE_DEPENDENCY"), E("FIT2", "GEN", "FITTED_TRANSFORM_EDGE")))), "NO_LEARNED_EDGE_TO_UPSTREAM_IDS")
    def test_malformed_closure_is_refused_not_passed(self):
        self.fails(binding(record(closure_id="")), "ANCESTRY_CLOSURE_MALFORMED")
    def test_malformed_binding_object(self):
        rig, o = run(lambda *a: "not-a-binding"); self.assertEqual(anc(o), "FAIL")
    def test_missing_upstream_identity_fails(self):
        a = adm_of(lambda *a: binding(), bo={"ORDER_ID": "ORD-1", "CREATION_REQUEST_ID": "REQ-1"}); self.assertEqual(a.ancestry[0], "FAIL")

class NarrowFitRefSeparate(unittest.TestCase):
    def test_current_fit_ref_with_unbound_ancestry_is_held(self):
        a = adm_of(None); self.assertEqual(a.ancestry[0], "UNKNOWN"); self.assertFalse([f for f in a.failed if f[0] == "FIT_ANCESTRY"])
    def test_stale_fit_ref_fails_fit_ancestry_even_with_good_closure(self):
        a = adm_of(lambda *a: binding(), fit_refs=[{"generation": 1, "ref_hash": "a" * 64}]); self.assertTrue([f for f in a.failed if f[0] == "FIT_ANCESTRY"])
    def test_resolver_receives_the_package_strings_not_a_comparison(self):
        seen = []
        adm_of(lambda fk, m, g, fr: seen.append((m, g, fr)) or binding()); self.assertEqual(seen[0][:2], ("MODEL-TEST", "GEN-TEST"))
    def test_witness_stays_unadmitted(self):
        self.assertFalse(CL.derive(record()).qualified)
