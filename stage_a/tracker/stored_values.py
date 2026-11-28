"""R37: persisted materialized VALUE series and the L2 maintenance verification that COMPARES THEM (Registry 203-212: L2 independently recomputes the authoritative inputs AND compares the STORED materialized values (206); a required L2 that is UNAVAILABLE is UNKNOWN / NOT_HEALTHY with no L1 fallback (208-210); the path is independent (211-212)).
`persist_stored_values` writes the PRODUCER's values (the Tracker's own incremental evaluator, `materialization.stateful_materializer.IncrementalEvaluator`) bound to the ACCEPTED materialization record; `verify_stored_values` recomputes the series with the verifier's OWN reference evaluator (`source_inputs.verify_source_values`) and compares the STORED bit patterns
to it. Producer and verifier are two implementations; neither reads the other's output to produce its own.
CANDIDATE LAYOUT, NOT source-defined: the object key (`candidate/stored-values/<materialization_hash>.json`) and the record shape are this module's own; no E-09 normative key exists for stored values. The series hash encoding is the CALLER's `series_hash` (no source defines it). `stream_verified` is ALWAYS False and provider/vintage/as-of-clock proof is HELD (a stored series equal to its recomputation is not provider evidence).
`record_stored_value_maintenance` records the typed outcome into the Core as CALLER_ASSERTED evidence (never COMPOSED: the Core mints that label only for the materialization verifier run) with L1 unchanged by this check (L1 = the as-found binding) and L2 PASS / FAIL / UNAVAILABLE; there is no daemon, cadence or appointed L2."""
import json
from ..errors import Refusal, IntegrityFailure
from ..storage.byte_primitives import canonical_bytes, domain_hash
from .materialization.stateful_materializer import IncrementalEvaluator, _bits
from .reverification import accepted_as_found
from . import source_inputs as SI
VERIFIER_ID = "tracker.stored_values.verify_stored_values"
def stored_values_key(materialization_hash): return "candidate/stored-values/%s.json" % materialization_hash
def _check_bindings(b):
    return isinstance(b, dict) and b and all(isinstance(n, str) and SI._shape_ok(v) for n, v in b.items())
def persist_stored_values(*, journal, store, feature_key, bindings, fetch, series_hash) -> dict:
    """Write-once producer record for the ACCEPTED materialization: values evaluated by the producer path over the fetched series whose hashes equal the supplied bindings. Identical retry idempotent; different bytes under the same accepted materialization refuse (STORED_VALUES_IMMUTABLE)."""
    if not (_check_bindings(bindings) and callable(fetch) and callable(series_hash)): raise Refusal("inputs", code="STORED_VALUES_INPUTS_INVALID")
    names, raw, p, why = SI._as_found(journal, store, feature_key)
    if names is None: raise Refusal(why, code="STORED_VALUES_ACCEPTED_RECORD_NOT_AS_FOUND")
    body = accepted_as_found(journal, store, feature_key)[0]
    if set(bindings) != set(names): raise Refusal(",".join(sorted(set(bindings) ^ set(names))), code="STORED_VALUES_INPUT_SET_MISMATCH")
    series = {}
    for n in sorted(names):
        v = fetch(bindings[n]["ref"])
        if not (isinstance(v, (list, tuple)) and v and all(type(x) is float and SI._bits_finite(x) for x in v)): raise Refusal(n, code="STORED_VALUES_SERIES_UNUSABLE")
        if series_hash(list(v)) != bindings[n]["hash"]: raise Refusal(n, code="STORED_VALUES_SERIES_HASH_MISMATCH")
        series[n] = list(v)
    if len({len(v) for v in series.values()}) != 1: raise Refusal("length", code="STORED_VALUES_SERIES_LENGTH_DIFFERS")
    from ..composer.expression.manifest import Manifest
    inc = IncrementalEvaluator(Manifest.from_dict(p)); length = len(next(iter(series.values())))
    vals = [_bits(inc.push({k: v[t] for k, v in series.items()})) for t in range(length)]
    rec = {"feature_key": feature_key.key(), "feature_version": feature_key.feature_version, "materialization_hash": body["materialization_hash"], "bindings": {n: dict(bindings[n]) for n in sorted(bindings)}, "values": vals}
    data = canonical_bytes(rec); k = stored_values_key(body["materialization_hash"])
    if not store.put_if_absent(k, data):
        got = store.get(k)
        if got is None or got[0] != data: raise IntegrityFailure("stored values for %s differ" % body["materialization_hash"])
    return rec
