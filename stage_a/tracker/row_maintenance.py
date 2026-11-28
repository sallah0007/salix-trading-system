"""R53 generic per-ROW L2 maintenance (Registry p203-212: L2 independently recomputes stored/materialized values from authoritative inputs; a REQUIRED L2 that is unavailable is UNKNOWN/NOT_HEALTHY and L1 never substitutes; the verifier path differs from the producer; FrozenParent p455-465: every registered feature resolves its inputs, predecessor, step and independent verification).

REUSES existing pieces only: the committed `PendingRowStore` rows (INPUT_REFS, predecessor, state schema/version), the ROW_ACCEPTED records, the independent `verify_row_step` through a SUPPLIED profile port (the same port the separated row handlers use), the Core `record_verification`, and the existing StoredBinding maintenance scope (`run_stored_value_pass` dispatches here; a RowBinding may carry the feature-version `StoredBinding` and the two results are combined WORST-OF in ONE Core record, because the Core holds one health slot per subject and a later PASS must not mask an earlier FAIL).

Per stored row of the feature: re-read the row (bytes re-hashed, independent hash recomputed), its predecessor, its inputs; re-run the independent verifier; the re-derived result hash must equal the evidence hash the ACCEPTED record carries. PASS => VERIFIED. Verifier FAIL / unreadable or corrupt stored row / predecessor / differing evidence => FAIL. Inputs not re-readable, profile ports or schema/invariant identity unbound => UNAVAILABLE (never PASS, never the L1 result). A stored row with no ROW_ACCEPTED record is PENDING (listed, not part of the accepted set); zero accepted rows is UNAVAILABLE, not a completed search.
The original accepted records are untouched: this pass only RECORDS current trust in the Core. Not appointed: no real profile, input codec, hash rule, source, currentness, cadence or calendar is defined here; a SUPPLIED profile is the instance, and an absent/incomplete one is HELD. Candidate/SIM; clears no gate or hold."""
import json
from dataclasses import dataclass
from typing import Any, Optional
from ..errors import Refusal, IntegrityFailure
from ..storage.byte_primitives import canonical_bytes, domain_hash
from ..schema import independent as X
from . import row_acceptance as RA
from .materialization import row_store as RS
from .verification.row_step_verifier import verify_row_step, SCOPE_ROW_STEP
from .verification.verification_result import PASS, FAIL
VERIFIER_ID = "tracker.row_maintenance.verify_stored_rows"
NEED = ("tables", "schema", "schema_registry", "reference_step", "decode", "encode", "resolve_inputs", "input_symbols")

@dataclass(frozen=True)
class RowBinding:
    journals: Any; rows: Any; store: Any; feature_key: Any; profile: Optional[dict]; segments: Any = None      # segments: the feature-version StoredBinding, if the feature also has one
    @property
    def journal(self): return self.journals

def _profile_ok(p): return isinstance(p, dict) and all(k in p and p[k] is not None for k in NEED)
def _attribute(store):
    """(hash -> fields) for every stored row sidecar. A sidecar that cannot be parsed cannot be attributed to any feature: returned separately (fail-closed for every row-maintained feature; disclosed blast radius)."""
    ok, bad = {}, []
    for k in sorted(store.list_prefix("pending-row-fields/")):
        h = k.rsplit("/", 1)[-1]; got = store.get("pending-row-fields/" + h)
        try: ok[h] = RS._from_json(got[0])
        except Exception: bad.append(h)
    return ok, bad
def _accepted(journals, row, h):
    j = journals.journal(RA.row_namespace(row)); head = j.head(); hit = None
    if head.seq:
        for r in j.read_from(1):
            if r.seq > head.seq: break
            b = json.loads(r.body_json)
            if b.get("row_content_hash") == h: hit = b
    return hit
