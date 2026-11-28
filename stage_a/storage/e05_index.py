"""R40: the E05 LOGICAL read-model interface (Build Plan 1CVUUPJ4... lines 2126-2166; R3 E05-L1 p1087-1089): the eleven `stagea_*` tables, their primary keys and indexed columns exactly as listed there, over a SQL backend adapter (a labelled CANDIDATE sqlite rehearsal; NOT deployed Postgres, NOT provider acceptance).
Rules carried (cited by line, text not copied):
  * 2164: EVERY projected row carries the canonical object/transition REF and its content HASH (`ref`, `ref_hash`); a row without both is refused;
  * 2165: the index is rebuilt EXCLUSIVELY from canonical artifacts/journals through SUPPLIED source adapters (`rebuild`); nothing is written from anywhere else except `upsert_projection` used by the same adapters;
  * 2163: row presence grants NO authority: `lookup` returns an `IndexedRow` that is never `authoritative`, and re-resolves the canonical ref through a supplied resolver, refusing a hash that differs (DRIFT);
  * `stagea_current_status` holds the projected transition HEAD ONLY and is read only when the index head equals the journal head (`STALE_INDEX` otherwise; the existing sidecar/head-matching rule);
  * E05-L1: every row has `data_vintage_mode` and `supersedes_ref` (explicit supersession lineage); `current_rows` = rows no other row supersedes (a fork or cycle REFUSES); `as_known_rows` is defined only for tables that carry an as-of column.
HELD (not invented): extra column payloads/byte definitions (a `payload` TEXT column carries caller JSON, labelled candidate), the vintage-mode vocabulary (any non-empty string is carried, never interpreted), retention. Legacy E09/E10 history is only READ by adapters; this module never rekeys or migrates canonical bytes."""
import json, re, sqlite3
from ..errors import Refusal, IntegrityFailure
TABLES = {   # name: (primary key, indexed columns [each its own index], as-of column or None)
    "stagea_manifest_index": (("manifest_hash",), ("feature_id", "feature_version", "status_currentness"), None),
    "stagea_fit_generation_index": (("fit_generation_ref",), ("feature_id", "feature_version", "instrument_id", "timeframe", "available_asof"), "available_asof"),   # E09-H1: a feature-scoped fit-generation namespace MUST carry INSTRUMENT_ID and TIMEFRAME unless the governing schema defines the ID globally unique over them (fit_generation_ref is an opaque Ref; no such uniqueness is shown), so the projection carries both (R54)
    "stagea_pending_row_index": (("row_content_hash",), ("feature_id", "materialization_version", "event_time", "state"), None),
    "stagea_transition_index": (("transition_hash",), ("namespace_id", "epoch", "sequence", "subject_id", "accepted_at"), None),
    "stagea_current_status": (("subject_id", "materialization_version"), (), None),
    "stagea_consumer_binding_index": (("consumer_binding_id",), ("consumer_id", "purpose", "decision_window", "final_package_hash"), None),
    "stagea_non_delivery_index": (("non_delivery_resolution_id",), ("resolution_identity", "reason_code", "expected_dependency_key"), None),
    "stagea_health_index": (("health_evidence_id",), ("subject_id", "observed_at", "local_state", "carried_upstream_state"), None),
    "stagea_event_context_index": (("event_context_identity",), ("available_asof", "event_time", "applicability_map_ref"), "available_asof"),
    "stagea_scheduler_queue": (("job_id",), ("priority_class", "next_eligible_at", "family_id"), None),
    "stagea_replay_queue": (("replay_job_id",), ("status", "namespace_id", "requested_at"), None)}
UNIQUE = {"stagea_transition_index": ("namespace_id", "epoch", "sequence")}       # UNIQUE(namespace_id, epoch, sequence)
COMMON = ("ref", "ref_hash", "data_vintage_mode", "supersedes_ref", "payload")
_ID = re.compile(r"^[a-z_]+$"); _HASH = re.compile(r"^[0-9a-f]{64}$")
def _cols(t): pk, ix, _ = TABLES[t]; return tuple(dict.fromkeys(pk + ix))
class IndexedRow(dict):
    authoritative = False                                   # 2163: a row is a pointer, never authority
