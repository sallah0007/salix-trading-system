"""Bounded, deterministic replay scheduling (Q16 boundary). Correlated replay of many namespaces cannot starve
others and cannot exceed the declared budget; exceeding it is a refusal, not a silent truncation."""
from ..errors import Refusal

class ReplayScheduler:
    def __init__(self, max_total: int, max_batch: int):
        if max_total < 1 or max_batch < 1:
            raise Refusal("budgets must be >=1", code="BAD_BUDGET")
        self.max_total, self.max_batch = max_total, max_batch

    def plan(self, pending: dict):
        """pending: namespace -> list of work items. Returns batches, round-robin over sorted namespaces."""
        total = sum(len(v) for v in pending.values())
        if total > self.max_total:
            raise Refusal("%d > %d" % (total, self.max_total), code="REPLAY_BUDGET_EXCEEDED")
        queues = {ns: list(items) for ns, items in sorted(pending.items())}
        batches, cur = [], []
        while any(queues.values()):
            for ns in sorted(queues):
                if queues[ns]:
                    cur.append((ns, queues[ns].pop(0)))
                    if len(cur) == self.max_batch:
                        batches.append(cur); cur = []
        if cur:
            batches.append(cur)
        return batches
