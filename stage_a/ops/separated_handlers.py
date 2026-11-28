"""R40: the ACTUAL separated tracker-materializer / tracker-verifier / tracker-acceptance handlers (run INSIDE `worker_child` processes by the `ProcessSupervisor`), as opposed to the marker handlers of the process harness. Reference-only IPC: the job carries governing (name, hash) refs; every input is re-read from the SHARED store by canonical ref and RE-HASHED; nothing rides in the message.
  materialize ("manifest", mh)                                    : re-read manifest bytes, independent digest must equal mh, certify, `StatefulMaterializer.materialize` (the real library), write the materialization record write-if-absent (a differing duplicate is an IntegrityFailure) + a pointer `sep/mat-by-manifest/<mh>`;
  verify      ("materialization", matH) ("declared", mh)          : re-read the record, bind matH, run the real independent `verify_materialization`; ONLY a PASS writes `sep/verification/<result_hash>` + pointer; any other status raises (never recorded as acceptance input);
  accept      ("verification", rh) ("materialization", matH) ("acceptin", mh) : re-read both, bind them to each other and to the stored acceptance input, then call the REAL `TrackerPipeline._accept` (claim/witness check, fence check before and at commit, CAS append, unknown-commit recovery, idempotent replay).
Shared state is ONE directory (`SALIX_SEP_ROOT`) through the labelled TEST adapter `FileObjectStore`, wrapped in `SimulationStore` (physical SIM isolation); the QUALIFIED path stays held. `SALIX_SEP_CRASH_ONCE_DIR` is a TEST hook: after the effect and BEFORE the reply the process exits once per job (crash-after-effect). No principal, host, deployment or provider is created or claimed; the claims trust anchor is read from a TEST object `sep/anchor`, not a governed source."""
import json, os, types
from ..errors import Refusal, IntegrityFailure
from ..storage.byte_primitives import canonical_bytes
from ..storage.file_object_store import FileObjectStore
from ..storage.authority_class import SimulationStore, approve_test_adapter
from ..storage.keys import artifact_key
from ..identifiers import FeatureKey, Scope
from ..composer.expression.manifest import Manifest
from ..tracker.verification.independent_encoding import parse
from ..tracker.verification.independent_hashing import manifest_digest, materialization_digest
from ..tracker.verification.independent_encoding import enc_bytes
from ..tracker.verification.verification_result import make_result, split_levels, PASS, SCOPE_MATERIALIZATION
from ..tracker.verification.stateful_verifier import verify_materialization, probe_for
from ..tracker.materialization.stateful_materializer import StatefulMaterializer
from ..tracker.quant_certification import certify
approve_test_adapter(FileObjectStore)
def _store(): return SimulationStore(FileObjectStore(os.environ["SALIX_SEP_ROOT"]))
def K(kind, h): return "sep/%s/%s" % (kind, h)
def _ref(job, name):
    v = [h for n, h in job.governing_refs if n == name]
    if len(v) != 1 or not isinstance(v[0], str) or not v[0]: raise Refusal(name, code="SEP_JOB_REF_MISSING_OR_DUPLICATE")
    return v[0]
def _get(store, key, code):
    g = store.get(key)
    if g is None: raise Refusal(key, code=code)
    return g[0]
def _put_once(store, key, data):
    if not store.put_if_absent(key, data):
        g = store.get(key)
        if g is None or g[0] != data: raise IntegrityFailure("%s holds different bytes" % key)
def _crash_after_effect(job):
    d = os.environ.get("SALIX_SEP_CRASH_ONCE_DIR")
    if d:
        m = os.path.join(d, job.job_id + ".crashed")
        if not os.path.exists(m): open(m, "w").close(); os._exit(9)
def materialize(job):
    store = _store(); mh = _ref(job, "manifest"); raw = _get(store, artifact_key(mh), "SEP_MANIFEST_ABSENT")
    if manifest_digest(raw) != mh: raise Refusal(mh, code="SEP_MANIFEST_HASH_MISMATCH")
    p = parse(raw); m = Manifest.from_dict(p); probe = probe_for(raw); cert = certify(m, probe)
    if cert.status != "CERTIFIED": raise Refusal(mh, code="SEP_CERTIFICATION_NOT_CERTIFIED")
    rec = StatefulMaterializer(store).materialize(m, probe)
    if rec["manifest_hash"] != mh: raise Refusal(mh, code="SEP_MATERIALIZED_MANIFEST_DIFFERS")
    _put_once(store, K("materialization", rec["materialization_hash"]), canonical_bytes(rec)); _put_once(store, K("mat-by-manifest", mh), rec["materialization_hash"].encode()); _crash_after_effect(job)
def verify(job):
    store = _store(); matH = _ref(job, "materialization"); mh = _ref(job, "declared"); rec = json.loads(_get(store, K("materialization", matH), "SEP_MATERIALIZATION_ABSENT"))
    if rec.get("materialization_hash") != matH or rec.get("manifest_hash") != mh: raise Refusal(matH, code="SEP_MATERIALIZATION_REF_MISMATCH")
    declared = json.loads(_get(store, K("declared", mh), "SEP_DECLARED_ABSENT"))
    ver = verify_materialization(store_get=lambda k: (lambda g: None if g is None else g[0])(store.get(k)), record=rec, declared={k: declared[k] for k in ("manifest_hash", "graph_hash", "program_hash")}, expect_scope_key=declared["scope_key"])
    if ver.status != "PASS": raise Refusal(",".join(ver.reasons), code="SEP_VERIFICATION_NOT_PASS")
    _put_once(store, K("verification", ver.result_hash), canonical_bytes(_receipt(ver, matH))); _put_once(store, K("ver-by-mat", matH), ver.result_hash.encode()); _crash_after_effect(job)
