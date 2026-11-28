"""R54: the manual audit table is regenerated from tools/r54_manual_audit.py (transcription equality ONLY), covers all 62 reconciliation rows with a hand verdict, every cited test file exists, and every MR row carries a review question or an explicit none."""
import pathlib, subprocess, sys, unittest
ROOT = pathlib.Path(__file__).resolve().parents[2]
def gen(tool): return subprocess.run([sys.executable, str(ROOT / "tools" / tool)], capture_output=True, text=True, check=True, cwd=ROOT).stdout
class ManualAudit(unittest.TestCase):
    def test_tables_equal_their_generators(self):
        for tool, doc in (("r54_manual_audit.py", "TRK-STAGE-A-R54-MANUAL-AUDIT.md"), ("r54_row_audit.py", "TRK-STAGE-A-R54-ROW-AUDIT.md")): self.assertEqual(gen(tool), (ROOT / "docs/closeout" / doc).read_text(), tool)
    def test_all_62_rows_and_no_missing_tests_and_mr_rows_have_a_question(self):
        out = gen("r54_manual_audit.py"); rows = [l for l in out.splitlines() if l.startswith("| ") and not l.startswith("| Row") and not l.startswith("|---")]
        self.assertEqual(len(rows), 62); self.assertNotIn("MISSING:", out)
        for l in rows:
            c = [x.strip() for x in l.strip("|").split("|")]
            if c[1] == "MR": self.assertNotEqual(c[6], "-", c[0])
if __name__ == "__main__": unittest.main()
