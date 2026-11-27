"""R22: Core mechanics through ONE composition path (TrackerCore over a single fenced journal) with downstream Gateway / FW / ML consuming its actual typed health output.
Simulation evidence over internal CANDIDATE carriers. Qualified-class Core holds anything that would assert eligibility/health/reconstruction/mixed-declared (typed HELD), while qualified mechanics
that need no external authority (admission, contract resolution, snapshot sealing, quarantine opening) are positively controlled. Includes the Codex PR45 reproductions."""
import unittest
from stage_a.errors import Refusal, StaleFence
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.storage.authority_class import SimulationStore
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.core.tracker_core import TrackerCore, NEW, REPEAT, CONFLICT, OBS_FACTS_CANDIDATE, HELD, SIM_ELIGIBLE, CoreHealthSnapshot
from stage_a.gateway import contracts as G
from stage_a.fw import receiver as FW
from stage_a.ml import receiver as ML
from stage_a.storage.byte_primitives import domain_hash
from .test_boundaries import _entry, _gw, I, R, NONE_, T
def code(fn, *a, **k):
    try: fn(*a, **k)
    except Refusal as e: return e.code
def mk(sim=True, ns="core1", store=None):
    st = store or InMemoryObjectStore(); st = SimulationStore(st) if sim else st
    j = ObjectStoreJournal(st, ns, "w"); j.acquire_epoch(); return TrackerCore(j, simulation=sim)
def facts(**o):
    f = {k: k + "-v" for k in OBS_FACTS_CANDIDATE}; f.update(instrument="XAUUSD", timeframe="H4"); f.update(o); return f
def adm(c, p=b"p", av=5, v="V1", **fo): return c.admit_observation(facts(**fo), p, av, v)
def ver(c, s="K", version="1", req="REQUIRED", l2="PASS", l1="PASS", at=10, age=5, **k): c.record_verification(s, version, req, l2, l1, at, age, "verifier-1", "digest-1", **k)

class Observation(unittest.TestCase):
    def test_idempotent_conflict_quarantine_no_overwrite(self):
        c = mk(); self.assertEqual(adm(c), NEW); self.assertEqual(adm(c), REPEAT)
        self.assertEqual(adm(c, b"b"), CONFLICT); self.assertFalse(c.observation_usable(c.obs_key(facts())))
        self.assertEqual(adm(c), CONFLICT)
    def test_same_payload_different_availability_or_vintage_is_a_conflict(self):
        c = mk(); adm(c); self.assertEqual(adm(c, av=6), CONFLICT)
    def test_instrument_qualified_no_collision_and_bad_facts(self):
        c = mk(); self.assertNotEqual(c.obs_key(facts()), c.obs_key(facts(instrument="EURUSD")))
        self.assertEqual(code(c.obs_key, {"instrument": "x"}), "OBSERVATION_FACTS_INVALID"); self.assertEqual(code(adm, c, av=-1), "OBSERVATION_FIELDS_INVALID")
    def test_resolution_needs_independent_certifier_and_candidate(self):
        c = mk(); adm(c); adm(c, b"b"); k = c.obs_key(facts()); d = domain_hash("TRK/PAYLOAD", b"p")
        self.assertEqual(code(c.resolve_ambiguity, k, d, "x", "x"), "CREATOR_IS_CERTIFIER"); self.assertEqual(code(c.resolve_ambiguity, k, "nope", "x", "y"), "NOT_A_PENDING_CANDIDATE")
        c.resolve_ambiguity(k, d, "x", "y"); self.assertTrue(c.observation_usable(k))
    def test_qualified_class_core_admits_observations_positive_control(self):
        c = mk(False); self.assertEqual(adm(c), NEW); self.assertEqual(adm(c), REPEAT)
