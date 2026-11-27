"""R21 Core mechanics through ONE composition path (TrackerCore over a single fenced journal) with downstream Gateway / FW / ML consuming its actual health output.
Simulation evidence over internal CANDIDATE carriers: no provider, no canonical production bytes, no gate."""
import unittest
from stage_a.errors import Refusal
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.storage.authority_class import SimulationStore
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.core.tracker_core import TrackerCore, NEW, REPEAT, CONFLICT, OBS_FACTS_CANDIDATE
from stage_a.gateway import contracts as G
from stage_a.fw import receiver as FW
from stage_a.ml import receiver as ML
from .test_boundaries import _entry, _gw, I, R, NONE_, T
def code(fn, *a, **k):
    try: fn(*a, **k)
    except Refusal as e: return e.code
def core(sim=True, ns="core1"):
    st = InMemoryObjectStore(); st = SimulationStore(st) if sim else st
    j = ObjectStoreJournal(st, ns, "w"); j.acquire_epoch(); return TrackerCore(j, simulation=sim)
def facts(**o):
    f = {k: k + "-v" for k in OBS_FACTS_CANDIDATE}; f.update(o); return f
def mem(key, tf="H4", v="V1", av=5, ins="XAUUSD"): return {"key": key, "timeframe": tf, "vintage": v, "available_asof": av, "instrument": ins}

class Observation(unittest.TestCase):
    def test_idempotent_conflict_quarantine_no_overwrite(self):
        c = core(); self.assertEqual(c.admit_observation(facts(), b"a"), NEW); self.assertEqual(c.admit_observation(facts(), b"a"), REPEAT)
        self.assertEqual(c.admit_observation(facts(), b"b"), CONFLICT); self.assertFalse(c.observation_usable(c.obs_key(facts())))
        self.assertEqual(c.admit_observation(facts(), b"a"), CONFLICT)               # original payload no longer silently wins
    def test_instrument_qualified_no_collision_and_bad_facts(self):
        c = core(); self.assertNotEqual(c.obs_key(facts()), c.obs_key(facts(instrument="EURUSD")))
        self.assertEqual(code(c.obs_key, {"instrument": "x"}), "OBSERVATION_FACTS_INVALID")
    def test_resolution_needs_independent_certifier_and_candidate(self):
        c = core(); c.admit_observation(facts(), b"a"); c.admit_observation(facts(), b"b"); k = c.obs_key(facts())
        from stage_a.storage.byte_primitives import domain_hash
        d = domain_hash("TRK/PAYLOAD", b"a")
        self.assertEqual(code(c.resolve_ambiguity, k, d, "x", "x"), "CREATOR_IS_CERTIFIER")
        self.assertEqual(code(c.resolve_ambiguity, k, "nope", "x", "y"), "NOT_A_PENDING_CANDIDATE")
        c.resolve_ambiguity(k, d, "x", "y"); self.assertTrue(c.observation_usable(k))
class Contract(unittest.TestCase):
    def test_exactly_one_zero_many_stale_and_label_spoof(self):
        c = core(); env = {"o": 1, "h": 2, "label": "PROVIDER_A", "watermark": 100}; fp = c.derive_fingerprint(env)
        self.assertEqual(c.resolve_contract(env, b"r", 101)[0], "QUARANTINED")                  # zero match
        c.register_contract("A", "1", fp, 10, True); self.assertEqual(c.resolve_contract(env, b"r", 105), ("RESOLVED", ("A", "1")))
        self.assertEqual(c.resolve_contract(dict(env, label="SOMETHING_ELSE"), b"r", 105)[0], "RESOLVED")   # label is not the discriminator
        self.assertEqual(c.resolve_contract(dict(env, extra=[]), b"r", 105)[0], "QUARANTINED")  # different structure -> no match
        self.assertEqual(c.resolve_contract(env, b"r", 200), ("HELD", "STALE_OR_MISSING_WATERMARK"))
        c.register_contract("B", "1", fp, 10, True); self.assertEqual(c.resolve_contract(env, b"r", 105), ("QUARANTINED", "MULTI_MATCH"))
    def test_battery_not_passed_is_not_usable(self):
        c = core(); env = {"o": 1, "watermark": 1}; c.register_contract("A", "1", c.derive_fingerprint(env), 10, False)
        self.assertEqual(c.resolve_contract(env, b"r", 2)[0], "NOT_USABLE")
