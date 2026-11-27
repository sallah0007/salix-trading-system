"""E-05: explicit rebuildable read-model projections. NON-CANONICAL: no row grants authority by presence; every projected row carries the canonical object/transition REF + hash it was rebuilt from; `rebuild` drops and recreates the projections EXCLUSIVELY from supplied canonical artifacts.
`TABLES` is the logical table list of Build Plan E-05 (PK + index columns). `ddl()` renders PostgreSQL DDL TEXT only - nothing here connects to or deploys a database. An in-memory backend is provided for rebuild/refusal tests."""
from ..errors import Refusal
TABLES = {
 "stagea_manifest_index": (("manifest_hash",), ("feature_id", "feature_version", "status_projection", "data_vintage_mode", "supersession_ref")),
 "stagea_fit_generation_index": (("fit_generation_ref",), ("feature_id", "feature_version", "instrument_id", "timeframe", "available_asof")),
 "stagea_pending_row_index": (("row_content_hash",), ("feature_id", "materialization_version", "instrument_id", "timeframe", "event_time", "state", "data_vintage_mode", "supersession_ref")),
 "stagea_transition_index": (("transition_hash",), ("namespace_id", "epoch", "sequence", "subject_id", "accepted_at")),
 "stagea_current_status": (("subject_id", "materialization_version", "instrument_id", "timeframe"), ("data_vintage_mode", "supersession_ref", "head_hash")),
 "stagea_consumer_binding_index": (("consumer_binding_id",), ("consumer_id", "purpose", "decision_window", "final_package_hash")),
 "stagea_non_delivery_index": (("non_delivery_resolution_id",), ("resolution_identity", "reason_code", "expected_dependency_key")),
 "stagea_health_index": (("health_evidence_id",), ("subject_id", "observed_at", "local_state", "carried_upstream_state")),
 "stagea_event_context_index": (("event_context_identity",), ("available_asof", "event_time", "applicability_map_ref")),
 "stagea_scheduler_queue": (("job_id",), ("priority_class", "next_eligible_at", "family_id")),
 "stagea_replay_queue": (("replay_job_id",), ("status", "namespace_id", "requested_at")),
}
# Build Plan overlays applied: R3 E05-L1 (DATA_VINTAGE_MODE + supersession lineage on row/status projections), R3 E09-H1 (INSTRUMENT_ID/TIMEFRAME on feature-scoped projections; part of the current-status PK), R3 E01-H1 (a projection is usable only when proven caught up to the accepted HEAD).
PROVENANCE = ("canonical_ref", "canonical_hash")
def ddl() -> str:
    out = []
    for t, (pk, ix) in TABLES.items():
        cols = sorted(set(pk) | set(ix) | set(PROVENANCE)); out.append("CREATE TABLE %s (\n  %s,\n  PRIMARY KEY (%s)\n);" % (t, ",\n  ".join(c + " TEXT NOT NULL" for c in cols), ", ".join(pk)))
        if t == "stagea_transition_index": out.append("CREATE UNIQUE INDEX %s_ns_epoch_seq ON %s (namespace_id, epoch, sequence);" % (t, t))
        for c in ix: out.append("CREATE INDEX %s_%s ON %s (%s);" % (t, c, t, c))
    return "\n".join(out)
class ProjectedRow(dict):
    """A read-model row: DATA ONLY. `authoritative` is always False; code that needs authority must go back to the canonical object named by canonical_ref/canonical_hash."""
    authoritative = False
class ReadModel:
    def __init__(self): self._t = {t: {} for t in TABLES}; self._built_from_head = None
    def built_from_head(self): return self._built_from_head
    def require_caught_up(self, accepted_head_hash: str):
        """E01-H1: publication/Gateway eligibility derives from the accepted journal, or from a projection PROVEN caught up to that exact accepted HEAD; missing/stale/inconsistent -> fail closed (repair idempotently from the journal, then retry)."""
        if not isinstance(accepted_head_hash, str) or not accepted_head_hash or self._built_from_head != accepted_head_hash: raise Refusal("projection", code="READ_MODEL_NOT_CAUGHT_UP")
    def upsert(self, table: str, row: dict):
        if table not in TABLES: raise Refusal(table, code="READ_MODEL_TABLE_UNKNOWN")
        pk, ix = TABLES[table]; need = set(pk) | set(ix) | set(PROVENANCE)
        if not isinstance(row, dict) or set(row) != need or not all(isinstance(v, str) and v for v in row.values()): raise Refusal(table, code="READ_MODEL_ROW_MALFORMED")      # a row without canonical ref+hash is refused
        k = tuple(row[c] for c in pk); old = self._t[table].get(k)
        if old is not None and old != row and (old["canonical_ref"], old["canonical_hash"]) != (row["canonical_ref"], row["canonical_hash"]): raise Refusal(str(k), code="READ_MODEL_ROW_PROVENANCE_CONFLICT")
        self._t[table][k] = dict(row)
    def get(self, table: str, *key):
        r = self._t[table].get(tuple(key)); return None if r is None else ProjectedRow(r)
    def snapshot(self): return {t: dict(sorted(rows.items())) for t, rows in self._t.items()}
    def rebuild(self, canonical_rows, built_from_head=None):
        """canonical_rows: iterable of (table, row) DERIVED FROM canonical artifacts/journal by the caller. Drops every projection first; a failure part-way leaves the model EMPTY (fail closed), never half-old."""
        self._t = {t: {} for t in TABLES}; self._built_from_head = None
        try:
            for table, row in canonical_rows: self.upsert(table, row)
        except BaseException:
            self._t = {t: {} for t in TABLES}; self._built_from_head = None; raise
        self._built_from_head = built_from_head
        return sum(len(v) for v in self._t.values())