class Atomicity(unittest.TestCase):
    """Codex repro: two actual calls read empty state, then append A then B on the same live journal."""
    def race(self, pa, pb):
        c1 = mk(); c2 = TrackerCore(c1._j, simulation=True); orig = c1._replay; done = []
        def hooked(upto=None):
            r = orig(upto)
            if not done: done.append(1); res.append(adm(c2, pb))          # the other writer lands between c1's read and c1's append
            return r
        res = []; c1._replay = hooked; first = adm(c1, pa); return first, res[0], c1
    def test_conflicting_interleaving_yields_conflict_not_last_wins(self):
        first, other, c = self.race(b"A", b"B")
        self.assertEqual(sorted([first, other]), sorted([NEW, CONFLICT])); self.assertFalse(c.observation_usable(c.obs_key(facts())))
        self.assertEqual(sum(1 for r in c._j.read_from(0) if r.kind == "OBS_ADMITTED"), 1)
    def test_identical_interleaving_is_one_record_and_a_repeat(self):
        first, other, c = self.race(b"A", b"A"); self.assertEqual(sorted([first, other]), sorted([NEW, REPEAT]))
        self.assertTrue(c.observation_usable(c.obs_key(facts()))); self.assertEqual(sum(1 for r in c._j.read_from(0) if r.kind == "OBS_ADMITTED"), 1)
    def test_unrelated_instrument_positive_control_and_restart_and_stale_epoch(self):
        c = mk(ns="a"); adm(c); self.assertEqual(adm(c, instrument="EURUSD"), NEW)
        store = c._j._s; j2 = ObjectStoreJournal(store, "a", "w2"); j2.acquire_epoch(); c2 = TrackerCore(j2, simulation=True)       # restart: new writer replays the journal
        self.assertEqual(adm(c2), REPEAT); self.assertEqual(adm(c2, b"z"), CONFLICT)
        with self.assertRaises(StaleFence): adm(c, instrument="OTHER")                                                            # c's epoch was fenced out by the restart
class Contract(unittest.TestCase):
    def test_exactly_one_zero_many_stale_and_label_spoof(self):
        c = mk(); env = {"o": 1, "h": 2, "label": "PROVIDER_A", "watermark": 100}; fp = c.derive_fingerprint(env)
        self.assertEqual(c.resolve_contract(env, b"r", 101)[0], "QUARANTINED")
        c.register_contract("A", "1", fp, 10, True); self.assertEqual(c.resolve_contract(env, b"r", 105), ("RESOLVED", ("A", "1")))
        self.assertEqual(c.resolve_contract(dict(env, label="SOMETHING_ELSE"), b"r", 105)[0], "RESOLVED")
        self.assertEqual(c.resolve_contract(dict(env, extra=[]), b"r", 105)[0], "QUARANTINED")
        self.assertEqual(c.resolve_contract(env, b"r", 200), ("HELD", "STALE_OR_MISSING_WATERMARK"))
        c.register_contract("B", "1", fp, 10, True); self.assertEqual(c.resolve_contract(env, b"r", 105), ("QUARANTINED", "MULTI_MATCH"))
    def test_battery_not_passed_is_not_usable(self):
        c = mk(); env = {"o": 1, "watermark": 1}; c.register_contract("A", "1", c.derive_fingerprint(env), 10, False)
        self.assertEqual(c.resolve_contract(env, b"r", 2)[0], "NOT_USABLE")
