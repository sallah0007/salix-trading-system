"""Re-verification through the EXISTING materializer and the EXISTING independent verifier (R24), replacing the arbitrary injected callable as the path that produces Core health evidence.

What this composes: `StatefulMaterializer.materialize` (batch + incremental over a verifier-authored probe) -> `verify_materialization` (re-derives hashes from the stored bytes, structure, opcode/capability
declaration equality, bit-exact reference evaluation) -> `TrackerCore.record_verification` with evidence class COMPOSED_RECOMPUTATION_SIMULATION and the verifier's own `result_hash` as the result digest.

What it is NOT: not operational qualification, not an appointed L2 verifier (appointment/profile/thresholds are source-owned and unbound), not independent of its author (D4: the verifier is a second implementation
by the same author), and the producer-declared hashes must be SUPPLIED by the caller from the request record (never taken from the artifact being verified). The Core stays qualified-HELD for health in a qualified
journal; this path changes the evidence a SIMULATION Core records, nothing else."""
import json
from ..errors import Refusal
from ..storage.byte_primitives import canonical_bytes
from ..composer.expression.artifacts import build_artifact
from ..composer.expression.canonical_encoding import encode_manifest
from ..identifiers import Scope, FeatureKey
from .materialization.stateful_materializer import StatefulMaterializer
from .verification.stateful_verifier import verify_materialization, probe_for
from .verification.verification_result import PASS, FAIL, INSUFFICIENT_EVIDENCE, COMPOSED_VERIFIER_ID, split_levels
from ..storage.authority_class import authority_class_of, SIMULATION, QUALIFIED
from ..core.tracker_core import COMPOSED_RECOMPUTATION
from ..replay import replay
from ..storage.keys import accepted_materialization_key

VERIFIER_ID = COMPOSED_VERIFIER_ID

def _require_class(core, store):
    want = SIMULATION if core.simulation else QUALIFIED
    got = authority_class_of(store)
    if got != want: raise Refusal("carrier class %s != core plane %s" % (got, want), code="REVERIFY_CARRIER_CLASS_MISMATCH")

RECORDING_EVIDENCE_PREFIX = "candidate-recording-evidence/"      # CANDIDATE storage reference under 2A: NOT a new canonical authority kind, not an accepted-persistence claim
def pinned_key(fk) -> str: return RECORDING_EVIDENCE_PREFIX + fk.key()

def reverify_pinned(core, *, manifest, declared: dict, store, now: int, max_age: int):
    """Verifies the EXISTING pinned candidate recording evidence for this feature without rebuilding or overwriting it. If none is pinned yet the materializer builds it ONCE, it is pinned with put_if_absent
    (a race/second writer never replaces it) and the stored bytes are what gets verified. A corrupt/unparseable/altered pinned record is verified AS FOUND and fails (NOT_HEALTHY evidence); it is never repaired
    or re-derived here. Returns (result, 'PINNED_NEW' | 'PINNED_EXISTING')."""
    if not isinstance(declared, dict) or set(declared) != {"manifest_hash", "graph_hash", "program_hash"} or any(not isinstance(v, str) or not v for v in declared.values()):
        raise Refusal("producer-declared hashes are required and must come from the request record", code="DECLARED_HASHES_REQUIRED")
    _require_class(core, store)
    fk = FeatureKey(Scope(manifest.instrument, manifest.timeframe), manifest.feature_id, manifest.feature_version); k = pinned_key(fk)
    got = store.get(k); state = "PINNED_EXISTING"
    if got is None:
        rec = StatefulMaterializer(store).materialize(manifest, probe_for(encode_manifest(manifest)))
        store.put_if_absent(k, canonical_bytes(rec)); got = store.get(k); state = "PINNED_NEW"
        if got is None: raise Refusal(k, code="PINNED_EVIDENCE_NOT_READABLE")
    try: rec = json.loads(got[0]); rec = rec if isinstance(rec, dict) else {}
    except (ValueError, UnicodeDecodeError): rec = {}
    res = verify_materialization(store_get=lambda key: (lambda g: None if g is None else g[0])(store.get(key)), record=rec, declared=declared, expect_scope_key=fk.key())
    l1, l2 = split_levels(res)
    core.record_verification(fk.key(), manifest.feature_version, "REQUIRED", l2, l1, now, max_age, VERIFIER_ID, res.result_hash, evidence_class=COMPOSED_RECOMPUTATION, result=res)
    return res, state

