"""The whole Tracker lifecycle, in the frozen order:
SAFE INTAKE -> ADMISSIBILITY -> FEATURE IDENTIFICATION -> CLASSIFICATION -> CERTIFICATION -> MATERIALIZATION ->
RECORDING VERIFICATION, then CANONICAL ACCEPTANCE (status transition). PUBLISHABLE is a later explicit call.

Authority: orders/claims are journal-verified (tracker_component.ClaimService). The acceptance step first EXERCISES
the claim (CLAIM_CONSUMED, compare-and-append on the claims journal re-verifying order validity at the commit
point) and then appends CANONICAL_ACCEPTED carrying that consumption record as its witness. A crash between the two
leaves a consumed claim with no acceptance; a retry of the same request completes it (idempotent)."""
from ..storage.authority_class import QUALIFIED, SIMULATION, authority_class_of
from ..storage.keys import accepted_materialization_key
from ..storage.byte_primitives import canonical_bytes
from dataclasses import dataclass, field
from typing import Optional, Any
from tracker_component.canonical import canonical_json
from tracker_component.journal_port import HeadMismatch
from tracker_component.claims import Refusal as ClaimRefusal
from tracker_component import report as R
from tracker_identity import safe_intake_built_identity, identity_lookup
from ..errors import Refusal, StaleFence, UnknownCommit, IntegrityFailure
from ..coordination import transition_record as T
from ..coordination.recovery import resolve_unknown_commit, COMMITTED
from ..replay import replay
from ..authority import AuthorityRef
from .terminal_identity import subject_terminal_resolution, UNRESOLVED
from .quant_intake_adapter import (admit, reserve_authority, build_safe_intake_report, build_candidate,
                                   QUANT_FEATURE, NO_QUANT_FEATURE, CLASSIFICATION_UNRESOLVED, FAILED_REQUESTED_BUILD, BuildPackage, DutyEvidence, unresolved_mandatory)
from ..composer.expression.canonical_encoding import encode_manifest
from .quant_certification import certify
from .materialization.stateful_materializer import StatefulMaterializer
from .verification.stateful_verifier import verify_materialization, probe_for
from .verification.verification_result import SCOPE_MATERIALIZATION

@dataclass
class BaselineBinding:
    store: Any
    era_boundary: Any
    search_policy: Any
    normalizer: Any

@dataclass
class Outcome:
    stage: str
    classification: str
    report: Optional[dict] = None
    admission: Any = None
    certification: Any = None
    materialization: Optional[dict] = None
    verification: Any = None
    accepted: Any = None           # JournalRecord of CANONICAL_ACCEPTED
    authority_ref: Optional[str] = None
    failures: list = field(default_factory=list)
    duty_evidence: Optional[object] = None
    simulation: bool = False
    terminal_identities: tuple = ()      # typed, subject-bound TerminalIdentity results (report-only); NOT in the intake report: CANONICAL_SURVIVOR stays None

    @property
    def limits(self):
        """Duties the Tracker could not determine for this outcome (class-to-structure capability compatibility; full s28 conformance). Acceptance does not certify them."""
        done = self.duty_evidence.duties if (self.simulation and isinstance(self.duty_evidence, DutyEvidence)) else frozenset()
        extra = (("SIMULATION_NOT_QUALIFIED", "DUTY_EVIDENCE_IS_SIMULATED:" + self.duty_evidence.evidence_ref),) if (self.simulation and self.accepted is not None) else ()
        if self.terminal_identities:
            extra += (("CANONICAL_SURVIVOR_REPORT_SLOT", "UNBOUND_NO_ACCEPTED_REPORT_ENCODING_FOR_TERMINAL_IDENTITY_NOT_CONNECTED_TO_REPORT"),)
        if self.classification == NO_QUANT_FEATURE:
            extra += (("NO_QUANT_CLASSIFICATION", "CALLER_FLAG_NOT_SOURCE_VERIFIED_NO_SOURCE_OWNED_MAPPING"),)
        return tuple(u for u in getattr(self.admission, "unverified", ()) if u[0] not in done) + extra

    @property
    def accepted_ok(self):
        return self.accepted is not None