class Snapshot(unittest.TestCase):
    def setUp(self):
        self.c = mk()
        for k in "abc": adm(self.c, bar_identity=k, av={"a": 9, "b": 10, "c": 3}[k])
        self.k = {k: self.c.obs_key(facts(bar_identity=k)) for k in "abc"}
    def test_half_open_fence_and_identical_members_one_hash(self):
        r1 = self.c.seal("XAUUSD", 10, 10, [self.k["a"], self.k["b"]]); self.assertEqual(r1, self.c.seal("XAUUSD", 10, 10, [self.k["a"], self.k["b"]])); self.assertEqual(r1[0], "SEALED")
        self.assertEqual(self.c.seal("XAUUSD", 10, 10, [self.k["a"]])[1], r1[1])                 # b (available_asof == fence) is excluded from the hash
        self.assertNotEqual(self.c.seal("XAUUSD", 11, 11, [self.k["a"], self.k["b"]])[1], r1[1])
        self.assertTrue(self.c.verify_snapshot(r1[1], "XAUUSD", 10, 10, [self.k["a"], self.k["b"]]))
        self.assertFalse(self.c.verify_snapshot(r1[1], "XAUUSD", 10, 10, [self.k["a"], self.k["c"]]))
    def test_codex_repro_relabelled_provenance_is_refused(self):
        c = mk(); c.admit_observation(facts(instrument="EURUSD", timeframe="H1"), b"EURUSD", 1, "V9"); k = c.obs_key(facts(instrument="EURUSD", timeframe="H1"))
        self.assertEqual(code(c.seal, "XAUUSD", 10, 10, [k]), "CROSS_INSTRUMENT_MEMBER")                      # members come from the stored facts, not the caller
        for bad in ({"timeframe": "H4"}, {"vintage": "V1"}, {"available_asof": 2}):
            self.assertEqual(code(c.seal, "EURUSD", 10, 10, [k], None, {k: bad}), "MEMBER_CLAIM_MISMATCH")
        self.assertEqual(c.seal("EURUSD", 10, 10, [k], None, {k: {"timeframe": "H1", "vintage": "V9", "available_asof": 1}})[0], "SEALED")      # honest claims positive control
    def test_mixed_vintage_is_refused_and_qualified_holds_mixed_declared(self):
        c = self.c; adm(c, bar_identity="m", v="V2", av=2); km = c.obs_key(facts(bar_identity="m")); mem = [self.k["a"], km]
        self.assertEqual(c.seal("XAUUSD", 10, 10, mem), ("MIXED_VINTAGE_REFUSED", None))
        self.assertEqual(c.seal("XAUUSD", 10, 10, mem, "unregistered"), ("MIXED_VINTAGE_REFUSED", None))
        c.register_mixed_policy("P", "owner", 100); r = c.seal("XAUUSD", 10, 10, mem, "P"); self.assertEqual(r[0], "SIMULATION_MIXED_VIEW")       # never labelled SEALED
        c.revoke_mixed_policy("P"); self.assertEqual(c.seal("XAUUSD", 10, 10, mem, "P"), ("MIXED_VINTAGE_REFUSED", None))
        c.register_mixed_policy("Q", "owner", 5); self.assertEqual(c.seal("XAUUSD", 10, 10, mem, "Q"), ("MIXED_VINTAGE_REFUSED", None))          # expired
        q = mk(False); adm(q, bar_identity="a", v="V1"); adm(q, bar_identity="m", v="V2")
        self.assertEqual(q.seal("XAUUSD", 10, 10, [q.obs_key(facts(bar_identity="a")), q.obs_key(facts(bar_identity="m"))]), ("MIXED_DECLARED_POLICY_UNBOUND_HELD", None))
        self.assertEqual(code(q.register_mixed_policy, "P", "o", 9), "MIXED_DECLARED_POLICY_UNBOUND_HELD")
        self.assertEqual(q.seal("XAUUSD", 10, 10, [q.obs_key(facts(bar_identity="a"))])[0], "SEALED")                                            # qualified single-vintage positive control
    def test_unknown_ambiguous_blocked_members_and_bad_asof_refused(self):
        self.assertEqual(code(self.c.seal, "XAUUSD", 10, 10, ["ghost"]), "MEMBER_NOT_USABLE_OBSERVATION")
        self.assertEqual(code(self.c.seal, "XAUUSD", 12, 10, []), "ASOF_AFTER_FENCE")
        self.c.quarantine(self.k["a"], "R"); self.assertEqual(code(self.c.seal, "XAUUSD", 10, 10, [self.k["a"]]), "MEMBER_BLOCKED")
        adm(self.c, b"DIFFERENT", bar_identity="c"); self.assertEqual(code(self.c.seal, "XAUUSD", 10, 10, [self.k["c"]]), "MEMBER_NOT_USABLE_OBSERVATION")
