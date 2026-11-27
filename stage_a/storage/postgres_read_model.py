"""Derived read model. NAME follows the plan; the engine here is stdlib sqlite3 because no Postgres provider is
selected (R5 OPEN). It is a rebuildable projection: it holds no authority, and a read from a model that is not at
the journal head is refused (stale sidecar)."""
import sqlite3
from ..errors import Refusal, IntegrityFailure
from ..replay import replay

class ReadModel:
    def __init__(self):
        self._c = sqlite3.connect(":memory:", check_same_thread=False)
        self._c.execute("CREATE TABLE status(namespace TEXT, version TEXT, status TEXT, accepted_seq INT, "
                        "publishable_seq INT, PRIMARY KEY(namespace, version))")
        self._c.execute("CREATE TABLE meta(namespace TEXT PRIMARY KEY, seq INT, hash TEXT)")

    def rebuild(self, namespace: str, journal):
        recs = journal.read_from(1)
        states = replay(namespace, recs)
        head = journal.head()
        with self._c:
            self._c.execute("DELETE FROM status WHERE namespace=?", (namespace,))
            for s in states.values():
                self._c.execute("INSERT INTO status VALUES(?,?,?,?,?)",
                                (namespace, s.version, s.status, s.accepted_seq, s.publishable_seq))
            self._c.execute("INSERT OR REPLACE INTO meta VALUES(?,?,?)", (namespace, head.seq, head.hash))

    def _require_fresh(self, namespace, journal):
        row = self._c.execute("SELECT seq,hash FROM meta WHERE namespace=?", (namespace,)).fetchone()
        h = journal.head()
        if row is None or row != (h.seq, h.hash):
            raise Refusal("read model at %s, journal at %s" % (row, (h.seq, h.hash)), code="STALE_READ_MODEL")

    def status(self, namespace: str, version: str, journal):
        self._require_fresh(namespace, journal)
        row = self._c.execute("SELECT status FROM status WHERE namespace=? AND version=?",
                              (namespace, version)).fetchone()
        return None if row is None else row[0]

    def verify_against(self, namespace: str, journal):
        self._require_fresh(namespace, journal)
        want = {(s.version, s.status) for s in replay(namespace, journal.read_from(1)).values()}
        have = set(self._c.execute("SELECT version,status FROM status WHERE namespace=?", (namespace,)))
        if want != have:
            raise IntegrityFailure("read model drift: %s vs %s" % (sorted(have), sorted(want)))
