"""R22: Core mechanics through ONE composition path (TrackerCore over a single fenced journal) with downstream Gateway / FW / ML consuming its actual typed health output.
Simulation evidence over internal CANDIDATE carriers. Qualified-class Core holds anything that would assert eligibility/health/reconstruction/mixed-declared (typed HELD), while qualified mechanics
that need no external authority (admission, contract resolution, snapshot sealing, quarantine opening) are positively controlled. Includes the Codex PR45 reproductions."""
import unittest
from stage_a.errors import Refusal, StaleFence, UnknownCommit
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.storage.authority_class import SimulationStore
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.core.tracker_core import TrackerCore, NEW, REPEAT, CONFLICT, REJECTED_KNOWN, OBS_FACTS_CANDIDATE, HELD, SIM_ELIGIBLE, CoreHealthSnapshot
from stage_a.gateway import contracts as G
from stage_a.fw import receiver as FW
from stage_a.ml import receiver as ML
from stage_a.storage.byte_primitives import domain_hash
from .test_boundaries import _entry, _gw, I, R, NONE_, T
from .strict_gateway import sgw, bind
def code(fn, *a, **k):
    try: fn(*a, **k)
    except Refusal as e: return e.code
def mk(sim=True, ns="core1", store=None):
    st = store or InMemoryObjectStore(); st = SimulationStore(st) if sim else st
    j = ObjectStoreJournal(st, ns, "w"); j.acquire_epoch(); return TrackerCore(j, simulation=sim)
def facts(**o):
    f = {k: k + "-v" for k in OBS_FACTS_CANDIDATE}; f.update(instrument="XAUUSD", timeframe="H4"); f.update(o); return f
def rh(c, *a): return c.recording_health(*a).state
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
        c = mk(); adm(c); adm(c, b"b"); k = c.obs_key(facts()); d = TrackerCore._cid(domain_hash("TRK/PAYLOAD", b"p"), 5, "V1")
        self.assertEqual(code(c.resolve_ambiguity, k, d, "x", "x"), "CREATOR_IS_CERTIFIER"); self.assertEqual(code(c.resolve_ambiguity, k, "nope", "x", "y"), "NOT_A_PENDING_CANDIDATE")
        c.resolve_ambiguity(k, d, "x", "y"); self.assertTrue(c.observation_usable(k))
        self.assertEqual(code(mk(False).resolve_ambiguity, k, d, "x", "y"), "SOURCE_APPROVAL_BINDING_UNBOUND_HELD")      # qualified: two caller names are not approval
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
        self.assertEqual(c.resolve_contract(env, b"r", 200), ("HELD", "STALE_WATERMARK"))
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
        self.assertEqual(code(c.reresolve, "C", "1", 11), "UPSTREAM_STILL_INVALID")                       # Codex repro: B still invalid
        self.assertEqual(code(c.reresolve, "B", "1", 11), "NO_FRESH_WITNESS")
        ver(c, "B"); c.reresolve("B", "1", 11); ver(c, "C"); c.reresolve("C", "1", 11); self.assertEqual(c.blocked("C"), []); self.assertEqual(code(c.reresolve, "C", "1", 11), "NOT_INVALIDATED")
        self.assertEqual(code(mk(False).reresolve, "x", "1", 11), "VERIFIER_BINDING_UNBOUND_HELD")
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
        q = mk(False); q.quarantine("S", "R"); self.assertEqual(code(q.clear_reason, "S", "R", "c", "m"), "SOURCE_APPROVAL_BINDING_UNBOUND_HELD"); self.assertEqual(code(q.reactivate, "S"), "RECONSTRUCTION_PROOF_BINDING_UNBOUND_HELD")
        q.quarantine("T", "R"); self.assertFalse(q.retry_allowed("T"))                              # qualified quarantine opening works
    def test_reverse_dependents_are_blocked_by_a_quarantined_ancestor(self):
        c = mk(); c.declare_dependency("D", "U"); c.quarantine("U", "R"); self.assertEqual(c.blocked("D"), ["UPSTREAM_BLOCKED"])
