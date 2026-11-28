"""R40: E05 logical read model (11 tables, REF+hash on every row, rebuild only from canonical journals, drift/stale refusal, supersession). SQLite rehearsal; NOT Postgres/provider acceptance."""
import hashlib, unittest
from stage_a.errors import Refusal, IntegrityFailure
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.storage import e05_index as E, e05_sources as S
from .test_foundations import accepted_body
H = lambda x: hashlib.sha256(x.encode()).hexdigest()
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
def J(ns="XAUUSD/H4/mom3"):
    j = ObjectStoreJournal(InMemoryObjectStore(), ns, "w"); j.acquire_epoch(); return j
def seed(j):
    j.append(j.head(), "CANONICAL_ACCEPTED", accepted_body("1")); return j
AT = lambda r: 1000 + r.seq
class Tables(unittest.TestCase):
    def test_exactly_the_eleven_source_tables_with_their_listed_keys_and_indexes(self):
        self.assertEqual(len(E.TABLES), 11); self.assertEqual(E.TABLES["stagea_current_status"][0], ("subject_id", "materialization_version")); self.assertEqual(E.TABLES["stagea_transition_index"][1][:3], ("namespace_id", "epoch", "sequence")); self.assertEqual(E.UNIQUE["stagea_transition_index"], ("namespace_id", "epoch", "sequence"))
        c = E.E05Index()._c; names = {r[0] for r in c.execute("select name from sqlite_master where type='table'")}; self.assertTrue(set(E.TABLES) <= names)
        idx = {r[0] for r in c.execute("select name from sqlite_master where type='index' and name like 'stagea_%'")}; self.assertIn("stagea_manifest_index_feature_version", idx); self.assertIn("stagea_scheduler_queue_next_eligible_at", idx)
    def test_every_row_needs_columns_ref_and_a_64hex_hash_and_a_vintage_mode(self):
        x = E.E05Index(); ok = dict(job_id="j1", priority_class="p", next_eligible_at=1, family_id="f", ref="journal:XAUUSD/H4/mom3/1", ref_hash=H("a"), data_vintage_mode="M"); x.upsert_projection("stagea_scheduler_queue", ok)
        for bad, want in ((dict(ok, job_id="j2", ref_hash="zz"), "E05_ROW_CANONICAL_REF_HASH_REQUIRED"), (dict(ok, job_id="j3", ref=""), "E05_ROW_CANONICAL_REF_HASH_REQUIRED"), (dict(ok, job_id="j4", data_vintage_mode=""), "E05_ROW_VINTAGE_MODE_REQUIRED"), (dict(ok, job_id="j5", extra="x"), "E05_ROW_COLUMNS_INVALID"), ({k: v for k, v in dict(ok, job_id="j6").items() if k != "family_id"}, "E05_ROW_COLUMNS_INVALID"), (dict(ok), "E05_ROW_KEY_CONFLICT"), (dict(ok, job_id="j7", supersedes_ref=""), "E05_ROW_SUPERSESSION_INVALID")): self.assertEqual(code(x.upsert_projection, "stagea_scheduler_queue", bad), want, want)
        self.assertEqual(code(x.upsert_projection, "nope", ok), "E05_UNKNOWN_TABLE")
