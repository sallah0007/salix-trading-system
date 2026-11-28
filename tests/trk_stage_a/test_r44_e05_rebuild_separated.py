"""R44: E05 read-model REBUILD on the separated path's OWN objects: the durable final-resolution records written by the separated acceptance -> Core -> Gateway -> FW + ML deliveries are projected by the owning source; a lost index is rebuilt to the same rows; a later denial moves the head; a tampered record is drift. Same objects as R41-R43 (no second store)."""
import unittest
from stage_a.errors import IntegrityFailure
from stage_a.storage import e05_sources as S
from stage_a.storage.e05_index import E05Index
from .test_r43_maintenance_recovery import Maintenance as _M
from .test_r41_separated_caller import supplied, FB
def bind_cols(ident, out): return dict(consumer_binding_id=ident.consumer_id + ":" + ident.window_fence_id, consumer_id=ident.consumer_id, purpose="P", decision_window=ident.window_fence_id, final_package_hash=out.delivered_feature_hash.hex() if isinstance(out.delivered_feature_hash, (bytes, bytearray)) else str(out.delivered_feature_hash))
def nd_cols(ident, out): return dict(non_delivery_resolution_id=ident.consumer_id + ":" + ident.window_fence_id, resolution_identity=ident.scope, reason_code=getattr(out, "reason", "NONE"), expected_dependency_key="k")
class Rebuild(_M):
    test_all_segment_l2_failure_denies_both_consumers_for_that_feature_only_and_restoring_the_source_restores_delivery = None
    test_quarantine_denies_both_consumers_restoration_needs_a_distinct_certifier_and_a_restart_replays_the_same_state = None
    test_separated_child_acceptance_then_committed_status_core_gateway_with_unknown_ancestry_denied_and_the_unrelated_baseline_delivered = None
    test_a_failed_child_job_never_yields_an_acceptance_or_publication = None
    test_a_non_admissible_package_is_not_staged_claimed_or_run = None
    def rows(self, co):
        raw = co.gateway.final_store._o; ix = E05Index(); ix.rebuild({"fr": S.final_resolution_source(raw, binding_columns=bind_cols, non_delivery_columns=nd_cols)}); return raw, ix
    def test_a_lost_index_is_rebuilt_to_the_same_rows_a_denial_moves_the_head_and_a_tampered_record_is_drift(self):
        (fka, coa, ra, ba, sa), (fkb, cob, rb, bb, sb) = self._two()
        self._delivered(coa, self._both(fka, coa, ba, supplied().feature_id, "A1"))
        raw, ix1 = self.rows(coa); res = S.object_resolver(raw)
        n1 = ix1.verify_all(res); self.assertEqual(n1, 2)                                                                   # FW + ML Binding rows, both from durable records written on the separated path
        for cons in ("FW", "ML"):
            self.assertIsNotNone(ix1.lookup("stagea_consumer_binding_index", {"consumer_binding_id": cons + ":A1"}, res))
        ix2 = E05Index(); ix2.rebuild({"fr": S.final_resolution_source(raw, binding_columns=bind_cols, non_delivery_columns=nd_cols)}); self.assertEqual(sorted(map(str, ix2.current_rows("stagea_consumer_binding_index"))), sorted(map(str, ix1.current_rows("stagea_consumer_binding_index"))))     # lost index -> identical rebuild
        h1 = S.final_resolution_source(raw, binding_columns=bind_cols, non_delivery_columns=nd_cols)[0]()
        self.c.quarantine(fka.key(), "TEST_REASON"); self._denied(coa, self._both(fka, coa, ba, supplied().feature_id, "A2"))
        raw, ix3 = self.rows(coa); h2 = S.final_resolution_source(raw, binding_columns=bind_cols, non_delivery_columns=nd_cols)[0]()
        self.assertNotEqual(h1, h2); self.assertEqual(h2[0], h1[0] + 2); self.assertIsNotNone(ix3.lookup("stagea_non_delivery_index", {"non_delivery_resolution_id": "FW:A2"}, S.object_resolver(raw)))      # the required denial is a durable NonDelivery row, not an absence
        k = raw.list_prefix("final-resolution/id/")[0]; b, e = raw.get(k); raw.put_if_match(k, b.replace(b"XAUUSD", b"EURUSD"), e)
        with self.assertRaises(IntegrityFailure): ix3.verify_all(S.object_resolver(raw))                                  # a replaced record is drift
if __name__ == "__main__": unittest.main()
