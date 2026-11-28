"""R37: generic, NON-DEPLOYED worker runner over the E-04/E-06 job queue (Build Plan E-04 jobs carry job refs only; E-06 separation; E-08 JSON events). It supervises nothing: no OS process is started, no credential exists, no principal is appointed.
SUPPLIED: `slots` {worker: (os_process_id, principal)} - validated by `workers.check_separation` (the full ten-worker assignment must pass before any job runs); `handlers` {job kind: (worker, callable(job))}.
Semantics: a job runs only on the worker that owns its kind and only after the whole assignment passes separation; success => `complete`; an exception leaves the job PENDING (idempotent retry) up to `max_attempts`, after which it is DEAD-LETTERED and stays visible (never silently dropped, never completed). The wire form of a job is a JOB REFERENCE (ids + exact governing refs/hashes) - extra or missing fields refuse,
so no payload, authority, status or Health claim can ride in a message. Recovery is `workers.recover_pending` from canonical history; the runner never reads queue state as authority. Events go to the supplied non-authoritative sink."""
import json
from ..errors import Refusal
from . import workers as W
_JOB_FIELDS = ("job_id", "kind", "idempotency_key", "governing_refs")
def encode_job_ref(job) -> bytes:
    if not isinstance(job, W.Job): raise Refusal("job", code="JOB_REF_MALFORMED")
    return json.dumps({"job_id": job.job_id, "kind": job.kind, "idempotency_key": job.idempotency_key, "governing_refs": [list(r) for r in job.governing_refs]}, sort_keys=True, separators=(",", ":")).encode("ascii")
def decode_job_ref(b: bytes) -> W.Job:
    try: d = json.loads(b.decode("ascii"))
    except (ValueError, UnicodeDecodeError, AttributeError): raise Refusal("bytes", code="JOB_REF_MALFORMED")
    if not (isinstance(d, dict) and set(d) == set(_JOB_FIELDS) and isinstance(d["governing_refs"], list) and all(isinstance(r, list) and len(r) == 2 for r in d["governing_refs"])): raise Refusal("fields", code="JOB_REF_MALFORMED")
    j = W.Job(d["job_id"], d["kind"], d["idempotency_key"], tuple(tuple(r) for r in d["governing_refs"])); W.JobQueue().submit(j); return j      # same validation as submit
class WorkerRunner:
    def __init__(self, queue, slots, handlers, *, sink=None, max_attempts=3):
        W.check_separation(slots)
        if not (isinstance(handlers, dict) and handlers and all(isinstance(k, str) and isinstance(v, tuple) and len(v) == 2 and v[0] in W.WORKERS and callable(v[1]) for k, v in handlers.items())) or type(max_attempts) is not int or max_attempts < 1: raise Refusal("handlers", code="RUNNER_CONFIG_INVALID")
        self._q, self._slots, self._h, self._sink, self._max = queue, dict(slots), dict(handlers), sink, max_attempts; self._tries = {}; self.dead = {}
    def _emit(self, name, job, **f):
        if self._sink is None: return
        try: self._sink.emit(name, job_id=job.job_id, subject_id=job.idempotency_key, **f)
        except Exception: pass                                            # telemetry never changes a job outcome
    def run_one(self):
        """Run the first runnable pending job. Returns (idempotency_key, 'DONE'|'RETRY'|'DEAD'|'NO_HANDLER') or None when nothing is pending."""
        for job in self._q.pending():
            k = job.idempotency_key
            if k in self.dead: continue
            h = self._h.get(job.kind)
            if h is None: self._emit("JOB_NO_HANDLER", job, result="NO_HANDLER", reason_code=job.kind); continue
            worker, fn = h; self._emit("JOB_STARTED", job, service_role=worker)
            try: fn(job)
            except Exception as e:
                self._tries[k] = self._tries.get(k, 0) + 1; code = getattr(e, "code", type(e).__name__)
                if self._tries[k] >= self._max: self.dead[k] = (job, code); self._emit("JOB_DEAD_LETTERED", job, service_role=worker, result="DEAD", reason_code=str(code)); return k, "DEAD"
                self._emit("JOB_RETRY", job, service_role=worker, result="RETRY", reason_code=str(code)); return k, "RETRY"
            self._q.complete(k); self._emit("JOB_DONE", job, service_role=worker, result="DONE"); return k, "DONE"
        return None
    def run_until_idle(self, limit=1000):
        out = []
        for _ in range(limit):
            r = self.run_one()
            if r is None or r[1] == "NO_HANDLER": break
            out.append(r)
        return out
