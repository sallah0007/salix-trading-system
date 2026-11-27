"""Accepted SOURCE-INPUT binding verification (generic; closes the gap that the accepted record is PROBE-valued: the pipeline materializes `probe_for(manifest)`, not the real source-value history).
What IS authorable under the existing schemas: the accepted manifest (read from the content-addressed artifact the accepted record names) declares its input names (`manifest.inputs`); Typed Annex V1.2 (13PE_pli3ZlFjjPdhHtWtLyyH2XdAv8XGA4FN0KGcIlA) section V requires INPUT_REFS_AND_HASHES (LIST<REF+HASH>) on every row and
Composer 27/28 require that every input resolve to a Tracker identity or a returned node. This module verifies, AS FOUND, that a SUPPLIED binding map {input_name: {"ref": str, "hash": hex64}} covers EXACTLY the accepted manifest's declared inputs and, where a SUPPLIED resolver `resolver(ref) -> hex64 | None` exists, that each ref resolves to the
declared hash. It never fetches data, never invents a ref/hash encoding, never overwrites the artifact, and with NO resolver reports BOUND_UNVERIFIED (shape-only), never VERIFIED. The source-value/history STREAM itself (real provider data, vintage, as-of series) is NOT verified here and its proof stays unbound.
Statuses per input: BOUND_VERIFIED | BOUND_UNVERIFIED | MISSING | MISMATCH | UNRESOLVED(resolver returned None). Overall: VERIFIED only if every input is BOUND_VERIFIED and there are no extras; HELD_UNVERIFIED if all are BOUND_UNVERIFIED/BOUND_VERIFIED (no resolver) ; FAIL otherwise."""
import json, re
from ..errors import Refusal
from ..replay import replay
from ..storage.keys import accepted_materialization_key
from ..tracker.verification.independent_encoding import parse
_H = re.compile(r"[0-9a-f]{64}\Z")

def verify_accepted_source_inputs(*, journal, store, feature_key, bindings, resolver=None) -> dict:
    st = replay(feature_key.namespace(), journal.read_from(1)).get(feature_key.feature_version)
    if st is None: raise Refusal(feature_key.key(), code="NO_ACCEPTED_RECORD")
    if st.legacy_binding_absent: raise Refusal(feature_key.key(), code="ACCEPTED_RECORD_LEGACY_MAINTENANCE_HOLD")
    if not isinstance(bindings, dict) or (resolver is not None and not callable(resolver)): raise Refusal("bindings", code="SOURCE_INPUT_BINDINGS_INVALID")
    got = store.get(accepted_materialization_key(st.accepted_body["materialization_hash"]))
    if got is None: return {"overall": "FAIL", "reason": "ACCEPTED_RECORD_ABSENT", "inputs": {}, "extra": (), "stream_verified": False}
    try:
        rec = json.loads(got[0]); art = store.get(rec["object_key"]); names = tuple(parse(art[0])["inputs"]) if art is not None else None
    except Exception: names = None
    if names is None: return {"overall": "FAIL", "reason": "ACCEPTED_MANIFEST_UNREADABLE", "inputs": {}, "extra": (), "stream_verified": False}
    out = {}
    for n in sorted(names):
        b = bindings.get(n)
        if not (isinstance(b, dict) and set(b) == {"ref", "hash"} and isinstance(b["ref"], str) and b["ref"] and isinstance(b["hash"], str) and _H.match(b["hash"])): out[n] = "MISSING"; continue
        if resolver is None: out[n] = "BOUND_UNVERIFIED"; continue
        r = resolver(b["ref"]); out[n] = "UNRESOLVED" if r is None else ("BOUND_VERIFIED" if r == b["hash"] else "MISMATCH")
    extra = tuple(sorted(set(bindings) - set(names)))
    if extra or any(v in ("MISSING", "MISMATCH", "UNRESOLVED") for v in out.values()): overall = "FAIL"
    elif all(v == "BOUND_VERIFIED" for v in out.values()): overall = "VERIFIED"
    else: overall = "HELD_UNVERIFIED"
    return {"overall": overall, "reason": "", "inputs": out, "extra": extra, "stream_verified": False}
