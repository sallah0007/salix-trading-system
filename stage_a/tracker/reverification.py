"""Re-verification through the EXISTING materializer and the EXISTING independent verifier (R24), replacing the arbitrary injected callable as the path that produces Core health evidence.

What this composes: `StatefulMaterializer.materialize` (batch + incremental over a verifier-authored probe) -> `verify_materialization` (re-derives hashes from the stored bytes, structure, opcode/capability
declaration equality, bit-exact reference evaluation) -> `TrackerCore.record_verification` with evidence class COMPOSED_RECOMPUTATION_SIMULATION and the verifier's own `result_hash` as the result digest.

What it is NOT: not operational qualification, not an appointed L2 verifier (appointment/profile/thresholds are source-owned and unbound), not independent of its author (D4: the verifier is a second implementation
by the same author), and the producer-declared hashes must be SUPPLIED by the caller from the request record (never taken from the artifact being verified). The Core stays qualified-HELD for health in a qualified
journal; this path changes the evidence a SIMULATION Core records, nothing else."""
from ..errors import Refusal
from ..composer.expression.artifacts import build_artifact
from ..composer.expression.canonical_encoding import encode_manifest
from ..identifiers import Scope, FeatureKey
from .materialization.stateful_materializer import StatefulMaterializer
from .verification.stateful_verifier import verify_materialization, probe_for
from .verification.verification_result import PASS, FAIL, INSUFFICIENT_EVIDENCE
from ..core.tracker_core import COMPOSED_RECOMPUTATION

VERIFIER_ID = "tracker.verification.stateful_verifier.verify_materialization"
_L2_CHECKS = ("equivalence_probe_batch", "equivalence_probe_incremental")        # the independent numeric recomputation; everything else is L1 structure/identity

def split_levels(result):
    """(l1, l2) from the verifier's typed result. L2 is UNAVAILABLE (never PASS, never a fallback to L1) when the verifier never reached the recomputation."""
    names = dict(result.checks)
    if result.status == INSUFFICIENT_EVIDENCE: return "FAIL", "UNAVAILABLE"
    l1 = "PASS" if all(ok for n, ok in result.checks if n not in _L2_CHECKS) else "FAIL"
    if not all(n in names for n in _L2_CHECKS): return l1, "UNAVAILABLE"          # early return before recomputation
    return l1, ("PASS" if all(names[n] for n in _L2_CHECKS) else "FAIL")

def reverify_manifest(core, *, manifest, declared: dict, store, now: int, max_age: int):
    """Runs the real materializer and verifier for `manifest` and records the result on `core`. `declared` = {manifest_hash, graph_hash, program_hash} from the producer's request record (required, no default)."""
    if not isinstance(declared, dict) or set(declared) != {"manifest_hash", "graph_hash", "program_hash"} or any(not isinstance(v, str) or not v for v in declared.values()):
        raise Refusal("producer-declared hashes are required and must come from the request record", code="DECLARED_HASHES_REQUIRED")
    fk = FeatureKey(Scope(manifest.instrument, manifest.timeframe), manifest.feature_id, manifest.feature_version)
    raw = encode_manifest(manifest)
    rec = StatefulMaterializer(store).materialize(manifest, probe_for(raw))
    res = verify_materialization(store_get=lambda k: (lambda g: None if g is None else g[0])(store.get(k)), record=rec, declared=declared, expect_scope_key=fk.key())
    l1, l2 = split_levels(res)
    core.record_verification(fk.key(), manifest.feature_version, "REQUIRED", l2, l1, now, max_age, VERIFIER_ID, res.result_hash, evidence_class=COMPOSED_RECOMPUTATION)
    return res
