"""Lane / Plan-B provenance (Annex §§XI, XIII, XIV; F1-F3, M1, M3). Baseline status is CLOSURE-DERIVED, not inferred from
current DEPENDENCIES[] alone. The lane predicate for MODEL_SPECIFIC vs CONFLUENCE is the author's reading (see D11)."""
from dataclasses import dataclass
from typing import Tuple, Optional, Dict
from ..errors import Refusal

BASELINE, MODEL_SPECIFIC, CONFLUENCE = "BASELINE", "MODEL_SPECIFIC", "CONFLUENCE"

@dataclass(frozen=True)
class ConsumerManifest:
    manifest_id: str
    kind: str                                  # "FW" | "ML"
    dependency_feature_ids: Tuple[bytes, ...]
    includes_baseline_dependencies: bool = False
    derived_from: Optional[str] = None         # DERIVED_FROM_MANIFEST_REF
    artifact_closure_features: Tuple[bytes, ...] = ()   # features in the dependency closure of results/artifacts it carries
    post_target_retuning: bool = False
    declared_lane: Optional[str] = None

def closure_contains_target(m: ConsumerManifest, target: bytes, graph: Dict[str, ConsumerManifest]) -> bool:
    seen = set(); cur = m
    while cur is not None:
        if cur.manifest_id in seen:
            raise Refusal(cur.manifest_id, code="DERIVATION_CYCLE")
        seen.add(cur.manifest_id)
        if target in cur.dependency_feature_ids or target in cur.artifact_closure_features or cur.post_target_retuning:
            return True
        if cur.derived_from is None:
            return False
        nxt = graph.get(cur.derived_from)
        if nxt is None:
            raise Refusal(cur.derived_from, code="DERIVED_FROM_UNRESOLVED")      # unread ancestry fails closed
        cur = nxt
    return False

def classify(m: ConsumerManifest, target: bytes, graph: Dict[str, ConsumerManifest]) -> str:
    listed = target in m.dependency_feature_ids
    if not listed:
        if closure_contains_target(m, target, graph):
            raise Refusal(m.manifest_id, code="HIDDEN_QUANT_ANCESTOR")            # M3 / Q14
        lane = BASELINE
    else:
        lane = CONFLUENCE if m.includes_baseline_dependencies else MODEL_SPECIFIC
    if m.declared_lane is not None and m.declared_lane != lane:
        raise Refusal("%s != %s" % (m.declared_lane, lane), code="LANE_MISDECLARED")
    return lane
