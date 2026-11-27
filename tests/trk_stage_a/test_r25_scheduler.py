"""R25 bounded trigger -> actual verifier -> Core Health -> Gateway consumption. Simulation-labelled; not a daemon; no host/scheduling qualification."""
import unittest
from stage_a.errors import Refusal
from stage_a.composer.expression.manifest import Manifest
from stage_a.gateway import contracts as G
from stage_a.core.tracker_core import TrackerCore
from stage_a.tracker import reverify_scheduler as S
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.storage.authority_class import SimulationStore
from .fixtures import momentum_manifest
from .test_boundaries import _entry, _gw, I, R
from .test_r24_composed import core, declared, SIMS
from .test_r24_core import code, ver
from .strict_gateway import sgw, bind

KEY = "XAUUSD/H4/mom3/1"
class Scheduler(unittest.TestCase):
    def setUp(self): self.m = Manifest.from_dict(momentum_manifest()); self.b = {KEY: (self.m, declared(self.m), SIMS())}
    def test_absent_subject_is_verified_then_not_due_and_gateway_consumes_the_result(self):
        c = core(); r = S.run_reverification_pass(c, self.b, [KEY], now=10, max_age=50)
        self.assertEqual([(i.subject, i.trigger, i.outcome, i.detail) for i in r], [(KEY, "ABSENT", "VERIFIED", "PASS")])
        self.assertEqual([r_.kind for r_ in c._j.read_from(0) if r_.kind == "REVERIFY_REQUESTED"], ["REVERIFY_REQUESTED"])            # the trigger is journaled before the verifier runs
        self.assertEqual(S.run_reverification_pass(c, self.b, [KEY], now=11, max_age=50), [])                    # fresh evidence: nothing due, nothing re-run
        hs = c.gateway_health(KEY, "1", 12, R("hl"), 11, binding=bind(c, KEY)); self.assertTrue(hs.acceptable); self.assertEqual(hs.evidence_class, "SIMULATION")
        self.assertIsInstance(sgw(c).resolve("o", _entry(ver="1"), I, I, 3, 20, hs), G.Binding)
    def test_stale_future_epoch_and_unknown_l2_block_gateway_until_a_real_pass(self):
        c = core(); S.run_reverification_pass(c, self.b, [KEY], now=10, max_age=5)
        self.assertEqual([i.trigger for i in S.run_reverification_pass(c, self.b, [KEY], now=20, max_age=5)], ["STALE"])
        self.assertTrue(c.gateway_health(KEY, "1", 21, R("hl"), 20).acceptable)
        c.declare_dependency(KEY, "UP"); c.advance_epoch("UP", 1)
        self.assertFalse(c.gateway_health(KEY, "1", 21, R("hl"), 20).acceptable)                                  # invalidated: blocked before re-verification
        self.assertEqual(code(c.reresolve, KEY, "1", 21), "NO_FRESH_WITNESS")                                  # old evidence is no witness
        self.assertEqual([i.trigger for i in S.run_reverification_pass(c, self.b, [KEY], now=22, max_age=5)], ["EPOCH_ADVANCED"])
        c.reresolve(KEY, "1", 23); self.assertTrue(c.gateway_health(KEY, "1", 24, R("hl"), 23).acceptable)           # positive control: new verifier pass clears
    def test_corrupt_bytes_never_become_healthy_and_future_evidence_is_due(self):
        class Tamper(InMemoryObjectStore):
            def get(self, k):
                g = super().get(k); return None if g is None else (g[0][:-1] + bytes([g[0][-1] ^ 1]),) + tuple(g[1:])
        from stage_a.storage.authority_class import approve_test_adapter; approve_test_adapter(Tamper)
        c = core(); b = {KEY: (self.m, declared(self.m), SimulationStore(Tamper()))}
        r = S.run_reverification_pass(c, b, [KEY], now=10, max_age=5); self.assertEqual((r[0].outcome, r[0].detail), ("VERIFIED", "FAIL"))
        self.assertFalse(c.gateway_health(KEY, "1", 11, R("hl"), 10).acceptable)
        c2 = core(); c2.record_verification(KEY, "1", "REQUIRED", "PASS", "PASS", 50, 5, "v", "d")               # evidence dated in the future relative to now
        self.assertEqual([i.trigger for i in S.run_reverification_pass(c2, self.b, [KEY], now=10, max_age=5)], ["STALE"])
    def test_unbound_mismatched_and_bounded_items_are_reported_not_verified(self):
        c = core(); r = S.run_reverification_pass(c, {}, [KEY, "OTHER/H4/x/1"], now=10, max_age=5); self.assertEqual([i.outcome for i in r], ["UNBOUND", "UNBOUND"])
        self.assertEqual(c.recording_health(KEY, "1", 11).state, "UNKNOWN")
        r = S.run_reverification_pass(c, {"OTHER/H4/x/1": self.b[KEY]}, ["OTHER/H4/x/1"], now=10, max_age=5); self.assertEqual(r[0].outcome, "KEY_MISMATCH")
        r = S.run_reverification_pass(c, self.b, [KEY, "A/H4/a/1", "B/H4/b/1"], now=10, max_age=5, max_items=1); self.assertEqual([i.outcome for i in r], ["VERIFIED", "SKIPPED_BOUND_EXCEEDED", "SKIPPED_BOUND_EXCEEDED"])
        self.assertEqual(code(S.run_reverification_pass, c, self.b, [KEY], now=10, max_age=5, max_items=0), "SCHEDULER_BOUND_INVALID")
    def test_wrong_class_store_is_refused_and_leaves_no_writes_and_unrelated_baseline_is_untouched(self):
        c = core(); ver(c, "BASE", at=10, age=100); plain = InMemoryObjectStore()
        r = S.run_reverification_pass(c, {KEY: (self.m, declared(self.m), plain)}, [KEY, "BASE"], now=11, max_age=5)
        self.assertEqual([(i.subject, i.outcome, i.detail) for i in r], [(KEY, "REFUSED", "REVERIFY_CARRIER_CLASS_MISMATCH")]); self.assertEqual(plain.list_prefix(""), [])
        self.assertEqual(c.recording_health("BASE", "1", 12).state, "HEALTHY")