def verify_stored_values(*, journal, store, feature_key, bindings, fetch, series_hash) -> dict:
    """L2 maintenance verification. overall: VERIFIED_STORED_EQUALS_RECOMPUTED | FAIL | UNAVAILABLE. UNAVAILABLE (no accepted-as-found record, no stored record, or no usable inputs) is `l2 = UNAVAILABLE`, `health_effect = NOT_HEALTHY`, `l1_fallback = False`: a missing L2 is never a PASS and never replaced by the L1 result."""
    base = {"stream_verified": False, "provider_vintage_clock_proof": "HELD", "l1_fallback": False, "stored_values_compared": False}
    if not (_check_bindings(bindings) and callable(fetch) and callable(series_hash)): raise Refusal("inputs", code="STORED_VALUES_INPUTS_INVALID")
    names, raw, p, why = SI._as_found(journal, store, feature_key)
    if names is None: return dict(base, overall="UNAVAILABLE", reason=why, l1="FAIL", l2="UNAVAILABLE", health_effect="NOT_HEALTHY")
    body = accepted_as_found(journal, store, feature_key)[0]; got = store.get(stored_values_key(body["materialization_hash"]))
    if got is None: return dict(base, overall="UNAVAILABLE", reason="STORED_VALUES_ABSENT", l1="PASS", l2="UNAVAILABLE", health_effect="NOT_HEALTHY")
    try: rec = json.loads(got[0])
    except (ValueError, UnicodeDecodeError): return dict(base, overall="FAIL", reason="STORED_VALUES_UNPARSEABLE", l1="PASS", l2="FAIL", health_effect="NOT_HEALTHY")
    if not (isinstance(rec, dict) and rec.get("materialization_hash") == body["materialization_hash"] and rec.get("feature_key") == feature_key.key() and rec.get("feature_version") == feature_key.feature_version and isinstance(rec.get("values"), list)):
        return dict(base, overall="FAIL", reason="STORED_VALUES_NOT_BOUND_TO_ACCEPTED_MATERIALIZATION", l1="PASS", l2="FAIL", health_effect="NOT_HEALTHY")
    if rec.get("bindings") != {n: dict(bindings[n]) for n in sorted(bindings)}: return dict(base, overall="FAIL", reason="STORED_INPUT_BINDINGS_DIFFER_FROM_SUPPLIED", l1="PASS", l2="FAIL", health_effect="NOT_HEALTHY")
    v = SI.verify_source_values(journal=journal, store=store, feature_key=feature_key, bindings=bindings, fetch=fetch, series_hash=series_hash)
    if v["overall"] != "VERIFIED_RECOMPUTED":
        unavailable = any(s in ("UNRESOLVED", "MISSING") for s in v["inputs"].values())
        return dict(base, overall="UNAVAILABLE" if unavailable else "FAIL", reason="RECOMPUTATION_" + v["overall"] + ":" + v["reason"], l1="PASS", l2="UNAVAILABLE" if unavailable else "FAIL", health_effect="NOT_HEALTHY", inputs=v["inputs"])
    same = rec["values"] == v["recomputed"]
    return dict(base, stored_values_compared=True, overall="VERIFIED_STORED_EQUALS_RECOMPUTED" if same else "FAIL", reason="" if same else "STORED_VALUES_DIFFER_FROM_INDEPENDENT_RECOMPUTATION",
                l1="PASS", l2="PASS" if same else "FAIL", health_effect="NONE_ASSERTED" if same else "NOT_HEALTHY", inputs=v["inputs"], recomputed=v["recomputed"])
def record_stored_value_maintenance(core, *, journal, store, feature_key, bindings, fetch, series_hash, now, max_age) -> dict:
    """One bounded maintenance call: verify, then record the typed L2 outcome in the Core (CALLER_ASSERTED, see module doc). The result digest is the domain hash of the typed outcome. UNAVAILABLE/FAIL make the subject NOT HEALTHY in the Core's own calculation."""
    r = verify_stored_values(journal=journal, store=store, feature_key=feature_key, bindings=bindings, fetch=fetch, series_hash=series_hash)
    digest = domain_hash("SALIX_STORED_VALUE_L2_V1", canonical_bytes({k: r[k] for k in ("overall", "reason", "l1", "l2", "stored_values_compared")}))
    core.record_verification(feature_key.key(), feature_key.feature_version, "REQUIRED", r["l2"], r["l1"], now, max_age, VERIFIER_ID, digest)
    return dict(r, result_digest=digest)