class Rebuild(unittest.TestCase):
    def setUp(self):
        self.j = seed(J()); self.x = E.E05Index(); self.src = {"XAUUSD/H4/mom3": S.journal_source(self.j, "XAUUSD/H4/mom3", epoch=1, accepted_at_of=AT)}; self.res = S.journal_resolver({"XAUUSD/H4/mom3": self.j}); self.h = lambda: (self.j.head().seq, self.j.head().hash)
    def test_rebuild_only_from_the_canonical_journal_then_lookups_and_the_current_status_head_resolve(self):
        self.x.rebuild(self.src); t = self.x.lookup("stagea_transition_index", {"transition_hash": self.j.read_from(1)[0].record_hash}, self.res); self.assertFalse(t.authoritative); self.assertEqual((t["ref"], t["sequence"]), ("journal:XAUUSD/H4/mom3/1", "1"))
        s = self.x.current_status("XAUUSD/H4/mom3", "1", "XAUUSD/H4/mom3", self.h(), self.res); self.assertEqual(s["ref"], "journal:XAUUSD/H4/mom3/1"); self.assertEqual(self.x.verify_all(self.res), 2)
    def test_stale_index_after_the_journal_head_moves_refuses_and_a_rebuild_recovers_it(self):
        self.x.rebuild(self.src); self.j.append(self.j.head(), "CANONICAL_ACCEPTED", accepted_body("2"))
        self.assertEqual(code(self.x.current_status, "XAUUSD/H4/mom3", "1", "XAUUSD/H4/mom3", self.h(), self.res), "STALE_INDEX"); self.x.rebuild(self.src); self.assertIsNotNone(self.x.current_status("XAUUSD/H4/mom3", "1", "XAUUSD/H4/mom3", self.h(), self.res)); self.assertIsNotNone(self.x.current_status("XAUUSD/H4/mom3", "2", "XAUUSD/H4/mom3", self.h(), self.res))
    def test_drift_a_row_whose_hash_or_ref_no_longer_matches_the_canonical_journal_fails_closed(self):
        self.x.rebuild(self.src); th = self.j.read_from(1)[0].record_hash
        self.x._c.execute("UPDATE stagea_transition_index SET ref_hash=?", (H("forged"),)); self.assertRaises(IntegrityFailure, self.x.lookup, "stagea_transition_index", {"transition_hash": th}, self.res); self.assertRaises(IntegrityFailure, self.x.verify_all, self.res)
        self.x.rebuild(self.src); self.x._c.execute("UPDATE stagea_transition_index SET ref='journal:XAUUSD/H4/mom3/9'"); self.assertRaises(IntegrityFailure, self.x.lookup, "stagea_transition_index", {"transition_hash": th}, self.res)
        self.x.rebuild(self.src); self.assertEqual(self.x.verify_all(self.res), 2)                                              # rebuild from canonical restores; nothing migrated
    def test_row_presence_is_not_authority_a_fabricated_row_with_a_ref_the_journal_lacks_is_refused(self):
        self.x.rebuild(self.src); self.x.upsert_projection("stagea_scheduler_queue", dict(job_id="ghost", priority_class="p", next_eligible_at=1, family_id="f", ref="journal:XAUUSD/H4/mom3/77", ref_hash=H("x"), data_vintage_mode="M"))
        self.assertRaises(IntegrityFailure, self.x.lookup, "stagea_scheduler_queue", {"job_id": "ghost"}, self.res)
    def test_source_time_must_be_supplied_a_moving_head_is_retried_then_refused_and_a_failed_rebuild_keeps_nothing_partial(self):
        self.assertEqual(code(self.x.rebuild, {"XAUUSD/H4/mom3": S.journal_source(self.j, "XAUUSD/H4/mom3", epoch=1, accepted_at_of=lambda r: None)}), "E05_SOURCE_TIME_NOT_SUPPLIED"); self.assertEqual(self.x._c.execute("select count(*) from stagea_transition_index").fetchone()[0], 0)
        n = []; h, r = self.src["XAUUSD/H4/mom3"]
        def moving(): n.append(1); return (len(n), "h")
        self.assertEqual(code(self.x.rebuild, {"XAUUSD/H4/mom3": (moving, r)}), "E05_REBUILD_SOURCE_HEAD_UNSTABLE"); self.assertEqual(code(self.x.rebuild, {}), "E05_REBUILD_INPUT_INVALID")
    def test_rebuild_is_idempotent_and_the_unique_namespace_epoch_sequence_is_enforced(self):
        self.x.rebuild(self.src); a = self.x._c.execute("select * from stagea_transition_index").fetchall(); self.x.rebuild(self.src); self.assertEqual(a, self.x._c.execute("select * from stagea_transition_index").fetchall())
        r = dict(transition_hash=H("t2"), namespace_id="XAUUSD/H4/mom3", epoch=1, sequence=1, subject_id="s", accepted_at=1, ref="journal:XAUUSD/H4/mom3/1", ref_hash=H("t2"), data_vintage_mode="M"); self.assertEqual(code(self.x.upsert_projection, "stagea_transition_index", r), "E05_ROW_KEY_CONFLICT")
class Supersede(unittest.TestCase):
    def test_fit_generation_projection_requires_instrument_and_timeframe(self):
        # E09-H1 (R54): a fit-generation projection row without INSTRUMENT_ID/TIMEFRAME is refused; fit_generation_ref is an opaque Ref with no shown global uniqueness.
        base = dict(fit_generation_ref="fg1", feature_id="f", feature_version="1", instrument_id="XAUUSD", timeframe="H4", available_asof=1, ref="r1", ref_hash=H("1"), data_vintage_mode="M", supersedes_ref=None)
        for k in ("instrument_id", "timeframe"):
            d = {x: v for x, v in base.items() if x != k}; self.assertEqual(code(E.E05Index().upsert_projection, "stagea_fit_generation_index", d), "E05_ROW_COLUMNS_INVALID", k)
        E.E05Index().upsert_projection("stagea_fit_generation_index", base)
    def _fit(self, x, n, asof, sup=None): x.upsert_projection("stagea_fit_generation_index", dict(fit_generation_ref="fg%d" % n, feature_id="f", feature_version="1", instrument_id="XAUUSD", timeframe="H4", available_asof=asof, ref="r%d" % n, ref_hash=H(str(n)), data_vintage_mode="M", supersedes_ref=sup))
    def test_current_excludes_superseded_as_known_ignores_later_supersession_and_forks_cycles_refuse(self):
        x = E.E05Index(); self._fit(x, 1, 10); self._fit(x, 2, 20, "r1"); self._fit(x, 3, 30, "r2"); self.assertEqual(x.current_rows("stagea_fit_generation_index"), ["r3"]); self.assertEqual(x.as_known_rows("stagea_fit_generation_index", 25), ["r1", "r2"]); self.assertEqual(x.as_known_rows("stagea_fit_generation_index", 5), [])
        self.assertEqual(code(x.as_known_rows, "stagea_manifest_index", 5), "E05_AS_KNOWN_NOT_DEFINED_FOR_TABLE"); self.assertEqual(code(x.as_known_rows, "stagea_fit_generation_index", "5"), "E05_KEY_INVALID")
        self._fit(x, 4, 40, "r2"); self.assertEqual(code(x.current_rows, "stagea_fit_generation_index"), "E05_SUPERSESSION_FORK")
        y = E.E05Index(); self._fit(y, 1, 10, "r2"); self._fit(y, 2, 20, "r1"); self.assertEqual(code(y.current_rows, "stagea_fit_generation_index"), "E05_SUPERSESSION_CYCLE")
if __name__ == "__main__": unittest.main()