class Health(unittest.TestCase):
    def test_required_l2_never_falls_back_and_stale_future_never_certify(self):
        c = mk(); ver(c, l2="UNAVAILABLE"); self.assertEqual(rh(c, "K", "1", 11), "UNKNOWN")
        ver(c); self.assertEqual(rh(c, "K", "1", 11), "HEALTHY"); self.assertEqual(rh(c, "K", "1", 99), "UNKNOWN")
        self.assertEqual(rh(c, "K", "2", 11), "UNKNOWN")                                  # wrong version
        ver(c, req="NOT_APPLICABLE_BY_GOVERNED_DEFINITION", l2="UNAVAILABLE", definition_ref="DEF-1"); self.assertEqual(rh(c, "K", "1", 11), "HEALTHY")
        ver(c, l2="FAIL"); self.assertEqual(rh(c, "K", "1", 11), "NOT_HEALTHY"); self.assertEqual(rh(mk(), "x", "1", 1), "UNKNOWN")
    def test_codex_repro_future_evidence_does_not_certify_and_inputs_are_validated(self):
        c = mk(); ver(c, "future", at=999, age=1); self.assertEqual(rh(c, "future", "1", 2), "UNKNOWN")
        self.assertEqual(code(ver, c, at=-1), "HEALTH_INTERVAL_INVALID"); self.assertEqual(code(ver, c, age=0), "HEALTH_INTERVAL_INVALID")
        self.assertEqual(code(ver, c, req="NOT_APPLICABLE_BY_GOVERNED_DEFINITION", l2="UNAVAILABLE"), "NOT_APPLICABLE_NEEDS_DEFINITION_PROOF")
        self.assertEqual(code(c.record_verification, "K", "1", "UNAVAILABLE", "PASS", "PASS", 1, 1, "v", "d"), "HEALTH_VOCABULARY_UNKNOWN")
        self.assertEqual(code(c.record_verification, "K", "1", "REQUIRED", "PASS", "PASS", 1, 1, "", "d"), "HEALTH_BINDING_INCOMPLETE")
    def test_reverification_trigger_and_epoch_supersession(self):
        c = mk(); self.assertEqual(c.due_for_reverification(["K"], 11), [("K", "ABSENT")]); ver(c)
        self.assertEqual(c.due_for_reverification(["K"], 11), []); self.assertEqual(c.due_for_reverification(["K"], 50), [("K", "STALE")])
        c.advance_epoch("K", 2); self.assertEqual(rh(c, "K", "1", 11), "UNKNOWN"); self.assertEqual(c.due_for_reverification(["K"], 11), [("K", "EPOCH_ADVANCED")])
        c.reverify("K", "1", lambda s, v: ("PASS", "PASS", "dg"), 11, "REQUIRED", 5); self.assertEqual(rh(c, "K", "1", 12), "HEALTHY")
        c.request_reverification("K", "SCHEDULED"); self.assertEqual(rh(c, "K", "1", 12), "UNKNOWN")
        self.assertEqual(code(c.request_reverification, "K", "WHENEVER"), "UNKNOWN_REVERIFY_TRIGGER")
        def bad(s, v): return ("FAIL", "PASS", "dg")
        c.reverify("K", "1", bad, 13, "REQUIRED", 5); self.assertEqual(rh(c, "K", "1", 14), "NOT_HEALTHY")
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
        gw = sgw(c); e = _entry(ver="1"); hs = c.gateway_health("K", "1", 5, R("hl"), 4, binding=bind(c, "K")); return gw, e, hs, gw.resolve("o", e, I, I, 3, 10, hs)
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
            c = mk(); ver(c, "K", at=4, age=10); mut(c); gw = sgw(c); out = gw.resolve("o", _entry(ver="1"), I, I, 3, 10, c.gateway_health("K", "1", 5, R("hl"), 4, binding=bind(c, "K"))); self.assertNotIsInstance(out, G.Binding); self.assertEqual(out.reason, "HEALTH_UNACCEPTABLE")


from stage_a.storage.authority_class import approve_test_adapter, _APPROVED_TEST_ADAPTERS
class Flaky(InMemoryObjectStore):
    """Approved fault-injection adapter. kind: lost_ack (HEAD CAS lands, ack lost) | dropped (HEAD CAS never lands) | pre_object (fails before the immutable record is written)."""
    kind = None; fail_at = None; calls = 0; hook = None
    def arm(self, kind, hook=None): self.kind, self.hook, self.calls = kind, hook, 0; self.fail_at = 1
    def put_if_match(self, k, d, e):
        if self.kind in ("lost_ack", "dropped") and k.endswith("/" + "core1") or (self.kind in ("lost_ack", "dropped") and "head" in k):
            self.calls += 1
            if self.calls == self.fail_at:
                self.kind_now = self.kind
                if self.hook: self.hook()
                if self.kind == "lost_ack": super().put_if_match(k, d, e)
                raise UnknownCommit(self.kind)
        return super().put_if_match(k, d, e)
    def put_if_absent(self, k, d):
        if self.kind == "pre_object" and "journal" in k:
            self.kind = None; raise UnknownCommit("pre_object")
        return super().put_if_absent(k, d)
