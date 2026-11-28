"""R54 ancestry: whole-ancestry completeness is bound to a SOURCE-BACKED closure (ml/closure candidate) through an EXPLICIT resolver. Two package strings are never correlated by intake; the narrow fit-reference currency is separate.
Candidate/SIM only: the completeness witness stays unadmitted, nothing here admits, qualifies or clears a gate."""
import dataclasses, unittest
from stage_a.ml import closure as CL
from stage_a.tracker.quant_intake_adapter import AncestryBinding, AncestryQueryReceipt, query_receipt_for, admit
from stage_a.identifiers import Scope, FeatureKey
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
DEFAULT_FK = FeatureKey(Scope("XAUUSD", "H4"), "mom3", "1")
def receipt(**k):
    d = dict(instrument="XAUUSD", timeframe="H4", feature_id="mom3", feature_version="1", upstream_model_id="MODEL-TEST", upstream_generation_id="GEN-TEST", fit_refs=((2, "b" * 64),), closure_id="C1"); d.update(k); return AncestryQueryReceipt(**d)
def binding(rec=None, **k):
    d = dict(record=rec or record(), subject_node="FEAT", upstream_model_node="MODEL", upstream_generation_node="GEN", fit_ref_nodes={2: "FIT2"}, query_receipt=receipt()); d.update(k); return AncestryBinding(**d)
def genuine_resolver(fk, mid, gid, fit_refs):
    """An honest resolver: builds the closure for the query it was handed and echoes THAT query in its receipt."""
    return binding(query_receipt=query_receipt_for(fk, mid, gid, fit_refs, "C1"))

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

class QueryBoundReceipt(unittest.TestCase):
    """R52: a consistent binding issued for ANOTHER query (public resolver-cache misassociation) is refused; an absent receipt is UNKNOWN; an honest resolver is accepted. SIM/candidate only."""
    def test_genuine_resolver_positive_control_echoes_the_actual_query(self):
        rig, o = run(genuine_resolver); self.assertTrue(o.accepted_ok, o.failures); self.assertEqual(anc(o), "PASS")
    def test_absent_receipt_cannot_establish_the_mapping_so_it_is_unknown(self):
        rig, o = run(lambda *a: binding(query_receipt=None)); self.assertFalse(o.accepted_ok); self.assertEqual(anc(o), "UNKNOWN")
    def test_receipt_wrong_type_is_malformed(self):
        rig, o = run(lambda *a: binding(query_receipt="x")); self.assertEqual(anc(o), "FAIL")
    def replay(self, **query):
        """ONE cached genuine binding (made for the default query) is returned for a different query."""
        cache = {}
        def cached(fk, m, g, fr):
            if "b" not in cache: cache["b"] = binding()
            return cache["b"]
        mkw = {k: query.pop(k) for k in ("feature_id", "version", "window") if k in query}; fr = query.pop("fit_refs", FR); bo = query.pop("bo", None)
        m = momentum_manifest(fit_refs=fr, **mkw); p = package(m)
        if bo: p = dataclasses.replace(p, build_output=dict(p.build_output, **bo))
        return admit(p, accepted_fit_generations={**FITS, 3: "c" * 64}, conformance=SIM_CONF, ancestry_resolver=cached)
    def test_consistent_foreign_binding_replayed_for_other_feature_version_generation_or_fit_hash_fails(self):
        for what, kw in (("feature id", dict(feature_id="mom9")), ("feature version", dict(version="2")), ("window (another feature definition)", dict(window=5, feature_id="mom5")),
                         ("generation id", dict(bo={"UPSTREAM_GENERATION_ID": "FOREIGN-GENERATION-999"})), ("model id", dict(bo={"UPSTREAM_MODEL_ID": "FOREIGN-MODEL"})),
                         ("fit hash", dict(fit_refs=[{"generation": 2, "ref_hash": "d" * 64}])), ("fit generation", dict(fit_refs=[{"generation": 3, "ref_hash": "c" * 64}]))):
            a = self.replay(**kw)
            if what == "fit hash": self.assertTrue([f for f in a.failed if f[0] == "FIT_ANCESTRY"], what); continue          # the narrow currency check already refuses a stale hash; the receipt also differs
            self.assertEqual(a.ancestry[0], "FAIL", what); self.assertIn("ANCESTRY_BINDING_QUERY_MISMATCH", a.ancestry[1], what)
    def test_the_same_cached_binding_is_accepted_only_for_its_own_query(self):
        self.assertEqual(self.replay().ancestry[0], "PASS_CANDIDATE")
    def test_instrument_or_timeframe_replay_fails(self):
        for k in ("instrument", "timeframe"):
            self.assertEqual(adm_of(lambda *a: binding(query_receipt=receipt(**{k: "OTHER"}))).ancestry[0], "FAIL", k)
    def test_a_receipt_for_another_closure_record_fails(self):
        a = adm_of(lambda *x: binding(query_receipt=receipt(closure_id="C-OTHER"))); self.assertEqual(a.ancestry, ("FAIL", "ANCESTRY_RECEIPT_FOR_ANOTHER_CLOSURE"))
    def test_binding_is_immutable_and_normalised(self):
        b = binding(); self.assertIsInstance(b.fit_ref_nodes, tuple)
        with self.assertRaises(dataclasses.FrozenInstanceError): b.subject_node = "X"
        with self.assertRaises(dataclasses.FrozenInstanceError): b.query_receipt.feature_id = "x"
    def test_refused_replay_has_no_registry_effects(self):
        from .test_pipeline import feature_records
        rig = Rig(fits=FITS, ancestry_resolver=lambda *a: binding(query_receipt=receipt(feature_id="mom-other"))); p = package(momentum_manifest(fit_refs=FR)); rig.issue(p); o = rig.pipe.run(p)
        self.assertFalse(o.accepted_ok); self.assertEqual(feature_records(rig), []); self.assertEqual(anc(o), "FAIL")
    def test_foreign_fit_hash_is_caught_by_the_receipt_even_when_currency_passes(self):
        fr = [{"generation": 2, "ref_hash": "d" * 64}]; p = package(momentum_manifest(fit_refs=fr))
        a = admit(p, accepted_fit_generations={2: "d" * 64}, conformance=SIM_CONF, ancestry_resolver=lambda *x: binding())      # currency is current for THIS query; the cached receipt echoes hash b*64
        self.assertFalse([f for f in a.failed if f[0] == "FIT_ANCESTRY"]); self.assertEqual(a.ancestry, ("FAIL", "ANCESTRY_BINDING_QUERY_MISMATCH"))
