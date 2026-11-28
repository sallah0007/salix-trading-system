"""R44 D14: the Gateway/Tracker inclusion boundary is the frozen HALF-OPEN snapshot fence (available_asof < fence; equality EXCLUDED; Registry p123, Blueprint NEWS-02/03 reading by Manager). NewsHub V2's own inclusive '<= decision cutoff' wording is a NewsHub causal-view comparator only and must never feed Gateway/Tracker inclusion."""
import pathlib, re, unittest
from stage_a.tracker.registry_semantics import included_in_snapshot
from stage_a.context import news_hub_v2 as N
ROOT = pathlib.Path(__file__).resolve().parents[2]
class D14(unittest.TestCase):
    def test_equality_at_the_fence_is_excluded_and_below_is_included(self):
        self.assertFalse(included_in_snapshot(10, 10)); self.assertTrue(included_in_snapshot(9, 10)); self.assertFalse(included_in_snapshot(11, 10))
    def test_news_snapshot_fence_comparator_excludes_equality_while_decision_cutoff_stays_a_news_only_view(self):
        self.assertTrue(N._past(10, 10, "SNAPSHOT_FENCE")); self.assertFalse(N._past(10, 10, "DECISION_CUTOFF"))
    def test_no_gateway_or_tracker_module_imports_the_news_hub_inclusive_comparator(self):
        bad = []
        for d in ("stage_a/gateway", "stage_a/tracker", "stage_a/core"):
            for p in (ROOT / d).rglob("*.py"):
                if re.search(r"news_hub_v2|DECISION_CUTOFF", p.read_text()): bad.append(str(p.relative_to(ROOT)))
        self.assertEqual(bad, [])
if __name__ == "__main__": unittest.main()