class UnknownCommitResolution(unittest.TestCase):
    def setUp(self): approve_test_adapter(Flaky)
    def tearDown(self): _APPROVED_TEST_ADAPTERS.remove(Flaky)
    def rig(self):
        st = Flaky(); c = mk(True, "core1", st); return st, c
    def effects(self, c, kind): return sum(1 for r in c._j.read_from(0) if r.kind == kind)
    def test_codex_repro_committed_lost_ack_returns_the_stored_result_with_one_effect(self):
        st, c = self.rig(); st.arm("lost_ack"); c.advance_epoch("A", 1)                    # was: EPOCH_NOT_ADVANCING while epoch 1 was committed
        self.assertEqual(self.effects(c, "EPOCH"), 1); self.assertEqual(c._replay()["epoch"]["A"], 1)
    def test_lost_ack_on_admission_is_not_reported_as_a_repeat_and_does_not_duplicate(self):
        st, c = self.rig(); st.arm("lost_ack"); self.assertEqual(adm(c), NEW); self.assertEqual(self.effects(c, "OBS_ADMITTED"), 1); self.assertEqual(adm(c), REPEAT)
    def test_dropped_write_is_revalidated_and_lands_once(self):
        st, c = self.rig(); st.arm("dropped"); c.advance_epoch("A", 1); self.assertEqual(self.effects(c, "EPOCH"), 1)
    def test_unknown_before_the_immutable_object_is_retried_once(self):
        st, c = self.rig(); st.arm("pre_object"); c.advance_epoch("A", 1); self.assertEqual(self.effects(c, "EPOCH"), 1)
    def test_competing_writer_lands_first_then_this_operation_revalidates_and_lands_once(self):
        st, c = self.rig(); other = TrackerCore(c._j, simulation=True)
        st.arm("dropped", hook=lambda: other.advance_epoch("B", 1))                      # another writer lands first; our write is dropped
        c.advance_epoch("A", 1); e = c._replay()["epoch"]; self.assertEqual((e["A"], e["B"]), (1, 1)); self.assertEqual(self.effects(c, "EPOCH"), 2)
    def test_identical_record_landed_by_another_writer_is_one_effect(self):
        st, c = self.rig(); other = TrackerCore(c._j, simulation=True); st.arm("dropped", hook=lambda: other.advance_epoch("A", 1))
        c.advance_epoch("A", 1); self.assertEqual(self.effects(c, "EPOCH"), 1)           # identical record at the same position: the effect exists exactly once
    def test_ordinary_success_and_restart_after_a_resolved_unknown(self):
        st, c = self.rig(); c.advance_epoch("A", 1); st.arm("lost_ack"); c.advance_epoch("A", 2)
        j2 = ObjectStoreJournal(c._j._s, "core1", "w2"); j2.acquire_epoch(); c2 = TrackerCore(j2, simulation=True)
        self.assertEqual(c2._replay()["epoch"]["A"], 2); self.assertEqual(self.effects(c2, "EPOCH"), 2)
