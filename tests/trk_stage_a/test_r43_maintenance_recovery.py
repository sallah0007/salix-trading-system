"""R43: stored-SOURCE-VALUE L2 ALL-segment maintenance, safe quarantine/restoration and restart recovery on the SAME objects as the separated acceptance -> committed SIM status -> Core -> Gateway -> FW + ML consumer path. One owning truth: the Core's own health calculation (L2 outcome recorded by `run_stored_value_pass`, quarantine reasons in the Core journal) is what the Gateway reads; no second Health/lifecycle authority is introduced. The restoration here uses the Core's EXISTING creator != certifier rule (SIMULATION mode); no source-owned lifecycle graph, transition mapping or PUBLISHABLE=CURRENT guess is used."""
import unittest
from stage_a.errors import Refusal
from stage_a.fw import receiver as FWR
from stage_a.gateway import contracts as G
from stage_a.gateway.v038 import FinalResolutionIdentity as FI
from stage_a.core.tracker_core import TrackerCore
from stage_a.tracker import stored_values as SV
from stage_a.ml import receiver as MLR
from .test_r41_separated_caller import Caller as _Caller, FB, supplied, AP, I, T, R, _entry, ver
from .test_r37_stored_values import SER, H
NONE_ = ("ENUM", "REASON", "NONE"); EXCL = ("ENUM", "REASON", "REQUIRED_DEPENDENCY_NOT_DELIVERED")
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
class Maintenance(_Caller):
    test_separated_child_acceptance_then_committed_status_core_gateway_with_unknown_ancestry_denied_and_the_unrelated_baseline_delivered = None
    test_a_failed_child_job_never_yields_an_acceptance_or_publication = None
    test_a_non_admissible_package_is_not_staged_claimed_or_run = None
    def _two(self):
        a = self._feature("mom3", 1); b = self._feature("mom4", 2)          # BOTH orders are issued before either child acceptance (a child acceptor's epoch fences the claims writer)
        return self._accept(a, supplied().feature_id), self._accept(b, FB)
    def _accept(self, prepared, feat_id):
        p, fk, co = prepared; self.src = getattr(self, "src", {}); self.src[fk.key()] = SER
        si = dict(bindings={"close": {"ref": "SRC/close/" + fk.key(), "hash": H(SER)}}, fetch=lambda ref, k=fk.key(): self.src[k], series_hash=H)
        r = co.accept_and_publish(p, supplied(feature_id=feat_id), "SIM_CUR", sequence=1, now=10, max_age=50, stored_inputs=si, l2_applicability=AP, accept_fn=self.acc)
        self.assertEqual((r.status, r.stored_values["l2"]), ("PUBLISHED_SIMULATION", "PASS")); self.c.declare_ancestry_complete(fk.key(), "src"); b = G.HealthBinding(feat_id, fk.feature_version, I, I); self.c.associate_subject(fk.key(), b, "assoc")
        return fk, co, r, b, StoredBinding(fk, self.rig, self.src)
    def _res(self, fk, co, b, feat_id, consumer, tag, now=12):
        e = _entry(fid=feat_id, ver=fk.feature_version); health = self.c.gateway_health(fk.key(), fk.feature_version, now, R("hl-" + tag), now - 1, binding=b, require_ancestry=True)
        return e, co.gateway.resolve_window(consumer.lower() + "-" + tag, FI(consumer, "M-A", "XAUUSD", tag), e, I, I, 3, max(20, now), health)
    def _both(self, fk, co, b, feat_id, tag, now=12):
        out = {}
        for cons in ("FW", "ML"):
            e, o = self._res(fk, co, b, feat_id, cons, tag, now); out[cons] = (e, o)
        return out
    def _delivered(self, co, got):
        e, o = got["FW"]; self.assertIsInstance(o, G.Binding); self.assertIs(FWR.receive_verified(o, e, I, I, T, co.gateway), o)
        e, o = got["ML"]; self.assertIsInstance(o, G.Binding); self.assertTrue(MLR.build_row("r", R("gen"), [e], [o], co.gateway, "ORIGINAL_AS_OBSERVED", NONE_, lambda x: EXCL, tables=T).included)
    def _denied(self, co, got):
        for cons in ("FW", "ML"): self.assertEqual((type(got[cons][1]).__name__, got[cons][1].reason), ("NonDeliveryResolution", "HEALTH_UNACCEPTABLE"), cons)
    def _pass(self, now, bindings, events):
        return SV.run_stored_value_pass(self.c, {k: v.sb for k, v in bindings.items()}, list(bindings), events, now=now, max_age=50, max_items=8)
    def test_all_segment_l2_failure_denies_both_consumers_for_that_feature_only_and_restoring_the_source_restores_delivery(self):
        (fka, coa, ra, ba, sa), (fkb, cob, rb, bb, sb) = self._two(); bind = {fka.key(): sa, fkb.key(): sb}
        self._delivered(coa, self._both(fka, coa, ba, supplied().feature_id, "A1")); self._delivered(cob, self._both(fkb, cob, bb, FB, "B1"))                    # baseline: both consumers get both features
        self.src[fka.key()] = SER + [9.0] if isinstance(SER, list) else SER + b"x"                                                                                # the SOURCE series changes under A's stored segment
        o = self._pass(30, bind, [(fka.key(), "SCHEDULED"), (fkb.key(), "SCHEDULED")]); res = {x[0]: x[2] for x in o}; self.assertEqual(res[fkb.key()], "VERIFIED"); self.assertNotEqual(res[fka.key()], "VERIFIED")
        self._denied(coa, self._both(fka, coa, ba, supplied().feature_id, "A2", now=40)); self._delivered(cob, self._both(fkb, cob, bb, FB, "B2", now=40))             # required denial AND unrelated baseline delivery, same objects
        self.src[fka.key()] = SER; o = self._pass(60, bind, [(fka.key(), "SCHEDULED")]); self.assertEqual([x[2] for x in o], ["VERIFIED"])                            # restoration = re-verified against the restored source
        self._delivered(coa, self._both(fka, coa, ba, supplied().feature_id, "A3", now=70))
    def test_quarantine_denies_both_consumers_restoration_needs_a_distinct_certifier_and_a_restart_replays_the_same_state(self):
        (fka, coa, ra, ba, sa), (fkb, cob, rb, bb, sb) = self._two()
        self.c.quarantine(fka.key(), "TEST_REASON"); self._denied(coa, self._both(fka, coa, ba, supplied().feature_id, "A1")); self._delivered(cob, self._both(fkb, cob, bb, FB, "B1"))
        j = self.c._j; c2 = TrackerCore(j, simulation=True); self.assertFalse(c2.retry_allowed(fka.key())); self.assertTrue(c2.retry_allowed(fkb.key()))                         # a restarted Core replays the same journal: still quarantined, baseline untouched
        self.assertEqual(code(self.c.clear_reason, fka.key(), "TEST_REASON", "same", "same"), "CREATOR_IS_CERTIFIER"); self.assertEqual(code(self.c.clear_reason, fka.key(), "NOT_OPEN", "cert", "creator"), "REASON_NOT_OPEN")
        self._denied(coa, self._both(fka, coa, ba, supplied().feature_id, "A2"))                                                                                          # failed restorations changed nothing
        self.c.clear_reason(fka.key(), "TEST_REASON", "cert", "creator"); self.c.reactivate(fka.key())
        self._denied(coa, self._both(fka, coa, ba, supplied().feature_id, "A3"))                                                                                          # reactivated but the earlier evidence is superseded: UNKNOWN health is a denial until re-verified
        o = self._pass(30, {fka.key(): sa}, [(fka.key(), "SCHEDULED")]); self.assertEqual([x[2] for x in o], ["VERIFIED"]); self._delivered(coa, self._both(fka, coa, ba, supplied().feature_id, "A4", now=40))
class StoredBinding:
    def __init__(self, fk, rig, src): self.sb = SV.StoredBinding(rig.journals.journal(fk.namespace()), rig.store, fk, lambda ref, k=fk.key(): src[k], H)
if __name__ == "__main__": unittest.main()
