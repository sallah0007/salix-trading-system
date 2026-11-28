"""R43 guard: every requirement id appears exactly once with exactly one valid status; every cited test file exists; remaining cells carry four parts unless '-'; the committed document equals the generator output."""
import io, os, re, unittest, contextlib, importlib.util
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
spec = importlib.util.spec_from_file_location("r43cr", os.path.join(ROOT, "tools/r43_clause_reconciliation.py")); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
def emitted():
    b = io.StringIO()
    with contextlib.redirect_stdout(b): M.main()
    return b.getvalue()
class Reconciliation(unittest.TestCase):
    def test_every_id_once_with_one_valid_status(self):
        ids = [r[0] for r in M.ROWS]
        want = ["B%02d" % i for i in range(1, 25)] + ["D%d" % i for i in range(1, 19)] + ["D12'", "A07-1", "A07-2", "A07-3", "A07-4"] + ["TR-%02d" % i for i in range(1, 16)]
        self.assertEqual(sorted(ids), sorted(want))
        for r in M.ROWS: self.assertIn(r[2], M.STATUS, r[0])
    def test_cited_tests_exist_and_remaining_has_four_parts(self):
        for r in M.ROWS:
            for t in re.findall(r"test_[a-z0-9_]+", r[4]): self.assertTrue(os.path.exists(os.path.join(ROOT, "tests/trk_stage_a", t + ".py")) or os.path.exists(os.path.join(ROOT, "tests", t + ".py")), (r[0], t))
            if not r[5].startswith("-"): self.assertEqual(r[5].count(" | "), 3, r[0])
    def test_d10_and_tr10_corrected_wording(self):
        d = {r[0]: r for r in M.ROWS}
        self.assertNotIn("single-process", d["D10"][3]); self.assertIn("NOT single process", d["D10"][3])
        self.assertIn("already MAPPED", d["TR-10"][3])
    def test_committed_document_is_generator_output(self):
        with open(os.path.join(ROOT, "docs/closeout/TRK-STAGE-A-R43-CLAUSE-RECONCILIATION.md")) as f: self.assertEqual(f.read(), emitted())
if __name__ == "__main__": unittest.main()