class Snapshot(unittest.TestCase):
    def setUp(self):
        self.c = core()
        for k in "abc": self.c.admit_observation(facts(bar_identity=k), b"p")
        self.k = {k: self.c.obs_key(facts(bar_identity=k)) for k in "abc"}
    def test_half_open_fence_and_identical_members_one_hash(self):
        m = [mem(self.k["a"], av=9), mem(self.k["b"], av=10)]
        r1 = self.c.seal("XAUUSD", 10, 10, m); r2 = self.c.seal("XAUUSD", 10, 10, m)
        self.assertEqual(r1, r2); self.assertEqual(r1[0], "SEALED")
        self.assertNotEqual(r1[1], self.c.seal("XAUUSD", 10, 10, [mem(self.k["a"], av=9)])[1] + "x")
        self.assertEqual(self.c.seal("XAUUSD", 10, 10, [mem(self.k["a"], av=9)])[1], r1[1])    # av==fence member (b) is excluded from the hash
        self.assertNotEqual(self.c.seal("XAUUSD", 11, 11, m)[1], r1[1])                       # at fence 11 b is included
        self.assertTrue(self.c.verify_snapshot(r1[1], "XAUUSD", 10, 10, m))
    def test_mixed_vintage_refused_unless_source_owned_policy_registered(self):
        m = [mem(self.k["a"], v="V1"), mem(self.k["b"], v="V2")]
        self.assertEqual(self.c.seal("XAUUSD", 10, 10, m), ("MIXED_VINTAGE_REFUSED", None))
        self.assertEqual(self.c.seal("XAUUSD", 10, 10, m, "unregistered"), ("MIXED_VINTAGE_REFUSED", None))   # no default allow
        self.c.register_mixed_policy("P", "owner"); self.assertEqual(self.c.seal("XAUUSD", 10, 10, m, "P")[0], "SEALED")
    def test_cross_instrument_ambiguous_and_unknown_members_refused(self):
        self.assertEqual(code(self.c.seal, "XAUUSD", 10, 10, [mem(self.k["a"], ins="EURUSD")]), "CROSS_INSTRUMENT_MEMBER")
        self.assertEqual(code(self.c.seal, "XAUUSD", 10, 10, [mem("ghost")]), "MEMBER_NOT_USABLE_OBSERVATION")
        self.c.admit_observation(facts(bar_identity="a"), b"DIFFERENT")
        self.assertEqual(code(self.c.seal, "XAUUSD", 10, 10, [mem(self.k["a"])]), "MEMBER_NOT_USABLE_OBSERVATION")
        self.assertEqual(code(self.c.seal, "XAUUSD", 12, 10, []), "ASOF_AFTER_FENCE")
