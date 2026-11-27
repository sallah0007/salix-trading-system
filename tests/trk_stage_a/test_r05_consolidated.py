"""R05: D14 inequality cross-check, D15 residual, store recovery/interrupt cases. Each test can fail (see mutation sweep)."""
import threading
import pytest
from stage_a.errors import Refusal
from stage_a.context import news_hub_v2 as N
from stage_a.gateway import v038 as V

def _ident(n="w1"):
    return V.FinalResolutionIdentity("C", "M", "S", n)

def test_d14_news_hub_le_vs_gateway_lt_boundary_is_recorded_not_resolved():
    # An ACTUAL with ACTUAL_AVAILABLE_ASOF == cutoff is consumable under the News Hub text (<=) ...
    assert N.actual_available_asof(True, 7, 10, 10) == 10
    # ... but the Gateway's eligibility is AVAILABLE_ASOF < SNAPSHOT_FENCE_TS: equality is late. The two agree below the boundary
    # and differ only where decision cutoff == fence (relationship undefined in the sources: D14 residual).
    wm = V.VisibilityWatermark(5, 20)
    assert V.classify_late(10, 10, 1, wm) == V.GENUINE_LATE
    assert V.classify_late(9, 10, 1, wm) != V.GENUINE_LATE

def test_d15_unknown_reasons_fail_closed_and_known_stay_not_ready():
    assert V.status_for_reason("REQUIRED_DEPENDENCY_ABSENT") == V.NOT_READY
    assert V.status_for_reason("CHAIN_STATUS_NOT_CURRENT:X") == V.NOT_READY
    for r in ("", "SOMETHING_NEW", "required_dependency_absent"):      # case drift must not read as the known reason
        assert V.status_for_reason(r) == V.REJECTED

def test_store_recovers_after_failed_evaluator_and_counts_each_attempt():
    s, i = V.FinalResolutionStore(), _ident()
    def boom(): raise RuntimeError("interrupted")
    with pytest.raises(RuntimeError): s.resolve("r1", i, boom)
    with pytest.raises(Refusal): s.resolve("r1", i, lambda: None)
    assert s.resolve("r1", i, lambda: "OUT") == "OUT"
    assert s.resolve("r2", i, lambda: "OTHER") == "OUT"               # retry via another request id returns the stored outcome
    assert s.evaluations == 3
    with pytest.raises(Refusal): s.late_dependency_mutates(i)

def test_store_unresolved_identity_not_marked_final_after_failure():
    s, i = V.FinalResolutionStore(), _ident("w2")
    with pytest.raises(RuntimeError): s.resolve("r", i, lambda: (_ for _ in ()).throw(RuntimeError()))
    s.late_dependency_mutates(i)                                      # nothing stored => no immutability claim

def test_store_concurrent_callers_smoke_unsynchronised_start():
    # NOT barrier-based: threads start without a start gate or evaluator-entry barrier. Smoke only; forced interleavings live in
    # test_v038_conformance.py (evaluator-entry Events).
    s, i, outs = V.FinalResolutionStore(), _ident("w3"), []
    def run(k): outs.append(s.resolve(f"r{k}", i, lambda: object()))
    ts = [threading.Thread(target=run, args=(k,)) for k in range(16)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert len({id(o) for o in outs}) == 1 and s.evaluations == 1