if __name__ == "__main__": unittest.main()

class GatewayHealthBinding(unittest.TestCase):
    """R27: Core Health is journal-confirmed, bound to the exact dependency AND to an explicitly supplied subject association; plain/shape-only and forged snapshots are denied by default."""
    def setUp(self):
        self.c = core(); self.m = Manifest.from_dict(momentum_manifest())
        S.run_reverification_pass(self.c, {KEY: (self.m, declared(self.m), SIMS())}, [KEY], now=10, max_age=50)
    def hs(self, binding, assoc=True, c=None, key=KEY, version="1"):
        c = c or self.c
        if assoc and binding is not None: c.associate_subject(key, binding, "test-supplied-association")
        return c.gateway_health(key, version, 12, R("hl"), 11, binding=binding)
    def out(self, hs, gw=None, entry=None): return (gw or sgw(self.c)).resolve("o", entry or _entry(ver="1"), I, I, 3, 20, hs)
    def test_matching_associated_binding_delivers_unbound_and_mismatched_are_denied(self):
        self.assertIsInstance(self.out(self.hs(G.HealthBinding(I, "1", I, I))), G.Binding)
        self.assertEqual(self.out(self.hs(None)).reason, "HEALTH_SNAPSHOT_NOT_CONFIRMED")                                     # not journal-issued without a binding
        for b in (G.HealthBinding(bytes(16), "1", I, I), G.HealthBinding(I, "1", bytes(16), I), G.HealthBinding(I, "1", I, bytes(16))):
            self.assertEqual(self.out(self.hs(b), gw=sgw(self.c)).reason, "HEALTH_BINDING_MISMATCH")
    def test_codex_r27_repro_unrelated_subject_cannot_certify_the_dependency(self):
        c = core(); c.record_verification("unrelated-subject", "1", "REQUIRED", "PASS", "PASS", 10, 50, "v", "d")
        hs = c.gateway_health("unrelated-subject", "1", 12, R("hl"), 11, binding=G.HealthBinding(I, "1", I, I))
        self.assertFalse(hs.acceptable); self.assertEqual(hs.held_reason, "SUBJECT_ASSOCIATION_UNBOUND")
        out = sgw(c).resolve("o", _entry(ver="1"), I, I, 3, 20, hs); self.assertNotIsInstance(out, G.Binding); self.assertEqual(out.reason, "HEALTH_UNACCEPTABLE")
        self.assertEqual(code(c.associate_subject, "", G.HealthBinding(I, "1", I, I), "x"), "SUBJECT_ASSOCIATION_INVALID")
    def test_association_is_per_subject_and_per_binding(self):
        b = G.HealthBinding(I, "1", I, I); self.c.associate_subject("OTHER", b, "ref")
        hs = self.c.gateway_health(KEY, "1", 12, R("hl"), 11, binding=b); self.assertEqual(hs.held_reason, "SUBJECT_ASSOCIATION_UNBOUND")                  # OTHER's association never covers KEY
        self.c.associate_subject(KEY, G.HealthBinding(bytes(16), "1", I, I), "ref"); self.assertEqual(self.c.gateway_health(KEY, "1", 12, R("hl"), 11, binding=b).held_reason, "SUBJECT_ASSOCIATION_UNBOUND")
    def test_plain_and_forged_snapshots_are_denied_by_default_and_legacy_needs_the_explicit_switch(self):
        import dataclasses
        plain = G.HealthSnapshot(R("hl"), 4, True); self.assertEqual(self.out(plain).reason, "HEALTH_SNAPSHOT_SHAPE_ONLY_NOT_ACCEPTED")
        legacy = sgw(self.c); legacy.allow_shape_only_health = True; self.assertIsInstance(self.out(plain, gw=legacy), G.Binding)            # LEGACY harness only; proves nothing about any subject
        good = self.hs(G.HealthBinding(I, "1", I, I))
        for forged in (dataclasses.replace(good, binding=None), dataclasses.replace(good, acceptable=True, held_reason="x"), dataclasses.replace(good, resolved_at=1), dataclasses.replace(good, subject="OTHER"),
                       dataclasses.replace(good, snapshot_id="0" * 64), dataclasses.replace(good, binding=G.HealthBinding(I, "1", I, bytes(16)))):
            self.assertEqual(self.out(forged).reason, "HEALTH_SNAPSHOT_NOT_CONFIRMED")
        self.assertEqual(self.out(good, gw=_gw(ver="1")).reason, "HEALTH_SNAPSHOT_NOT_CONFIRMED")                                                  # a gateway without the issuing Core cannot confirm
        self.assertFalse(hasattr(good, "typed_internal"))                                                                                         # no optional public opt-out marker remains
    def test_confirmation_survives_restart_and_wrong_version_is_refused(self):
        good = self.hs(G.HealthBinding(I, "1", I, I)); c2 = TrackerCore(self.c._j, simulation=True); self.assertTrue(c2.confirm_snapshot(good)); self.assertIsInstance(self.out(good, gw=sgw(c2)), G.Binding)
        self.assertEqual(code(self.hs, G.HealthBinding(I, "999", I, I)), "HEALTH_BINDING_VERSION_MISMATCH")
        self.assertEqual(sgw(self.c, ver="2").resolve("o", _entry(ver="2"), I, I, 3, 20, good).reason, "HEALTH_BINDING_MISMATCH")