class ConflictResolutionRestoresChosenBytes(unittest.TestCase):
    def two(self, p1=b"A", p2=b"B", av2=5, v2="V1"):
        c = mk(); adm(c, p1); adm(c, p2, av=av2, v=v2); return c, c.obs_key(facts())
    def test_codex_repro_choosing_the_second_candidate_restores_its_exact_bytes(self):
        c, k = self.two(); cands = c.candidates(k); self.assertEqual(len(cands), 2)
        cb = [cid for cid, r in cands.items() if r["payload_hex"] == b"B".hex()][0]
        self.assertFalse(c.observation_usable(k)); c.resolve_ambiguity(k, cb, "maker", "cert"); self.assertTrue(c.observation_usable(k))
        st = c._replay(); self.assertEqual(st["obs"][k]["payload_hex"], b"B".hex()); self.assertTrue(c._payload_reconstructs(st["obs"][k]))
        self.assertEqual(c.seal("XAUUSD", 10, 10, [k])[0], "SEALED"); self.assertEqual(len(c.candidates(k)), 2)                     # history retained
        self.assertEqual(adm(c, b"B"), REPEAT)                                                                                       # the chosen candidate is a plain repeat
    def test_metadata_only_conflicts_are_uniquely_selectable(self):
        c, k = self.two(b"A", b"A", av2=6)                                                                                           # same payload, different availability
        cands = c.candidates(k); self.assertEqual(len(cands), 2); c6 = [cid for cid, r in cands.items() if r["available_asof"] == 6][0]
        c.resolve_ambiguity(k, c6, "m", "c"); self.assertEqual(c._replay()["obs"][k]["available_asof"], 6)
        c2, k2 = self.two(b"A", b"A", v2="V2"); self.assertEqual(len(c2.candidates(k2)), 2)
    def test_a_rejected_known_candidate_does_not_reopen_the_ambiguity_and_restart_replays(self):
        c, k = self.two(); ca = [cid for cid, r in c.candidates(k).items() if r["payload_hex"] == b"A".hex()][0]; c.resolve_ambiguity(k, ca, "m", "c")
        self.assertEqual(adm(c, b"B"), REJECTED_KNOWN); self.assertTrue(c.observation_usable(k)); self.assertEqual(sum(1 for r in c._j.read_from(0) if r.kind == "OBS_AMBIGUOUS"), 1)
        j2 = ObjectStoreJournal(c._j._s, "core1", "w2"); j2.acquire_epoch(); c2 = TrackerCore(j2, simulation=True); self.assertTrue(c2.observation_usable(k))
    def test_corrupted_candidate_cannot_be_selected_or_used_or_sealed(self):
        c = mk(); adm(c); k = c.obs_key(facts()); st = c._replay(); good = dict(st["obs"][k])
        bad = dict(good, payload_hex=b"tampered".hex(), cid="x"); bad["cid"] = TrackerCore._cid(good["digest"], 5, "V9"); bad["vintage"] = "V9"
        c._j.append(c._j.head(), "OBS_AMBIGUOUS", {"key": k, "candidate": bad})
        self.assertEqual(code(c.resolve_ambiguity, k, bad["cid"], "m", "c"), "CANDIDATE_INTEGRITY_FAILED")
        c3 = mk(ns="c3"); head = c3._j.head(); c3._j.append(head, "OBS_ADMITTED", dict(good, payload_hex=b"tampered".hex()))
        self.assertFalse(c3.observation_usable(k)); self.assertEqual(code(c3.seal, "XAUUSD", 10, 10, [k]), "MEMBER_NOT_USABLE_OBSERVATION")
    def test_metadata_corruption_with_an_unchanged_candidate_id_is_detected(self):
        c = mk(ns="m"); adm(c); k = c.obs_key(facts()); good = dict(c._replay()["obs"][k]); c2 = mk(ns="m2")
        c2._j.append(c2._j.head(), "OBS_ADMITTED", dict(good, available_asof=999))                                    # payload intact, availability altered, cid stale
        self.assertFalse(c2.observation_usable(k)); self.assertEqual(code(c2.seal, "XAUUSD", 1000, 1000, [k]), "MEMBER_NOT_USABLE_OBSERVATION")
    def test_unchanged_identical_replay_and_other_instrument_control(self):
        c = mk(); self.assertEqual(adm(c), NEW); self.assertEqual(adm(c), REPEAT); self.assertEqual(adm(c, instrument="EURUSD"), NEW)
class EpochSupersession(unittest.TestCase):
    def chain(self):
        c = mk(); c.declare_dependency("B", "A"); c.declare_dependency("C", "B"); return c
    def test_codex_repro_second_epoch_before_reresolution_invalidates_old_witnesses(self):
        c = self.chain(); c.advance_epoch("A", 1); ver(c, "B"); ver(c, "C"); c.advance_epoch("A", 2)
        self.assertEqual(code(c.reresolve, "B", "1", 11), "NO_FRESH_WITNESS"); self.assertEqual(rh(c, "C", "1", 11), "UNKNOWN"); self.assertNotEqual(c.blocked("C"), [])
        ver(c, "B"); c.reresolve("B", "1", 11); self.assertEqual(code(c.reresolve, "C", "1", 11), "NO_FRESH_WITNESS"); ver(c, "C"); c.reresolve("C", "1", 11); self.assertEqual(c.blocked("C"), [])
    def test_witness_must_match_the_current_basis_not_only_follow_an_old_marker(self):
        c = self.chain(); c.advance_epoch("A", 1); ver(c, "B"); c.advance_epoch("A", 2)                              # witness recorded under epoch 1 basis
        self.assertEqual(code(c.reresolve, "B", "1", 11), "NO_FRESH_WITNESS")
    def test_branching_shared_ancestry_and_unaffected_baseline(self):
        c = mk(); c.declare_dependency("B", "A"); c.declare_dependency("C", "A"); c.declare_dependency("D", "B"); c.declare_dependency("D", "C"); c.declare_dependency("X", "Z")
        ver(c, "X"); c.advance_epoch("A", 1); c.advance_epoch("A", 2)
        self.assertTrue(all(c.blocked(n) for n in "BCD")); self.assertEqual(c.blocked("X"), []); self.assertEqual(rh(c, "X", "1", 11), "HEALTHY")      # unaffected positive control
        c.advance_epoch("B", 1); self.assertEqual(code(c.reresolve, "D", "1", 11), "UPSTREAM_STILL_INVALID")                                                  # a new failure before outstanding re-resolution
