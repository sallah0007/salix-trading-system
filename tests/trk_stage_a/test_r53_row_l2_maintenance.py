"""R53 generic per-ROW L2 maintenance (Registry p203-212, FrozenParent p455-465) over the ACTUAL stored row set of the real per-row route, reaching BOTH actual consumers (FW deliver / ML deliver_ml).
SIM profile (UNADMITTED): schema/program/codec/clock/commit-point. The SOURCE is a mutable map the supplied resolve_inputs reads (so a changed or missing source is a real changed/missing input). Clears no gate/hold."""
import copy, dataclasses as dc, json, unittest
from stage_a.gateway import contracts as G
from stage_a.gateway.v038 import FinalResolutionIdentity as FI
from stage_a.storage import authority_class as AC
from stage_a.tracker import row_maintenance as RM, row_acceptance as RA
from . import test_r53_row_route_delivery as RR
from .test_r53_row_acceptance import acc as _acc
from .test_r53_row_route_delivery import GTAB, code, NONE_, I, R, FA, FB, T
from .test_r53_row_acceptance import SCHEMA, _ref_step, _i_enc, _i_dec

class Maint(RR.RowRoute):
    pass
for _n in [n for n in dir(RR.RowRoute) if n.startswith("test_")]: setattr(Maint, _n, None)         # inherited tests are not rerun here

