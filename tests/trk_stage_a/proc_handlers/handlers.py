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
def partial_frame_hang(job):
    import sys, time                                                   # R39 fault: a partial frame (no newline) then a long stall
    sys.stdout.write("{"); sys.stdout.flush(); time.sleep(8)
def oversized_frame(job):
    import sys, time
    sys.stdout.write("x" * (1 << 17)); sys.stdout.flush(); time.sleep(8)    # no newline, > MAX_FRAME_BYTES
def malformed_complete_line(job):
    import sys
    sys.stdout.write("this is not json\n"); sys.stdout.flush()
def two_frames_one_flush(job):
    import sys
    sys.stdout.write('{"a":1}\n{"b":2}\n'); sys.stdout.flush()