class TrackerPipeline:
    def __init__(self, *, store, claims, journals, clock, events, accepted_fit_generations=None, baseline=None, conformance_source=None, duty_source=None, simulation=False, producer_authority=None):
        self._store, self._claims, self._journals = store, claims, journals
        self._clock, self._events = clock, events
        self._fits = dict(accepted_fit_generations or {})
        self._baseline = baseline
        self._conformance_source = conformance_source
        self._producer_authority = producer_authority        # SUPPLIED source-owned seven-field authority (None => the duty is labelled unverified, not invented)
        # AUTHORITY-CLASS BOUNDARY: the caller's simulation flag cannot choose where records land. Simulation needs a SIMULATION store/journals/claims; a qualified run needs QUALIFIED ones,
        # so a simulated acceptance can never be written into an ordinary namespace and the distinction survives restart/replay/rebuild/publication (it is a property of the store).
        want = SIMULATION if simulation else QUALIFIED
        for nm, obj in (("store", store), ("journals", journals), ("claims", claims)):
            if authority_class_of(obj) != want:
                raise Refusal("%s is %s but pipeline simulation=%s" % (nm, authority_class_of(obj), bool(simulation)), code="AUTHORITY_CLASS_MISMATCH")
        self._simulation = bool(simulation)                  # explicit SIMULATION only: DutyEvidence may stand in and the baseline may be absent; such outcomes are never qualified
        self._duty_source = duty_source                      # Tracker-originated DutyEvidence provider; None (the only real state today) holds every mandatory duty
        self._mat = StatefulMaterializer(store)

    # ------------------------------------------------------------------ helpers
    def _reject(self, pkg, adm, stage, claim_id=None, extra=None):
        for item in (extra or []):
            adm.failed.append(item)
        adm.classification = FAILED_REQUESTED_BUILD
        if claim_id:
            try:
                self._claims.release(claim_id, "INTAKE_FAILED:" + stage)
            except ClaimRefusal:
                pass
        dup = any(d == "DUPLICATE" for d, _ in adm.failed)
        near = getattr(pkg.lookup_outcome, "value", pkg.lookup_outcome) == "NEAR_MATCH"
        if dup and len(adm.failed) == 1:
            verdict, decision = ("REVIEW_REQUIRED", "REVIEW_REQUIRED") if near else ("REUSE_EXISTING", "REUSE_EXISTING_CANONICAL_FEATURE")
        else:
            verdict, decision = "REJECT_FAIL_CLOSED", "REJECTED_INVALID"
        report = build_safe_intake_report(pkg, adm, clock=self._clock, verdict=verdict, identity_decision=decision,
                                          registry_ref=None)
        self._events.emit("INTAKE_REJECTED", stage=stage, attempt=pkg.attempt_id, failed=list(adm.failed))
        return Outcome(stage, FAILED_REQUESTED_BUILD, report=report, admission=adm, failures=list(adm.failed))

    def _release(self, claim_id, why):
        try:
            self._claims.release(claim_id, why)
        except ClaimRefusal:
            pass

    # -------------------------------------------------------------------- run
    def run(self, pkg: BuildPackage) -> Outcome:
        self._events.emit("INTAKE_STARTED", attempt=pkg.attempt_id, request=pkg.request_id)
        adm = admit(pkg, accepted_fit_generations=self._fits, conformance=None if self._conformance_source is None else self._conformance_source(pkg), producer_authority=self._producer_authority)
        if adm.classification == NO_QUANT_FEATURE:
            lineage = self._claims.lineage(pkg.order_id, pkg.request_id)
            if lineage:                                       # a caller flag cannot erase governed requested-build lineage (TR-06 / D8): fail closed
                adm.classification = FAILED_REQUESTED_BUILD
                return self._reject(pkg, adm, "CLASSIFICATION", None, [("CLASSIFICATION", "NO_QUANT_FLAG_CONTRADICTS_GOVERNED_LINEAGE:" + ",".join(lineage))])
            if not self._simulation:
                # QUALIFIED route: the three-way DIRECT_TRACKER / COMPOSER_BUILT_QUANT / NO_QUANT router sits at Tracker<->Composer (Build Plan para 1256) and its source-owned mapping from the governed
                # request to a classification is NOT bound here. An empty ClaimService.lineage() is absence in THIS journal, not proof that the governed request asked for no feature (unknown or
                # unbound order/request ids give the same empty answer). Unknown source identity is therefore HELD/UNRESOLVED, never interpreted as NO_QUANT_FEATURE. A genuine no-quant positive
                # exists only in explicit simulation until a verified Tracker classification source is supplied by its owner.
                self._events.emit("CLASSIFICATION_UNRESOLVED_HELD", attempt=pkg.attempt_id)
                return Outcome("CLASSIFICATION", CLASSIFICATION_UNRESOLVED, admission=adm,
                               failures=[("CLASSIFICATION", "NO_QUANT_NOT_VERIFIED_NO_SOURCE_OWNED_REQUEST_CLASSIFICATION_MAPPING")])
            self._events.emit("NO_QUANT_FEATURE", attempt=pkg.attempt_id)
            return Outcome("CLASSIFICATION", NO_QUANT_FEATURE, admission=adm, simulation=self._simulation)
        if not adm.admissible:
            return self._reject(pkg, adm, "ADMISSIBILITY")
        duty_ev = None if self._duty_source is None else self._duty_source(pkg, adm)
        held = unresolved_mandatory(adm, duty_ev, simulation=self._simulation, baseline_connected=self._baseline is not None)
        if held:                                              # Parent capability-class/structure firewall + governed-before-build binding: held BEFORE claim, certify, materialize, accept
            o = self._reject(pkg, adm, "MANDATORY_VERIFICATION_HELD", None, held)
            o.duty_evidence = duty_ev if isinstance(duty_ev, DutyEvidence) else None
            return o
        claim = reserve_authority(self._claims, pkg, adm)
        if claim is None:
            return self._reject(pkg, adm, "ADMISSIBILITY")
        claim_id = claim["claim_id"]
        fk, manifest = adm.feature_key, adm.manifest

        probe = probe_for(encode_manifest(manifest))      # verifier-authored probe, derived from the stored bytes
        cert = certify(manifest, probe)
        if cert.status != "CERTIFIED":
            o = self._reject(pkg, adm, "CERTIFICATION", claim_id, [("CERTIFICATION", r) for r in cert.reasons])
            o.certification = cert
            return o

        try:
            rec = self._mat.materialize(manifest, probe)
        except (Refusal, IntegrityFailure) as e:
            return self._reject(pkg, adm, "MATERIALIZATION", claim_id, [("MATERIALIZATION", e.code)])

        ver = verify_materialization(
            store_get=lambda k: (lambda g: None if g is None else g[0])(self._store.get(k)), record=rec,
            declared={"manifest_hash": pkg.declared_manifest_hash, "graph_hash": pkg.declared_graph_hash,
                      "program_hash": pkg.declared_program_hash},
            expect_scope_key=fk.key())
        if ver.status != "PASS":
            o = self._reject(pkg, adm, "RECORDING_VERIFICATION", claim_id,
                             [("INDEPENDENT_VERIFICATION", r) for r in ver.reasons])
            o.certification, o.materialization, o.verification = cert, rec, ver
            return o

        if self._baseline is not None:
            problems, terminals = self._register_baseline(pkg, adm, ver)
            if problems:
                o = self._reject(pkg, adm, "BASELINE_REGISTRATION", claim_id, [("BASELINE_REGISTRATION", p) for p in problems])
                o.certification, o.materialization, o.verification = cert, rec, ver
                o.terminal_identities = terminals
                return o

        report = build_safe_intake_report(pkg, adm, clock=self._clock, verdict="ACCEPT_FOR_REGISTRY",
                                          identity_decision="NEW_CANONICAL_FEATURE", registry_ref="PROPOSED:" + fk.key())
        try:
            accepted = self._accept(pkg, adm, cert, rec, ver, report)
        except ClaimRefusal as e:
            # authority was withdrawn/expired before it could be exercised: nothing was accepted
            self._events.emit("ACCEPTANCE_REFUSED", code=e.code, attempt=pkg.attempt_id)
            self._release(claim_id, "AUTHORITY_REFUSED:" + e.code)
            raise Refusal(str(e), code=e.code)
        except (Refusal, StaleFence) as e:
            code = getattr(e, "code", "ACCEPTANCE_REFUSED")
            self._events.emit("ACCEPTANCE_REFUSED", code=code, attempt=pkg.attempt_id)
            if code in ("VERSION_CONFLICT", "ILLEGAL_TRANSITION"):
                self._release(claim_id, "ACCEPTANCE_REFUSED:" + code)
            raise
        ref = AuthorityRef(fk.namespace(), accepted.seq, accepted.record_hash).to_str()
        self._events.emit("CANONICAL_ACCEPTED", attempt=pkg.attempt_id, authority=ref)
        return Outcome("CANONICAL_ACCEPTANCE", QUANT_FEATURE, report=report, admission=adm, certification=cert,
                       materialization=rec, verification=ver, accepted=accepted, authority_ref=ref, duty_evidence=duty_ev, simulation=self._simulation)

    # ------------------------------------------------------------ baseline step
    def _register_baseline(self, pkg, adm, ver):
        b = self._baseline
        subject = {"subject_mode": "PRE_ID", "feature_id": "", "feature_version": "", "definition_hash": "",
                     "graph_hash": "", "instrument": adm.definition.instrument, "timeframe": adm.definition.timeframe,
                     "lookup_era_scope": "ERA_1_ONLY", "candidate_content": adm.definition.declared_content()}
        lk = identity_lookup(store=b.store, subject=subject, request_id=pkg.request_id, search_policy=b.search_policy, normalizer=b.normalizer)
        if lk.absent_claim_token is None:
            # fail closed exactly as before; the terminal identity AND state of any noncurrent match are REPORTED (never authority: no claim, no resurrection, no substitution)
            tr = subject_terminal_resolution(subject, b.store.all(), b.normalizer, active_era_id=b.store.active_era_id, searched_scopes=tuple(b.search_policy.searched_scopes))
            extra = ["TERMINAL_IDENTITY_UNRESOLVED:" + tr.reason] if tr.status == UNRESOLVED else []
            return (list(lk.errors) or ["BASELINE_LOOKUP_NO_CLAIM"]) + extra, tr.identities
        cand = build_candidate(pkg, adm.definition, claim_request_id=pkg.request_id,
                               creation_evidence_ref="verification:" + ver.result_hash)
        res = safe_intake_built_identity(target_store=b.store, candidate=cand, era_boundary=b.era_boundary,
                                         search_policy=b.search_policy, normalizer=b.normalizer)
        return ([] if res.accepted else list(res.errors)), ()

    # --------------------------------------------------------------- acceptance
    def _accept(self, pkg, adm, cert, rec, ver, report):
        fk = adm.feature_key
        ns, version = fk.namespace(), fk.feature_version
        j = self._journals.journal(ns)
        claim_id = "CLAIM:" + pkg.request_id
        for _ in range(3):
            if not j.epoch_is_current():          # check the fence BEFORE exercising one-shot authority
                raise StaleFence("fence lost before acceptance")
            states = replay(ns, j.read_from(1))
            st = states.get(version)
            if st is not None:
                if st.accepted_body["manifest_hash"] == rec["manifest_hash"]:
                    return _RecordView(st.accepted_seq, st.accepted_hash)       # idempotent replay
                raise Refusal("%s already accepted with a different manifest" % fk.key(), code="VERSION_CONFLICT")
            c = self._claims.claim(claim_id)
            if c is None:
                raise Refusal(claim_id, code="NO_CLAIM_AT_ACCEPTANCE")
            if c["state"] == "BOUND":
                self._claims.consume(claim_id, fk.key())
            witness = self._claims.consumed_record(claim_id)
            if witness is None or witness.body().get("identity_ref") != fk.key():
                raise Refusal("claim not consumed for this feature", code="CLAIM_WITNESS_MISSING")
            body = {"feature_key": fk.key(), "feature_version": version, "manifest_hash": rec["manifest_hash"],
                    "graph_hash": rec["graph_hash"], "program_hash": rec["program_hash"], "attempt_id": pkg.attempt_id,
                    "verification_hash": ver.result_hash, "certification_hash": cert.cert_hash,
                    "claim_witness": "claims#%d:%s" % (witness.seq, witness.record_hash),
                    "safe_intake_report_hash": report["FINAL_REPORT_HASH"], "materialization_hash": rec["materialization_hash"]}
            mk = accepted_materialization_key(rec["materialization_hash"]); mb = canonical_bytes(rec)       # the exact verified record is persisted BEFORE the acceptance names it (content-addressed, never overwritten)
            if not self._store.put_if_absent(mk, mb):
                g = self._store.get(mk)
                if g is None or g[0] != mb: raise IntegrityFailure("accepted materialization key %s holds different bytes" % mk)
            T.validate_body(T.CANONICAL_ACCEPTED, body)
            T.check_transition(None, T.CANONICAL_ACCEPTED)
            head = j.head()
            if not j.epoch_is_current():
                raise StaleFence("fence lost before acceptance commit")
            try:
                return j.append(head, T.CANONICAL_ACCEPTED, body)
            except HeadMismatch:
                continue
            except UnknownCommit:
                if resolve_unknown_commit(j, kind=T.CANONICAL_ACCEPTED, body_json=canonical_json(body)) == COMMITTED:
                    for r in j.read_from(1):
                        if r.kind == T.CANONICAL_ACCEPTED and r.body_json == canonical_json(body):
                            return r
                continue
        raise Refusal("head race exhausted", code="FENCE_RACE_EXHAUSTED")

@dataclass(frozen=True)
class _RecordView:
    seq: int
    record_hash: str
