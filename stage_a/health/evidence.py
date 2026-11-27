"""Main Health / B0 evidence objects (Annex §XVII). EVIDENCE ONLY: Health is not refit authority and not delivery authority
(Q17). STATUS: payload/sub-schema objects + a one-way sink interface; no Health service exists in this repo."""
from dataclasses import dataclass, fields
from typing import Optional, Tuple
from ..errors import Refusal
from ..schema.encoding import Ref

def _u64(v, n):
    if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v < 2**64:
        raise Refusal(n, code="UINT64_RANGE")

@dataclass(frozen=True)
class LatencyMetricsV1:
    window_ref: Ref; sample_count: int; end_to_end_p50_ns: int; end_to_end_p95_ns: int; end_to_end_p99_ns: int
    incremental_feature_p50_ns: int; incremental_feature_p95_ns: int; incremental_feature_p99_ns: int
    storage_accept_p95_ns: int; verification_p95_ns: int; visibility_p95_ns: int; fence_miss_count: int
    def __post_init__(self):
        for f in fields(self):
            if f.name != "window_ref": _u64(getattr(self, f.name), f.name)

@dataclass(frozen=True)
class ResourceMetricsV1:
    window_ref: Ref; worker_utilization_bits: bytes; verifier_utilization_bits: bytes; pending_queue_depth: int
    replay_backlog_count: int; replay_backlog_max_age_ns: int; canonical_commit_queue_depth: int
    def __post_init__(self):
        for n in ("worker_utilization_bits", "verifier_utilization_bits"):
            if not isinstance(getattr(self, n), bytes) or len(getattr(self, n)) != 8:
                raise Refusal(n, code="BAD_BINARY64_BITS")
        for n in ("pending_queue_depth", "replay_backlog_count", "replay_backlog_max_age_ns", "canonical_commit_queue_depth"):
            _u64(getattr(self, n), n)

@dataclass(frozen=True)
class ModelMetric:
    metric_id: str; metric_program_ref: Ref; window_ref: Ref; sample_count: int; value_type: str; value: object
    def __post_init__(self):
        _u64(self.sample_count, "sample_count")
        if self.value_type == "UINT64_VALUE": _u64(self.value, "value")
        elif self.value_type == "BINARY64_BITS_VALUE":
            if not isinstance(self.value, bytes) or len(self.value) != 8: raise Refusal("value", code="BAD_BINARY64_BITS")
        else: raise Refusal(self.value_type, code="BAD_VALUE_TYPE")

def canonical_model_metrics(ms):
    ids = [m.metric_id.encode("utf-8") for m in ms]
    if len(set(ids)) != len(ids): raise Refusal("duplicate METRIC_ID", code="DUPLICATE_METRIC_ID")
    return tuple(sorted(ms, key=lambda m: m.metric_id.encode("utf-8")))

@dataclass(frozen=True)
class FeatureHealthEvidence:
    feature_version: str; instrument_id: bytes; timeframe_id: bytes
    materialization_version: Optional[str] = None; step_or_interval: Optional[tuple] = None
    fit_generation_ref: Optional[Ref] = None; row_hash: Optional[bytes] = None; input_refs: Tuple[Ref, ...] = ()

class HealthEvidenceSink:
    """One-way: accepts evidence, returns nothing that can act. No refit, no delivery, no status mutation methods exist."""
    def __init__(self): self._items = []
    def emit(self, evidence) -> None:
        if not isinstance(evidence, (FeatureHealthEvidence, LatencyMetricsV1, ResourceMetricsV1, ModelMetric)):
            raise Refusal(type(evidence).__name__, code="NOT_HEALTH_EVIDENCE")
        self._items.append(evidence)
    def evidence(self): return tuple(self._items)
