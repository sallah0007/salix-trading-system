"""R36 (frozen Tracker DOCX s7A RESOLVER DETERMINISM / AMBIGUITY): registration order, cache order or a later excluded row must not decide the result; materially non-equivalent valid candidates with no governed tie-break -> MULTIPLE_CANDIDATES."""
import dataclasses, unittest
from stage_a.gateway import contracts as G
from .test_boundaries import _gw, _entry, _health, _row, I
def r(**k): return _row(**k)
class Determinism(unittest.TestCase):
    def test_a_later_published_row_after_the_fence_does_not_hide_an_earlier_valid_one(self):
        g = _gw(avail=4); g.publish(r(avail=20, visible=20))                            # published LATER, but available_asof >= fence: excluded
        self.assertIsInstance(g.resolve("a", _entry(), I, I, 3, 10, _health()), G.Binding)       # the pre-R36 `cands[-1]` read the excluded row and denied NOT_AVAILABLE_BEFORE_FENCE
    def test_two_valid_non_equivalent_candidates_are_multiple_candidates_in_either_publication_order(self):
        a, b = r(avail=3, visible=3), dataclasses.replace(r(avail=4, visible=4), materialization_version="m2")
        for order in ((a, b), (b, a)):
            g = _gw(avail=4); g.rows.clear()
            for x in order: g.publish(x)
            self.assertEqual(g.resolve("a", _entry(), I, I, 3, 10, _health()).reason, "MULTIPLE_CANDIDATES")
    def test_a_republished_identical_row_is_not_ambiguity_and_the_outcome_does_not_depend_on_order(self):
        g = _gw(avail=4); g.publish(r(avail=4)); self.assertIsInstance(g.resolve("a", _entry(), I, I, 3, 10, _health()), G.Binding)
if __name__ == "__main__": unittest.main()
