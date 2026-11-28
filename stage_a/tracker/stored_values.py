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
from ..storage.authority_class import authority_class_of, SIMULATION, QUALIFIED
VERIFIER_ID = "tracker.stored_values.verify_stored_values"
STORED_PREFIX = "candidate/stored-values/"
def segment_id(bindings) -> str:
    """R38 L2 SCOPE: the stored series is scoped to ONE source segment/window = the exact bound input set (ref + content hash per named input). LABELLED CANDIDATE encoding (no D13 bytes): a later legitimate segment has different bound hashes, hence a different id and its own write-once record under the same accepted materialization."""
    if not _check_bindings(bindings): raise Refusal("bindings", code="STORED_VALUES_INPUTS_INVALID")
    return domain_hash("SALIX_STORED_VALUE_SEGMENT_CANDIDATE_V1", canonical_bytes({n: {"ref": bindings[n]["ref"], "hash": bindings[n]["hash"]} for n in sorted(bindings)}))
def stored_values_key(materialization_hash, seg): return "%s%s/%s.json" % (STORED_PREFIX, materialization_hash, seg)
def _check_bindings(b):
    return isinstance(b, dict) and b and all(isinstance(n, str) and SI._shape_ok(v) for n, v in b.items())
def persist_stored_values(*, journal, store, feature_key, bindings, fetch, series_hash) -> dict:
    """Write-once producer record for the ACCEPTED materialization: values evaluated by the producer path over the fetched series whose hashes equal the supplied bindings. Identical retry idempotent; different bytes under the same accepted materialization AND SEGMENT refuse (IntegrityFailure); a different segment (different bound input hashes) is a different record (R38)."""
    if not (_check_bindings(bindings) and callable(fetch) and callable(series_hash)): raise Refusal("inputs", code="STORED_VALUES_INPUTS_INVALID")
    if authority_class_of(journal) != authority_class_of(store): raise Refusal("journal/store class", code="STORED_VALUES_CLASS_MISMATCH")      # R38: before any write
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
    rec["segment_id"] = segment_id(bindings); data = canonical_bytes(rec); k = stored_values_key(body["materialization_hash"], rec["segment_id"])
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
    body = accepted_as_found(journal, store, feature_key)[0]; got = store.get(stored_values_key(body["materialization_hash"], segment_id(bindings)))
    if got is None: return dict(base, overall="UNAVAILABLE", reason="STORED_VALUES_ABSENT", l1="PASS", l2="UNAVAILABLE", health_effect="NOT_HEALTHY")
    try: rec = json.loads(got[0])
    except (ValueError, UnicodeDecodeError): return dict(base, overall="FAIL", reason="STORED_VALUES_UNPARSEABLE", l1="PASS", l2="FAIL", health_effect="NOT_HEALTHY")
    if not (isinstance(rec, dict) and rec.get("materialization_hash") == body["materialization_hash"] and rec.get("feature_key") == feature_key.key() and rec.get("feature_version") == feature_key.feature_version and rec.get("segment_id") == segment_id(bindings) and isinstance(rec.get("values"), list)):
        return dict(base, overall="FAIL", reason="STORED_VALUES_NOT_BOUND_TO_ACCEPTED_MATERIALIZATION", l1="PASS", l2="FAIL", health_effect="NOT_HEALTHY")
    if rec.get("bindings") != {n: dict(bindings[n]) for n in sorted(bindings)}: return dict(base, overall="FAIL", reason="STORED_INPUT_BINDINGS_DIFFER_FROM_SUPPLIED", l1="PASS", l2="FAIL", health_effect="NOT_HEALTHY")
    v = SI.verify_source_values(journal=journal, store=store, feature_key=feature_key, bindings=bindings, fetch=fetch, series_hash=series_hash)
    if v["overall"] != "VERIFIED_RECOMPUTED":
        unavailable = any(s in ("UNRESOLVED", "MISSING") for s in v["inputs"].values())
        return dict(base, overall="UNAVAILABLE" if unavailable else "FAIL", reason="RECOMPUTATION_" + v["overall"] + ":" + v["reason"], l1="PASS", l2="UNAVAILABLE" if unavailable else "FAIL", health_effect="NOT_HEALTHY", inputs=v["inputs"])
    same = rec["values"] == v["recomputed"]
    return dict(base, stored_values_compared=True, overall="VERIFIED_STORED_EQUALS_RECOMPUTED" if same else "FAIL", reason="" if same else "STORED_VALUES_DIFFER_FROM_INDEPENDENT_RECOMPUTATION",
                l1="PASS", l2="PASS" if same else "FAIL", health_effect="NONE_ASSERTED" if same else "NOT_HEALTHY", inputs=v["inputs"], recomputed=v["recomputed"])