def verify_stored_rows(b: RowBinding) -> dict:
    base = {"stream_verified": False, "provider_vintage_clock_proof": "HELD", "l1_fallback": False, "stored_values_compared": False, "route": "ROWS"}
    fk = b.feature_key
    if not _profile_ok(b.profile): return dict(base, overall="UNAVAILABLE", reason="ROW_PROFILE_HELD", l1="PASS", l2="UNAVAILABLE", health_effect="NOT_HEALTHY", rows={})
    from . import accepted_manifest as AM
    try: mh = AM.read_accepted_manifest(b.journals.journal(fk.namespace()), b.store, fk).manifest_hash
    except (Refusal, IntegrityFailure, KeyError, ValueError, TypeError): return dict(base, overall="UNAVAILABLE", reason="ACCEPTED_MANIFEST_UNAVAILABLE", l1="FAIL", l2="UNAVAILABLE", health_effect="NOT_HEALTHY", rows={})
    fields, bad = _attribute(b.store)
    if bad: return dict(base, overall="FAIL", reason="STORED_ROW_SIDECAR_UNATTRIBUTABLE", l1="FAIL", l2="FAIL", health_effect="NOT_HEALTHY", rows={h: "UNATTRIBUTABLE" for h in bad})
    out, p = {}, b.profile
    for h in sorted(fields):
        row = fields[h]
        if row.feature_version != fk.feature_version or row.quant_manifest_hash.hex() != mh: continue          # ATTRIBUTION by the ACCEPTED manifest hash + version (subject-bound); no symbol<->byte-id equality is guessed
        acc = _accepted(b.journals, row, h)
        if acc is None: out[h] = ("PENDING", "NO_ROW_ACCEPTED_RECORD"); continue
        try:
            rows = b.rows; stored = rows.load(h); pred = None if stored.predecessor_row_hash is None else rows.load(stored.predecessor_row_hash.hex())
        except (IntegrityFailure, Refusal, KeyError, ValueError, TypeError) as e: out[h] = ("FAIL", "STORED_ROW_OR_PREDECESSOR_UNREADABLE:" + getattr(e, "code", type(e).__name__)); continue
        try:
            res = verify_row_step(row=stored, predecessor=pred, schema=p["schema"], reference_step=p["reference_step"], decode=p["decode"], encode=p["encode"], resolve_inputs=p["resolve_inputs"], input_symbols=p["input_symbols"],
                                  recompute_row_hash=lambda r: X.row_hash(RS.independent_dict(p["tables"], r), p["tables"].enums).hex(), expect_row_hash=h, schema_registry=p["schema_registry"], invariant_resolver=p.get("invariant_resolver"))
        except Exception as e: out[h] = ("UNAVAILABLE", "ROW_VERIFIER_PORT_ERROR:" + type(e).__name__); continue
        if res.scope != SCOPE_ROW_STEP: out[h] = ("FAIL", "VERIFIER_SCOPE"); continue
        if res.status == FAIL: out[h] = ("FAIL", "ROW_REVERIFICATION_FAIL:" + ",".join(res.reasons)); continue
        if res.status != PASS: out[h] = ("UNAVAILABLE", "ROW_REVERIFICATION_" + res.status + ":" + ",".join(res.reasons)); continue
        ev = acc.get("verification_evidence_ref"); ok = isinstance(ev, list) and len(ev) == 4 and ev[3] == res.result_hash
        out[h] = ("VERIFIED", "") if ok else ("FAIL", "ROW_REVERIFICATION_DIFFERS_FROM_ACCEPTED_EVIDENCE")
    counted = {h: v for h, v in out.items() if v[0] != "PENDING"}; st = [v[0] for v in counted.values()]
    if not counted: overall, reason = "UNAVAILABLE", "ACCEPTED_ROWS_ABSENT"
    elif "FAIL" in st: overall, reason = "FAIL", "ROW_" + "FAIL"
    elif "UNAVAILABLE" in st: overall, reason = "UNAVAILABLE", "ROW_UNAVAILABLE"
    else: overall, reason = "VERIFIED_ROWS_EQUAL_RECOMPUTED", ""
    good = overall.startswith("VERIFIED")
    return dict(base, overall=overall, reason=reason, l1="PASS", l2="PASS" if good else overall, stored_values_compared=good, health_effect="NONE_ASSERTED" if good else "NOT_HEALTHY", rows={h[:16]: v for h, v in sorted(out.items())})
_RANK = {"PASS": 0, "UNAVAILABLE": 1, "FAIL": 2}
def verify_feature(b: RowBinding) -> dict:
    """Rows, and (when the feature also carries a feature-version StoredBinding) its segments; the WORST of the two is the single L2 outcome (FAIL > UNAVAILABLE > PASS). L1 stays the as-found binding (FAIL if either L1 FAIL)."""
    from . import stored_values as SV
    r = verify_stored_rows(b)
    if b.segments is None: return r
    s = SV.verify_all_stored_segments(journal=b.segments.journal, store=b.segments.store, feature_key=b.segments.feature_key, fetch=b.segments.fetch, series_hash=b.segments.series_hash)
    worst = r if _RANK[r["l2"]] >= _RANK[s["l2"]] else s
    return dict(r, overall=worst["overall"], reason=("ROWS:%s|SEGMENTS:%s" % (r["overall"], s["overall"])) if worst["l2"] != "PASS" else "", l1="FAIL" if "FAIL" in (r["l1"], s["l1"]) else "PASS", l2=worst["l2"],
                health_effect="NONE_ASSERTED" if worst["l2"] == "PASS" else "NOT_HEALTHY", stored_values_compared=r["stored_values_compared"] and s["stored_values_compared"], segments_overall=s["overall"], segments=s.get("segments", {}))
def record_row_maintenance(core, b: RowBinding, *, now, max_age) -> dict:
    from . import stored_values as SV
    SV._require_same_class(core, b.journals, b.store)
    r = verify_feature(b)
    digest = domain_hash("SALIX_ROW_L2_V1", canonical_bytes({k: r[k] for k in ("overall", "reason", "l1", "l2", "stored_values_compared", "rows")}))
    core.record_verification(b.feature_key.key(), b.feature_key.feature_version, "REQUIRED", r["l2"], r["l1"], now, max_age, VERIFIER_ID, digest)
    return dict(r, result_digest=digest)
