"""E-04/E-06: worker roles, hard separations, idempotent job queue and queue-loss recovery from canonical history.
`PRINCIPAL_MAP` is DOCUMENTARY: a lookup of which write scope a service principal NAME is meant to hold (Build Plan E-06 text). It is not authentication, appoints nobody and no credential exists here.
The queue is non-canonical: losing it loses nothing, because `recover_pending` rebuilds the pending set from the canonical journal(s)."""
from dataclasses import dataclass
from ..errors import Refusal
WORKERS = ("composer-build-worker", "composer-refit-worker", "tracker-materializer-worker", "tracker-verifier-worker", "tracker-acceptance-worker", "context-worker", "gateway-resolution-worker", "health-evidence-worker", "scheduler-worker", "replay-worker")
PRINCIPALS = {"composer-builder": "CANDIDATE_ARTIFACT_WRITE", "composer-refitter": "CANDIDATE_ARTIFACT_WRITE", "tracker-materializer": "PENDING_CANDIDATE_WRITE", "tracker-verifier": "VERIFICATION_EVIDENCE_WRITE", "tracker-acceptor": "CANONICAL_TRANSITION_AND_HEAD_WRITE",
              "context-writer": "CONTEXT_WRITE", "gateway-writer": "BINDING_NON_DELIVERY_WRITE", "health-writer": "HEALTH_EVIDENCE_WRITE", "scheduler": "QUEUE_METADATA_ONLY", "replay-reader": "READ_CANONICAL_AND_WRITE_REPLAY_READ_MODEL"}
WORKER_PRINCIPAL = dict(zip(WORKERS, ("composer-builder", "composer-refitter", "tracker-materializer", "tracker-verifier", "tracker-acceptor", "context-writer", "gateway-writer", "health-writer", "scheduler", "replay-reader")))
PRINCIPAL_MAP = "DOCUMENTARY_NOT_AUTHENTICATION"
def check_separation(assignment: dict) -> None:
    """assignment: worker -> (os_process_id, principal). Refuses a merge of prohibited roles: materializer, verifier and acceptor must be three different OS processes AND principals; Gateway writer != materializer; Health writer != any feature publisher; composer workers never hold a Tracker role."""
    if set(assignment) != set(WORKERS): raise Refusal("workers", code="WORKER_SET_INCOMPLETE")
    for w, (pid, pr) in assignment.items():
        if pr not in PRINCIPALS: raise Refusal(pr, code="PRINCIPAL_UNKNOWN")
    trio = ("tracker-materializer-worker", "tracker-verifier-worker", "tracker-acceptance-worker")
    for grp in (trio, ("tracker-materializer-worker", "gateway-resolution-worker"), ("health-evidence-worker", "tracker-materializer-worker"), ("health-evidence-worker", "tracker-acceptance-worker")):
        pids = [assignment[w][0] for w in grp]; prs = [assignment[w][1] for w in grp]
        if len(set(pids)) != len(pids) or len(set(prs)) != len(prs): raise Refusal(",".join(grp), code="PROHIBITED_ROLE_MERGE")
    for w in ("composer-build-worker", "composer-refit-worker"):
        if assignment[w][1] in ("tracker-materializer", "tracker-verifier", "tracker-acceptor", "gateway-writer"): raise Refusal(w, code="COMPOSER_HOLDS_TRACKER_ROLE")
    for w, (pid, pr) in assignment.items():
        if pr != WORKER_PRINCIPAL[w]: raise Refusal(w, code="WORKER_PRINCIPAL_MISMATCH")
def may_write(principal: str, scope: str) -> bool:
    """Documentary least-privilege lookup (E-06): True only when `scope` is exactly the scope the principal name is documented to hold."""
    if principal not in PRINCIPALS: raise Refusal(principal, code="PRINCIPAL_UNKNOWN")
    return PRINCIPALS[principal] == scope
@dataclass(frozen=True)
class Job:
    job_id: str; kind: str; idempotency_key: str; governing_refs: tuple      # ((ref, hash), ...) exact governing refs/hashes; no job without them
