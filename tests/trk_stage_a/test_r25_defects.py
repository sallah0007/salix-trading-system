"""R25 Codex-reproduced defects B1-B5, each with negatives that can fail (see mutation_sweep_r25.py)."""
import unittest
from stage_a.errors import Refusal
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.storage.authority_class import SimulationStore
from stage_a.composer.expression.manifest import Manifest
from stage_a.core.tracker_core import TrackerCore, COMPOSED_RECOMPUTATION
from stage_a.core import time_family as TF
from stage_a.health import envelope as HV
from stage_a.tracker import reverification as RV
from stage_a.tracker.verification import independent_hashing as ih
from stage_a.tracker.verification.independent_encoding import enc_bytes
from stage_a.tracker.verification.verification_result import make_result, SCOPE_MATERIALIZATION
from stage_a.tracker.verification.stateful_verifier import verify_materialization, probe_for
from stage_a.tracker.materialization.stateful_materializer import StatefulMaterializer
from stage_a.composer.expression.canonical_encoding import encode_manifest
from .fixtures import momentum_manifest
from .test_r24_core import code
from .test_r24_composed import core, declared, SIMS
from .test_health_envelope import env, SV

KEY = "XAUUSD/H4/mom3/1"
def world():
    m = Manifest.from_dict(momentum_manifest()); store = SIMS(); rec = StatefulMaterializer(store).materialize(m, probe_for(encode_manifest(m)))
    get = lambda k: (lambda g: None if g is None else g[0])(store.get(k))
    return m, store, rec, get
def verify(rec, get, d, key=KEY): return verify_materialization(store_get=get, record=rec, declared=d, expect_scope_key=key)
def failing(r): return {n for n, ok in r.checks if not ok}

class B1MaterializationHash(unittest.TestCase):
    def test_real_positive_and_hash_only_alteration_fails_with_exactly_that_check(self):
        m, store, rec, get = world(); d = declared(m)
        self.assertEqual(verify(rec, get, d).status, "PASS")
        r = verify(dict(rec, materialization_hash="arbitrary-corrupt-hash"), get, d)
        self.assertEqual(r.status, "FAIL"); self.assertEqual(failing(r), {"materialization_hash_recomputed"})
    def test_truncated_malformed_and_wrong_type_digests_fail(self):
        m, store, rec, get = world(); d = declared(m); good = rec["materialization_hash"]
        for bad in (good[:-1], good[:32], "", good.upper(), good + "0", 7, None, [good]):
            self.assertEqual(verify(dict(rec, materialization_hash=bad), get, d).status, "FAIL", repr(bad))
    def test_altered_record_or_probes_with_the_old_hash_fail_and_rehashed_forgery_is_caught_by_the_recomputation(self):
        m, store, rec, get = world(); d = declared(m)
        r = verify(dict(rec, probe_batch=list(reversed(rec["probe_batch"])) if len(set(map(str, rec["probe_batch"]))) > 1 else rec["probe_batch"][:-1]), get, d)
        self.assertEqual(r.status, "FAIL"); self.assertIn("materialization_hash_recomputed", failing(r))
        forged = dict(rec, probe_batch=rec["probe_batch"][:-1]); forged["materialization_hash"] = ih.materialization_digest(forged, enc_bytes)
        r2 = verify(forged, get, d); self.assertEqual(r2.status, "FAIL"); self.assertNotIn("materialization_hash_recomputed", failing(r2))      # hash now consistent; probe equivalence still objects
    def test_wrong_scope_still_fails(self):
        m, store, rec, get = world(); self.assertEqual(verify(rec, get, declared(m), key="XAUUSD/H4/other/1").status, "FAIL")

class B2CarrierClass(unittest.TestCase):
    def setUp(self): self.m = Manifest.from_dict(momentum_manifest())
    def test_simulation_core_with_ordinary_store_refuses_before_any_write(self):
        s = InMemoryObjectStore(); c = core(True)
        self.assertEqual(code(RV.reverify_manifest, c, manifest=self.m, declared=declared(self.m), store=s, now=10, max_age=5), "REVERIFY_CARRIER_CLASS_MISMATCH")
        self.assertEqual(s.list_prefix(""), []); self.assertEqual(c.recording_health(KEY, "1", 11).state, "UNKNOWN")
    def test_qualified_core_with_simulation_store_refuses_before_any_write(self):
        inner = InMemoryObjectStore(); c = core(False)
        self.assertEqual(code(RV.reverify_manifest, c, manifest=self.m, declared=declared(self.m), store=SimulationStore(inner), now=10, max_age=5), "REVERIFY_CARRIER_CLASS_MISMATCH")
        self.assertEqual(inner.list_prefix(""), [])
    def test_unknown_carrier_wrapper_refused_and_matching_classes_pass_with_physical_prefix(self):
        class Wrap(InMemoryObjectStore): pass
        self.assertEqual(code(RV.reverify_manifest, core(True), manifest=self.m, declared=declared(self.m), store=Wrap(), now=10, max_age=5), "UNKNOWN_CARRIER")
        inner = InMemoryObjectStore(); RV.reverify_manifest(core(True), manifest=self.m, declared=declared(self.m), store=SimulationStore(inner), now=10, max_age=5)
        ks = inner.list_prefix(""); self.assertTrue(ks and all(k.startswith("SIMULATION/") for k in ks))          # nothing ordinary written
        q = InMemoryObjectStore(); RV.reverify_manifest(core(False), manifest=self.m, declared=declared(self.m), store=q, now=10, max_age=5); self.assertTrue(any(k.startswith("artifact/") for k in q.list_prefix("")))

