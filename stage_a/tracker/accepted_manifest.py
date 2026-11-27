"""Accepted-manifest READ-BACK (R24): the missing join that feature_lineage.py names - from the journal's CANONICAL_ACCEPTED record for a FeatureKey to the manifest BYTES the Tracker actually stored, with every
identity re-derived from those bytes by the independent verifier modules. Fails closed on: no accepted record, absent/altered/non-canonical bytes, any hash or identity mismatch, malformed record body.

What a successful read-back proves: the stored artifact is byte-identical to what the accepted record names (manifest/graph/program hashes recomputed independently) and binds the requested identity.
What it does NOT prove: that the acceptance itself was authoritative (qualified acceptance is held while its duty evidence is unbound), that the manifest is a frozen governed QuantManifest (the pipeline admits the
expression-kernel Manifest), or anything about the lineage of its inputs. The lineage fields are returned as RECORDED references, not resolved."""
from dataclasses import dataclass
from ..errors import Refusal
from ..replay import replay
from ..storage.keys import artifact_key
from ..composer.expression.manifest import Manifest
from .verification.independent_encoding import enc_bytes, parse
from .verification.independent_hashing import manifest_digest, graph_digest, program_digest

RECORDED_LINEAGE = ("attempt_id", "verification_hash", "certification_hash", "claim_witness", "safe_intake_report_hash")

@dataclass(frozen=True)
class AcceptedManifestReadback:
    feature_key: str
    manifest: Manifest
    manifest_hash: str
    accepted_seq: int
    accepted_hash: str
    recorded_lineage: tuple          # ((name, recorded reference), ...) - references, NOT resolved evidence

def read_accepted_manifest(journal, store, feature_key) -> AcceptedManifestReadback:
    """feature_key: identifiers.FeatureKey. journal: the per-feature journal (namespace = feature_key.namespace()). store: the content-addressed artifact store (get(key) -> (bytes, ...) | None)."""
    st = replay(feature_key.namespace(), journal.read_from(1)).get(feature_key.feature_version)
    if st is None: raise Refusal(feature_key.key(), code="NO_ACCEPTED_RECORD")
    body = st.accepted_body
    for k in ("feature_key", "manifest_hash", "graph_hash", "program_hash") + RECORDED_LINEAGE:
        if not isinstance(body.get(k), str) or not body[k]: raise Refusal(k, code="ACCEPTED_RECORD_FIELD_MISSING")
    got = store.get(artifact_key(body["manifest_hash"]))
    if got is None: raise Refusal(body["manifest_hash"], code="ACCEPTED_ARTIFACT_ABSENT")
    raw = got[0]
    try: p = parse(raw)
    except Exception: raise Refusal(body["manifest_hash"], code="ACCEPTED_ARTIFACT_UNPARSEABLE")
    if not isinstance(p, dict) or enc_bytes(p) != raw: raise Refusal(body["manifest_hash"], code="ACCEPTED_ARTIFACT_NOT_CANONICAL")
    if manifest_digest(raw) != body["manifest_hash"] or graph_digest(p, enc_bytes) != body["graph_hash"] or program_digest(p, enc_bytes) != body["program_hash"]:
        raise Refusal(body["manifest_hash"], code="ACCEPTED_ARTIFACT_HASH_MISMATCH")
    if (p.get("instrument"), p.get("timeframe"), p.get("feature_id"), p.get("feature_version")) != (feature_key.scope.instrument, feature_key.scope.timeframe, feature_key.feature_id, feature_key.feature_version):
        raise Refusal(feature_key.key(), code="ACCEPTED_ARTIFACT_IDENTITY_MISMATCH")
    return AcceptedManifestReadback(feature_key.key(), Manifest.from_dict(p), body["manifest_hash"], st.accepted_seq, st.accepted_hash, tuple((k, body[k]) for k in RECORDED_LINEAGE))