class ReconstructabilityAndHealthTyping(unittest.TestCase):
    def test_codex_repro_health_record_is_not_reconstruction(self):
        c = mk(); c.declare_dependency("S", "derived-missing-raw"); ver(c, "derived-missing-raw", l2="UNAVAILABLE", age=100)
        c.quarantine("S", "R"); c.clear_reason("S", "R", "cert", "maker"); self.assertEqual(code(c.reactivate, "S"), "NOT_RECONSTRUCTABLE"); self.assertFalse(c.retry_allowed("S"))
    def test_genuine_reconstruction_positive_blocked_and_incomplete_closure(self):
        c = mk(); adm(c, bar_identity="raw"); raw = c.obs_key(facts(bar_identity="raw")); c.declare_dependency("D1", raw); c.declare_dependency("S", "D1")
        ver(c, "S"); self.assertEqual(rh(c, "S", "1", 11), "HEALTHY")
        c.quarantine("S", "R"); c.clear_reason("S", "R", "cert", "maker"); c.reactivate("S"); self.assertTrue(c.retry_allowed("S"))                         # raw -> derived -> S
        self.assertEqual(rh(c, "S", "1", 11), "UNKNOWN")                                                                                                     # earlier evidence does not survive reactivation                                                                                                     # reactivation does not restore eligibility evidence
        d = mk(); adm(d, bar_identity="raw"); raw = d.obs_key(facts(bar_identity="raw")); d.declare_dependency("D1", raw); d.declare_dependency("D1", "missing"); d.declare_dependency("S", "D1")
        d.quarantine("S", "R"); d.clear_reason("S", "R", "c", "m"); self.assertEqual(code(d.reactivate, "S"), "NOT_RECONSTRUCTABLE")                          # incomplete transitive closure
        e = mk(); adm(e, bar_identity="raw"); raw = e.obs_key(facts(bar_identity="raw")); e.declare_dependency("S", raw); e.quarantine(raw, "R2"); e.quarantine("S", "R"); e.clear_reason("S", "R", "c", "m")
        self.assertEqual(code(e.reactivate, "S"), "NOT_RECONSTRUCTABLE")                                                                                    # blocked raw ancestor
    def test_codex_repro_qualified_recording_health_is_held_with_the_local_calculation_visible(self):
        q = mk(False); ver(q, "K"); r = q.recording_health("K", "1", 11)
        self.assertEqual((r.state, r.evidence_class, r.local_state, r.qualified), ("HELD", "QUALIFIED_HELD", "HEALTHY", False))
        s = mk(); ver(s, "K"); r = s.recording_health("K", "1", 11); self.assertEqual((r.state, r.evidence_class, r.qualified), ("HEALTHY", "SIMULATION_CALLER_ASSERTED", False))

