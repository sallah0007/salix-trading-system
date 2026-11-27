"""R19: full-Tracker terminal/transitive identity resolution over the REAL identity_lookup (fixture prefix of tests/test_identity_surface.py). The narrow Type1 lookup stays
CURRENT-ONLY (outcome unchanged, no claim); the Tracker adds identity+state reporting. No terminal result authorizes a claim/resurrection/delivery/substitution."""
import unittest
from unittest import mock
from tests import test_identity_surface as T
from tracker_identity.models import FeatureIdentity, LookupOutcome
from tracker_identity.search import identity_lookup
from stage_a.tracker import terminal_identity as TI
def rec(fid, *, current=False, state="RETIRED", survivor=None, version="1", defn="abc"):
    return FeatureIdentity(feature_id=fid, feature_version=version, definition_hash=defn, graph_hash="def", lifecycle_state=state, is_current=current,
                           scope="current_active" if current else "canonical_survivor_discarded", canonical_survivor=survivor, instrument="EURUSD", timeframe="H1")
def lookup(rows):
    store = T.fixture_store(rows)
    return identity_lookup(store=store, subject=T.subject(), request_id="REQ-T", search_policy=T.complete_policy(), normalizer=T.normalizer()), store
A = lambda survivor, **k: rec("returns.1bar", survivor=survivor, **k)           # matches the subject's exact canonical key; noncurrent
class Resolution(unittest.TestCase):
    def test_rejected_terminal_returns_identity_and_state_not_not_found(self):          # Codex reproduction 1
        rows = [A("b"), rec("b", state="REJECTED_INVALID")]
        lk, store = lookup(rows)
        self.assertEqual(lk.outcome, LookupOutcome.INCOMPLETE_LOOKUP); self.assertIsNone(lk.absent_claim_token)      # narrow Type1 result UNCHANGED, no claim
        t = TI.resolve_terminal_identity(rows[0], rows)
        self.assertEqual((t.status, t.terminal_id, t.terminal_state, t.terminal_is_current), (TI.TERMINAL_NONCURRENT, "b", "REJECTED_INVALID", False))
    def test_transitive_chain_reaches_the_current_survivor(self):                      # Codex reproduction 2: a -> b(RETIRED) -> c(CURRENT)
        rows = [A("b"), rec("b", survivor="c"), rec("c", current=True, state="CURRENT")]
        lk, _ = lookup(rows); self.assertIsNone(lk.absent_claim_token)                  # one-hop current-only lookup still fails closed (accepted Type1 semantics preserved)
        t = TI.resolve_terminal_identity(rows[0], rows)
        self.assertEqual((t.status, t.chain, t.terminal_id, t.terminal_is_current), (TI.CURRENT_SURVIVOR, ("returns.1bar", "b", "c"), "c", True))
    def test_cycle_orphan_and_ambiguity_are_refused_not_resolved(self):
        self.assertEqual(TI.resolve_terminal_identity(*(lambda r: (r[0], r))([rec("a", survivor="b"), rec("b", survivor="a")])).status, TI.CYCLE)
        r = [rec("a", survivor="a")]; self.assertEqual(TI.resolve_terminal_identity(r[0], r).status, TI.CYCLE)
        r = [rec("a", survivor="missing")]; t = TI.resolve_terminal_identity(r[0], r); self.assertEqual((t.status, t.terminal_id), (TI.ORPHAN, ""))
        r = [rec("a", survivor="b"), rec("b", current=True, state="CURRENT", version="1"), rec("b", current=True, state="CURRENT", version="2", defn="zzz")]
        self.assertEqual(TI.resolve_terminal_identity(r[0], r).status, TI.AMBIGUOUS)
    def test_long_chain_terminates_and_resolves(self):
        r = [rec("n%d" % i, survivor="n%d" % (i + 1)) for i in range(50)] + [rec("n50", current=True, state="CURRENT")]
        self.assertEqual(TI.resolve_terminal_identity(r[0], r).terminal_id, "n50")
    def test_current_record_is_its_own_terminal_and_noncurrent_without_survivor_returns_its_own_state(self):
        c = rec("c", current=True, state="CURRENT"); self.assertEqual(TI.resolve_terminal_identity(c, [c]).status, TI.CURRENT_SURVIVOR)
        d = rec("d", state="DISCARDED"); t = TI.resolve_terminal_identity(d, [d]); self.assertEqual((t.status, t.terminal_state), (TI.TERMINAL_NONCURRENT, "DISCARDED"))
    def test_a_noncurrent_terminal_is_never_made_current_and_authorizes_nothing(self):
        rows = [A("b"), rec("b", state="REJECTED_INVALID")]; t = TI.resolve_terminal_identity(rows[0], rows)
        self.assertFalse(t.terminal_is_current)
        for a in ("authorizes_claim", "authorizes_resurrection", "authorizes_delivery", "authorizes_near_match_substitution"): self.assertIs(getattr(t, a), False)
        self.assertTrue(all(r.is_current is False for r in rows))                          # input rows untouched
