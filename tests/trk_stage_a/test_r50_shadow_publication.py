import unittest
from stage_a.errors import Refusal
from stage_a.ml.shadow_ledger import ShadowLedger
from stage_a.ml.shadow_publication import ShadowPublisher, AtomicRecordSink
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.tracker.atomic_publication import AtomicRecordStore
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
SCHED = [("k", "t1"), ("k", "t2"), ("k", "t3"), ("k", "t4")]       # TEST schedule only; no source defines one
class Sink:
    """TEST idempotent sink (in-memory): commit lands the record; `fail_before` raises BEFORE landing, `fail_after` raises AFTER landing (unknown outcome); `unreadable` makes readback raise."""
    def __init__(self): self.store = {}; self.commits = []; self.fail_before = set(); self.fail_after = set(); self.unreadable = False
    def commit(self, eid, payload):
        self.commits.append(eid)
        if eid in self.fail_before: raise RuntimeError("sink down")
        if eid in self.store and self.store[eid] != payload: raise RuntimeError("different payload")
        self.store[eid] = payload
        if eid in self.fail_after: raise RuntimeError("WRITE_LANDED_OUTCOME_UNKNOWN")
    def readback(self, eid):
        if self.unreadable: raise RuntimeError("readback down")
        return self.store.get(eid)
class Rig:
    def __init__(self, fenced=(), verdicts=None, sched=SCHED, eid=None):
        self.l = ShadowLedger(); self.sink = Sink(); self.calls = []; self.fenced = set(fenced); self.v = verdicts or {}
        self.p = ShadowPublisher(self.l, schedule=sched, fence=lambda k, t: t in self.fenced, event_id=eid or (lambda k, t: "E-%s-%s" % (k, t)), model=self.model, sink=self.sink)
    def model(self, slot):
        self.calls.append(slot[1]); v = self.v.get(slot[1], ("PUBLISH", {"p": slot[1]}))
        if isinstance(v, Exception): raise v
        return v