class PlaneAndSafetyActions(unittest.TestCase):
    def test_plane_identity_is_stamped_and_a_foreign_plane_journal_is_refused_on_restore(self):
        st = InMemoryObjectStore(); j = ObjectStoreJournal(SimulationStore(st), "p", "w"); j.acquire_epoch(); c = TrackerCore(j, simulation=True, plane="core_market"); adm(c)
        self.assertTrue(all(json.loads(r.body_json)["plane"] == "core_market" for r in j.read_from(0)))
        j2 = ObjectStoreJournal(SimulationStore(st), "p", "w2"); j2.acquire_epoch()
        from stage_a.errors import IntegrityFailure
        with self.assertRaises(IntegrityFailure): TrackerCore(j2, simulation=True, plane="research")._replay()                    # restore does not change plane identity
        self.assertEqual(TrackerCore(j2, simulation=True, plane="core_market").observation_usable(c.obs_key(facts())), True)       # same plane: positive control
        self.assertEqual(code(TrackerCore, j2, simulation=True, plane="bogus"), "UNKNOWN_PLANE")
    def test_qualified_hold_never_suppresses_fail_closed_safety_actions(self):
        q = mk(False); q.declare_dependency("D", "U"); q.advance_epoch("U", 2); self.assertNotEqual(q.blocked("D"), [])                       # invalidation works when qualified
        q.fail_closed_missing_context_metadata("SUBJ"); self.assertFalse(q.retry_allowed("SUBJ")); self.assertEqual(q.blocked("SUBJ"), ["QUARANTINED"])
        self.assertEqual(code(q.clear_reason, "SUBJ", "CONTEXT_DOMAIN_METADATA_MISSING", "c", "m"), "SOURCE_APPROVAL_BINDING_UNBOUND_HELD")       # restoration stays blocked
        self.assertEqual(code(q.reactivate, "SUBJ"), "RECONSTRUCTION_PROOF_BINDING_UNBOUND_HELD")
        adm(q, bar_identity="x"); kx = q.obs_key(facts(bar_identity="x")); q.quarantine(kx, "R"); self.assertEqual(code(q.seal, "XAUUSD", 10, 10, [kx]), "MEMBER_BLOCKED")
import json

from stage_a.errors import IntegrityFailure
from stage_a.tracker.chain_status import ChainStatusAuthority, StatusFact
def shared(plane=None, sim=True, ns="pl"):
    st = InMemoryObjectStore(); st = SimulationStore(st) if sim else st; j = ObjectStoreJournal(st, ns, "w"); j.acquire_epoch(); return st, j, TrackerCore(j, simulation=sim, plane=plane)
def attach(st, ns="pl", w="w2", **k):
    j = ObjectStoreJournal(st, ns, w); j.acquire_epoch(); return j, TrackerCore(j, simulation=True, **k)

class R24PlaneIdentity(unittest.TestCase):
    def test_codex_repro_omitted_plane_cannot_attach_to_or_poison_a_tagged_journal(self):
        st, j, a = shared("core_market"); a.quarantine("S", "R")
        j2 = ObjectStoreJournal(st, "pl", "w2"); j2.acquire_epoch(); n = len(list(j2.read_from(0)))
        with self.assertRaises(IntegrityFailure): TrackerCore(j2, simulation=True)                         # refused at attach, before any append
        self.assertEqual(len(list(j2.read_from(0))), n); self.assertEqual(a.blocked("S"), ["QUARANTINED"])  # the correctly labelled reader is unharmed
    def test_race_attach_empty_then_other_writer_tags_the_plane_less_core_refuses_before_append(self):
        st, j, c0 = shared(None); j2, c1 = attach(st, plane="core_market"); c1.quarantine("S", "R")      # plane-less Core attached while the journal was still empty
        n = len(list(j.read_from(0)))
        with self.assertRaises(IntegrityFailure): c0.quarantine("S2", "R2")
        with self.assertRaises(IntegrityFailure): c0.blocked("S")
        self.assertEqual(len(list(j.read_from(0))), n); self.assertEqual(c1.blocked("S"), ["QUARANTINED"])
    def test_explicit_foreign_plane_and_mixed_history_are_refused_and_same_plane_restart_works(self):
        st, j, a = shared("core_market"); a.quarantine("S", "R")
        with self.assertRaises(IntegrityFailure): attach(st, plane="research")
        j2 = ObjectStoreJournal(st, "pl", "w3"); j2.acquire_epoch(); j2.append(j2.head(), "Q_REASON", {"subject": "X", "reason": "R"})            # untagged record forced into a tagged history
        with self.assertRaises(IntegrityFailure): TrackerCore(j2, simulation=True, plane="core_market")                                         # mixed history refused even for the right plane
        st2, ja, b = shared("research", ns="r"); b.quarantine("S", "R"); _, b2 = attach(st2, ns="r", plane="research"); self.assertEqual(b2.blocked("S"), ["QUARANTINED"])    # same plane restart: positive
    def test_tagged_core_cannot_attach_to_legacy_untagged_history_and_legacy_scope_is_explicit(self):
        st, j, legacy = shared(None, ns="lg"); legacy.quarantine("S", "R")
        with self.assertRaises(IntegrityFailure): attach(st, ns="lg", plane="core_market")
        _, l2 = attach(st, ns="lg"); self.assertEqual(l2.blocked("S"), ["QUARANTINED"]); self.assertIsNone(l2.plane)                                       # legacy mechanics stay scoped to plane-less Cores
    def test_identity_and_evidence_mode_are_not_mutable_by_label(self):
        _, _, c = shared("core_market")
        with self.assertRaises(AttributeError): c.plane = "research"
        with self.assertRaises(AttributeError): c.simulation = False
        self.assertEqual(c.plane, "core_market"); self.assertTrue(c.simulation)
        self.assertEqual(code(TrackerCore, c._j, simulation="yes"), "SIMULATION_FLAG_INVALID")