class B3ComposedProvenance(unittest.TestCase):
    def good(self):
        m, store, rec, get = world(); return verify(rec, get, declared(m))
    def test_fake_composed_label_without_result_is_refused_and_not_recorded(self):
        c = core(); self.assertEqual(code(c.record_verification, "fake", "1", "REQUIRED", "PASS", "PASS", 10, 5, "not-the-verifier", "arbitrary", evidence_class=COMPOSED_RECOMPUTATION), "HEALTH_COMPOSED_RESULT_MISSING")
        self.assertEqual(c.recording_health("fake", "1", 11).state, "UNKNOWN")
    def test_result_must_be_self_consistent_scope_subject_digest_verifier_and_level_bound(self):
        c = core(); r = self.good(); ok = dict(l2_requirement="REQUIRED", l1="PASS", l2="PASS", verifier=RV.VERIFIER_ID)
        def rec(res=r, subject=KEY, req="REQUIRED", l1="PASS", l2="PASS", vid=RV.VERIFIER_ID, dg=None):
            return code(c.record_verification, subject, "1", req, l2, l1, 10, 5, vid, dg or res.result_hash, evidence_class=COMPOSED_RECOMPUTATION, result=res)
        from dataclasses import replace
        self.assertIsNone(rec())                                                                                  # genuine positive
        self.assertEqual(rec(res=replace(r, result_hash="0" * 64)), "HEALTH_COMPOSED_RESULT_FORGED")
        self.assertEqual(rec(res=replace(r, checks=tuple((n, True) for n, _ in r.checks[:-1]))), "HEALTH_COMPOSED_RESULT_FORGED")
        wrong_scope = make_result("PASS", "OTHER_SCOPE", dict(r.subject), r.checks, r.reasons); self.assertEqual(rec(res=wrong_scope, dg=wrong_scope.result_hash), "HEALTH_COMPOSED_RESULT_UNBOUND")
        self.assertEqual(rec(subject="XAUUSD/H4/other/1"), "HEALTH_COMPOSED_RESULT_UNBOUND")                      # subject binding
        self.assertEqual(rec(dg="1" * 64), "HEALTH_COMPOSED_RESULT_UNBOUND"); self.assertEqual(rec(vid="not-the-verifier"), "HEALTH_COMPOSED_RESULT_UNBOUND")
        fl = make_result("FAIL", SCOPE_MATERIALIZATION, dict(r.subject), (("record_field_set", False),), ["x"]); self.assertEqual(rec(res=fl, dg=fl.result_hash), "HEALTH_COMPOSED_RESULT_UNBOUND")   # claims PASS/PASS over a failing result
        self.assertEqual(rec(req="NOT_APPLICABLE_BY_GOVERNED_DEFINITION"), "HEALTH_COMPOSED_RESULT_UNBOUND")
    def test_result_on_caller_asserted_class_is_refused_and_honest_label_is_preserved(self):
        c = core(); self.assertEqual(code(c.record_verification, "S", "1", "REQUIRED", "PASS", "PASS", 10, 5, "v", "d", result=self.good()), "HEALTH_RESULT_WITHOUT_COMPOSED_CLASS")
        c.record_verification("S", "1", "REQUIRED", "PASS", "PASS", 10, 5, "v", "d"); self.assertEqual(c.recording_health("S", "1", 11).evidence_class, "SIMULATION_CALLER_ASSERTED")
    def test_actual_composed_path_still_labels_composed(self):
        m = Manifest.from_dict(momentum_manifest()); c = core(); RV.reverify_manifest(c, manifest=m, declared=declared(m), store=SIMS(), now=10, max_age=5)
        self.assertEqual(c.recording_health(KEY, "1", 11).evidence_class, "SIMULATION_COMPOSED_RECOMPUTATION")