class PinnedEvidence(unittest.TestCase):
    """R26: the scheduler verifies the EXISTING pinned candidate record; it never rebuilds/overwrites it."""
    def setUp(self):
        import json; self.json = json
        self.m = Manifest.from_dict(momentum_manifest()); self.store = SIMS(); self.b = {KEY: (self.m, declared(self.m), self.store)}
        from stage_a.tracker.reverification import pinned_key
        from stage_a.identifiers import Scope, FeatureKey
        self.pk = pinned_key(FeatureKey(Scope(self.m.instrument, self.m.timeframe), self.m.feature_id, self.m.feature_version))
    def raw(self): return self.store._i._d["SIMULATION/" + self.pk][0]
    def test_first_pass_pins_then_later_passes_verify_the_same_bytes(self):
        c = core(); r = S.run_reverification_pass(c, self.b, [KEY], now=10, max_age=5); self.assertEqual((r[0].evidence, r[0].detail), ("PINNED_NEW", "PASS")); pinned = self.raw()
        r = S.run_reverification_pass(c, self.b, [KEY], now=20, max_age=5); self.assertEqual((r[0].trigger, r[0].evidence, r[0].detail), ("STALE", "PINNED_EXISTING", "PASS")); self.assertEqual(self.raw(), pinned)
    def test_altered_pinned_record_is_verified_as_found_fails_and_is_never_repaired(self):
        c = core(); S.run_reverification_pass(c, self.b, [KEY], now=10, max_age=5)
        rec = self.json.loads(self.raw()); rec["materialization_hash"] = "arbitrary-corrupt-hash"; bad = self.json.dumps(rec, sort_keys=True, separators=(",", ":")).encode()
        self.store._i._d["SIMULATION/" + self.pk] = (bad, 99)
        r = S.run_reverification_pass(c, self.b, [KEY], now=20, max_age=5); self.assertEqual((r[0].evidence, r[0].detail), ("PINNED_EXISTING", "FAIL")); self.assertEqual(self.raw(), bad)
        self.assertEqual(c.recording_health(KEY, "1", 21).state, "NOT_HEALTHY"); self.assertFalse(c.gateway_health(KEY, "1", 21, R("hl"), 20, binding=G.HealthBinding(I, "1", I, I)).acceptable)
    def test_garbage_pinned_bytes_and_probe_tamper_fail(self):
        for payload in (b"\xff\xfe not json", b"[1,2]", b"{}"):
            c = core(); S.run_reverification_pass(c, self.b, [KEY], now=10, max_age=5); self.store._i._d["SIMULATION/" + self.pk] = (payload, 99)
            r = S.run_reverification_pass(c, self.b, [KEY], now=20, max_age=5); self.assertEqual(r[0].detail, "FAIL", payload); self.assertEqual(c.recording_health(KEY, "1", 21).state, "NOT_HEALTHY")
        self.setUp()      # fresh store: the loop above left garbage pinned
        c = core(); S.run_reverification_pass(c, self.b, [KEY], now=10, max_age=5); rec = self.json.loads(self.raw()); rec["probe_batch"] = rec["probe_batch"][:-1]
        self.store._i._d["SIMULATION/" + self.pk] = (self.json.dumps(rec).encode(), 99); self.assertEqual(S.run_reverification_pass(c, self.b, [KEY], now=20, max_age=5)[0].detail, "FAIL")
    def test_existing_pin_for_other_feature_binding_fails_scope(self):
        c = core(); S.run_reverification_pass(c, self.b, [KEY], now=10, max_age=5); rec = self.json.loads(self.raw()); rec["feature_version"] = "2"
        self.store._i._d["SIMULATION/" + self.pk] = (self.json.dumps(rec).encode(), 99); self.assertEqual(S.run_reverification_pass(c, self.b, [KEY], now=20, max_age=5)[0].detail, "FAIL")
    def test_pin_race_never_replaces_and_wrong_class_store_refused_before_any_write(self):
        c = core(); S.run_reverification_pass(c, self.b, [KEY], now=10, max_age=5); before = self.raw()
        self.assertFalse(self.store.put_if_absent(self.pk, b"other")); self.assertEqual(self.raw(), before)
        plain = InMemoryObjectStore(); c2 = core(); r = S.run_reverification_pass(c2, {KEY: (self.m, declared(self.m), plain)}, [KEY], now=10, max_age=5); self.assertEqual(r[0].detail, "REVERIFY_CARRIER_CLASS_MISMATCH"); self.assertEqual(plain.list_prefix(""), [])