class E05Index:
    def __init__(self, conn=None):
        self._c = conn or sqlite3.connect(":memory:", check_same_thread=False); self._create(); self.rebuilds = 0
    def _create(self):
        for t, (pk, ix, _) in TABLES.items():
            assert _ID.match(t); cols = _cols(t)
            self._c.execute("CREATE TABLE IF NOT EXISTS %s(%s, ref TEXT NOT NULL, ref_hash TEXT NOT NULL, data_vintage_mode TEXT NOT NULL, supersedes_ref TEXT, payload TEXT, PRIMARY KEY(%s)%s)" % (t, ", ".join(c + " TEXT" for c in cols), ", ".join(pk), (", UNIQUE(%s)" % ", ".join(UNIQUE[t])) if t in UNIQUE else ""))
            for c in ix:
                if c not in pk: self._c.execute("CREATE INDEX IF NOT EXISTS %s_%s ON %s(%s)" % (t, c, t, c))
        self._c.execute("CREATE TABLE IF NOT EXISTS stagea_index_meta(source TEXT PRIMARY KEY, seq INT, hash TEXT)")
    def upsert_projection(self, table, row):
        if table not in TABLES: raise Refusal(str(table), code="E05_UNKNOWN_TABLE")
        cols = _cols(table); allowed = set(cols) | set(COMMON)
        if not isinstance(row, dict) or set(row) - allowed or any(c not in row for c in cols): raise Refusal(table, code="E05_ROW_COLUMNS_INVALID")
        if not (isinstance(row.get("ref"), str) and row["ref"] and isinstance(row.get("ref_hash"), str) and _HASH.match(row["ref_hash"])): raise Refusal(table, code="E05_ROW_CANONICAL_REF_HASH_REQUIRED")      # 2164
        if not (isinstance(row.get("data_vintage_mode"), str) and row["data_vintage_mode"]): raise Refusal(table, code="E05_ROW_VINTAGE_MODE_REQUIRED")
        if row.get("supersedes_ref") is not None and not (isinstance(row["supersedes_ref"], str) and row["supersedes_ref"]): raise Refusal(table, code="E05_ROW_SUPERSESSION_INVALID")
        if any(not isinstance(row[c], (str, int)) or isinstance(row[c], bool) for c in cols): raise Refusal(table, code="E05_ROW_COLUMNS_INVALID")
        vals = [str(row[c]) for c in cols] + [row["ref"], row["ref_hash"], row["data_vintage_mode"], row.get("supersedes_ref"), json.dumps(row.get("payload"), sort_keys=True) if row.get("payload") is not None else None]
        names = list(cols) + list(COMMON)
        try: self._c.execute("INSERT INTO %s(%s) VALUES(%s)" % (table, ",".join(names), ",".join("?" * len(names))), vals)
        except sqlite3.IntegrityError: raise Refusal(table, code="E05_ROW_KEY_CONFLICT")                       # a projection key is written once per rebuild; a differing duplicate never overwrites
    def rebuild(self, sources, *, max_attempts=3):
        """sources: {source_name: (head_fn, rows_fn)} where rows_fn() yields (table, row) FROM canonical artifacts/journals and head_fn() -> (seq, hash). The whole index is rebuilt in one transaction; if any source head moved while its rows were read, the attempt is discarded and retried (bounded), then refused. Rows that fail validation abort the rebuild (nothing partial is kept)."""
        if not (isinstance(sources, dict) and sources) or type(max_attempts) is not int or max_attempts < 1: raise Refusal("sources", code="E05_REBUILD_INPUT_INVALID")
        for _ in range(max_attempts):
            before = {n: tuple(h()) for n, (h, r) in sources.items()}
            try:
                with self._c:
                    for t in TABLES: self._c.execute("DELETE FROM " + t)
                    self._c.execute("DELETE FROM stagea_index_meta")
                    for n, (h, r) in sources.items():
                        for t, row in r(): self.upsert_projection(t, row)
                    after = {n: tuple(h()) for n, (h, r) in sources.items()}
                    if after != before: raise _Moved()
                    for n, hd in before.items(): self._c.execute("INSERT INTO stagea_index_meta VALUES(?,?,?)", (n, hd[0], hd[1]))
                self.rebuilds += 1; return before
            except _Moved: continue
        raise Refusal("source head kept moving", code="E05_REBUILD_SOURCE_HEAD_UNSTABLE")
    def _require_head(self, source, head):
        row = self._c.execute("SELECT seq,hash FROM stagea_index_meta WHERE source=?", (source,)).fetchone()
        if row is None or tuple(row) != tuple(head): raise Refusal("index at %s, source at %s" % (row, tuple(head)), code="STALE_INDEX")
    def current_status(self, subject_id, materialization_version, source, head, resolver):
        """The projected transition HEAD only; refused unless the index equals the exact source head; the canonical ref is re-resolved (hash must match)."""
        self._require_head(source, head); return self.lookup("stagea_current_status", {"subject_id": subject_id, "materialization_version": materialization_version}, resolver)
    def lookup(self, table, key, resolver):
        if table not in TABLES: raise Refusal(str(table), code="E05_UNKNOWN_TABLE")
        pk = TABLES[table][0]
        if not (isinstance(key, dict) and set(key) == set(pk)): raise Refusal(table, code="E05_KEY_INVALID")
        cur = self._c.execute("SELECT * FROM %s WHERE %s" % (table, " AND ".join(c + "=?" for c in pk)), [str(key[c]) for c in pk]); cols = [d[0] for d in cur.description]; r = cur.fetchone()
        if r is None: return None
        row = IndexedRow(zip(cols, r)); got = resolver(row["ref"])
        if got is None: raise IntegrityFailure("E05 DRIFT: canonical ref %s no longer resolves" % row["ref"])
        if got != row["ref_hash"]: raise IntegrityFailure("E05 DRIFT: ref %s hash %s != indexed %s" % (row["ref"], got, row["ref_hash"]))
        return row
    def verify_all(self, resolver):
        """Re-resolve every indexed ref; returns the number checked or raises DRIFT."""
        n = 0
        for t in TABLES:
            for (ref, h) in self._c.execute("SELECT ref, ref_hash FROM %s" % t).fetchall():
                got = resolver(ref)
                if got != h: raise IntegrityFailure("E05 DRIFT in %s: %s" % (t, ref))
                n += 1
        return n
    def current_rows(self, table):
        """Rows no other row supersedes. A row superseded twice (fork), a dangling supersession to nowhere is allowed (the predecessor may be outside this index) but a cycle REFUSES."""
        if table not in TABLES: raise Refusal(str(table), code="E05_UNKNOWN_TABLE")
        rows = self._c.execute("SELECT ref, supersedes_ref FROM %s" % table).fetchall(); sup = {}
        for ref, s in rows:
            if s is None: continue
            if s in sup: raise Refusal(s, code="E05_SUPERSESSION_FORK")
            sup[s] = ref
        for start in sup:
            seen, cur = {start}, sup.get(start)
            while cur is not None:
                if cur in seen: raise Refusal(start, code="E05_SUPERSESSION_CYCLE")
                seen.add(cur); cur = sup.get(cur)
        refs = [r for r, _ in rows if r not in sup]; return sorted(refs)
    def as_known_rows(self, table, asof):
        col = TABLES[table][2] if table in TABLES else None
        if col is None: raise Refusal(str(table), code="E05_AS_KNOWN_NOT_DEFINED_FOR_TABLE")
        if type(asof) is not int: raise Refusal("asof", code="E05_KEY_INVALID")
        return sorted(r for (r, a) in self._c.execute("SELECT ref, %s FROM %s" % (col, table)).fetchall() if int(a) <= asof)          # later supersession is NOT applied: what was knowable at asof
class _Moved(Exception): pass
