"""Handlers run INSIDE worker child processes (tests only). Side effects go to files named by the job's governing ref (a test hook), never to a payload."""
import os
def _marker(job): return job.governing_refs[0][0]
def ok(job):
    with open(_marker(job) + ".done", "a") as f: f.write("%d\n" % os.getpid())
def die_once(job):
    m = _marker(job) + ".died"
    if not os.path.exists(m):
        open(m, "w").close(); os._exit(9)
    ok(job)
def always_fail(job): raise ValueError("boom")
def hang_once(job):
    import time
    m = _marker(job) + ".hung"
    if not os.path.exists(m): open(m, "w").close(); time.sleep(60)
    ok(job)