class EpochQuarantineHealth(unittest.TestCase):
    def test_epoch_invalidates_transitive_dependents_until_reresolved(self):
        c = core(); c.declare_dependency("B", "A"); c.declare_dependency("C", "B"); c.advance_epoch("A", 2)
        self.assertEqual(c.blocked("C"), ["EPOCH_INVALIDATED"]); self.assertEqual(code(c.advance_epoch, "A", 2), "EPOCH_NOT_ADVANCING")
        c.reresolve("C"); self.assertEqual(c.blocked("C"), []); self.assertEqual(code(c.reresolve, "C"), "NOT_INVALIDATED")
    def test_multi_reason_retry_suppression_reopen_is_not_reactivation(self):
        c = core(); c.admit_observation(facts(), b"p"); k = c.obs_key(facts())
        c.quarantine("S", "R1"); c.quarantine("S", "R2"); self.assertFalse(c.retry_allowed("S"))
        c.clear_reason("S", "R1", "cert", "maker"); self.assertFalse(c.retry_allowed("S"))             # R2 still open
        self.assertEqual(code(c.reactivate, "S", [k]), "REASONS_STILL_OPEN")
        c.clear_reason("S", "R2", "cert", "maker"); c.reopen("S"); self.assertFalse(c.retry_allowed("S"))   # reopened but not reactivated
        self.assertEqual(code(c.reactivate, "S", ["ghost"]), "NOT_RECONSTRUCTABLE"); c.reactivate("S", [k]); self.assertTrue(c.retry_allowed("S"))
        self.assertEqual(code(c.clear_reason, "S", "R1", "x", "x"), "CREATOR_IS_CERTIFIER")
    def test_recording_health_never_falls_back_from_required_l2_and_stale_never_certifies(self):
        c = core(); c.record_verification("K", "REQUIRED", "UNAVAILABLE", "PASS", 10, 5); self.assertEqual(c.recording_health("K", 11), "UNKNOWN")
        c.record_verification("K", "REQUIRED", "PASS", "PASS", 10, 5); self.assertEqual(c.recording_health("K", 11), "HEALTHY"); self.assertEqual(c.recording_health("K", 99), "UNKNOWN")
        c.record_verification("K", "NOT_APPLICABLE_BY_GOVERNED_DEFINITION", "UNAVAILABLE", "PASS", 10, 5); self.assertEqual(c.recording_health("K", 11), "HEALTHY")
        c.record_verification("K", "REQUIRED", "FAIL", "PASS", 10, 5); self.assertEqual(c.recording_health("K", 11), "NOT_HEALTHY")
        self.assertEqual(code(c.record_verification, "K", "UNAVAILABLE", "PASS", "PASS", 1, 1), "HEALTH_VOCABULARY_UNKNOWN")      # the old appendix error is not a state
        self.assertEqual(core().recording_health("none", 1), "UNKNOWN")
    def test_asof_eligibility_only_from_qualified_journals(self):
        sim = core(True); sim.record_verification("K", "REQUIRED", "PASS", "PASS", 1, 100); self.assertEqual(sim.eligible_asof("K", sim._j.head().seq, 2)["reasons"], ["SIMULATION_NOT_ELIGIBLE"])   # healthy simulation is still never eligible
        q = core(False); q.record_verification("K", "REQUIRED", "PASS", "PASS", 1, 100); seq = q._j.head().seq
        self.assertTrue(q.eligible_asof("K", seq, 2)["eligible"]); self.assertIn("RECORDING_HEALTH_NOT_HEALTHY", q.eligible_asof("K", 0, 2)["reasons"])   # as-of before the record
        q.quarantine("K", "R"); self.assertFalse(q.eligible_asof("K", q._j.head().seq, 2)["eligible"]); self.assertTrue(q.eligible_asof("K", seq, 2)["eligible"])   # as-known view unchanged
    def test_class_mismatch_and_reviewer_guard(self):
        j = ObjectStoreJournal(SimulationStore(InMemoryObjectStore()), "x", "w"); j.acquire_epoch()
        self.assertEqual(code(TrackerCore, j, simulation=False), "AUTHORITY_CLASS_MISMATCH")
        c = core(); f = dict(finding_id="F1", task_origin="R21", summary="s", author="codex"); c.accept_finding(f)
        self.assertEqual(code(c.accept_finding, dict(f, authorizes_stage_advance="true")), "REVIEW_INPUT_NOT_FINDING_ONLY")
        self.assertEqual(code(c.accept_finding, {k: v for k, v in f.items() if k != "task_origin"}), "REVIEW_INPUT_NOT_FINDING_ONLY")
class Composition(unittest.TestCase):
    """Core output -> actual Gateway.resolve -> FW.receive_verified / ML.build_row."""
    def run_path(self, healthy):
        c = core(False)
        if healthy: c.record_verification("K", "REQUIRED", "PASS", "PASS", 4, 10)
        else: c.record_verification("K", "REQUIRED", "UNAVAILABLE", "PASS", 4, 10)
        gw = _gw(); e = _entry(); hs = c.gateway_health("K", 5, R("hl"), 4)
        return gw, e, gw.resolve("o", e, I, I, 3, 10, hs)
    def test_healthy_core_yields_binding_consumed_by_fw_and_ml(self):
        gw, e, out = self.run_path(True); self.assertIsInstance(out, G.Binding)
        self.assertIs(FW.receive_verified(out, e, I, I, T, gw), out)
        self.assertTrue(ML.build_row("r", R("gen"), [e], [out], gw, "ORIGINAL_AS_OBSERVED", NONE_, lambda o: NONE_).included)
    def test_unknown_health_blocks_delivery_downstream(self):
        gw, e, out = self.run_path(False); self.assertNotIsInstance(out, G.Binding)
    def test_quarantine_or_epoch_invalidation_blocks_delivery_downstream(self):
        for mut in (lambda c: c.quarantine("K", "R"), lambda c: (c.declare_dependency("K", "U"), c.advance_epoch("U", 2))):
            c = core(False); c.record_verification("K", "REQUIRED", "PASS", "PASS", 4, 10); mut(c)
            gw = _gw(); out = gw.resolve("o", _entry(), I, I, 3, 10, c.gateway_health("K", 5, R("hl"), 4)); self.assertNotIsInstance(out, G.Binding)
if __name__ == "__main__": unittest.main()
