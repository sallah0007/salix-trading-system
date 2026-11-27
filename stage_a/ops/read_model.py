"""E-05: explicit rebuildable read-model projections. NON-CANONICAL: no row grants authority by presence; every projected row carries the canonical object/transition REF + hash it was rebuilt from; `rebuild` drops and recreates the projections EXCLUSIVELY from supplied canonical artifacts.
`TABLES` is the logical table list of Build Plan E-05 (PK + index columns). `ddl()` renders PostgreSQL DDL TEXT only - nothing here connects to or deploys a database. An in-memory backend is provided for rebuild/refusal tests."""
from ..errors import Refusal
TABLES = {
 "stagea_manifest_index": (("manifest_hash",), ("feature_id", "feature_version", "status_projection")),
 "stagea_fit_generation_index": (("fit_generation_ref",), ("feature_id", "feature_version", "available_asof")),
 "stagea_pending_row_index": (("row_content_hash",), ("feature_id", "materialization_version", "event_time", "state")),
 "stagea_transition_index": (("transition_hash",), ("namespace_id", "epoch", "sequence", "subject_id", "accepted_at")),
 "stagea_current_status": (("subject_id", "materialization_version"), ()),
 "stagea_consumer_binding_index": (("consumer_binding_id",), ("consumer_id", "purpose", "decision_window", "final_package_hash")),
 "stagea_non_delivery_index": (("non_delivery_resolution_id",), ("resolution_identity", "reason_code", "expected_dependency_key")),
 "stagea_health_index": (("health_evidence_id",), ("subject_id", "observed_at", "local_state", "carried_upstream_state")),
 "stagea_event_context_index": (("event_context_identity",), ("available_asof", "event_time", "applicability_map_ref")),
 "stagea_scheduler_queue": (("job_id",), ("priority_class", "next_eligible_at", "family_id")),
 "stagea_replay_queue": (("replay_job_id",), ("status", "namespace_id", "requested_at")),
}
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
    def __init__(self): self._t = {t: {} for t in TABLES}
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
    def rebuild(self, canonical_rows):
        """canonical_rows: iterable of (table, row) DERIVED FROM canonical artifacts/journal by the caller. Drops every projection first; a failure part-way leaves the model EMPTY (fail closed), never half-old."""
        self._t = {t: {} for t in TABLES}
        try:
            for table, row in canonical_rows: self.upsert(table, row)
        except BaseException:
            self._t = {t: {} for t in TABLES}; raise
        return sum(len(v) for v in self._t.values())
