"""R42 item D guard: the generated clause-level table covers EVERY requirement id, every cited test file exists, every unresolved row names input | ROLE | consequence | recommendation, and the committed document equals what the generator emits (no stale table)."""
import io, os, re, subprocess, sys, unittest, contextlib, importlib.util
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
spec = importlib.util.spec_from_file_location("r42cs", os.path.join(ROOT, "tools/r42_clause_status.py")); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
def emitted():
    b = io.StringIO()
    with contextlib.redirect_stdout(b): M.main()
    return b.getvalue()
class ClauseStatus(unittest.TestCase):
    def test_every_requirement_id_is_present_exactly_once(self):
        ids = [r[0] for r in M.ROWS] + list(M.TR); want = ["B%02d" % i for i in range(1, 25)] + ["D%d" % i for i in range(1, 19)] + ["D12'", "A07-1", "A07-2", "A07-3", "A07-4"] + ["TR-%02d" % i for i in range(1, 16)]
        self.assertEqual(sorted(ids), sorted(want)); self.assertEqual(len(ids), len(set(ids)))
    def test_every_cited_test_exists_and_unresolved_rows_name_the_four_parts(self):
        for r in M.ROWS:
            for t in re.findall(r"test_[a-z0-9_]+", r[4]): self.assertTrue(any(os.path.exists(os.path.join(ROOT, d, t + ".py")) for d in ("tests/trk_stage_a", "tests")), (r[0], t))
            if r[6] != "-" and not r[6].startswith("-"): self.assertEqual(r[6].count(" | "), 3, r[0])
        for t, v in M.TRROWS.items():
            for x in re.findall(r"test_[a-z0-9_]+", v[2]): self.assertTrue(any(os.path.exists(os.path.join(ROOT, d, x + ".py")) for d in ("tests/trk_stage_a", "tests")), (t, x))
    def test_the_committed_document_is_the_generator_output(self):
        with open(os.path.join(ROOT, "docs/closeout/TRK-STAGE-A-R42-CLAUSE-STATUS.md")) as f: self.assertEqual(f.read(), emitted())
if __name__ == "__main__": unittest.main()