def _require_same_class(core, journal, store):
    """R38: Core plane, accepted journal and store must be ONE class before any read-for-recording or write (same rule as reverification._require_class, extended to the journal). A cross-plane combination would file a SIMULATION-derived L2 outcome into an ordinary Core HEAD."""
    want = SIMULATION if core.simulation else QUALIFIED
    got = (authority_class_of(journal), authority_class_of(store))
    if got != (want, want): raise Refusal("core plane %s, journal %s, store %s" % ((want,) + got), code="STORED_VALUES_CLASS_MISMATCH")
def record_stored_value_maintenance(core, *, journal, store, feature_key, bindings, fetch, series_hash, now, max_age) -> dict:
    """One bounded maintenance call: verify, then record the typed L2 outcome in the Core (CALLER_ASSERTED, see module doc). The result digest is the domain hash of the typed outcome. UNAVAILABLE/FAIL make the subject NOT HEALTHY in the Core's own calculation."""
    _require_same_class(core, journal, store)       # before ANY verification read or Core write
    r = verify_stored_values(journal=journal, store=store, feature_key=feature_key, bindings=bindings, fetch=fetch, series_hash=series_hash)
    digest = domain_hash("SALIX_STORED_VALUE_L2_V1", canonical_bytes({k: r[k] for k in ("overall", "reason", "l1", "l2", "stored_values_compared")}))
    core.record_verification(feature_key.key(), feature_key.feature_version, "REQUIRED", r["l2"], r["l1"], now, max_age, VERIFIER_ID, digest)
    return dict(r, result_digest=digest)

def verify_all_stored_segments(*, journal, store, feature_key, fetch, series_hash) -> dict:
    """R38 'compare stored values AS FOUND': enumerate EVERY stored segment under the accepted materialization and verify each against its OWN recorded bindings (re-fetched and re-hashed, independently recomputed). VERIFIED only when at least one segment exists and all verify; any FAIL -> FAIL; otherwise (none, or an unresolved input) -> UNAVAILABLE. Never an L1 fallback."""
    base = {"stream_verified": False, "provider_vintage_clock_proof": "HELD", "l1_fallback": False, "stored_values_compared": False}
    names, raw, p, why = SI._as_found(journal, store, feature_key)
    if names is None: return dict(base, overall="UNAVAILABLE", reason=why, l1="FAIL", l2="UNAVAILABLE", health_effect="NOT_HEALTHY", segments={})
    mh = accepted_as_found(journal, store, feature_key)[0]["materialization_hash"]; keys = sorted(store.list_prefix("%s%s/" % (STORED_PREFIX, mh)))
    if not keys: return dict(base, overall="UNAVAILABLE", reason="STORED_VALUES_ABSENT", l1="PASS", l2="UNAVAILABLE", health_effect="NOT_HEALTHY", segments={})
    out = {}
    for k in keys:
        got = store.get(k)
        try: rec = json.loads(got[0]); b = rec["bindings"]; assert _check_bindings(b)
        except Exception: out[k] = dict(base, overall="FAIL", reason="STORED_VALUES_UNPARSEABLE", l1="PASS", l2="FAIL", health_effect="NOT_HEALTHY"); continue
        if k != stored_values_key(mh, segment_id(b)) or rec.get("segment_id") != segment_id(b) or rec.get("materialization_hash") != mh or rec.get("feature_key") != feature_key.key():      # R39: the ENUMERATED key/body/segment/accepted identity must agree; never follow another record
            out[k] = dict(base, overall="FAIL", reason="STORED_VALUES_KEY_BODY_SEGMENT_MISMATCH", l1="PASS", l2="FAIL", health_effect="NOT_HEALTHY"); continue
        out[k] = verify_stored_values(journal=journal, store=store, feature_key=feature_key, bindings=b, fetch=fetch, series_hash=series_hash)
    ov = [v["overall"] for v in out.values()]; overall = "FAIL" if "FAIL" in ov else "UNAVAILABLE" if "UNAVAILABLE" in ov else "VERIFIED_STORED_EQUALS_RECOMPUTED"
    l1 = "FAIL" if any(v["l1"] == "FAIL" for v in out.values()) else "PASS"
    return dict(base, overall=overall, reason="" if overall.startswith("VERIFIED") else "SEGMENT_" + overall, l1=l1, l2="PASS" if overall.startswith("VERIFIED") else overall, stored_values_compared=overall.startswith("VERIFIED"), health_effect="NONE_ASSERTED" if overall.startswith("VERIFIED") else "NOT_HEALTHY", segments={k.rsplit("/", 1)[1]: v["overall"] for k, v in out.items()})