SRC0 = {"in0": 1.0, "in1": 2.0, "in2": 4.0}
class RowL2(Maint):
    def prof(self, src, **o):
        p = dict(tables=T, schema=copy.deepcopy(SCHEMA), schema_registry=lambda v: copy.deepcopy(SCHEMA), reference_step=_ref_step, decode=_i_dec, encode=_i_enc,
                 resolve_inputs=lambda d: None if any(r.target_id.decode() not in src for r, hh in d) else {"declared": [(r, hh, src[r.target_id.decode()]) for r, hh in d]}, input_symbols={"x": 0}); p.update(o); return p
    def setUp(self):
        super().setUp(); self.src = dict(SRC0); self.publish("A", 0); self.publish("A", 1); self.publish("B", 0); self.publish("B", 1)         # row 2 of each feature is stored but NOT accepted (PENDING)
        self.res = {t: self.o[t][1].recover_publication(self.o[t][0]) for t in "AB"}
    def deliver(self, tag, n, step, now):
        fk, co, r0, b, e = self.o[tag]; e = dc.replace(e, expected_projection=self.chain[tag][0][0].published_projection_name); k = dict(binding=b, now=now, ref=R("hl-" + n), resolved_at=now - 1, tables=GTAB); res = self.res[tag]
        fw = co.deliver("fw-" + n, FI("FW", "M-" + n, "XAUUSD", "W" + n), e, I, I, step, 60, res, **k) if False else None
        try: fw = co.deliver("fw-" + n, FI("FW", "M-" + n, "XAUUSD", "W" + n), e, I, I, step, 60, res, **k)
        except Exception as ex: fw = ex
        ml = co.deliver_ml("ml-" + n, FI("ML", "D-" + n, "XAUUSD", "W" + n), e, I, I, step, 60, res, row_id="row-" + n, generation_ref=R("gen"), vintage_mode="ORIGINAL_AS_OBSERVED", omissions=NONE_, exclusion_reason=lambda x: ("ENUM", "REASON", "L2_ROW"), **k)
        return fw, ml
    def maint(self, now, tag="B"):
        return self.o[tag][1].run_maintenance([(self.o[tag][0].key(), "SCHEDULED")], now=now, max_age=50, max_items=4)
    def reg(self, p=None, tag="B"): return self.o[tag][1].register_row_maintenance(self.res[tag], self.prof(self.src) if p is None else p)
    def denied(self, tag, n, step, now):
        fw, ml = self.deliver(tag, n, step, now); self.assertFalse(isinstance(fw, G.Binding)); self.assertFalse(ml.included); return fw, ml
    def delivered(self, tag, n, step, now):
        fw, ml = self.deliver(tag, n, step, now); self.assertIsInstance(fw, G.Binding); self.assertTrue(ml.included)
    def heads(self): return {n: self.a.rig.journals.journal(n).head().seq for n in (RA.row_namespace(self.chain["B"][0][0]),)}

    def test_genuine_actual_inputs_verify_every_accepted_stored_row_pending_rows_are_listed_not_counted_and_both_consumers_still_deliver(self):
        self.delivered("B", "c0", 0, 12); b = self.reg(); r = RM.verify_stored_rows(b)
        self.assertEqual(r["overall"], "VERIFIED_ROWS_EQUAL_RECOMPUTED"); self.assertEqual(sorted(v[0] for v in r["rows"].values()), ["PENDING", "VERIFIED", "VERIFIED"])                  # rows 0,1 accepted+verified; row 2 stored, never accepted
        self.assertEqual([x[2] for x in self.maint(13)], ["VERIFIED"]); self.delivered("B", "p0", 0, 14); self.delivered("B", "p1", 1, 14)
        self.denied("A", "a0", 0, 14)                                                                                          # BASE B delivers to both consumers while the affected feature A (ancestry UNKNOWN) stays denied for both, accepted+published rows notwithstanding
    def test_a_changed_SOURCE_input_fails_the_recomputation_and_FW_denies_ML_excludes_while_the_independent_BASE_feature_still_delivers_and_history_is_untouched(self):
        self.reg(); self.assertEqual([x[2] for x in self.maint(13)], ["VERIFIED"]); before = self.heads(); rowbytes = {k: self.a.rig.store.get(k) for k in self.a.rig.store.list_prefix("pending-row/")}
        self.src["in1"] = 99.0                                                                                              # the authoritative input behind stored row 1 changes
        self.assertEqual([x[2] for x in self.maint(15)], ["RECORDED_NOT_PASS"]); r = RM.verify_stored_rows(self.o["B"][1]._sv[self.o["B"][0].key()]); self.assertEqual(r["overall"], "FAIL"); self.assertEqual(r["l1_fallback"], False)
        self.assertIn("ROW_REVERIFICATION_FAIL", sorted(v[1] for v in r["rows"].values())[0] + "".join(v[1] for v in r["rows"].values()))
        self.denied("B", "n0", 0, 16); self.denied("B", "n1", 1, 16)                                                         # BOTH consumers refuse the affected feature's windows (even the row whose own input is unchanged: its successor chain / feature trust is not current)
        self.denied("A", "a-still", 0, 16)                                                                                    # A's ancestry stays UNKNOWN (unchanged by B's maintenance outcome)
        self.assertEqual(self.heads(), before); self.assertEqual({k: self.a.rig.store.get(k) for k in self.a.rig.store.list_prefix("pending-row/")}, rowbytes)    # historical accepted records and stored rows untouched; current trust lives only in the Core
        self.src["in1"] = 2.0; self.assertEqual([x[2] for x in self.maint(17)], ["VERIFIED"]); self.delivered("B", "back", 0, 18)             # negative control: restoring the real source returns to PASS
    def test_a_missing_source_is_UNAVAILABLE_never_PASS_and_L1_cannot_substitute(self):
        self.reg(); del self.src["in2"], self.src["in1"]; b = self.o["B"][1]._sv[self.o["B"][0].key()]; r = RM.verify_stored_rows(b)
        self.assertEqual((r["overall"], r["l2"], r["l1"], r["l1_fallback"]), ("UNAVAILABLE", "UNAVAILABLE", "PASS", False)); self.assertEqual([x[2] for x in self.maint(13)], ["RECORDED_NOT_PASS"]); self.denied("B", "m0", 0, 14)
    def test_a_corrupted_stored_row_or_predecessor_is_FAIL_not_a_skip(self):
        self.reg(); h0, h1 = (self.chain["B"][i][1].row_hash for i in (0, 1)); st = self.a.rig.store._i; k0 = AC._PREFIX + "pending-row/" + h0; d, e = st._d[k0]; st._d[k0] = (d[:-1] + bytes([d[-1] ^ 1]), e)
        r = RM.verify_stored_rows(self.o["B"][1]._sv[self.o["B"][0].key()]); self.assertEqual(r["overall"], "FAIL"); rs = dict(r["rows"]); self.assertTrue(rs[h0[:16]][0] == "FAIL" and rs[h1[:16]][0] == "FAIL")     # row 0 unreadable; row 1's predecessor unreadable
        self.assertEqual([x[2] for x in self.maint(13)], ["RECORDED_NOT_PASS"]); self.denied("B", "x0", 0, 14)
    def drop(self, key):                                                                                                      # the store-port fault: ONE object absent from get/list_prefix; journals, manifest, heads and all other data unchanged
        st = self.a.rig.store._i; k = AC._PREFIX + key; d = st._d.pop(k); return d
    def test_an_unparseable_sidecar_of_an_ACCEPTED_row_fails_that_feature_via_the_owning_journal_namespace(self):
        self.reg(); h = self.chain["B"][0][1].row_hash; st = self.a.rig.store._i; k = AC._PREFIX + "pending-row-fields/" + h; d, e = st._d[k]; st._d[k] = (b"{not json", e)
        r = RM.verify_stored_rows(self.o["B"][1]._sv[self.o["B"][0].key()]); self.assertEqual(r["overall"], "FAIL"); self.assertEqual(r["rows"][h[:16]], ("FAIL", "ACCEPTED_ROW_SIDECAR_ABSENT_OR_UNREADABLE"))
        self.assertEqual(RM.verify_stored_rows(self.o["A"][1].register_row_maintenance(self.res["A"], self.prof(self.src)))["overall"], "VERIFIED_ROWS_EQUAL_RECOMPUTED")          # the unrelated feature is not failed
    def test_a_missing_FINAL_accepted_row_sidecar_is_FAIL_not_a_silent_omission_and_both_consumers_deny(self):
        b = self.reg(); r0 = RM.verify_stored_rows(b); self.assertEqual((r0["overall"], sorted(v[0] for v in r0["rows"].values())), ("VERIFIED_ROWS_EQUAL_RECOMPUTED", ["PENDING", "VERIFIED", "VERIFIED"]))      # full control
        h1 = self.chain["B"][1][1].row_hash; heads = self.heads(); self.drop("pending-row-fields/" + h1); r = RM.verify_stored_rows(b)
        self.assertEqual(r["overall"], "FAIL"); self.assertEqual(r["rows"][h1[:16]], ("FAIL", "ACCEPTED_ROW_SIDECAR_ABSENT_OR_UNREADABLE")); self.assertEqual(sorted(v[0] for v in r["rows"].values()), ["FAIL", "PENDING", "VERIFIED"])                                    # survivor still verifies; the missing tail is not silently omitted
        self.assertEqual([x[2] for x in self.maint(13)], ["RECORDED_NOT_PASS"]); self.denied("B", "ms0", 0, 14); self.denied("B", "ms1", 1, 14); self.denied("A", "ms-a", 0, 14); self.assertEqual(self.heads(), heads)
    def test_a_missing_INTERNAL_accepted_row_sidecar_or_row_bytes_is_FAIL_and_an_all_sidecars_missing_feature_is_HELD_not_a_clean_pass(self):
        b = self.reg(); h0, h1 = (self.chain["B"][i][1].row_hash for i in (0, 1)); self.drop("pending-row-fields/" + h0); r = RM.verify_stored_rows(b)
        self.assertEqual((r["overall"], r["rows"][h0[:16]][0]), ("FAIL", "FAIL")); self.assertEqual(r["rows"][h1[:16]][0], "FAIL")                                # h1's predecessor is gone too: unreadable
        self.drop("pending-row-fields/" + h1); r = RM.verify_stored_rows(b); self.assertEqual((r["overall"], r["reason"]), ("FAIL", "ROW_FAIL"))             # the pending row's sidecar still attributes the feature_id: both accepted rows FAIL
        self.drop("pending-row-fields/" + self.chain["B"][2][1].row_hash); r = RM.verify_stored_rows(b); self.assertEqual((r["overall"], r["reason"]), ("UNAVAILABLE", "ROW_ACCEPTED_NAMESPACE_UNATTRIBUTABLE_HELD")); self.assertEqual(len(r["unattributable"]), 2)   # nothing left to attribute by: HELD, never PASS, never a global verdict
        self.assertEqual(RM.verify_stored_rows(self.o["A"][1].register_row_maintenance(self.res["A"], self.prof(self.src)))["overall"], "VERIFIED_ROWS_EQUAL_RECOMPUTED")                          # unrelated feature (different feature_id namespace) unaffected
        self.assertEqual([x[2] for x in self.maint(13)], ["RECORDED_NOT_PASS"]); self.denied("B", "ms2", 0, 14)
    def test_row_bytes_missing_with_the_sidecar_present_is_FAIL(self):
        b = self.reg(); h1 = self.chain["B"][1][1].row_hash; self.drop("pending-row/" + h1); r = RM.verify_stored_rows(b); self.assertEqual((r["overall"], r["rows"][h1[:16]][0]), ("FAIL", "FAIL"))
    def test_the_read_basis_must_be_coherent_a_journal_that_advances_during_the_pass_is_HELD_and_a_genuine_complete_history_is_VERIFIED(self):
        from unittest import mock
        b = self.reg(); self.assertEqual(RM.verify_stored_rows(b)["overall"], "VERIFIED_ROWS_EQUAL_RECOMPUTED")
        real = RM.verify_row_step; state = {"done": False}
        def advancing(**k):
            if not state["done"]: state["done"] = True; _acc(self.acc, self.chain["B"][2][1].row_hash)                 # a legitimate NEW accepted row lands mid-pass
            return real(**k)
        with mock.patch.object(RM, "verify_row_step", advancing): r = RM.verify_stored_rows(b)
        self.assertEqual((r["overall"], r["reason"]), ("UNAVAILABLE", "ROW_ACCEPTED_JOURNAL_ADVANCED_DURING_READ_HELD")); r2 = RM.verify_stored_rows(b); self.assertEqual(sorted(v[0] for v in r2["rows"].values()), ["VERIFIED", "VERIFIED", "VERIFIED"])   # re-run on the new basis: all three accepted rows
    def test_an_incoherent_head_read_is_HELD(self):
        class J:
            def __init__(s, j): s.j, s.n = j, 0
            def head(s):
                s.n += 1; h = s.j.head(); return h if s.n % 2 else type(h)(h.seq + 1, h.hash)
            def read_from(s, n): return s.j.read_from(n)
        class JS:
            def __init__(s, js): s.js = js
            def journal(s, ns): return J(s.js.journal(ns)) if ns.startswith("rowtx/") else s.js.journal(ns)
        b = self.reg(); b = RM.RowBinding(JS(b.journals), b.rows, b.store, b.feature_key, b.profile); r = RM.verify_stored_rows(b); self.assertEqual((r["overall"], r["reason"]), ("UNAVAILABLE", "ROW_ACCEPTED_JOURNAL_BASIS_NOT_COHERENT_HELD"))
    def test_an_unbound_or_incomplete_profile_is_HELD_UNAVAILABLE_not_PASS_and_zero_accepted_rows_is_not_a_completed_search(self):
        for p in (None, {}, dict(self.prof(self.src), resolve_inputs=None)):
            b = self.o["B"][1].register_row_maintenance(self.res["B"], p); r = RM.verify_stored_rows(b); self.assertEqual((r["overall"], r["reason"], r["l2"]), ("UNAVAILABLE", "ROW_PROFILE_HELD", "UNAVAILABLE"))
        self.assertEqual([x[2] for x in self.maint(13)], ["RECORDED_NOT_PASS"]); self.denied("B", "h0", 0, 14)
    def test_registration_is_only_for_a_result_this_composition_published(self):
        from stage_a.errors import Refusal
        with self.assertRaises(Refusal) as e: self.o["B"][1].register_row_maintenance(self.res["A"], self.prof(self.src))
        self.assertEqual(e.exception.code, "COMPOSITION_RESULT_NOT_THIS_PUBLICATION")

    def test_corruption_of_ANOTHER_features_stored_row_does_not_fail_this_feature_per_feature_attribution_scopes_the_blast_radius(self):
        self.reg(); hA = self.chain["A"][0][1].row_hash; st = self.a.rig.store._i; k = AC._PREFIX + "pending-row/" + hA; d, e = st._d[k]; st._d[k] = (d[:-1] + bytes([d[-1] ^ 1]), e)
        r = RM.verify_stored_rows(self.o["B"][1]._sv[self.o["B"][0].key()]); self.assertEqual(r["overall"], "VERIFIED_ROWS_EQUAL_RECOMPUTED"); self.assertEqual([x[2] for x in self.maint(13)], ["VERIFIED"]); self.delivered("B", "iso", 0, 14)
        bA = self.o["A"][1].register_row_maintenance(self.res["A"], self.prof(self.src)); self.assertEqual(RM.verify_stored_rows(bA)["overall"], "FAIL")             # but A's own maintenance sees its corrupt row

    def _both_routes(self):
        from .test_r37_stored_values import SER, H as SH
        segs = {"SRC/close": list(SER)}; si = dict(bindings={"close": {"ref": "SRC/close", "hash": SH(SER)}}, fetch=lambda ref: segs.get(ref), series_hash=SH)
        co = self.o["B"][1]; self.res["B"] = co.recover_publication(self.o["B"][0], stored_inputs=si); co.register_stored_maintenance(self.res["B"]); b = self.reg(); self.assertIsNotNone(b.segments); return segs, SER
    def test_feature_version_segments_and_rows_are_combined_worst_of_in_ONE_record_neither_masks_the_other(self):
        segs, SER = self._both_routes(); self.assertEqual([x[2] for x in self.maint(13)], ["VERIFIED"]); self.delivered("B", "w0", 0, 14)
        segs["SRC/close"] = SER[:-1] + [-1]                                                                                  # segment source changes, row sources intact
        self.assertEqual([x[2] for x in self.maint(15)], ["RECORDED_NOT_PASS"]); r = RM.verify_feature(self.o["B"][1]._sv[self.o["B"][0].key()]); self.assertEqual((r["l2"], r["segments_overall"]), ("FAIL", "FAIL")); self.assertIn("ROWS:VERIFIED_ROWS_EQUAL_RECOMPUTED", r["reason"]); self.denied("B", "w1", 0, 16)
        segs["SRC/close"] = list(SER); self.assertEqual([x[2] for x in self.maint(17)], ["VERIFIED"])                         # restored
        self.src["in1"] = 7.0; self.assertEqual([x[2] for x in self.maint(19)], ["RECORDED_NOT_PASS"]); r = RM.verify_feature(self.o["B"][1]._sv[self.o["B"][0].key()]); self.assertEqual((r["l2"], r["segments_overall"]), ("FAIL", "VERIFIED_STORED_EQUALS_RECOMPUTED"))   # rows fail, segments pass: still FAIL
        self.denied("B", "w2", 0, 20)

    def test_a_PASS_whose_rederived_result_differs_from_the_evidence_the_acceptance_recorded_is_FAIL(self):
        from unittest import mock
        from stage_a.tracker.verification.verification_result import _issue_result
        real = RM.verify_row_step
        def other(**k):
            r = real(**k); return _issue_result(r.status, r.scope, dict(dict(r.subject), profile_note="different"), r.checks, r.reasons)          # genuine receipt, PASS, but a DIFFERENT verification identity than at acceptance
        b = self.reg(); self.assertEqual(RM.verify_stored_rows(b)["overall"], "VERIFIED_ROWS_EQUAL_RECOMPUTED")
        with mock.patch.object(RM, "verify_row_step", other): r = RM.verify_stored_rows(b)
        self.assertEqual(r["overall"], "FAIL"); self.assertTrue(all(v[1] == "ROW_REVERIFICATION_DIFFERS_FROM_ACCEPTED_EVIDENCE" for v in r["rows"].values() if v[0] != "PENDING"))

class RowL2NoAcceptedRows(Maint):
    def test_stored_but_never_accepted_rows_are_not_a_completed_search_UNAVAILABLE_and_deny(self):
        co, fk = self.o["B"][1], self.o["B"][0]; res = co.recover_publication(fk); p = RowL2.prof(self, dict(SRC0)); b = co.register_row_maintenance(res, p); r = RM.verify_stored_rows(b)
        self.assertEqual((r["overall"], r["reason"], r["l2"]), ("UNAVAILABLE", "ACCEPTED_ROWS_ABSENT", "UNAVAILABLE")); self.assertEqual([v[0] for v in r["rows"].values()], ["PENDING"] * 3)
