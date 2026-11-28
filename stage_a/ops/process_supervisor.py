"""R38: a generic, BOUNDED, TEST-ONLY process supervisor for the E-04/E-06 worker roles (Build Plan E-04: jobs carry references only; E-06: materializer/verifier/acceptor etc. are separate OS processes; E-08 events). It replaces the inline `WorkerRunner` handler call and the caller-supplied pid slots with REAL evidence:
  * one `subprocess.Popen` child per worker role, so the pids fed to `workers.check_separation` are the actual OS pids (not asserted); a child's own reply carries `os.getpid()` and the parent refuses a reply whose pid is not the spawned pid;
  * ref-only IPC: the parent writes exactly `runner.encode_job_ref(job)` (ids + governing refs/hashes) per line; the child re-validates with `decode_job_ref`; the reply is {job_id, result, code, pid}: a reply is never authority, only the supervisor's `complete()` after a DONE reply with the matching job id/pid;
  * bounded: per-job reply timeout (a hung child is killed), `max_attempts` per idempotency key (then DEAD-LETTERED, still visible), a bounded respawn count;
  * recovery: a child that dies or hangs mid-job leaves the job PENDING; the supervisor respawns that worker (NEW pid, re-checked for separation) and retries; after queue loss `workers.recover_pending` rebuilds the pending set from canonical history and a fresh supervisor runs it.
NOT a deployment: no production principal, credential, host, container or scheduler is created or claimed; principals are the DOCUMENTARY `workers.WORKER_PRINCIPAL` names. Handlers are caller-supplied `module:function` names. A passing test here is not an E04 acceptance."""
import json, math, os, select, subprocess, sys, time
from ..errors import Refusal
from . import workers as W
from .runner import encode_job_ref
_BOOT = "import sys; sys.path[:0] = [sys.argv[1]]; from stage_a.ops.worker_child import main; main(sys.argv[2:])"
MAX_FRAME_BYTES = 1 << 16          # R39: one reply frame is one short JSON line; a larger one is oversized => the child is killed/replaced
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
class ProcessSupervisor:
    def __init__(self, queue, handlers, *, sink=None, max_attempts=3, reply_timeout=10.0, max_respawns=6, extra_paths=()):
        """handlers: {job kind: (worker, "module:function")}. Every worker role in W.WORKERS is started (one process each) so the full separation can be checked on real pids."""
        if not (isinstance(handlers, dict) and handlers and all(isinstance(k, str) and isinstance(v, tuple) and len(v) == 2 and v[0] in W.WORKERS and isinstance(v[1], str) and v[1].count(":") == 1 for k, v in handlers.items())) or type(max_attempts) is not int or max_attempts < 1 or not (type(reply_timeout) in (int, float) and math.isfinite(reply_timeout) and reply_timeout > 0) or type(max_respawns) is not int or max_respawns < 0:
            raise Refusal("handlers", code="SUPERVISOR_CONFIG_INVALID")
        self._q, self._h, self._sink, self._max, self._to, self._maxresp, self._paths = queue, dict(handlers), sink, max_attempts, float(reply_timeout), max_respawns, tuple(extra_paths)
        self._procs = {}; self._tries = {}; self.dead = {}; self.respawns = 0; self.pid_history = {w: [] for w in W.WORKERS}
        try:
            for w in W.WORKERS: self._spawn(w)
            self._check()
        except BaseException: self.close(); raise
    def _spawn(self, w):
        mine = {k: v[1] for k, v in self._h.items() if v[0] == w}
        p = subprocess.Popen([sys.executable, "-I", "-c", _BOOT, _ROOT, w, json.dumps(mine, sort_keys=True)] + list(self._paths), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0, cwd="/")
        self._procs[w] = p; self.pid_history[w].append(p.pid)
    def pids(self): return {w: p.pid for w, p in self._procs.items()}
    def slots(self): return {w: (p.pid, W.WORKER_PRINCIPAL[w]) for w, p in self._procs.items() if p.poll() is None}
    def _check(self): W.check_separation(self.slots())              # REAL spawned pids; a dead worker makes the set incomplete => refuse
    def _emit(self, name, job, **f):
        if self._sink is None: return
        try: self._sink.emit(name, job_id=job.job_id, subject_id=job.idempotency_key, **f)
        except Exception: pass
    def _ask(self, w, job):
        """One job over ref-only IPC. Returns (result, code) or ('LOST', reason) when the child died/hung/lied (the worker is then replaced)."""
        p = self._procs[w]
        try: p.stdin.write(encode_job_ref(job) + b"\n"); p.stdin.flush()
        except (BrokenPipeError, OSError, ValueError): return "LOST", "CHILD_PIPE_BROKEN"
        deadline = time.monotonic() + self._to; buf = b""; fd = p.stdout.fileno()         # R39: ONE bounded whole-FRAME deadline with non-blocking accumulation (never a blocking readline after a partial byte)
        while b"\n" not in buf:
            left = deadline - time.monotonic()
            if left <= 0: p.kill(); p.wait(); return "LOST", "CHILD_REPLY_TIMEOUT"
            r, _, _ = select.select([fd], [], [], left)
            if not r: continue
            try: chunk = os.read(fd, 4096)
            except OSError: chunk = b""
            if not chunk: p.wait(); return "LOST", "CHILD_EXITED"
            buf += chunk
            if len(buf) > MAX_FRAME_BYTES and b"\n" not in buf[:MAX_FRAME_BYTES]: p.kill(); p.wait(); return "LOST", "CHILD_REPLY_OVERSIZED"
        line, rest = buf.split(b"\n", 1)
        if rest or len(line) > MAX_FRAME_BYTES: p.kill(); p.wait(); return "LOST", "CHILD_REPLY_MALFORMED"
        try: d = json.loads(line.decode("utf-8"))
        except ValueError: return "LOST", "CHILD_REPLY_MALFORMED"
        if not (isinstance(d, dict) and set(d) == {"job_id", "result", "code", "pid"}) or d["pid"] != p.pid or d["job_id"] != job.job_id: return "LOST", "CHILD_REPLY_NOT_FROM_SPAWNED_PID_OR_JOB"
        return d["result"], d["code"]
    @staticmethod
    def _close_streams(p):
        for f in (p.stdin, p.stdout):
            try:
                if f: f.close()
            except Exception: pass
    def _replace(self, w):
        old = self._procs[w]
        if old.poll() is None: old.kill()
        old.wait(); self._close_streams(old)
        if self.respawns >= self._maxresp: raise Refusal(w, code="SUPERVISOR_RESPAWN_BOUND_EXCEEDED")
        self.respawns += 1; self._spawn(w); self._check()
    def run_one(self):
        for job in self._q.pending():
            k = job.idempotency_key
            if k in self.dead: continue
            h = self._h.get(job.kind)
            if h is None: self._emit("JOB_NO_HANDLER", job, result="NO_HANDLER", reason_code=job.kind); continue
            w = h[0]; self._emit("JOB_STARTED", job, service_role=w)
            if self._procs[w].poll() is not None: self._replace(w)
            res, code = self._ask(w, job)
            if res == "DONE": self._q.complete(k); self._emit("JOB_DONE", job, service_role=w, result="DONE"); return k, "DONE"
            if res == "LOST": self._replace(w)
            self._tries[k] = self._tries.get(k, 0) + 1
            if self._tries[k] >= self._max: self.dead[k] = (job, code); self._emit("JOB_DEAD_LETTERED", job, service_role=w, result="DEAD", reason_code=str(code)); return k, "DEAD"
            self._emit("JOB_RETRY", job, service_role=w, result="RETRY", reason_code=str(code)); return k, "RETRY"
        return None
    def run_until_idle(self, limit=1000):
        out = []
        for _ in range(limit):
            r = self.run_one()
            if r is None: break
            out.append(r)
        return out
    def close(self):
        for p in self._procs.values():
            try:
                if p.stdin: p.stdin.close()
            except Exception: pass
            try: p.wait(timeout=2)
            except Exception: p.kill(); p.wait()
            self._close_streams(p)
    def __enter__(self): return self
    def __exit__(self, *a): self.close()