class PersistedPass(unittest.TestCase):
    """R31: the pass result (including work NOT done) is journaled and re-readable after restart; skipped/unbound never become health."""
    def test_pass_record_persists_skipped_and_unbound_work_survives_restart_and_is_idempotent_but_not_rewritable(self):
        m = Manifest.from_dict(momentum_manifest()); b = {KEY: (m, declared(m), SIMS())}; c = core()
        r = S.run_reverification_pass(c, b, [KEY, "A/H4/a/1", "B/H4/b/1"], now=10, max_age=50, max_items=1, pass_id="P1")
        self.assertEqual([i.outcome for i in r], ["VERIFIED", "SKIPPED_BOUND_EXCEEDED", "SKIPPED_BOUND_EXCEEDED"])
        c2 = TrackerCore(c._j, simulation=True); p = c2.reverify_pass("P1"); self.assertEqual((p["at"], p["max_items"], [i[2] for i in p["items"]]), (10, 1, ["VERIFIED", "SKIPPED_BOUND_EXCEEDED", "SKIPPED_BOUND_EXCEEDED"]))
        self.assertEqual(c2.recording_health("A/H4/a/1", "1", 11).state, "UNKNOWN")                                          # skipped work is not health
        n = len(c._j.read_from(0)); c.record_reverify_pass("P1", 10, 1, p["items"]); self.assertEqual(len(c._j.read_from(0)), n)   # identical re-record: no-op
        self.assertEqual(code(c.record_reverify_pass, "P1", 10, 1, [["x", "y", "VERIFIED", "PASS", ""]]), "REVERIFY_PASS_ID_REUSED")
        self.assertEqual(code(c.record_reverify_pass, "", 10, 1, []), "REVERIFY_PASS_INVALID"); self.assertIsNone(c.reverify_pass("nope"))
        S.run_reverification_pass(c, b, [KEY], now=11, max_age=50); self.assertEqual([k.kind for k in c._j.read_from(0)].count("REVERIFY_PASS"), 1)       # no pass_id: nothing recorded
