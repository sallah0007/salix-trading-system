"""R41: a bounded ACTUAL caller that drives the separated materializer -> verifier -> acceptor child processes (`separated_handlers`) over reference-only jobs and returns an `Outcome`-shaped result for `Composition.accept_and_publish(accept_fn=...)`, so the committed SIM status projection, Core, Gateway and consumer path run over the acceptance the CHILD processes wrote to the SAME accepted journal / ClaimService store.
It stages only what the handlers read (manifest artifact, declared hashes, acceptance input, anchor) into the shared SIMULATION store; it reserves the claim authority via the real `reserve_authority`. It never runs the materializer/verifier/acceptor in this process, and any job that is not DONE within the bounded drain yields NOT ACCEPTED (no partial credit). Composition's NORMAL path is unchanged: it still runs all libraries in one process; this caller is the separated rehearsal path (SIMULATION only; no principal, deployment or provider)."""
import types
from ..errors import Refusal
from ..storage.byte_primitives import canonical_bytes
from ..storage.keys import artifact_key
from ..composer.expression.canonical_encoding import encode_manifest
from ..tracker.verification.independent_hashing import manifest_digest
from ..tracker.verification.stateful_verifier import probe_for
from ..tracker.quant_certification import certify
from ..tracker.quant_intake_adapter import reserve_authority, build_safe_intake_report
from ..clocks import FixedClock
from . import workers as W
class SeparatedAcceptor:
    def __init__(self, supervisor, queue, store, journals, claims, anchor, admit_fn, *, reacquire_claims=None, max_drain=20):
        self._s, self._q, self._st, self._js, self._cl, self._an, self._admit, self._max, self._re = supervisor, queue, store, journals, claims, anchor, admit_fn, max_drain, reacquire_claims
    def _put(self, key, v):
        d = canonical_bytes(v)
        if not self._st.put_if_absent(key, d):
            g = self._st.get(key)
            if g is None or g[0] != d: raise Refusal(key, code="SEP_CALLER_STAGED_INPUT_CONFLICT")
    def _ptr(self, kind, h):
        g = self._st.get("sep/%s/%s" % (kind, h)); return None if g is None else g[0].decode()
    def __call__(self, pkg):
        adm = self._admit(pkg)
        if not adm.admissible: return types.SimpleNamespace(accepted=None, admission=adm, stage="SEP_CALLER_NOT_ADMISSIBLE")
        if self._re is not None: self._re()           # the claims journal is single-writer per EPOCH: the child acceptor acquires its own epoch, which fences this caller's writer; the caller must re-acquire (explicitly supplied) before its next claim write
        if reserve_authority(self._cl, pkg, adm) is None: return types.SimpleNamespace(accepted=None, admission=adm, stage="SEP_CALLER_AUTHORITY_NOT_RESERVED")
        raw = encode_manifest(adm.manifest); mh = manifest_digest(raw); fk = adm.feature_key
        if not self._st.put_if_absent(artifact_key(mh), raw) and (self._st.get(artifact_key(mh)) or (None,))[0] != raw: raise Refusal(mh, code="SEP_CALLER_STAGED_INPUT_CONFLICT")
        cert = certify(adm.manifest, probe_for(raw)); rep = build_safe_intake_report(pkg, adm, clock=FixedClock(), verdict="ACCEPT_FOR_REGISTRY", identity_decision="NEW_CANONICAL_FEATURE", registry_ref="PROPOSED:" + fk.key())
        self._put("sep/declared/" + mh, {"manifest_hash": mh, "graph_hash": pkg.declared_graph_hash, "program_hash": pkg.declared_program_hash, "scope_key": fk.key()})
        self._put("sep/acceptin/" + mh, {"request_id": pkg.request_id, "attempt_id": pkg.attempt_id, "instrument": fk.scope.instrument, "timeframe": fk.scope.timeframe, "feature_id": fk.feature_id, "feature_version": fk.feature_version, "cert_hash": cert.cert_hash, "report_hash": rep["FINAL_REPORT_HASH"]})
        self._put("sep/anchor", {"issuers": sorted(self._an.issuer_ids), "binding": self._an.source_binding_hash})
        tag = mh[:12]
        self._q.submit(W.Job("m-" + tag, "tracker.materialize", "idem-m-" + tag, (("manifest", mh),)))
        done = list(self._s.run_until_idle(self._max)); matH = self._ptr("mat-by-manifest", mh); rh = None if matH is None else self._ptr("ver-by-mat", matH)
        if matH is not None:
            self._q.submit(W.Job("v-" + tag, "tracker.verify", "idem-v-" + tag, (("materialization", matH), ("declared", mh)))); done += self._s.run_until_idle(self._max); rh = self._ptr("ver-by-mat", matH)
        if rh is not None:
            self._q.submit(W.Job("a-" + tag, "tracker.accept", "idem-a-" + tag, (("verification", rh), ("materialization", matH), ("acceptin", mh)))); done += self._s.run_until_idle(self._max)
        if not (len(done) == 3 and all(r[1] == "DONE" for r in done)): return types.SimpleNamespace(accepted=None, admission=adm, stage="SEP_CALLER_JOB_NOT_DONE:" + ",".join("%s=%s" % r for r in done))
        recs = [r for r in self._js.journal(fk.namespace()).read_from(1) if r.kind == "CANONICAL_ACCEPTED"]
        if not recs: return types.SimpleNamespace(accepted=None, admission=adm, stage="SEP_CALLER_NO_ACCEPTED_RECORD")
        return types.SimpleNamespace(accepted=recs[-1], admission=adm, stage="SEPARATED_ACCEPTED", matH=matH, rh=rh)
