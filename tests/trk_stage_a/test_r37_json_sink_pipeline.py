"""R37: the E-08 JSON sink is injected into the actual TrackerPipeline; telemetry never changes, masks or aborts an outcome and never carries authority."""
import io, json, unittest
from stage_a.observability import JsonEventSink
from stage_a.tracker.quant_intake_adapter import admit
from stage_a.composer import order_authority as OA
from stage_a.composer.build_gate import accept_build_start as abs_
from .fixtures import Rig, package, SIM_CONF
from .test_r29_intake_order import issue, br
def run_with(sink):
    rig = Rig(); rig.pipe._events = sink; oid = OA.order_id_for("cand-1"); p = package(order_id=oid); sk = admit(p, accepted_fit_generations=rig.fits, conformance=SIM_CONF).subject_key; issue(rig.claims, subject_key=sk); abs_(rig.claims, oid, br())
    return rig, rig.pipe.run(p)
class Sink(unittest.TestCase):
    def test_actual_pipeline_emits_stable_json_lines_that_are_never_authoritative(self):
        buf = io.StringIO(); rig, out = run_with(JsonEventSink(stream=buf)); self.assertEqual(out.accepted.kind, "CANONICAL_ACCEPTED"); lines = [json.loads(l) for l in buf.getvalue().splitlines()]
        names = [l["event_name"] for l in lines]; self.assertIn("INTAKE_STARTED", names); self.assertIn("CANONICAL_ACCEPTED", names); self.assertTrue(all(l["authoritative"] is False for l in lines)); self.assertEqual(rig.pipe.sink_failures, 0)
    def test_a_failing_sink_after_the_commit_neither_aborts_nor_masks_the_accepted_outcome(self):
        class Boom:
            def emit(self, kind, **f): raise OSError("disk full")
        rig, out = run_with(Boom()); self.assertEqual(out.accepted.kind, "CANONICAL_ACCEPTED"); self.assertGreaterEqual(rig.pipe.sink_failures, 2)                 # the commit stands and the caller sees the real outcome
        self.assertEqual(len(rig.journals.journal("XAUUSD/H4/mom3").read_from(1)), 1)
    def test_a_non_json_field_is_a_counted_telemetry_failure_not_a_pipeline_failure(self):
        s = JsonEventSink(stream=io.StringIO()); rig, out = run_with(s); before = rig.pipe.sink_failures; rig.pipe._emit("X", bad=object()); self.assertEqual(rig.pipe.sink_failures, before + 1)
if __name__ == "__main__": unittest.main()
