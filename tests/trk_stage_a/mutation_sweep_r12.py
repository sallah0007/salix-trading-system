"""Mutants for R12 new code only (ceilings, SQE opset, status projection, blast radius, augmented check). Known EQUIVALENT (not mutated): dropping the _out() on the FIXED_DOT product, because a non-finite product always reaches acc+p which _out() then refuses with the same code. Run: python3 -B tests/trk_stage_a/mutation_sweep_r12.py"""
import subprocess, sys, pathlib, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
CE = "stage_a/composer/expression/ceilings.py"; SO = "stage_a/composer/expression/sqe_opset.py"; SP = "stage_a/tracker/status_projection.py"
BR = "stage_a/health/blast_radius.py"; ML = "stage_a/ml/receiver.py"; GW = "stage_a/gateway/contracts.py"
M = [(CE, 'if not isinstance(ref, str) or not ref.strip():', "if False:"), (CE, "        if k not in values:", "        if False:"),
     (CE, "or values[k] < 0:", "or False:"), (CE, "if not _int(values[k])", "if False"),
     (CE, 'if len(nodes) > ceilings["MAX_OPCODE_COUNT_PER_PROGRAM"]:', "if False:"),
     (CE, 'n["n"] > ceilings["MAX_REDUCTION_LENGTH"]', "False"),
     (CE, 'if decl.get("PROGRAM_CAPABILITY_CLASS") not in CAPABILITY_CLASSES:', "if False:"),
     (CE, "len(set(used)) != len(used)", "False"), (CE, "if sorted(used) != extract_opcodes(m):", "if False:"),
     (CE, 'if decl.get("RESOURCE_CEILING_REF") != ceiling_ref:', "if False:"),
     (SO, "return struct.pack(\">d\", _in(a)) == struct.pack(\">d\", _in(b))", "return _in(a) == _in(b) and False"),
     (SO, "    if type(cond) is not bool:", "    if False:"), (SO, "(then_thunk if cond else else_thunk)()", "(then_thunk if not cond else else_thunk)()"),
     (SO, "    acc = 0.0\n    for x, y in zip(a, b):", "    acc = 1.0\n    for x, y in zip(a, b):"),
     (SO, "acc = _out(acc + _in(x))", "acc = acc + _in(x)"), (SO, 'if any(len(v) != declared_length for v in vs):', "if False:"),
     (SO, 'if declared_length > ceilings["MAX_REDUCTION_LENGTH"]:', "if False:"), (SO, "if shape > ceilings[\"MAX_VECTOR_LENGTH\"]:", "if False:"),
     (SO, "if r > ceilings[\"MAX_MATRIX_ROWS\"]:", "if False:"), (SO, "if c > ceilings[\"MAX_MATRIX_COLS\"]:", "if False:"),
     (SO, "if 2 > ceilings[\"MAX_BRANCH_COUNT\"]:", "if False:"), (SO, "if b == 0.0: raise", "if False: raise"),
     (SP, "and self._built == self._j.head()", "and True"), (SP, "        if not self.authoritative:\n            raise", "        if False:\n            raise"),
     (SP, "if not isinstance(f, StatusFact):", "if False:"), (SP, "if f is None:", "if False:"),
     (SP, "self._auth, self._built, self._invalid = fresh, head, None", "self._auth, self._built, self._invalid = self._auth, head, None"),
     (GW, 'if not getattr(self.status, "authoritative", False) and not self.allow_uncommitted_status:', "if False:"),
     (BR, "if proven:", "if False:"), (BR, "        elif unread:", "        elif False:"), (BR, "        elif features_incomplete:", "        elif False:"),
     (BR, "if f not in affected:", "if True:"), (BR, "return impact.verdict == AFFECTED", "return impact.verdict != UNAFFECTED"),
     (BR, "if not isinstance(failed, bytes) or not failed:", "if False:"), (BR, "if d not in feature_deps and d != failed:", "if False:"),
     (ML, 'if m.kind != "ML":', "if False:"), (ML, "if m.derived_from is None:\n        raise Refusal(m.manifest_id, code=\"AUGMENTED_WITHOUT", "if False:\n        raise Refusal(m.manifest_id, code=\"AUGMENTED_WITHOUT"),
     (ML, 'if parent.kind != "FW":', "if False:"), (ML, 'not getattr(aug.gateway_rebind, "request_id", None)', "False")]
T = ["tests/trk_stage_a/test_r12_ceilings.py", "tests/trk_stage_a/test_r12_sqe_opset.py", "tests/trk_stage_a/test_r12_status_projection.py",
     "tests/trk_stage_a/test_r12_blast_radius.py", "tests/trk_stage_a/test_r12_ml_augmented.py"]
def run():
    try: return _run()
    except subprocess.TimeoutExpired: return 99          # a hanging mutant is killed by the timeout
def _run(): return subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-x", *[str(ROOT / t) for t in T]], cwd=ROOT, capture_output=True, text=True, timeout=60, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1")).returncode
def main():
    assert run() == 0; bad = []
    for rel, old, new in M:
        p = ROOT / rel; s = p.read_text()
        if s.count(old) != 1: print("NOT APPLICABLE", old[:60]); bad.append(old); continue
        try: p.write_text(s.replace(old, new)); k = run() != 0
        finally: p.write_text(s)
        print("killed  " if k else "SURVIVED", old[:70]); k or bad.append(old)
    print("mutants: %d, survived/unapplied: %d" % (len(M), len(bad))); assert run() == 0; return 1 if bad else 0
if __name__ == "__main__": sys.exit(main())
