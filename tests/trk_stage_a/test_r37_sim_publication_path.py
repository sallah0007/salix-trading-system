"""R37: accepted receipt -> committed SIMULATION journal -> StatusProjection(simulation) + decoded PublishedRows -> Gateway resolve. This is the SIMULATION committed path; it is NOT the QUALIFIED path and clears nothing.
Distinct from test_r36_status_decoder (separate machinery over a hand-built journal): here the rows and the status are derived from the real accepted record the pipeline wrote."""
import json, unittest
from tracker_component.journal_port import GENESIS_HEAD
from stage_a.errors import Refusal
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.gateway import contracts as G
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.tracker import chain_status as C
from stage_a.tracker import sim_publication_path as SP
from stage_a.tracker.status_projection import StatusProjection
from stage_a.tracker.quant_intake_adapter import admit
from stage_a.composer import order_authority as OA
from stage_a.composer.build_gate import accept_build_start as abs_
from .fixtures import Rig, package, SIM_CONF
from .test_boundaries import T, I, H, BITS, R, _entry, _health
from .test_r29_intake_order import issue, br
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
F = bytes(range(16, 32)); J = bytes(range(32, 48))
SPEC = dict(record_kind=SP.STATUS_KIND, mv=("fid", "fver", "instr", "tf", "mver"), bytes_fields={"fid": 16, "instr": 16, "tf": 16}, status_field="st", status_map={"SIM_CUR": C.CURRENT, "SIM_OUT": C.SUPERSEDED}, sequence_field="seq", available_asof_field="asof", correction_field="corr")
def supplied(**o):
    d = dict(feature_id=F, instrument_id=I, timeframe_id=I, materialization_version="m1", step_index=3, event_time=10, logical_encoding_version="l", published_projection_name="p", published_projection_bits=BITS, published_projection_hash=H, fit_generation_ref=R("fit"), data_vintage_mode="ORIGINAL_AS_OBSERVED", available_asof=4, visible_at=4, source_or_causal_policy_ref=R("pol"), canonical_transition_ref=R("ct")); d.update(o); return SP.SuppliedRowInputs(**d)
def build():
    rig = Rig(); oid = OA.order_id_for("cand-1"); p = package(order_id=oid); a = admit(p, accepted_fit_generations=rig.fits, conformance=SIM_CONF); issue(rig.claims, subject_key=a.subject_key); abs_(rig.claims, oid, br()); out = rig.pipe.run(p); assert out.accepted.kind == "CANONICAL_ACCEPTED"
    fk = a.feature_key; fj = rig.journals.journal(fk.namespace()); sj = ObjectStoreJournal(rig.store, "SIMPUB-" + fk.scope.instrument, "sim-pub-writer"); sj.acquire_epoch()
    return rig, fk, fj, SP.SimulationPublicationPath(rig.store, fj, sj, SPEC), json.loads(out.accepted.body_json)
def gw(proj, allow=True):
    g = G.SimulatedGateway(T, proj, watermark=100, allow_shape_only_health=True, allow_simulation_status=allow); return g
