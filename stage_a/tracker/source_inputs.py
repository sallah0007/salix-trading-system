"""Accepted SOURCE-INPUT binding verification (generic). R36 CORRECTION: this module does NOT recompute accepted source VALUES by itself; `verify_accepted_source_inputs` checks the input-name coverage and caller-resolved ref/hash, and now ONLY after the accepted receipt -> materialization record -> artifact binding was verified AS FOUND (`accepted_as_found` + the independent `verify_materialization` PASS). `verify_source_values` below is the value-recomputation path.
What IS authorable under the existing schemas: the accepted manifest (read from the content-addressed artifact the accepted record names) declares its input names (`manifest.inputs`); Typed Annex V1.2 (13PE_pli3ZlFjjPdhHtWtLyyH2XdAv8XGA4FN0KGcIlA) section V requires INPUT_REFS_AND_HASHES (LIST<REF+HASH>) on every row and
Composer 27/28 require that every input resolve to a Tracker identity or a returned node. This module verifies, AS FOUND, that a SUPPLIED binding map {input_name: {"ref": str, "hash": hex64}} covers EXACTLY the accepted manifest's declared inputs and, where a SUPPLIED resolver `resolver(ref) -> hex64 | None` exists, that each ref resolves to the
declared hash. It never fetches data, never invents a ref/hash encoding, never overwrites the artifact, and with NO resolver reports BOUND_UNVERIFIED (shape-only), never VERIFIED. The source-value/history STREAM itself (real provider data, vintage, as-of series) is NOT verified here and its proof stays unbound.
Statuses per input: BOUND_VERIFIED | BOUND_UNVERIFIED | MISSING | MISMATCH | UNRESOLVED(resolver returned None). Overall: VERIFIED only if every input is BOUND_VERIFIED and there are no extras; HELD_UNVERIFIED if all are BOUND_UNVERIFIED/BOUND_VERIFIED (no resolver) ; FAIL otherwise."""
import json, re, struct
from ..errors import Refusal
from .reverification import accepted_as_found
from .verification.stateful_verifier import verify_materialization
from .verification.verification_result import PASS
from .verification.independent_encoding import parse
from .verification.independent_traversal import reference_evaluate, RefEvalError, bits
_H = re.compile(r"[0-9a-f]{64}\Z")

def _as_found(journal, store, feature_key):
    """(names, artifact_bytes, p, reason). reason != "" means nothing may be read from the record. The artifact is read ONLY after the accepted receipt, the stored record and the artifact bytes bind (hashes recomputed by the independent verifier against the acceptance's own declared hashes)."""
    body, rec, state, declared = accepted_as_found(journal, store, feature_key)
    if state != "ACCEPTED_RECORD_AS_FOUND": return None, None, None, "ACCEPTED_RECORD_ABSENT_OR_UNBOUND"
    res = verify_materialization(store_get=lambda k: (lambda g: None if g is None else g[0])(store.get(k)), record=rec, declared=declared, expect_scope_key=feature_key.key())
    if res.status != PASS: return None, None, None, "ACCEPTED_RECORD_NOT_VERIFIED_AS_FOUND:" + ",".join(res.reasons)
    raw = store.get(rec["object_key"])[0]; p = parse(raw)
    return tuple(p["inputs"]), raw, p, ""

def _shape_ok(b): return isinstance(b, dict) and set(b) == {"ref", "hash"} and isinstance(b["ref"], str) and b["ref"] and isinstance(b["hash"], str) and bool(_H.match(b["hash"]))

def verify_accepted_source_inputs(*, journal, store, feature_key, bindings, resolver=None) -> dict:
    if not isinstance(bindings, dict) or (resolver is not None and not callable(resolver)): raise Refusal("bindings", code="SOURCE_INPUT_BINDINGS_INVALID")
    names, _, _, why = _as_found(journal, store, feature_key)
    if names is None: return {"overall": "FAIL", "reason": why, "inputs": {}, "extra": (), "stream_verified": False}
    out = {}
    for n in sorted(names):
        b = bindings.get(n)
        if not _shape_ok(b): out[n] = "MISSING"; continue
        if resolver is None: out[n] = "BOUND_UNVERIFIED"; continue
        r = resolver(b["ref"]); out[n] = "UNRESOLVED" if r is None else ("BOUND_VERIFIED" if r == b["hash"] else "MISMATCH")
    extra = tuple(sorted(set(bindings) - set(names)))
    if extra or any(v in ("MISSING", "MISMATCH", "UNRESOLVED") for v in out.values()): overall = "FAIL"
    elif all(v == "BOUND_VERIFIED" for v in out.values()): overall = "VERIFIED"
    else: overall = "HELD_UNVERIFIED"
    return {"overall": overall, "reason": "", "inputs": out, "extra": extra, "stream_verified": False}