class EpochQuarantine(unittest.TestCase):
    def test_epoch_invalidates_transitive_dependents_and_codex_repro_reresolve_needs_valid_upstream_and_fresh_witness(self):
        c = mk(); c.declare_dependency("B", "A"); c.declare_dependency("C", "B"); c.advance_epoch("A", 2)
        self.assertEqual(c.blocked("C"), ["EPOCH_INVALIDATED", "UPSTREAM_BLOCKED"]); self.assertEqual(code(c.advance_epoch, "A", 2), "EPOCH_NOT_ADVANCING")
        self.assertEqual(code(c.reresolve, "C"), "UPSTREAM_STILL_INVALID")                       # Codex repro: B still invalid
        self.assertEqual(code(c.reresolve, "B"), "NO_FRESH_WITNESS")
        ver(c, "B"); c.reresolve("B"); ver(c, "C"); c.reresolve("C"); self.assertEqual(c.blocked("C"), []); self.assertEqual(code(c.reresolve, "C"), "NOT_INVALIDATED")
        self.assertEqual(code(mk(False).reresolve, "x"), "VERIFIER_BINDING_UNBOUND_HELD")
    def test_dependency_cycle_is_refused(self):
        c = mk(); c.declare_dependency("B", "A"); self.assertEqual(code(c.declare_dependency, "A", "B"), "DEPENDENCY_CYCLE")
    def test_codex_repro_reactivate_uses_recorded_closure_not_a_caller_list(self):
        c = mk(); c.declare_dependency("S", "missing-upstream"); c.quarantine("S", "R"); c.clear_reason("S", "R", "cert", "maker")
        self.assertEqual(code(c.reactivate, "S"), "NOT_RECONSTRUCTABLE"); self.assertFalse(c.retry_allowed("S"))
    def test_observation_presence_is_not_reconstructability_payload_must_reproduce_digest(self):
        c = mk(); adm(c); k = c.obs_key(facts()); c.declare_dependency("S", k); c.quarantine("S", "R"); c.clear_reason("S", "R", "cert", "maker")
        c.reactivate("S"); self.assertTrue(c.retry_allowed("S"))                                  # reconstructable closure: positive control
        c2 = mk(); adm(c2); k2 = c2.obs_key(facts()); c2.declare_dependency("S", k2); c2.quarantine("S", "R"); c2.clear_reason("S", "R", "cert", "maker")
        st = c2._replay(); st["obs"][k2]["payload_hex"] = b"tampered".hex()
        self.assertFalse(c2._reconstructable(st, k2))
    def test_multi_reason_retry_suppression_reopen_is_not_reactivation_and_qualified_holds_reactivation(self):
        c = mk(); c.quarantine("S", "R1"); c.quarantine("S", "R2"); self.assertFalse(c.retry_allowed("S"))
        c.clear_reason("S", "R1", "cert", "maker"); self.assertFalse(c.retry_allowed("S")); self.assertEqual(code(c.reactivate, "S"), "REASONS_STILL_OPEN")
        c.clear_reason("S", "R2", "cert", "maker"); c.reopen("S"); self.assertFalse(c.retry_allowed("S")); c.reactivate("S"); self.assertTrue(c.retry_allowed("S"))
        self.assertEqual(code(c.clear_reason, "S", "R1", "x", "x"), "CREATOR_IS_CERTIFIER")
        q = mk(False); q.quarantine("S", "R"); q.clear_reason("S", "R", "c", "m"); self.assertEqual(code(q.reactivate, "S"), "RECONSTRUCTION_PROOF_BINDING_UNBOUND_HELD")
        q.quarantine("T", "R"); self.assertFalse(q.retry_allowed("T"))                              # qualified quarantine opening works
    def test_reverse_dependents_are_blocked_by_a_quarantined_ancestor(self):
        c = mk(); c.declare_dependency("D", "U"); c.quarantine("U", "R"); self.assertEqual(c.blocked("D"), ["UPSTREAM_BLOCKED"])
