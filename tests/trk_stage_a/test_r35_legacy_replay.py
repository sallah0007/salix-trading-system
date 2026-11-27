import json, unittest
from stage_a.errors import Refusal
from stage_a.replay import replay
from stage_a.coordination import transition_record as T
from stage_a.tracker import reverification as RV
from stage_a.identifiers import FeatureKey
from .test_foundations import accepted_body, pub_body, mk, NS
from .test_r25_scheduler import core
from .fixtures import Rig
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
def legacy_body(): b = accepted_body(); del b["materialization_hash"]; return b
class LegacyAcceptedHistory(unittest.TestCase):
    def test_new_writes_still_require_the_binding_but_committed_legacy_bodies_replay_with_a_maintenance_hold(self):
        self.assertEqual(code(T.validate_body, T.CANONICAL_ACCEPTED, legacy_body()), "TRANSITION_BODY_INCOMPLETE")                # a NEW write may not omit it
        s, j = mk(); r = j.append(j.head(), T.CANONICAL_ACCEPTED, legacy_body()); st = replay(NS, j.read_from(1))["1"]
        self.assertTrue(st.legacy_binding_absent); self.assertNotIn("materialization_hash", st.accepted_body)                            # not fabricated, record untouched
        j.append(j.head(), T.PUBLISHABLE, pub_body((r.seq, r.record_hash))); self.assertEqual(replay(NS, j.read_from(1))["1"].status, T.PUBLISHABLE)   # old history continues to rebuild
        s2, j2 = mk(); j2.append(j2.head(), T.CANONICAL_ACCEPTED, accepted_body()); self.assertFalse(replay(NS, j2.read_from(1))["1"].legacy_binding_absent)       # new-shape positive
    def test_legacy_shape_exceptions_are_narrow(self):
        for mut in ({"extra": "x"}, {"verification_hash": ""}, {"manifest_hash": None}):
            s, j = mk(); b = legacy_body(); b.update(mut); j.append(j.head(), T.CANONICAL_ACCEPTED, b); self.assertIsNotNone(code(replay, NS, j.read_from(1)), mut)
        s, j = mk(); b = accepted_body(); b["materialization_hash"] = ""; j.append(j.head(), T.CANONICAL_ACCEPTED, b); self.assertEqual(code(replay, NS, j.read_from(1)), "TRANSITION_BODY_INCOMPLETE")      # present-but-empty is not legacy
    def test_verifier_holds_a_legacy_acceptance_and_records_nothing(self):
        rig = Rig(); from stage_a.identifiers import Scope; fk = FeatureKey(Scope("XAUUSD", "H4"), "mom3", "1")
        j = rig.journals.journal(fk.namespace()); j.append(j.head(), T.CANONICAL_ACCEPTED, legacy_body())
        c = core(); self.assertEqual(code(RV.reverify_accepted, c, journal=j, store=rig.store, feature_key=fk, now=10, max_age=50), "ACCEPTED_RECORD_LEGACY_MAINTENANCE_HOLD")
        self.assertEqual(c.recording_health(fk.key(), "1", 11).state, "UNKNOWN")                                                      # no verification was fabricated
if __name__ == "__main__": unittest.main()
