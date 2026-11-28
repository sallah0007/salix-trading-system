"""R37 F3: GenerationRegistry commits a DETACHED, immutable result payload; published()/annotated() cannot be used to alter history."""
import unittest
from stage_a.ml import generation_lifecycle as GL
from .test_r29_generation_lifecycle import reg, ev, code
def committed():
    r = reg("M1"); s = r.snapshot("q1", ev(), "M1", 100); payload = {"forecast": {"value": 1.0}, "lineage": ["ORIGINAL"]}
    assert r.compare_and_publish(s, payload).status == GL.PUBLISHED; return r, s, payload
class Frozen(unittest.TestCase):
    def test_mutating_the_original_nested_payload_after_publish_does_not_change_the_stored_value(self):
        r, s, p = committed(); p["forecast"]["value"] = 999; p["lineage"].append("X"); p["new"] = 1
        got = r.published(ev())[1]; self.assertEqual(got["forecast"]["value"], 1.0); self.assertEqual(tuple(got["lineage"]), ("ORIGINAL",)); self.assertNotIn("new", got)
    def test_the_published_and_annotated_views_are_read_only_and_revocation_annotation_stays_separate(self):
        r, s, p = committed(); got = r.published(ev())[1]
        for f in (lambda: got.__setitem__("x", 1), lambda: got["forecast"].__setitem__("value", -1), lambda: got["lineage"].append("ALTERED"), lambda: got["lineage"].__setitem__(0, "ALTERED"), lambda: got.pop("forecast")):
            with self.assertRaises((TypeError, AttributeError)): f()
        self.assertEqual(got["forecast"]["value"], 1.0); self.assertEqual(got["lineage"][0], "ORIGINAL")
        r.append_lifecycle("M1", "REVOKED", 50, "bad", "A"); a = r.annotated(ev()); self.assertTrue(a["later_revoked"])
        with self.assertRaises((TypeError, AttributeError)): a["record"][1]["forecast"]["value"] = -999
        a["record"][1]; self.assertEqual(r.annotated(ev())["record"][1]["forecast"]["value"], 1.0); self.assertEqual(r.published(ev())[0], s)       # historical value and snapshot unchanged; later_revoked only in the annotation
        self.assertEqual(r.read_class("M1")["class"], "FORENSIC_ONLY")
    def test_unsupported_payload_types_are_held_before_any_commit_and_scalars_and_idempotent_republish_still_work(self):
        r = reg("M1"); s = r.snapshot("q1", ev(), "M1", 100)
        class Foreign: pass
        for bad in (Foreign(), {1: 2}, [Foreign()], {"a": object()}):
            self.assertEqual(code(r.compare_and_publish, s, bad), "ML_RESULT_PAYLOAD_TYPE_HELD"); self.assertIsNone(r.published(ev()))                   # held, not committed, not failed-event
        self.assertEqual(r.compare_and_publish(s, "R").status, GL.PUBLISHED); self.assertEqual(r.compare_and_publish(s, {"a": [1]}).reason, "ALREADY_PUBLISHED_IDEMPOTENT"); self.assertEqual(r.published(ev())[1], "R")
if __name__ == "__main__": unittest.main()
