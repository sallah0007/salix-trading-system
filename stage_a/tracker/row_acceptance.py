"""R53 per-ROW typed acceptance bridge (CANDIDATE). Granularity: ONE accepted transition per committed PendingRow (Typed Annex CANONICAL_TRANSITION), distinct from the feature-VERSION
acceptance in tracker/pipeline. Authority stays with the journal: the typed transition is recorded as the body of a journal record in a ROW namespace and becomes accepted only when the
conditional HEAD CAS succeeds (Build Plan E01-M1; here HEAD installs the journal record hash, and the typed transition hash is carried in the body and recomputed by two encoders).
SUPPLIED, never defaulted: attempt-time port (coordination/attempt_time; a fresh time per CAS attempt; AVAILABLE_ASOF == CANONICAL_ACCEPTED_AT), commit-point id port (derivation rule is
not defined by any source read: unbound = HELD), the verification-evidence ref, currentness state and status event symbols (checked against the supplied code tables).
NOT claimed: qualified clock, normative commit-point id, byte admission (D13), gate/hold clearance. Legacy feature-VERSION journals and probe path are untouched."""
import copy, json
from ..errors import Refusal, UnknownCommit, IntegrityFailure, StaleFence
from ..coordination import attempt_time as AT
from tracker_component.journal_port import HeadMismatch
from tracker_component.canonical import canonical_json
from ..schema import objects as O, independent as X
from .materialization.row_store import _xref, _ref_j
from .verification.verification_result import issued_by_verifier_run, PASS
from .verification.row_step_verifier import SCOPE_ROW_STEP

KIND = "ROW_ACCEPTED"
VERSION_TAG = "ROW_TRANSITION_CANDIDATE_V1"

def row_namespace(row):
    return "rowtx/%s/%s/%s/%s" % (row.feature_id.hex(), row.instrument_id.hex(), row.timeframe_id.hex(), row.materialization_version.encode("utf-8").hex())

def transition_independent_dict(t, c):
    return {"row_content_hash": c.row_content_hash, "verification_evidence_ref": _xref(t, c.verification_evidence_ref), "sifp_fencing_epoch": c.sifp_fencing_epoch,
            "canonical_commit_point_id": c.canonical_commit_point_id, "canonical_accepted_at": c.canonical_accepted_at, "available_asof": c.available_asof,
            "gate_dependency_transition_ref": None if c.gate_dependency_transition_ref is None else _xref(t, c.gate_dependency_transition_ref),
            "currentness_state_at_acceptance": t.enums["CURRENTNESS_STATE"][c.currentness_state_at_acceptance], "status_event": t.enums["TRANSITION_STATUS_EVENT"][c.status_event]}

class RowAcceptor:
    def __init__(self, journals, rows, tables, time_port, commit_point_port):
        AT.port_ok(time_port)
        if commit_point_port is None: raise Refusal("commit-point id port", code="COMMIT_POINT_RULE_NOT_SUPPLIED_HELD")
        if not callable(getattr(commit_point_port, "derive", None)): raise Refusal("commit-point id port", code="COMMIT_POINT_PORT_INVALID")
        self._j, self._rows, self._t, self._time, self._cp = journals, rows, copy.deepcopy(tables), time_port, commit_point_port

    @staticmethod
    def _accepted_rows(records):
        out = {}
        for r in records:
            if r.kind != KIND: raise Refusal(r.kind, code="ROW_NAMESPACE_FOREIGN_KIND")
            b = json.loads(r.body_json); out[b["row_content_hash"]] = r
        return out

    @staticmethod
    def _bind_evidence(row_hash, res, ref):
        """The accepted transition is bound to the ACTUAL independent row-step verification of THIS row: a typed PASS of scope ROW_STEP issued by an actual verifier run (in-process receipt, not a security boundary) whose subject names this row, and an
        evidence ref whose hash IS that result's hash. A byte-hash match alone, another row's result, another scope, or a ref not naming the result is refused."""
        if not issued_by_verifier_run(res): raise Refusal("verification result", code="ROW_VERIFICATION_NOT_ISSUED_BY_A_VERIFIER_RUN")
        res.require_pass(SCOPE_ROW_STEP)
        if res.status != PASS or dict(res.subject).get("row_content_hash") != row_hash: raise Refusal(row_hash, code="ROW_VERIFICATION_NOT_FOR_THIS_ROW")
        if ref is None or ref.target_hash != bytes.fromhex(res.result_hash): raise Refusal("evidence ref", code="EVIDENCE_REF_DOES_NOT_NAME_THE_VERIFICATION")

    def accept(self, row_hash, *, verification_result, verification_evidence_ref, currentness_state, status_event, gate_dependency_transition_ref=None):
        row = self._rows.load(row_hash)                                         # committed, re-verified row only
        self._bind_evidence(row_hash, verification_result, verification_evidence_ref)
        j = self._j.journal(row_namespace(row)); seen = set()
        for _ in range(3):
            if not j.epoch_is_current(): raise StaleFence("fence lost before row acceptance")
            basis = j.head(); acc = self._accepted_rows([r for r in j.read_from(1) if r.seq <= basis.seq])
            if row_hash in acc: return acc[row_hash]                              # idempotent replay: the SAME record, no new time
            if row.predecessor_row_hash is not None and row.predecessor_row_hash.hex() not in acc: raise Refusal(row_hash, code="PREDECESSOR_ROW_NOT_ACCEPTED")
            cp = self._cp.derive(row_hash)
            if type(cp) is not bytes or len(cp) != 16: raise Refusal("commit-point id", code="COMMIT_POINT_ID_INVALID")
            t = AT.mint_fresh(self._time, seen)
            c = O.CanonicalTransition(bytes.fromhex(row_hash), verification_evidence_ref, j.epoch, cp, t, t, gate_dependency_transition_ref, currentness_state, status_event)
            th = O.transition_hash(self._t, c)
            if X.transition_hash(transition_independent_dict(self._t, c), self._t.enums) != th: raise IntegrityFailure("independent transition hash disagrees with producer")
            body = {"version": VERSION_TAG, "row_content_hash": row_hash, "transition_hash": th.hex(), "verification_evidence_ref": _ref_j(verification_evidence_ref),
                    "sifp_fencing_epoch": j.epoch, "canonical_commit_point_id": cp.hex(), AT.TIME_KEY: t, "available_asof": t,
                    "gate_dependency_transition_ref": _ref_j(gate_dependency_transition_ref), "currentness_state_at_acceptance": currentness_state, "status_event": status_event}
            if not j.epoch_is_current(): raise StaleFence("fence lost before row acceptance commit")
            try:
                return j.append(basis, KIND, body)
            except HeadMismatch:
                continue
            except UnknownCommit:
                r = AT.find_attempt(j, basis, KIND, canonical_json(body))
                if r is not None: return r
                continue
        raise Refusal(row_hash, code="ROW_ACCEPTANCE_RACE_EXHAUSTED")
