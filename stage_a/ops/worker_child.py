"""R38: the CHILD side of the bounded test-process supervisor (`process_supervisor.py`). One OS process per worker role. It reads ONE job REFERENCE per stdin line (the exact wire form `runner.encode_job_ref` produces; any extra or missing field refuses), runs only handlers declared for its OWN worker, and answers one JSON line {job_id, result, code, pid}.
No payload, authority, status or Health claim can ride in a message: a message is ids + exact governing refs/hashes only. Handlers are importable `module:function` names supplied by the parent; nothing here appoints a principal or holds a credential. TEST/GENERIC process: no production deployment."""
import importlib, json, os, sys
from ..errors import Refusal
from .runner import decode_job_ref

def _reply(job_id, result, code=""):
    sys.stdout.write(json.dumps({"job_id": job_id, "result": result, "code": code, "pid": os.getpid()}, sort_keys=True, separators=(",", ":")) + "\n"); sys.stdout.flush()

def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    worker, handlers = argv[0], json.loads(argv[1])                     # handlers: {job kind: "module:function"} for THIS worker only
    if len(argv) > 2: sys.path[:0] = [p for p in argv[2:]]
    fns = {}
    for line in sys.stdin:
        line = line.rstrip("\n")
        try: job = decode_job_ref(line.encode("ascii", "strict"))
        except (Refusal, UnicodeEncodeError) as e: _reply("", "REFUSED", getattr(e, "code", "JOB_REF_MALFORMED")); continue
        spec = handlers.get(job.kind)
        if spec is None: _reply(job.job_id, "REFUSED", "KIND_NOT_OWNED_BY_WORKER"); continue
        try:
            if job.kind not in fns:
                mod, _, fn = spec.partition(":"); fns[job.kind] = getattr(importlib.import_module(mod), fn)
            fns[job.kind](job)
        except Exception as e: _reply(job.job_id, "ERROR", str(getattr(e, "code", type(e).__name__))); continue
        _reply(job.job_id, "DONE")

if __name__ == "__main__": main()