def record_stored_value_maintenance_all(core, *, journal, store, feature_key, fetch, series_hash, now, max_age) -> dict:
    _require_same_class(core, journal, store)
    r = verify_all_stored_segments(journal=journal, store=store, feature_key=feature_key, fetch=fetch, series_hash=series_hash)
    digest = domain_hash("SALIX_STORED_VALUE_L2_ALL_V1", canonical_bytes({k: r[k] for k in ("overall", "reason", "l1", "l2", "stored_values_compared", "segments")}))
    core.record_verification(feature_key.key(), feature_key.feature_version, "REQUIRED", r["l2"], r["l1"], now, max_age, VERIFIER_ID, digest)
    return dict(r, result_digest=digest)
from dataclasses import dataclass
@dataclass(frozen=True)
class StoredBinding:
    journal: object; store: object; feature_key: object; fetch: object; series_hash: object
def run_stored_value_pass(core, bindings: dict, subjects, events=(), *, now: int, max_age: int, max_items: int):
    """R38 due/trigger wiring (one bounded pass, NOT a daemon/cadence): work = Core-due subjects UNION supplied (subject, trigger) events, one item per subject (Core's own trigger wins), at most `max_items` (the rest reported SKIPPED_BOUND_EXCEEDED); a subject without a StoredBinding is UNBOUND. Each run records `request_reverification` then the all-segment maintenance outcome in the SAME Core. Unrelated healthy subjects are untouched."""
    if type(max_items) is not int or max_items < 1: raise Refusal("max_items", code="SCHEDULER_BOUND_INVALID")
    from .row_maintenance import RowBinding, record_row_maintenance
    vers = {k: b.feature_key.feature_version for k, b in bindings.items() if isinstance(b, (StoredBinding, RowBinding))}; work = {}
    for sub, trig in core.due_for_reverification(list(subjects), now, vers): work[sub] = trig
    for sub, trig in sorted(events): work.setdefault(sub, trig)
    out = []
    for n, sub in enumerate(sorted(work)):
        b = bindings.get(sub)
        if n >= max_items: out.append((sub, work[sub], "SKIPPED_BOUND_EXCEEDED", "")); continue
        if not isinstance(b, (StoredBinding, RowBinding)) or b.feature_key.key() != sub: out.append((sub, work[sub], "UNBOUND", "")); continue
        try:
            core.request_reverification(sub, work[sub]); r = (record_row_maintenance(core, b, now=now, max_age=max_age) if isinstance(b, RowBinding) else record_stored_value_maintenance_all(core, journal=b.journal, store=b.store, feature_key=b.feature_key, fetch=b.fetch, series_hash=b.series_hash, now=now, max_age=max_age)); out.append((sub, work[sub], "VERIFIED" if r["l2"] == "PASS" else "RECORDED_NOT_PASS", r["overall"]))
        except Refusal as e: out.append((sub, work[sub], "REFUSED", e.code))
    return out