def reverify_manifest(core, *, manifest, declared: dict, store, now: int, max_age: int):
    """Runs the real materializer and verifier for `manifest` and records the result on `core`. `declared` = {manifest_hash, graph_hash, program_hash} from the producer's request record (required, no default)."""
    if not isinstance(declared, dict) or set(declared) != {"manifest_hash", "graph_hash", "program_hash"} or any(not isinstance(v, str) or not v for v in declared.values()):
        raise Refusal("producer-declared hashes are required and must come from the request record", code="DECLARED_HASHES_REQUIRED")
    _require_class(core, store)      # checked BEFORE any materialization write
    fk = FeatureKey(Scope(manifest.instrument, manifest.timeframe), manifest.feature_id, manifest.feature_version)
    raw = encode_manifest(manifest)
    rec = StatefulMaterializer(store).materialize(manifest, probe_for(raw))
    res = verify_materialization(store_get=lambda k: (lambda g: None if g is None else g[0])(store.get(k)), record=rec, declared=declared, expect_scope_key=fk.key())
    l1, l2 = split_levels(res)
    core.record_verification(fk.key(), manifest.feature_version, "REQUIRED", l2, l1, now, max_age, VERIFIER_ID, res.result_hash, evidence_class=COMPOSED_RECOMPUTATION, result=res)
    return res

ACCEPTED_FIELDS = ("feature_key", "feature_version", "manifest_hash", "graph_hash", "program_hash", "materialization_hash")
def reverify_accepted(core, *, journal, store, feature_key, now: int, max_age: int):
    """Verifies the ACCEPTED materialization AS FOUND (R34). The subject is the journal's CANONICAL_ACCEPTED record for `feature_key` (identifiers.FeatureKey) and the exact verified materialization record it names by `materialization_hash`;
    the three hashes the verifier compares against come from THAT accepted record, never from a caller manifest, so a different manifest under the same feature key/version cannot pass or be pinned. Nothing is rebuilt or overwritten: an absent,
    unparseable, unbound (record hash / feature key / version differ from the acceptance) or altered record, or altered manifest bytes, is verified as found and yields FAIL evidence (NOT_HEALTHY), never repaired. No accepted record -> refusal (nothing to
    bind). Evidence class stays COMPOSED_RECOMPUTATION_SIMULATION (verifier authored, same author, not an appointed L2). Returns (result, 'ACCEPTED_RECORD_AS_FOUND' | 'ACCEPTED_RECORD_UNBOUND_OR_ABSENT')."""
    _require_class(core, store)
    st = replay(feature_key.namespace(), journal.read_from(1)).get(feature_key.feature_version)
    if st is None: raise Refusal(feature_key.key(), code="NO_ACCEPTED_RECORD")
    body = st.accepted_body
    for k in ACCEPTED_FIELDS:
        if not isinstance(body.get(k), str) or not body[k]: raise Refusal(k, code="ACCEPTED_RECORD_FIELD_MISSING")
    if (body["feature_key"], body["feature_version"]) != (feature_key.key(), feature_key.feature_version): raise Refusal(feature_key.key(), code="ACCEPTED_RECORD_IDENTITY_MISMATCH")
    declared = {"manifest_hash": body["manifest_hash"], "graph_hash": body["graph_hash"], "program_hash": body["program_hash"]}
    rec, state = {}, "ACCEPTED_RECORD_UNBOUND_OR_ABSENT"
    try: got = store.get(accepted_materialization_key(body["materialization_hash"]))
    except Refusal: got = None
    if got is not None:
        try: r = json.loads(got[0])
        except (ValueError, UnicodeDecodeError): r = None
        if isinstance(r, dict) and r.get("materialization_hash") == body["materialization_hash"] and r.get("feature_key") == feature_key.key() and r.get("feature_version") == feature_key.feature_version: rec, state = r, "ACCEPTED_RECORD_AS_FOUND"
    res = verify_materialization(store_get=lambda key: (lambda g: None if g is None else g[0])(store.get(key)), record=rec, declared=declared, expect_scope_key=feature_key.key())
    l1, l2 = split_levels(res)
    core.record_verification(feature_key.key(), feature_key.feature_version, "REQUIRED", l2, l1, now, max_age, VERIFIER_ID, res.result_hash, evidence_class=COMPOSED_RECOMPUTATION, result=res)
    return res, state
