import unittest
from stage_a.errors import Refusal
from stage_a.ml.shadow_ledger import ShadowLedger
from stage_a.ml.shadow_publication import ShadowPublisher
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
SCHED = [("k", "t1"), ("k", "t2"), ("k", "t3"), ("k", "t4")]       # TEST schedule only; no source defines one
class Rig:
    def __init__(self, fenced=(), verdicts=None, sink_fail=()):
        self.l = ShadowLedger(); self.sunk = []; self.calls = []; self.fenced = set(fenced); self.v = verdicts or {}; self.sink_fail = set(sink_fail); self.fence_calls = []
        self.p = ShadowPublisher(self.l, schedule=SCHED, fence=self.fence, event_id=lambda k, t: "E-%s-%s" % (k, t), model=self.model, sink=self.sink)
    def fence(self, k, t): self.fence_calls.append(t); return t in self.fenced
    def model(self, slot):
        self.calls.append(slot[1]); v = self.v.get(slot[1], ("PUBLISH", "p"))
        if isinstance(v, Exception): raise v
        return v
    def sink(self, eid, payload):
        if any(eid.endswith(t) for t in self.sink_fail): raise RuntimeError("sink down")
        self.sunk.append(eid)
class Caller(unittest.TestCase):
    def test_positive_mixed_dispositions_and_exact_coverage_pair(self):
        r = Rig(fenced={"t3"}, verdicts={"t2": ("ABSTAIN", "no edge")}); self.assertEqual(r.p.declare_schedule(), 4); self.assertEqual(r.p.declare_schedule(), 4)
        self.assertEqual([r.p.trigger("k", t) for t in ("t1", "t2", "t3")], ["PUBLISHED", "MODEL_ABSTAINED", "LIFECYCLE_FENCED"]); self.assertEqual(r.l.coverage("k"), (1, 4)); self.assertEqual(r.l.missing("k"), ["t4"]); self.assertEqual(r.sunk, ["E-k-t1"])
    def test_retry_of_a_terminal_calls_neither_model_nor_sink_and_never_double_counts(self):
        r = Rig(); r.p.declare_schedule(); r.p.trigger("k", "t1"); n = (len(r.calls), len(r.sunk)); self.assertEqual(r.p.trigger("k", "t1"), "PUBLISHED"); self.assertEqual((len(r.calls), len(r.sunk)), n); self.assertEqual(r.l.coverage("k"), (1, 4))
    def test_model_or_sink_failure_records_nothing_stays_in_the_denominator_and_a_retry_may_succeed_and_others_are_unaffected(self):
        r = Rig(verdicts={"t1": RuntimeError("boom")}, sink_fail={"t2"}); r.p.declare_schedule()
        with self.assertRaises(RuntimeError): r.p.trigger("k", "t1")
        with self.assertRaises(RuntimeError): r.p.trigger("k", "t2")
        self.assertEqual(r.l.coverage("k"), (0, 4)); self.assertEqual(r.l.missing("k"), ["t1", "t2", "t3", "t4"]); self.assertEqual(r.p.trigger("k", "t3"), "PUBLISHED")          # unrelated baseline still publishes
        r.v.pop("t1"); self.assertEqual(r.p.trigger("k", "t1"), "PUBLISHED"); self.assertEqual(r.l.coverage("k"), (2, 4))
    def test_fence_beats_a_provisional_abstention_and_a_fence_arriving_after_compute_prevents_the_commit(self):
        r = Rig(verdicts={"t1": ("ABSTAIN", "x")}); r.p.declare_schedule(); seq = iter([False, True]); r.p._fence = lambda k, t: next(seq) if t == "t1" else False
        self.assertEqual(r.p.trigger("k", "t1"), "LIFECYCLE_FENCED"); self.assertEqual(r.l.fenced("k"), ["t1"])
        r2 = Rig(); r2.p.declare_schedule(); s2 = iter([False, True]); r2.p._fence = lambda k, t: next(s2); self.assertEqual(r2.p.trigger("k", "t1"), "LIFECYCLE_FENCED"); self.assertEqual(r2.sunk, [])
    def test_held_slots_refuse_and_write_nothing(self):
        l = ShadowLedger()
        self.assertEqual(code(ShadowPublisher(l).declare_schedule), "SHADOW_SCHEDULE_HELD")
        for kw, c in (({"fence": None}, "SHADOW_FENCE_HELD"), ({"event_id": None}, "SHADOW_EVENT_ID_HELD"), ({"model": None}, "SHADOW_MODEL_HELD"), ({"sink": None}, "SHADOW_SINK_HELD")):
            base = dict(schedule=SCHED, fence=lambda k, t: False, event_id=lambda k, t: "e", model=lambda s: ("PUBLISH", 1), sink=lambda e, p: None); base.update(kw); p = ShadowPublisher(ShadowLedger(), **base); p.declare_schedule(); self.assertEqual(code(p.trigger, "k", "t1"), c)
        self.assertEqual(l.coverage("k"), None)
        self.assertEqual(code(ShadowPublisher(ShadowLedger(), schedule=[("k",)]).declare_schedule), "SHADOW_SCHEDULE_MALFORMED"); self.assertEqual(code(ShadowPublisher, ShadowLedger(), fence=5), "SHADOW_PUBLISHER_SLOT_INVALID"); self.assertEqual(code(ShadowPublisher, "x"), "SHADOW_PUBLISHER_LEDGER_INVALID")
    def test_unexpected_trigger_non_boolean_fence_and_malformed_verdict_refuse(self):
        r = Rig(); r.p.declare_schedule(); self.assertEqual(code(r.p.trigger, "k", "nope"), "SHADOW_TRIGGER_NOT_EXPECTED_HELD_UNBOUND")
        r.p._fence = lambda k, t: 1; self.assertEqual(code(r.p.trigger, "k", "t1"), "SHADOW_FENCE_PROBE_NOT_BOOLEAN"); r.p._fence = lambda k, t: False; r.v["t1"] = "PUBLISH"; self.assertEqual(code(r.p.trigger, "k", "t1"), "SHADOW_MODEL_VERDICT_MALFORMED"); r.v["t1"] = ("MAYBE", 1); self.assertEqual(code(r.p.trigger, "k", "t1"), "SHADOW_MODEL_VERDICT_MALFORMED"); self.assertEqual(r.l.coverage("k"), (0, 4)); self.assertEqual(r.sunk, [])