class R24FailClosedSafetyIntegration(unittest.TestCase):
    MV = ("f", "1", "XAUUSD", "H4", "m1")
    def test_codex_repro_bound_chain_stays_current_and_is_reported_not_claimed_applied(self):
        ch = ChainStatusAuthority(); ch.append(StatusFact(self.MV, 1, "CURRENT", 1, False))
        j = ObjectStoreJournal(SimulationStore(InMemoryObjectStore()), "x", "w"); j.acquire_epoch(); c = TrackerCore(j, simulation=True, chain_status=ch)
        r = c.fail_closed_missing_context_metadata("S", mv=self.MV, fence=10)
        self.assertEqual(c.blocked("S"), ["QUARANTINED"]); self.assertEqual(ch.status_at(self.MV, 10).status, "CURRENT")         # the owning chain is NOT transitioned by Core
        self.assertEqual(r.chain_reading, "CHAIN_STILL_CURRENT"); self.assertTrue(r.owning_lifecycle_transition.startswith("NOT_APPLIED")); self.assertFalse(r.restoration_allowed)
        self.assertEqual(c.reviews("S"), ["CONTEXT_DOMAIN_RESOLUTION_FAILURE"])                                                  # source-named review is a committed projection
        self.assertEqual(c.eligible_asof("S", "1", None, 11, mv=self.MV, fence=10)["reasons"][0], "QUARANTINED")                  # Core eligibility is closed even though the chain reads CURRENT
    def test_qualified_hold_does_not_suppress_the_action_and_restoration_stays_prohibited(self):
        for sim in (True, False):
            _, _, c = shared(None, sim=sim, ns="q%s" % sim); r = c.fail_closed_missing_context_metadata("S")
            self.assertTrue(r.core_quarantined and not r.restoration_allowed and r.chain_reading == "NO_CHAIN_BOUND_OR_MV_NOT_SUPPLIED"); self.assertEqual(c.blocked("S"), ["QUARANTINED"])
        _, _, s = shared(None, ns="qs"); s.fail_closed_missing_context_metadata("S")
        self.assertEqual(code(s.clear_reason, "S", "CONTEXT_DOMAIN_METADATA_MISSING", "cert", "maker"), "RESTORATION_PROHIBITED_UNTIL_GOVERNED_CONTEXT")   # even simulation cannot restore
        self.assertEqual(code(s.fail_closed_missing_context_metadata, "S", subject_kind="NOPE"), "UNKNOWN_SUBJECT_KIND"); self.assertFalse(s.retry_allowed("S"))
    def test_chain_mv_not_supplied_never_claims_a_chain_effect(self):
        ch = ChainStatusAuthority(); _, _, c = shared(None, ns="z"); c._chain = ch
        self.assertEqual(c.fail_closed_missing_context_metadata("S", mv=self.MV, fence=5).chain_reading, "CHAIN_NO_VISIBLE_STATUS")