class B4TimeFamilyTies(unittest.TestCase):
    def test_distinct_tied_parents_are_held_in_every_order_and_unique_positive_selects(self):
        a, b = ("A", 5, True), ("B", 5, True)
        for ps in ([a, b], [b, a]):
            r = TF.latest_visible_parent(ps, 10); self.assertEqual((r.state, r.parent_id, r.candidates), (TF.MULTIPLE_CANDIDATES, None, ("A", "B")))
        r = TF.latest_visible_parent([a, b, ("C", 7, True)], 10); self.assertEqual((r.state, r.parent_id), (TF.SELECTED, "C"))
        r = TF.latest_visible_parent([("A", 5, True), ("B", 7, False)], 10); self.assertEqual((r.state, r.parent_id), (TF.SELECTED, "A"))       # incomplete never competes
        self.assertEqual(TF.latest_visible_parent([a, b], 5).state, TF.NONE_VISIBLE)                                                          # half-open: not yet visible
    def test_identical_repeats_are_one_candidate_and_conflicting_availability_is_malformed(self):
        r = TF.latest_visible_parent([("A", 5, True), ("A", 5, True)], 10); self.assertEqual((r.state, r.parent_id), (TF.SELECTED, "A"))
        self.assertEqual(code(TF.latest_visible_parent, [("A", 5, True), ("A", 6, True)], 10), "PARENT_LISTED_WITH_TWO_AVAILABILITIES")
    def test_tie_is_not_resolved_by_id_order_or_by_a_later_restart(self):
        for ps in ([("Z", 5, True), ("A", 5, True)], [("A", 5, True), ("Z", 5, True)]): self.assertEqual(TF.latest_visible_parent(ps, 10).state, TF.MULTIPLE_CANDIDATES)

class B5AntiReplaySubject(unittest.TestCase):
    sid = staticmethod(lambda **kw: dict({"AUTHORITY_STATE": "LIVE", "INSTRUMENT_ID": "EURUSD"}, **kw))
    def test_distinct_subjects_same_sequence_pass_and_same_subject_replay_refuses(self):
        a = HV.AntiReplay(); A = env(SUBJECT_IDENTITY=self.sid(SUBJECT="A"), PRODUCER_SEQUENCE=1); B = env(SUBJECT_IDENTITY=self.sid(SUBJECT="B"), PRODUCER_SEQUENCE=1)
        a.admit(A, True); a.admit(B, True)
        for e in (A, B):
            with self.assertRaises(Refusal) as c: a.admit(e, True)
            self.assertEqual(c.exception.code, "HEALTH_REPLAY_OR_STALE")
        a.admit(dict(A, PRODUCER_SEQUENCE=2), True)
    def test_key_order_of_the_subject_scope_does_not_matter_and_other_boundaries_are_retained(self):
        a = HV.AntiReplay(); a.admit(env(SUBJECT_IDENTITY={"INSTRUMENT_ID": "EURUSD", "AUTHORITY_STATE": "LIVE", "X": 1}, PRODUCER_SEQUENCE=3), True)
        with self.assertRaises(Refusal): a.admit(env(SUBJECT_IDENTITY={"AUTHORITY_STATE": "LIVE", "X": 1, "INSTRUMENT_ID": "EURUSD"}, PRODUCER_SEQUENCE=3), True)
        a.admit(env(SUBJECT_IDENTITY={"AUTHORITY_STATE": "PAPER", "INSTRUMENT_ID": "EURUSD", "X": 1}, PRODUCER_SEQUENCE=3), True)              # authority differs
        a.admit(env(SUBJECT_IDENTITY={"AUTHORITY_STATE": "LIVE", "INSTRUMENT_ID": "GBPUSD", "X": 1}, PRODUCER_SEQUENCE=3), True)               # instrument differs
        a.admit(env(SUBJECT_IDENTITY={"AUTHORITY_STATE": "LIVE", "INSTRUMENT_ID": "EURUSD", "X": 1}, SUBJECT_VERSION_OR_HASH="v2", PRODUCER_SEQUENCE=3), True)   # version differs
        a.admit(env(SUBJECT_IDENTITY={"AUTHORITY_STATE": "LIVE", "INSTRUMENT_ID": "EURUSD", "X": 1}, PRODUCER_ID="other", PRODUCER_SEQUENCE=3), True)         # producer differs
        with self.assertRaises(Refusal): a.admit(env(SUBJECT_IDENTITY={"AUTHORITY_STATE": "LIVE", "INSTRUMENT_ID": "EURUSD", "X": 1}, PRODUCER_SEQUENCE=3), False)   # integrity first
    def test_non_serializable_subject_scope_is_refused_and_changes_nothing(self):
        a = HV.AntiReplay()
        for bad in (self.sid(S=object()), self.sid(S=float("nan"))):
            with self.assertRaises(Refusal) as c: a.admit(env(SUBJECT_IDENTITY=bad, PRODUCER_SEQUENCE=1), True)
            self.assertEqual(c.exception.code, "SUBJECT_IDENTITY_NOT_SERIALIZABLE")
        a.admit(env(PRODUCER_SEQUENCE=1), True)
    def test_callpath_absence_is_explicit(self):
        import pathlib; hits = [p for p in pathlib.Path("stage_a").rglob("*.py") if "AntiReplay" in p.read_text() and p.name != "envelope.py"]
        self.assertEqual(hits, [])          # no Health boundary in this repository consumes packets: AntiReplay is a pure validator (REFERENCE_ONLY)
if __name__ == "__main__": unittest.main()