class Path(unittest.TestCase):
    def test_accepted_receipt_to_committed_rows_and_status_delivers_and_binds_the_manifest_hash_from_the_receipt(self):
        rig, fk, fj, path, body = build(); path.commit(fk, supplied(), "SIM_CUR", sequence=1); proj = path.status_projection(); self.assertTrue(proj.authoritative); self.assertTrue(proj.simulation)
        g = gw(proj); self.assertEqual(path.feed(g), 1); rows = path.rows(); self.assertEqual(rows[0].quant_manifest_hash, bytes.fromhex(body["manifest_hash"])); self.assertEqual(rows[0].feature_version, fk.feature_version)       # bound from the accepted record, never supplied
        r = g.resolve("r1", _entry(fid=F, ver=fk.feature_version), I, I, 3, 10, _health()); self.assertIsInstance(r, G.Binding)
    def test_a_gateway_that_did_not_opt_in_refuses_the_simulated_status_and_the_default_projection_refuses_a_simulation_journal(self):
        rig, fk, fj, path, body = build(); path.commit(fk, supplied(), "SIM_CUR", sequence=1); proj = path.status_projection(); g = gw(proj, allow=False); path.feed(g)
        self.assertEqual(g.resolve("r1", _entry(fid=F, ver=fk.feature_version), I, I, 3, 10, _health()).reason, "STATUS_SOURCE_SIMULATION_NOT_ALLOWED")
        self.assertEqual(code(StatusProjection, path._sj, lambda r: None), "SIMULATION_NOT_ELIGIBLE")                                                  # strict qualified default unchanged
        q = ObjectStoreJournal(InMemoryObjectStore(), "Q", "w"); q.acquire_epoch(); self.assertEqual(code(StatusProjection, q, lambda r: None, simulation=True), "SIMULATION_PROJECTION_REQUIRES_SIMULATION_JOURNAL")      # a QUALIFIED journal cannot be relabelled simulation
        self.assertEqual(code(SP.SimulationPublicationPath, rig.store, fj, q, SPEC), "SIM_PUBLICATION_REQUIRES_SIMULATION_JOURNAL")
    def test_no_accepted_receipt_unmapped_status_and_bad_ids_write_nothing(self):
        rig, fk, fj, path, body = build(); import dataclasses
        self.assertTrue(dataclasses.is_dataclass(fk)); other = dataclasses.replace(fk, feature_version="99"); self.assertEqual(code(path.commit, other, supplied(), "SIM_CUR", sequence=1), "NO_ACCEPTED_RECORD")
        self.assertEqual(code(path.commit, fk, supplied(), "PUBLISHABLE", sequence=1), "SIM_PUBLICATION_INPUT_INVALID")                                  # PUBLISHABLE is not a mapped token and is never read as CURRENT
        self.assertEqual(code(path.commit, fk, supplied(feature_id=b"short"), "SIM_CUR", sequence=1), "SIM_PUBLICATION_INPUT_INVALID"); self.assertEqual(code(path.commit, fk, supplied(), "SIM_CUR", sequence=0), "SIM_PUBLICATION_INPUT_INVALID")
        self.assertEqual(path._sj.head(), GENESIS_HEAD)                                                                                                    # nothing committed by any refusal
    def test_a_row_whose_accepted_binding_is_altered_in_the_committed_journal_fails_closed(self):
        rig, fk, fj, path, body = build(); path.commit(fk, supplied(), "SIM_CUR", sequence=1); self.assertEqual(len(path.rows()), 1)
        bad = json.loads(path._sj.read_from(1)[0].body_json); bad["accepted_hash"] = "0" * 64; path._sj.append(path._sj.head(), SP.STATUS_KIND, bad)
        self.assertEqual(code(path.rows), "SIM_PUBLICATION_ACCEPTED_BINDING_MISMATCH")
        rig2, fk2, fj2, path2, body2 = build(); path2.commit(fk2, supplied(), "SIM_CUR", sequence=1); b2 = json.loads(path2._sj.read_from(1)[0].body_json); b2["row"]["quant_manifest_hash"] = "1" * 64; path2._sj.append(path2._sj.head(), SP.STATUS_KIND, b2)
        self.assertEqual(code(path2.rows), "SIM_PUBLICATION_ACCEPTED_BINDING_MISMATCH")
    def test_a_later_committed_non_current_status_stops_delivery_and_the_projection_goes_stale_until_refreshed(self):
        rig, fk, fj, path, body = build(); path.commit(fk, supplied(), "SIM_CUR", sequence=1); proj = path.status_projection(); g = gw(proj); path.feed(g); e = _entry(fid=F, ver=fk.feature_version)
        self.assertIsInstance(g.resolve("r1", e, I, I, 3, 10, _health()), G.Binding)
        path.commit(fk, supplied(), "SIM_OUT", sequence=2); self.assertFalse(proj.authoritative); self.assertEqual(g.resolve("r2", e, I, I, 3, 10, _health()).reason, "STATUS_SOURCE_NOT_COMMITTED_PROJECTION")      # stale projection fails closed
        proj.refresh(); self.assertNotIsInstance(g.resolve("r3", e, I, I, 3, 10, _health()), G.Binding)
class Composed(unittest.TestCase):
    def test_accepted_receipt_core_reverify_committed_sim_rows_status_then_window_gateway_with_the_durable_store_delivers_fw_and_denies_unknown_ancestry(self):
        from stage_a.gateway import durable_final_store as D
        from stage_a.gateway.v038 import FinalResolutionIdentity as FI
        from stage_a.tracker import reverification as RV
        from stage_a.fw import receiver as FWR
        from .test_r25_scheduler import core, ver
        rig, fk, fj, path, body = build(); path.commit(fk, supplied(), "SIM_CUR", sequence=1); key = json.loads(fj.read_from(1)[0].body_json)["feature_key"]; c = core(); c.declare_dependency(key, "UP"); ver(c, "UP", version="1", at=9, age=50)
        res, st = RV.reverify_accepted(c, journal=fj, store=rig.store, feature_key=fk, now=10, max_age=50); self.assertEqual((res.status, st), ("PASS", "ACCEPTED_RECORD_AS_FOUND"))
        b1 = G.HealthBinding(F, fk.feature_version, I, I); c.associate_subject(key, b1, "assoc"); g = G.SimulatedGateway(T, path.status_projection(), watermark=100, health_source=c, allow_shape_only_health=False, allow_simulation_status=True); g.final_store = D.DurableFinalResolutionStore(InMemoryObjectStore()); path.feed(g)
        e = _entry(fid=F, ver=fk.feature_version); hs = lambda: c.gateway_health(key, fk.feature_version, 12, R("hl"), 11, binding=b1, require_ancestry=True)
        nd = g.resolve_window("fw1", FI("FW", "M-A", "XAUUSD", "W1"), e, I, I, 3, 20, hs()); self.assertEqual((type(nd).__name__, nd.reason), ("NonDeliveryResolution", "HEALTH_UNACCEPTABLE"))      # unknown required ancestry: fails closed on the committed-status path
        c.declare_ancestry_complete("UP", "src"); c.declare_ancestry_complete(key, "src"); d = g.resolve_window("fw2", FI("FW", "M-A", "XAUUSD", "W2"), e, I, I, 3, 20, hs()); self.assertIsInstance(d, G.Binding); self.assertIs(FWR.receive_verified(d, e, I, I, T, g), d)
if __name__ == "__main__": unittest.main()