def _bits_finite(x):
    """INDEPENDENT finite test on the IEEE-754 binary64 bit pattern (exponent field != all ones); deliberately does not use the evaluator's or producer's helper. Frozen Parent p90: every operator input must be finite BEFORE evaluation."""
    return ((struct.unpack(">Q", struct.pack(">d", x))[0] >> 52) & 0x7FF) != 0x7FF

def verify_source_values(*, journal, store, feature_key, bindings, fetch, series_hash, expected_output=None) -> dict:
    """Generic accepted source-VALUE verification under the existing schemas, with INDEPENDENT recomputation.
    After the as-found accepted binding: for every declared input, `fetch(ref)` supplies the actual value series (list of binary64 floats; None = unresolved) and the binding hash must equal `series_hash(series)` - the
    series HASH ENCODING is not defined by any source read, so it is a CALLER-SUPPLIED callable and nothing is invented here. All series must have the same length. The accepted manifest is then evaluated over the
    supplied series by the verifier's OWN reference evaluator (not the materializer); the bit-exact output is returned and, if `expected_output` (list of bit patterns) is supplied, compared to it.
    Overall: VERIFIED_RECOMPUTED only if every input hash verified, no extras, the evaluation did not refuse, and any expected output matched. `stream_verified` is ALWAYS False and `provider_vintage_clock_proof` is HELD:
    a value series equal to its binding is not proof that a provider delivered it, of its vintage or of its as-of clock."""
    if not isinstance(bindings, dict) or not callable(fetch) or not callable(series_hash): raise Refusal("inputs", code="SOURCE_VALUE_INPUTS_INVALID")
    names, raw, p, why = _as_found(journal, store, feature_key)
    base = {"stream_verified": False, "provider_vintage_clock_proof": "HELD", "recomputed": None, "matches_expected": None}
    if names is None: return dict(base, overall="FAIL", reason=why, inputs={}, extra=())
    out, series = {}, {}
    for n in sorted(names):
        b = bindings.get(n)
        if not _shape_ok(b): out[n] = "MISSING"; continue
        v = fetch(b["ref"])
        if v is None: out[n] = "UNRESOLVED"; continue
        if not isinstance(v, (list, tuple)) or not v or not all(type(x) is float for x in v): out[n] = "SERIES_MALFORMED"; continue
        if not all(_bits_finite(x) for x in v): out[n] = "SERIES_NONFINITE"; continue                # checked BEFORE hash comparison and evaluation: a matching hash does not make NaN/Inf admissible
        out[n] = "BOUND_VERIFIED" if series_hash(list(v)) == b["hash"] else "MISMATCH"; series[n] = list(v)
    extra = tuple(sorted(set(bindings) - set(names)))
    if extra or any(v != "BOUND_VERIFIED" for v in out.values()): return dict(base, overall="FAIL", reason="INPUTS_NOT_VERIFIED", inputs=out, extra=extra)
    if len({len(v) for v in series.values()}) > 1: return dict(base, overall="FAIL", reason="SERIES_LENGTH_DIFFERS", inputs=out, extra=extra)
    try: rec = [bits(x) for x in reference_evaluate(p, series)]
    except RefEvalError as e: return dict(base, overall="FAIL", reason="REFERENCE_EVALUATION_REFUSED:" + str(e), inputs=out, extra=extra)
    if any(x is not None and (((int(x, 16) >> 52) & 0x7FF) == 0x7FF or int(x, 16) == 1 << 63) for x in rec): return dict(base, overall="FAIL", reason="RECOMPUTED_OUTPUT_NOT_CANONICAL_FINITE", inputs=out, extra=extra)       # p91 finite result, p92 +0 canonicalisation
    m = None if expected_output is None else (rec == expected_output)
    return dict(base, overall="VERIFIED_RECOMPUTED" if m in (None, True) else "FAIL", reason="" if m in (None, True) else "OUTPUT_DIFFERS_FROM_EXPECTED", inputs=out, extra=extra, recomputed=rec, matches_expected=m)
