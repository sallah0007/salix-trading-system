"""R50: the ONE acceptance caller (Composition) publishes status through the OWNING emitter: accepted -> committed lifecycle record -> A1 event + audit -> SIM_STATUS_FACT -> Core/Gateway; unknown required ancestry denies, the unrelated baseline delivers."""
import unittest
from stage_a.errors import Refusal
from stage_a.gateway import contracts as G
from stage_a.tracker.status_emitter import StatusEmitter
from .test_r38_composition import comp, W, AP, F, I, R, T, _entry
from .test_r37_sim_publication_path import supplied
from .test_r50_status_emitter import MAP, boundary, AUD
EM = lambda **o: dict(dict(boundary_evidence=boundary(), context_known=True, audit_fields=AUD), **o)
class Integrated(unittest.TestCase):
    def test_emitter_path_publishes_denies_unknown_ancestry_then_delivers_the_baseline_and_carries_audit(self):
        rig, pkg, fk, c, co, path = comp(); key = fk.key(); em = StatusEmitter(path, kind_to_token=MAP)
        r = co.accept_and_publish(pkg, supplied(), None, sequence=1, now=10, max_age=50, l2_applicability=AP, status_emitter=em, emit=EM())
        self.assertEqual(r.status, "PUBLISHED_SIMULATION"); self.assertEqual(r.steps[-1][:2], ("committed_status_and_rows", "OK")); self.assertIn(("status_emit", "EMITTED", "audit_complete=True"), r.steps)
        self.assertEqual(r.status_event["NEW_STATE"], "CANONICAL_ACCEPTED"); self.assertTrue(r.audit["complete"]); self.assertFalse(r.audit["authoritative"])
        b1 = G.HealthBinding(F, fk.feature_version, I, I); c.associate_subject(key, b1, "assoc"); e = _entry(fid=F, ver=fk.feature_version); kw = dict(binding=b1, now=12, ref=R("hl"), resolved_at=11, tables=T)
        with self.assertRaises(Refusal) as x: co.deliver("fw1", W("W1"), e, I, I, 3, 20, r, **kw)
        self.assertEqual(x.exception.code, "NON_DELIVERY")                                                       # required ancestry unknown: denied
        c.declare_ancestry_complete(key, "src"); self.assertIsInstance(co.deliver("fw2", W("W2"), e, I, I, 3, 20, r, **kw), G.Binding)
    def test_unbound_emit_inputs_hold_before_anything_is_published(self):
        cases = (("HELD_STATUS_EMIT_INPUT", None, dict(emit=None)), ("HELD_STATUS_EMIT_STATUS_EVENT_FIELD_MISSING", MAP, dict(emit=EM(boundary_evidence=boundary(PRIOR_STATE=None)))),
                 ("HELD_STATUS_EMIT_STATUS_WITHOUT_REQUIRED_CONTEXT", MAP, dict(emit=EM(context_known=False))), ("HELD_STATUS_EMIT_STATUS_MAPPING_HELD", None, dict(emit=EM())), ("HELD_STATUS_EMIT_INPUT", MAP, dict(emit=EM(), token="SIM_CUR")))
        for why, mp, kw in cases:
            rig, pkg, fk, c, co, path = comp(); em = StatusEmitter(path, kind_to_token=mp); n = path._sj.head(); tok = kw.pop("token", None)           # fresh rig per case: the pipeline accepts a package once
            r = co.accept_and_publish(pkg, supplied(), tok, sequence=1, now=10, max_age=50, l2_applicability=AP, status_emitter=em, **kw); self.assertEqual(r.status, why); self.assertEqual(path._sj.head(), n); self.assertIsNone(co.gateway); self.assertEqual(len(path.records()), 0)
    def test_an_emitter_over_another_path_is_refused(self):
        rig, pkg, fk, c, co, path = comp(); rig2, pkg2, fk2, c2, co2, path2 = comp(); em2 = StatusEmitter(path2, kind_to_token=MAP)
        r = co.accept_and_publish(pkg, supplied(), None, sequence=1, now=10, max_age=50, l2_applicability=AP, status_emitter=em2, emit=EM()); self.assertEqual(r.status, "HELD_STATUS_EMIT_INPUT"); self.assertEqual(path._sj.head(), path._sj.head()); self.assertEqual(len(path.records()), 0)
    def test_existing_token_path_is_unchanged(self):
        rig, pkg, fk, c, co, path = comp(); r = co.accept_and_publish(pkg, supplied(), "SIM_CUR", sequence=1, now=10, max_age=50, l2_applicability=AP); self.assertEqual(r.status, "PUBLISHED_SIMULATION"); self.assertIsNone(r.audit)