class JobQueue:
    """Non-canonical in-memory queue. An identical job (same idempotency key AND same governing refs) is a no-op; the same key with different refs is refused (a different decision must not hide behind one key)."""
    def __init__(self): self._jobs = {}; self._done = set()
    def submit(self, job: Job):
        if not isinstance(job, Job) or not all(isinstance(x, str) and x for x in (job.job_id, job.kind, job.idempotency_key)) or not job.governing_refs or not all(isinstance(r, tuple) and len(r) == 2 and all(isinstance(x, str) and x for x in r) for r in job.governing_refs): raise Refusal("job", code="JOB_MALFORMED")
        old = self._jobs.get(job.idempotency_key)
        if old is not None:
            if old != job: raise Refusal(job.idempotency_key, code="JOB_IDEMPOTENCY_KEY_REUSED_DIFFERENTLY")
            return old
        self._jobs[job.idempotency_key] = job; return job
    def complete(self, idempotency_key):
        if idempotency_key not in self._jobs: raise Refusal(idempotency_key, code="JOB_UNKNOWN")
        self._done.add(idempotency_key)
    def pending(self): return tuple(j for k, j in sorted(self._jobs.items()) if k not in self._done)
def recover_pending(journals: dict, kind_of_next) -> tuple:
    """Queue-loss recovery from CANONICAL history: `journals` {namespace: journal}; `kind_of_next(last_record_kind)` -> the job kind that must follow (or None when nothing is owed), supplied by the caller (the order/status machine is not invented here).
    Returns Jobs whose idempotency key is derived from (namespace, last seq, last record hash), so recovering twice yields the SAME jobs, and an advanced journal yields none for the superseded state."""
    out = []
    for ns in sorted(journals):
        recs = journals[ns].read_from(1)
        if not recs: continue
        last = recs[-1]; k = kind_of_next(last.kind)
        if k is not None: out.append(Job("recovered:%s:%d" % (ns, last.seq), k, "%s|%d|%s" % (ns, last.seq, last.record_hash), ((ns, last.record_hash),)))
    return tuple(out)

CAPABILITIES = ("materialize", "verify", "accept", "gateway_write", "health_write", "publish_feature")
PROHIBITED_COMBOS = (frozenset({"materialize", "verify"}), frozenset({"materialize", "accept"}), frozenset({"verify", "accept"}), frozenset({"gateway_write", "materialize"}), frozenset({"health_write", "publish_feature"}), frozenset({"health_write", "accept"}), frozenset({"publish_feature", "gateway_write"}))
def check_identity_capabilities(permanent: dict, break_glass=(), now: int = 0) -> None:
    """R3 E06-L1 (live para 1090-1093): no human administrator, CI, deployment or bootstrap identity may PERMANENTLY hold a prohibited combination of runtime capabilities. `permanent`: identity -> set(capabilities).
    Break-glass grants are (identity, capability, expires_at, authorization_ref, log_ref): time-bounded (`now` < expires_at), explicitly authorized and logged; a break-glass grant may never confer `accept` or `publish_feature` (it cannot create acceptance/currentness/publication authority outside the normal path) and, combined with the permanent set, may not form a prohibited combination.
    The identities and capabilities are SUPPLIED; nothing here appoints anyone."""
    for ident, caps in permanent.items():
        caps = set(caps)
        if not caps <= set(CAPABILITIES): raise Refusal(ident, code="CAPABILITY_UNKNOWN")
        if any(c <= caps for c in PROHIBITED_COMBOS): raise Refusal(ident, code="PERMANENT_PROHIBITED_CAPABILITY_COMBINATION")
    for g in break_glass:
        if not (isinstance(g, tuple) and len(g) == 5): raise Refusal("grant", code="BREAK_GLASS_MALFORMED")
        ident, cap, exp, auth, log = g
        if cap not in CAPABILITIES or not isinstance(exp, int) or not all(isinstance(x, str) and x for x in (ident, auth, log)): raise Refusal("grant", code="BREAK_GLASS_MALFORMED")
        if exp <= now: raise Refusal(ident, code="BREAK_GLASS_EXPIRED")
        if cap in ("accept", "publish_feature"): raise Refusal(ident, code="BREAK_GLASS_CANNOT_CONFER_ACCEPTANCE_OR_PUBLICATION")
        if any(c <= (set(permanent.get(ident, ())) | {cap}) for c in PROHIBITED_COMBOS): raise Refusal(ident, code="BREAK_GLASS_FORMS_PROHIBITED_COMBINATION")