RECEIPT_ENCODING = "R41_CANDIDATE_VERIFICATION_RECEIPT_V1"          # CANDIDATE encoding of the verifier's typed result so a consumer can re-derive its hash; not a normative byte format
def _receipt(ver, matH):
    return {"encoding": RECEIPT_ENCODING, "result_hash": ver.result_hash, "materialization_hash": matH, "status": ver.status, "scope": ver.scope, "subject": [list(x) for x in ver.subject], "checks": [[a, bool(b)] for a, b in ver.checks], "reasons": list(ver.reasons)}
def _check_bindings(store, rh, matH, mh, rec, ver):
    """The acceptor does NOT rerun the verifier/materializer; it independently re-derives (hash arithmetic only) that what it was handed is the exact content-addressed record, artifact and receipt, and that the verifier handler (not the caller) linked this receipt to this materialization."""
    why = lambda c: Refusal(rh, code=c)
    if not isinstance(rec, dict) or materialization_digest(rec, enc_bytes) != matH or rec.get("materialization_hash") != matH: raise why("SEP_ACCEPT_RECORD_NOT_CONTENT_ADDRESSED")
    if rec.get("manifest_hash") != mh or rec.get("object_key") != "artifact/" + mh: raise why("SEP_ACCEPT_REFS_DO_NOT_BIND")
    art = store.get(artifact_key(mh))
    if art is None or manifest_digest(art[0]) != mh: raise why("SEP_ACCEPT_ARTIFACT_NOT_CONTENT_ADDRESSED")
    if not (isinstance(ver, dict) and set(ver) == {"encoding", "result_hash", "materialization_hash", "status", "scope", "subject", "checks", "reasons"} and ver["encoding"] == RECEIPT_ENCODING and ver["result_hash"] == rh and ver["materialization_hash"] == matH): raise why("SEP_ACCEPT_RECEIPT_MALFORMED_OR_MISADDRESSED")
    try: res = make_result(ver["status"], ver["scope"], {k: v for k, v in ver["subject"]}, [(a, b) for a, b in ver["checks"]], ver["reasons"])
    except Exception: raise why("SEP_ACCEPT_RECEIPT_MALFORMED_OR_MISADDRESSED")
    if res.result_hash != rh: raise why("SEP_ACCEPT_RECEIPT_HASH_NOT_REDERIVED")
    sub = dict(res.subject)
    if res.status != PASS or res.scope != SCOPE_MATERIALIZATION or split_levels(res) != ("PASS", "PASS") or not all(ok for _, ok in res.checks): raise why("SEP_ACCEPT_RECEIPT_NOT_A_COMPLETE_PASS")
    if sub.get("materialization_hash") != matH or sub.get("graph_hash") != rec.get("graph_hash") or sub.get("program_hash") != rec.get("program_hash") or sub.get("record_manifest_hash") != mh: raise why("SEP_ACCEPT_RECEIPT_SUBJECT_DIFFERS_FROM_RECORD")
    link = store.get(K("ver-by-mat", matH))
    if link is None or link[0].decode() != rh: raise why("SEP_ACCEPT_RECEIPT_NOT_LINKED_BY_VERIFIER_HANDLER")
def accept(job):
    from tracker_component.claims import ClaimService
    from tracker_component.order import TrustAnchor
    from ..coordination.object_store_journal import ObjectStoreJournal
    from ..tracker.registry import FeatureJournalSet
    from ..tracker.pipeline import TrackerPipeline
    from ..clocks import FixedClock
    from ..observability import EventSink
    store = _store(); rh, matH, mh = _ref(job, "verification"), _ref(job, "materialization"), _ref(job, "acceptin")
    rec = json.loads(_get(store, K("materialization", matH), "SEP_MATERIALIZATION_ABSENT")); ver = json.loads(_get(store, K("verification", rh), "SEP_VERIFICATION_ABSENT"))
    _check_bindings(store, rh, matH, mh, rec, ver)
    ai = json.loads(_get(store, K("acceptin", mh), "SEP_ACCEPTIN_ABSENT")); a = json.loads(_get(store, "sep/anchor", "SEP_ANCHOR_ABSENT"))
    fk = FeatureKey(Scope(ai["instrument"], ai["timeframe"]), ai["feature_id"], ai["feature_version"])
    if fk.key() != rec["feature_key"]: raise Refusal(fk.key(), code="SEP_ACCEPT_FEATURE_DIFFERS_FROM_MATERIALIZATION")
    cj = ObjectStoreJournal(store, "claims", "claims-writer"); cj.acquire_epoch()
    pipe = TrackerPipeline(store=store, claims=ClaimService(cj, TrustAnchor(frozenset(a["issuers"]), a["binding"])), journals=FeatureJournalSet(store, "tracker-1"), clock=FixedClock(), events=EventSink(), simulation=True)
    pipe._accept(types.SimpleNamespace(request_id=ai["request_id"], attempt_id=ai["attempt_id"]), types.SimpleNamespace(feature_key=fk), types.SimpleNamespace(cert_hash=ai["cert_hash"]), rec, types.SimpleNamespace(result_hash=rh), {"FINAL_REPORT_HASH": ai["report_hash"]}); _crash_after_effect(job)