class Health(unittest.TestCase):
    def test_required_l2_never_falls_back_and_stale_future_never_certify(self):
        c = mk(); ver(c, l2="UNAVAILABLE"); self.assertEqual(c.recording_health("K", "1", 11), "UNKNOWN")
        ver(c); self.assertEqual(c.recording_health("K", "1", 11), "HEALTHY"); self.assertEqual(c.recording_health("K", "1", 99), "UNKNOWN")
        self.assertEqual(c.recording_health("K", "2", 11), "UNKNOWN")                                  # wrong version
        ver(c, req="NOT_APPLICABLE_BY_GOVERNED_DEFINITION", l2="UNAVAILABLE", definition_ref="DEF-1"); self.assertEqual(c.recording_health("K", "1", 11), "HEALTHY")
        ver(c, l2="FAIL"); self.assertEqual(c.recording_health("K", "1", 11), "NOT_HEALTHY"); self.assertEqual(mk().recording_health("x", "1", 1), "UNKNOWN")
    def test_codex_repro_future_evidence_does_not_certify_and_inputs_are_validated(self):
        c = mk(); ver(c, "future", at=999, age=1); self.assertEqual(c.recording_health("future", "1", 2), "UNKNOWN")
        self.assertEqual(code(ver, c, at=-1), "HEALTH_INTERVAL_INVALID"); self.assertEqual(code(ver, c, age=0), "HEALTH_INTERVAL_INVALID")
        self.assertEqual(code(ver, c, req="NOT_APPLICABLE_BY_GOVERNED_DEFINITION", l2="UNAVAILABLE"), "NOT_APPLICABLE_NEEDS_DEFINITION_PROOF")
        self.assertEqual(code(c.record_verification, "K", "1", "UNAVAILABLE", "PASS", "PASS", 1, 1, "v", "d"), "HEALTH_VOCABULARY_UNKNOWN")
        self.assertEqual(code(c.record_verification, "K", "1", "REQUIRED", "PASS", "PASS", 1, 1, "", "d"), "HEALTH_BINDING_INCOMPLETE")
    def test_reverification_trigger_and_epoch_supersession(self):
        c = mk(); self.assertEqual(c.due_for_reverification(["K"], 11), [("K", "ABSENT")]); ver(c)
        self.assertEqual(c.due_for_reverification(["K"], 11), []); self.assertEqual(c.due_for_reverification(["K"], 50), [("K", "STALE")])
        c.advance_epoch("K", 2); self.assertEqual(c.recording_health("K", "1", 11), "UNKNOWN"); self.assertEqual(c.due_for_reverification(["K"], 11), [("K", "EPOCH_ADVANCED")])
        c.reverify("K", "1", lambda s, v: ("PASS", "PASS", "dg"), 11, "REQUIRED", 5); self.assertEqual(c.recording_health("K", "1", 12), "HEALTHY")
        c.request_reverification("K", "SCHEDULED"); self.assertEqual(c.recording_health("K", "1", 12), "UNKNOWN")
        self.assertEqual(code(c.request_reverification, "K", "WHENEVER"), "UNKNOWN_REVERIFY_TRIGGER")
        def bad(s, v): return ("FAIL", "PASS", "dg")
        c.reverify("K", "1", bad, 13, "REQUIRED", 5); self.assertEqual(c.recording_health("K", "1", 14), "NOT_HEALTHY")
class Eligibility(unittest.TestCase):
    def test_codex_repro_qualified_core_cannot_assert_eligibility_from_a_caller_pass(self):
        c = mk(False); ver(c, "never-observed"); r = c.eligible_asof("never-observed", "1", c._j.head().seq, 11)
        self.assertEqual((r["state"], r["eligible"], r["mode"]), (HELD, False, "QUALIFIED_HELD")); self.assertIn("BASELINE_LIFECYCLE_AUTHORITY_UNBOUND", r["undetermined_inputs"])
        self.assertIn("VERIFIER_BINDING_UNBOUND", r["undetermined_inputs"])
    def test_simulation_is_explicit_evidence_with_positive_and_negative_controls(self):
        s = mk(); ver(s); seq = s._j.head().seq; r = s.eligible_asof("K", "1", seq, 11); self.assertEqual((r["state"], r["mode"], r["reasons"]), (SIM_ELIGIBLE, "SIMULATION_EVIDENCE_ONLY", []))
        self.assertIn("RECORDING_HEALTH_NOT_HEALTHY", s.eligible_asof("K", "1", 0, 11)["reasons"])                                      # as-known before the record
        s.quarantine("K", "R"); self.assertEqual(s.eligible_asof("K", "1", s._j.head().seq, 11)["state"], "SIMULATION_EVIDENCE_NOT_ELIGIBLE"); self.assertEqual(s.eligible_asof("K", "1", seq, 11)["state"], SIM_ELIGIBLE)
    def test_chain_status_authority_is_consulted_when_bound(self):
        from stage_a.tracker import chain_status as CS
        ch = CS.ChainStatusAuthority(); mv = ("f", "1", "XAUUSD", "H4", "m1"); ch.append(CS.StatusFact(mv, 1, CS.DEGRADED, 1, False))
        j = ObjectStoreJournal(SimulationStore(InMemoryObjectStore()), "x", "w"); j.acquire_epoch(); c = TrackerCore(j, simulation=True, chain_status=ch); ver(c, "f")
        self.assertIn("CHAIN_STATUS_NOT_CURRENT", c.eligible_asof("f", "1", j.head().seq, 11, mv=mv, fence=5)["reasons"])
        ch.append(CS.StatusFact(mv, 2, CS.CURRENT, 2, False)); self.assertEqual(c.eligible_asof("f", "1", j.head().seq, 11, mv=mv, fence=5)["state"], SIM_ELIGIBLE)