class Caller(unittest.TestCase):
    def test_positive_mixed_dispositions_and_exact_coverage_pair(self):
        r = Rig(fenced={"t3"}, verdicts={"t2": ("ABSTAIN", "no edge")}); self.assertEqual(r.p.declare_schedule(), 4); self.assertEqual(r.p.declare_schedule(), 4)
        self.assertEqual([r.p.trigger("k", t) for t in ("t1", "t2", "t3")], ["PUBLISHED", "MODEL_ABSTAINED", "LIFECYCLE_FENCED"]); self.assertEqual(r.l.coverage("k"), (1, 4)); self.assertEqual(r.l.missing("k"), ["t4"]); self.assertEqual(r.sink.commits, ["E-k-t1"])
    def test_retry_of_a_terminal_calls_neither_model_nor_sink_and_never_double_counts(self):
        r = Rig(); r.p.declare_schedule(); r.p.trigger("k", "t1"); n = (len(r.calls), len(r.sink.commits)); self.assertEqual(r.p.trigger("k", "t1"), "PUBLISHED"); self.assertEqual((len(r.calls), len(r.sink.commits)), n); self.assertEqual(r.l.coverage("k"), (1, 4))
        r2 = Rig(verdicts={"t2": ("ABSTAIN", "x")}); r2.p.declare_schedule(); r2.p.trigger("k", "t2"); r2.p.trigger("k", "t2"); self.assertEqual(r2.calls, ["t2"])        # a terminal abstention is never re-modelled
    def test_failure_before_landing_records_nothing_stays_in_the_denominator_and_a_retry_succeeds_and_others_are_unaffected(self):
        r = Rig(verdicts={"t1": RuntimeError("boom")}); r.sink.fail_before = {"E-k-t2"}; r.p.declare_schedule()
        with self.assertRaises(RuntimeError): r.p.trigger("k", "t1")
        with self.assertRaises(RuntimeError): r.p.trigger("k", "t2")
        self.assertEqual(r.l.coverage("k"), (0, 4)); self.assertEqual(r.p.trigger("k", "t3"), "PUBLISHED")                                   # unrelated baseline still publishes
        r.v.pop("t1"); r.sink.fail_before = set(); self.assertEqual(r.p.trigger("k", "t1"), "PUBLISHED"); self.assertEqual(r.p.trigger("k", "t2"), "PUBLISHED"); self.assertEqual(r.l.coverage("k"), (3, 4))
    def test_fence_beats_a_provisional_abstention_and_a_fence_arriving_after_compute_prevents_the_commit(self):
        r = Rig(verdicts={"t1": ("ABSTAIN", "x")}); r.p.declare_schedule(); seq = iter([False, True]); r.p._fence = lambda k, t: next(seq) if t == "t1" else False
        self.assertEqual(r.p.trigger("k", "t1"), "LIFECYCLE_FENCED"); self.assertEqual(r.l.fenced("k"), ["t1"])
        r2 = Rig(); r2.p.declare_schedule(); s2 = iter([False, True]); r2.p._fence = lambda k, t: next(s2); self.assertEqual(r2.p.trigger("k", "t1"), "LIFECYCLE_FENCED"); self.assertEqual(r2.sink.commits, [])
    def test_held_slots_refuse_and_a_bare_callable_is_not_a_sink(self):
        self.assertEqual(code(ShadowPublisher(ShadowLedger()).declare_schedule), "SHADOW_SCHEDULE_HELD")
        for kw, c in (({"fence": None}, "SHADOW_FENCE_HELD"), ({"event_id": None}, "SHADOW_EVENT_ID_HELD"), ({"model": None}, "SHADOW_MODEL_HELD"), ({"sink": None}, "SHADOW_SINK_HELD")):
            base = dict(schedule=SCHED, fence=lambda k, t: False, event_id=lambda k, t: "e", model=lambda s: ("PUBLISH", 1), sink=Sink()); base.update(kw); p = ShadowPublisher(ShadowLedger(), **base); p.declare_schedule(); self.assertEqual(code(p.trigger, "k", "t1"), c)
        self.assertEqual(code(ShadowPublisher, ShadowLedger(), sink=lambda e, p: None), "SHADOW_SINK_NOT_IDEMPOTENT_INTERFACE"); self.assertEqual(code(ShadowPublisher, ShadowLedger(), sink=object()), "SHADOW_SINK_NOT_IDEMPOTENT_INTERFACE")
        class CommitOnly:
            def commit(self, e, p): pass
        self.assertEqual(code(ShadowPublisher, ShadowLedger(), sink=CommitOnly()), "SHADOW_SINK_NOT_IDEMPOTENT_INTERFACE")
        self.assertEqual(code(ShadowPublisher(ShadowLedger(), schedule=[("k",)]).declare_schedule), "SHADOW_SCHEDULE_MALFORMED"); self.assertEqual(code(ShadowPublisher, ShadowLedger(), fence=5), "SHADOW_PUBLISHER_SLOT_INVALID"); self.assertEqual(code(ShadowPublisher, "x"), "SHADOW_PUBLISHER_LEDGER_INVALID")
    def test_unexpected_trigger_non_boolean_fence_and_malformed_verdict_refuse(self):
        r = Rig(); r.p.declare_schedule(); self.assertEqual(code(r.p.trigger, "k", "nope"), "SHADOW_TRIGGER_NOT_EXPECTED_HELD_UNBOUND")
        r.p._fence = lambda k, t: 1; self.assertEqual(code(r.p.trigger, "k", "t1"), "SHADOW_FENCE_PROBE_NOT_BOOLEAN"); r.p._fence = lambda k, t: False; r.v["t1"] = "PUBLISH"; self.assertEqual(code(r.p.trigger, "k", "t1"), "SHADOW_MODEL_VERDICT_MALFORMED"); r.v["t1"] = ("MAYBE", 1); self.assertEqual(code(r.p.trigger, "k", "t1"), "SHADOW_MODEL_VERDICT_MALFORMED"); self.assertEqual(r.l.coverage("k"), (0, 4)); self.assertEqual(r.sink.commits, [])
    # ---- R51 C: known ledger refusals happen BEFORE any publication side effect ----------------------------------------------------------------------------------------------------------
    def test_sealed_key_and_a_shared_event_id_refuse_before_the_sink_is_touched(self):
        r = Rig(); r.p.declare_schedule(); r.l.seal("k"); self.assertEqual(code(r.p.trigger, "k", "t1"), "SHADOW_RETROACTIVE_BACKFILL_PROHIBITED"); self.assertEqual(r.sink.commits, []); self.assertEqual(r.sink.store, {})
        r2 = Rig(eid=lambda k, t: "E"); r2.p.declare_schedule(); self.assertEqual(r2.p.trigger("k", "t1"), "PUBLISHED"); n = len(r2.sink.commits)
        self.assertEqual(code(r2.p.trigger, "k", "t2"), "SHADOW_EVENT_ID_CONFLICT"); self.assertEqual(len(r2.sink.commits), n); self.assertEqual(r2.l.coverage("k"), (1, 4))          # the second slot's event id is already bound globally: no second commit
        r3 = Rig(); r3.p.declare_schedule(); self.assertEqual(r3.p.trigger("k", "t1"), "PUBLISHED"); self.assertEqual(r3.p.trigger("k", "t3"), "PUBLISHED")                                   # unrelated positives
    def test_a_provisional_abstention_blocks_a_later_publication_before_the_sink(self):
        r = Rig(); r.p.declare_schedule(); r.l.provisional_abstain("k", "t1", "E-k-t1"); self.assertEqual(code(r.p.trigger, "k", "t1"), "SHADOW_PUBLISHED_AFTER_PROVISIONAL_ABSTENTION_NOT_DEFINED"); self.assertEqual(r.sink.commits, [])
    # ---- R51 D: unknown commit outcome -----------------------------------------------------------------------------------------------------------------------------------------------------
    def test_write_landed_then_raise_is_recovered_from_readback_with_one_commit_one_count(self):
        r = Rig(); r.sink.fail_after = {"E-k-t1"}; r.p.declare_schedule(); self.assertEqual(r.p.trigger("k", "t1"), "PUBLISHED"); self.assertEqual(r.l.coverage("k"), (1, 4)); self.assertEqual(r.sink.commits, ["E-k-t1"]); self.assertEqual(r.calls, ["t1"])
        self.assertEqual(r.p.trigger("k", "t1"), "PUBLISHED"); self.assertEqual(r.sink.commits, ["E-k-t1"])
    def _flaky(self, r, fail_calls):
        orig = r.sink.readback; n = [0]
        def rb(eid):
            n[0] += 1
            if n[0] in fail_calls: raise RuntimeError("readback down")
            return orig(eid)
        r.sink.readback = rb
    def test_unreadable_before_commit_fails_closed_with_no_model_or_sink_call(self):
        r = Rig(); r.p.declare_schedule(); r.sink.unreadable = True
        self.assertEqual(code(r.p.trigger, "k", "t1"), "SHADOW_PUBLICATION_OUTCOME_UNKNOWN"); self.assertEqual((r.calls, r.sink.commits, r.l.coverage("k")), ([], [], (0, 4)))
        r.sink.unreadable = False; self.assertEqual(r.p.trigger("k", "t1"), "PUBLISHED"); self.assertEqual((r.calls, r.sink.commits), (["t1"], ["E-k-t1"]))
    def test_readback_unavailable_after_an_unknown_commit_keeps_the_slot_unknown_until_it_resolves(self):
        r = Rig(); r.sink.fail_after = {"E-k-t1"}; r.p.declare_schedule(); self._flaky(r, {2, 3})                       # call 1 = pre-commit (ok), 2-3 = post-failure / retry (down)
        self.assertEqual(code(r.p.trigger, "k", "t1"), "SHADOW_PUBLICATION_OUTCOME_UNKNOWN"); self.assertEqual(code(r.p.trigger, "k", "t1"), "SHADOW_PUBLICATION_OUTCOME_UNKNOWN")
        self.assertEqual((r.calls, r.sink.commits, r.l.coverage("k")), (["t1"], ["E-k-t1"], (0, 4)))                    # no second model call, no second commit, nothing counted
        self.assertEqual(r.p.trigger("k", "t1"), "PUBLISHED"); self.assertEqual((r.calls, r.sink.commits, r.l.coverage("k")), (["t1"], ["E-k-t1"], (1, 4)))
        self.assertEqual(r.p.trigger("k", "t2"), "PUBLISHED"); self.assertEqual((r.calls, r.sink.commits), (["t1", "t2"], ["E-k-t1", "E-k-t2"]))   # unrelated baseline: model + sink once
    def test_a_restart_with_a_committed_event_records_it_without_calling_model_or_sink(self):
        r = Rig(); r.p.declare_schedule(); r.sink.store["E-k-t1"] = {"p": "t1"}; self.assertEqual(r.p.trigger("k", "t1"), "PUBLISHED"); self.assertEqual((r.calls, r.sink.commits), ([], []))
    def test_a_different_payload_found_after_an_unknown_commit_is_refused_and_not_recorded(self):
        r = Rig(); r.sink.fail_after = {"E-k-t1"}; r.p.declare_schedule(); self._flaky(r, {2})
        self.assertEqual(code(r.p.trigger, "k", "t1"), "SHADOW_PUBLICATION_OUTCOME_UNKNOWN"); r.sink.store["E-k-t1"] = {"p": "DIFFERENT"}
        self.assertEqual(code(r.p.trigger, "k", "t1"), "SHADOW_SINK_DIFFERENT_PAYLOAD"); self.assertEqual(r.l.coverage("k"), (0, 4))
        r3 = Rig(); r3.sink.fail_after = {"E-k-t1"}; r3.p.declare_schedule(); orig = r3.sink.readback; n = [0]
        def rb(eid):
            n[0] += 1; return {"p": "DIFFERENT"} if n[0] == 2 else orig(eid)
        r3.sink.readback = rb; self.assertEqual(code(r3.p.trigger, "k", "t1"), "SHADOW_SINK_DIFFERENT_PAYLOAD"); self.assertEqual(r3.l.coverage("k"), (0, 4))
    def test_the_real_atomic_record_store_is_an_idempotent_sink(self):
        a = AtomicRecordStore(InMemoryObjectStore(), required_fields=frozenset({"event_id", "payload"})); s = AtomicRecordSink(a); self.assertIsNone(s.readback("e1")); s.commit("e1", {"x": 1}); s.commit("e1", {"x": 1}); self.assertEqual(s.readback("e1"), {"x": 1})
        with self.assertRaises(Exception): s.commit("e1", {"x": 2})                                                                                                                           # different payload under one idempotency key is an integrity failure
        r = Rig(); r.p._sink = AtomicRecordSink(a); r.p.declare_schedule(); self.assertEqual(r.p.trigger("k", "t1"), "PUBLISHED"); self.assertEqual(r.p._sink.readback("E-k-t1"), {"p": "t1"})
