"""R41: the corrected separated materializer/verifier/acceptor child processes driven by a bounded ACTUAL caller over the same ClaimService/accepted journal, then the committed SIM status projection, Core, Gateway and consumer path: required-unknown ancestry denial AND unrelated baseline DELIVERY through the same objects. SIMULATION only; no principal/deployment/provider."""
import os, tempfile, unittest
from stage_a.errors import Refusal
from stage_a.gateway import contracts as G
from stage_a.gateway.v038 import FinalResolutionIdentity as FI
from stage_a.ops import workers as W
from stage_a.ops.process_supervisor import ProcessSupervisor
from stage_a.ops.separated_caller import SeparatedAcceptor
from stage_a.storage.file_object_store import FileObjectStore
from stage_a.storage.authority_class import approve_test_adapter
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.composer import order_authority as OA
from stage_a.composer.build_gate import accept_build_start as abs_
from stage_a.tracker import composition as CO, sim_publication_path as SP
from stage_a.tracker.quant_intake_adapter import admit
from .fixtures import Rig, package, SIM_CONF, momentum_manifest, IDENTITY_FIELDS, ANCHOR
from .test_r29_intake_order import issue, br, rec
from .test_r25_scheduler import core, ver
from .test_boundaries import T, I, _entry, R
from .test_r37_sim_publication_path import SPEC, supplied
from .test_r38_composition import _g, AP, RES
from .test_r40_separated_handlers import HS
approve_test_adapter(FileObjectStore)
FB = bytes(range(48, 64))
class Caller(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.root = os.path.join(self.d.name, "store"); os.environ["SALIX_SEP_ROOT"] = self.root
        self.rig = Rig(store=FileObjectStore(self.root)); self.c = core(); self.q = W.JobQueue(); self.sup = ProcessSupervisor(self.q, HS, reply_timeout=60, max_attempts=1)
        self.acc = lambda pkg: SeparatedAcceptor(self.sup, self.q, self.rig.store, self.rig.journals, self.rig.claims, ANCHOR, lambda p: admit(p, accepted_fit_generations=self.rig.fits, conformance=SIM_CONF), reacquire_claims=lambda: self.rig.claims._j.acquire_epoch())(pkg)
    def tearDown(self): self.sup.close(); os.environ.pop("SALIX_SEP_ROOT", None); self.d.cleanup()
    def _feature(self, fid, n):
        rig = self.rig; oid = OA.order_id_for("cand-%d" % n); p = package(momentum_manifest(feature_id=fid, window=2 + n), identity_fields=dict(IDENTITY_FIELDS, parameters={"lookback_bars": 2 + n}), request_id="REQ-%d" % n, attempt_id="ATT-%d" % n, order_id=oid)
        a = admit(p, accepted_fit_generations=rig.fits, conformance=SIM_CONF); issue(rig.claims, rec(CANDIDATE_IDENTITY="cand-%d" % n), subject_key=a.subject_key); abs_(rig.claims, oid, br(CANDIDATE_IDENTITY="cand-%d" % n)); fk = a.feature_key
        sj = ObjectStoreJournal(rig.store, "SIMPUB-%s-%s" % (fk.scope.instrument, fid), "w"); sj.acquire_epoch(); path = SP.SimulationPublicationPath(rig.store, rig.journals.journal(fk.namespace()), sj, SPEC)
        return p, fk, CO.Composition(pipeline=rig.pipe, journals=rig.journals, store=rig.store, core=self.c, path=path, gateway_factory=lambda proj: _g(proj, self.c), l2_scope_resolver=RES)
    def _deliver(self, co, fk, r, tag, fid=None):
        fid = fid or supplied().feature_id
        self.c.declare_ancestry_complete(fk.key(), "src"); b = G.HealthBinding(fid, fk.feature_version, I, I); self.c.associate_subject(fk.key(), b, "assoc"); e = _entry(fid=fid, ver=fk.feature_version)
        try: return co.deliver("fw-" + tag, FI("FW", "M-A", "XAUUSD", tag), e, I, I, 3, 20, r, binding=b, now=12, ref=R("hl-" + tag), resolved_at=11, tables=T)
        except Refusal as x: return x.code
    def test_separated_child_acceptance_then_committed_status_core_gateway_with_unknown_ancestry_denied_and_the_unrelated_baseline_delivered(self):
        pa, fka, coa = self._feature("mom3", 1); pb, fkb, cob = self._feature("mom4", 2); coa._up = {fka.key(): ("UP",)}; ver(self.c, "UP", version="1", at=9, age=50)
        ra = coa.accept_and_publish(pa, supplied(), "SIM_CUR", sequence=1, now=10, max_age=50, l2_applicability=AP, accept_fn=self.acc)
        rb = cob.accept_and_publish(pb, supplied(feature_id=FB), "SIM_CUR", sequence=1, now=10, max_age=50, l2_applicability=AP, accept_fn=self.acc)
        self.assertEqual((ra.status, rb.status), ("PUBLISHED_SIMULATION", "PUBLISHED_SIMULATION")); self.assertEqual(ra.outcome.stage, "SEPARATED_ACCEPTED")
        self.assertEqual(len([r for r in self.rig.journals.journal(fka.namespace()).read_from(1) if r.kind == "CANONICAL_ACCEPTED"]), 1)        # written by the CHILD acceptor into the same journal
        self.assertEqual(self._deliver(coa, fka, ra, "A1"), "NON_DELIVERY"); self.assertIsInstance(self._deliver(cob, fkb, rb, "B1", FB), G.Binding)
        self.c.declare_ancestry_complete("UP", "src"); self.assertIsInstance(self._deliver(coa, fka, ra, "A2"), G.Binding)
    def test_a_failed_child_job_never_yields_an_acceptance_or_publication(self):
        pa, fka, coa = self._feature("mom3", 1); self.sup._h.pop("tracker.verify"); self.sup._h["tracker.verify"] = ("tracker-verifier-worker", "stage_a.ops.separated_handlers:nonexistent")
        self.sup._replace("tracker-verifier-worker")
        r = coa.accept_and_publish(pa, supplied(), "SIM_CUR", sequence=1, now=10, max_age=50, l2_applicability=AP, accept_fn=self.acc)
        self.assertEqual(r.status, "NOT_ACCEPTED"); self.assertTrue(r.outcome.stage.startswith("SEP_CALLER_JOB_NOT_DONE")); self.assertIsNone(coa.gateway)
if __name__ == "__main__": unittest.main()