class Boundary(unittest.TestCase):
    def test_class_mismatch_and_reviewer_guard(self):
        j = ObjectStoreJournal(SimulationStore(InMemoryObjectStore()), "x", "w"); j.acquire_epoch()
        self.assertEqual(code(TrackerCore, j, simulation=False), "AUTHORITY_CLASS_MISMATCH")
        c = mk(); f = dict(finding_id="F1", task_origin="R22", summary="s", author="codex"); c.accept_finding(f)
        self.assertEqual(code(c.accept_finding, dict(f, authorizes_stage_advance="true")), "REVIEW_INPUT_NOT_FINDING_ONLY")
        self.assertEqual(code(c.accept_finding, {k: v for k, v in f.items() if k != "task_origin"}), "REVIEW_INPUT_NOT_FINDING_ONLY")
class Composition(unittest.TestCase):
    """Core output -> actual SimulatedGateway.resolve -> FW.receive_verified / ML.build_row (repository SimulatedGateway; NOT an external Gateway integration)."""
    def path(self, healthy, sim=True):
        c = mk(sim)
        if healthy: ver(c, "K", at=4, age=10)
        else: ver(c, "K", l2="UNAVAILABLE", at=4, age=10)
        gw = _gw(); e = _entry(); hs = c.gateway_health("K", "1", 5, R("hl"), 4); return gw, e, hs, gw.resolve("o", e, I, I, 3, 10, hs)
    def test_healthy_simulation_core_yields_typed_simulation_health_and_binding_consumed_downstream(self):
        gw, e, hs, out = self.path(True); self.assertIsInstance(hs, CoreHealthSnapshot); self.assertEqual(hs.evidence_class, "SIMULATION"); self.assertIsInstance(out, G.Binding)
        self.assertIs(FW.receive_verified(out, e, I, I, T, gw), out)
        self.assertTrue(ML.build_row("r", R("gen"), [e], [out], gw, "ORIGINAL_AS_OBSERVED", NONE_, lambda o: NONE_).included)
    def test_qualified_core_health_is_held_never_acceptable(self):
        gw, e, hs, out = self.path(True, sim=False); self.assertEqual((hs.acceptable, hs.evidence_class), (False, "QUALIFIED_HELD")); self.assertNotIsInstance(out, G.Binding)
    def test_unknown_health_blocks_and_historical_mode_is_unresolved(self):
        gw, e, hs, out = self.path(False); self.assertNotIsInstance(out, G.Binding)
        self.assertEqual(code(mk().gateway_health, "K", "1", 5, R("hl"), 4, asof_seq=1), "HISTORICAL_HEALTH_MODE_UNRESOLVED")
    def test_quarantine_or_epoch_invalidation_blocks_delivery_downstream(self):
        for mut in (lambda c: c.quarantine("K", "R"), lambda c: (c.declare_dependency("K", "U"), c.advance_epoch("U", 2)), lambda c: c.advance_epoch("K", 2)):
            c = mk(); ver(c, "K", at=4, age=10); mut(c); gw = _gw(); out = gw.resolve("o", _entry(), I, I, 3, 10, c.gateway_health("K", "1", 5, R("hl"), 4)); self.assertNotIsInstance(out, G.Binding)
if __name__ == "__main__": unittest.main()