class R24CandidateSemantics(unittest.TestCase):
    def two(self):
        c = mk(); adm(c, b"A"); adm(c, b"B"); k = c.obs_key(facts()); ca = [i for i, r in c.candidates(k).items() if r["payload_hex"] == b"A".hex()][0]; return c, k, ca
    def test_codex_repro_retransmit_of_rejected_candidate_reports_history_not_ambiguity(self):
        c, k, ca = self.two(); amb_n = lambda: sum(1 for r in c._j.read_from(0) if r.kind == "OBS_AMBIGUOUS"); n0 = amb_n(); self.assertEqual(adm(c, b"B"), CONFLICT); self.assertEqual(amb_n(), n0)   # no duplicate candidate record; while ambiguity is genuinely current the result agrees with state
        self.assertIn(k, c._replay()["amb"]); c.resolve_ambiguity(k, ca, "m", "c")
        self.assertEqual(adm(c, b"B"), REJECTED_KNOWN); self.assertTrue(c.observation_usable(k)); self.assertNotIn(k, c._replay()["amb"])    # result agrees with state; no policy adopted
        n = len(list(c._j.read_from(0))); adm(c, b"B"); self.assertEqual(len(list(c._j.read_from(0))), n)                       # no state change, no reopening
        self.assertEqual(adm(c, b"C"), CONFLICT); self.assertIn(k, c._replay()["amb"])                                         # a NEW conflicting candidate is still genuine ambiguity
    def test_future_watermark_is_held_and_freshness_inputs_are_validated(self):
        c = mk(); env = {"p": 1, "watermark": 1000}; c.register_contract("A", "1", c.derive_fingerprint(env), 5, True)
        self.assertEqual(c.resolve_contract(env, b"r", 10), ("HELD", "FUTURE_WATERMARK")); self.assertEqual(c.resolve_contract({"p": 1, "watermark": 8}, b"r", 10), ("RESOLVED", ("A", "1")))
        self.assertEqual(c.resolve_contract({"p": 1, "watermark": 10}, b"r", 10)[0], "RESOLVED")                              # equality: age 0 is fresh
        self.assertEqual(c.resolve_contract({"p": 1, "watermark": 4}, b"r", 10), ("HELD", "STALE_WATERMARK"))
        for bad in (-1, True, "8", 8.0, None): self.assertEqual(c.resolve_contract({"p": 1, "watermark": bad}, b"r", 10)[0], "HELD", bad)
        self.assertEqual(c.resolve_contract({"p": 1, "watermark": -1}, b"r", 3), ("HELD", "MISSING_OR_MALFORMED_WATERMARK"))      # negative watermark is malformed even when the arithmetic age would be inside the bound
        for args in (({"p": 1, "watermark": 8}, b"r", -1), ({"p": 1, "watermark": 8}, "r", 10), ("x", b"r", 10), ({"p": 1, "watermark": 8}, b"r", True)): self.assertEqual(code(c.resolve_contract, *args), "CONTRACT_INPUT_INVALID")
        fp = c.derive_fingerprint(env)
        for a in (("A", "1", fp, None, True), ("A", "1", fp, -1, True), ("A", "1", fp, True, True), ("A", "1", fp, 5, "no"), ("", "1", fp, 5, True)): self.assertEqual(code(c.register_contract, *a), "CONTRACT_FIELDS_INVALID", a)
    def test_codex_repro_a_failed_unavailable_future_stale_or_wrong_version_witness_never_clears_invalidation(self):
        def inv():
            c = mk(); c.declare_dependency("B", "A"); c.advance_epoch("A", 1); return c
        for kw, now, ver_ in (({"l2": "FAIL"}, 11, "1"), ({"l1": "FAIL"}, 11, "1"), ({"l2": "UNAVAILABLE"}, 11, "1"), ({}, 99, "1"), ({"at": 500}, 11, "1"), ({}, 11, "2")):
            c = inv(); ver(c, "B", **kw); self.assertEqual(code(c.reresolve, "B", ver_, now), "WITNESS_NOT_POSITIVE", (kw, now, ver_)); self.assertIn("EPOCH_INVALIDATED", c.blocked("B"))
        c = inv(); ver(c, "B", req="NOT_APPLICABLE_BY_GOVERNED_DEFINITION", l2="UNAVAILABLE", definition_ref="d"); c.reresolve("B", "1", 11)                 # not-applicable L2 + L1 PASS is a positive witness in simulation only
        c = inv(); ver(c, "B"); c.reresolve("B", "1", 11); self.assertEqual(c.blocked("B"), [])                                                          # positive control
    def test_epoch_acknowledgement_is_not_restoration_or_eligibility(self):
        c = mk(); c.declare_dependency("B", "A"); c.quarantine("B", "R"); c.advance_epoch("A", 1); ver(c, "B"); c.reresolve("B", "1", 11)
        self.assertEqual(c.blocked("B"), ["QUARANTINED"]); self.assertFalse(c.retry_allowed("B"))                               # the quarantine survives the acknowledgement
        self.assertEqual(c.eligible_asof("B", "1", None, 11)["state"], "SIMULATION_EVIDENCE_NOT_ELIGIBLE")

if __name__ == "__main__": unittest.main()