class Callpath(unittest.TestCase):
    def test_subject_terminal_identities_from_the_real_subject(self):
        rows = [A("b"), rec("b", survivor="c"), rec("c", current=True, state="CURRENT")]; lk, store = lookup(rows)
        res = TI.subject_terminal_identities(T.subject(), store.all(), T.normalizer(), active_era_id=store.active_era_id)
        self.assertEqual([(t.start_id, t.terminal_id, t.terminal_state, t.status) for t in res], [("returns.1bar", "c", "CURRENT", TI.CURRENT_SURVIVOR)])
    def test_pipeline_baseline_failure_reports_the_terminal_identity_and_still_fails_closed(self):
        from tests.trk_stage_a.fixtures import Rig, package
        from tests.trk_stage_a.test_pipeline import baseline_binding
        from stage_a.tracker.quant_intake_adapter import admit
        from tracker_identity import store as S
        p = package(); d = admit(p, accepted_fit_generations={}).definition
        key = d.content_identity_key()[0]
        old = T.keyed_row(key, feature_id="old.mom3", current=False, scope="canonical_survivor_discarded")
        old = FeatureIdentity(**{**old.__dict__, "lifecycle_state": "RETIRED", "canonical_survivor": "succ"})
        succ = rec("succ", state="REJECTED_INVALID")
        old = FeatureIdentity(**{**old.__dict__, "instrument": d.instrument, "timeframe": d.timeframe}); succ = FeatureIdentity(**{**succ.__dict__, "instrument": d.instrument, "timeframe": d.timeframe})   # same identity scope as the package
        bb = baseline_binding()
        with mock.patch.object(S, "_fixture_seeding_permitted", lambda: True): bb.store._fixture_write_records([old, succ]) if hasattr(bb.store, "_fixture_write_records") else T.seed_fixture(bb.store, [old, succ])
        rig = Rig(baseline=bb); rig.issue(p); o = rig.pipe.run(p)
        self.assertFalse(o.accepted_ok); self.assertEqual(o.stage, "BASELINE_REGISTRATION")
        msgs = [m for _, m in o.failures]
        t, = o.terminal_identities                                                           # typed, subject-bound (derived from the recomputed content key), not diagnostic text
        self.assertEqual((t.start_id, t.terminal_id, t.terminal_state, t.status, t.terminal_facts[8]), ("old.mom3", "succ", "REJECTED_INVALID", TI.TERMINAL_NONCURRENT, "REJECTED_INVALID"))
        self.assertIn("CANONICAL_SURVIVOR_REPORT_SLOT", dict(o.limits)); self.assertIsNone(o.report["CANONICAL_SURVIVOR"])      # report encoding is UNBOUND: not substituted by strings
        self.assertFalse(any("TERMINAL_IDENTITY" in m for m in msgs))
        self.assertEqual(rig.claims.claim("CLAIM:REQ-1")["state"], "RELEASED")              # no new claim authority was created
    def test_pipeline_reports_only_the_subjects_match_not_unrelated_same_scope_rows(self):
        from tests.trk_stage_a.fixtures import Rig, package
        from tests.trk_stage_a.test_pipeline import baseline_binding
        from stage_a.tracker.quant_intake_adapter import admit
        from tracker_identity import store as S
        p = package(); d = admit(p, accepted_fit_generations={}).definition
        key = d.content_identity_key()[0]
        old = T.keyed_row(key, feature_id="old.mom3", current=False, scope="canonical_survivor_discarded")
        old = FeatureIdentity(**{**old.__dict__, "lifecycle_state": "RETIRED", "canonical_survivor": "succ"})
        succ = rec("succ", state="REJECTED_INVALID")
        old = FeatureIdentity(**{**old.__dict__, "instrument": d.instrument, "timeframe": d.timeframe}); succ = FeatureIdentity(**{**succ.__dict__, "instrument": d.instrument, "timeframe": d.timeframe})   # same identity scope as the package
        bb = baseline_binding()
        with mock.patch.object(S, "_fixture_seeding_permitted", lambda: True): bb.store._fixture_write_records([old, succ, rec("unrelated", survivor="z"), rec("z", state="RETIRED")]) if hasattr(bb.store, "_fixture_write_records") else T.seed_fixture(bb.store, [old, succ, rec("unrelated", survivor="z"), rec("z", state="RETIRED")])
        rig = Rig(baseline=bb); rig.issue(p); o = rig.pipe.run(p)
        self.assertFalse(o.accepted_ok); self.assertEqual(o.stage, "BASELINE_REGISTRATION")
        msgs = [m for _, m in o.failures]
        self.assertEqual([t.start_id for t in o.terminal_identities], ["old.mom3"])                  # the unrelated same-scope start is NOT reported
        self.assertEqual(rig.claims.claim("CLAIM:REQ-1")["state"], "RELEASED")              # no new claim authority was created
if __name__ == "__main__": unittest.main()
if __name__ == "__main__": unittest.main()
