"""Unknown-commit resolution, orphan discovery, cold rebuild."""
from ..errors import Refusal
from ..storage.keys import journal_prefix, journal_key
from tracker_component.journal_port import verify_chain, Head

COMMITTED = "COMMITTED"
NOT_COMMITTED = "NOT_COMMITTED"

def resolve_unknown_commit(journal, *, kind: str, body_json: str) -> str:
    """After UnknownCommit, decide by reading the chain, never by guessing. Idempotency is by (kind, canonical body)."""
    for rec in journal.read_from(1):
        if rec.kind == kind and rec.body_json == body_json:
            return COMMITTED
    return NOT_COMMITTED

def find_orphans(store, namespace: str, journal):
    """Journal objects not on the accepted chain: evidence of fenced-out or failed writers; carry no authority."""
    accepted = {journal_key(namespace, r.seq, r.record_hash) for r in journal.read_from(1)}
    return [k for k in store.list_prefix(journal_prefix(namespace)) if k not in accepted]

def cold_rebuild_head(journal) -> Head:
    """Recompute the head purely from the records and require it equals the HEAD doc."""
    recs = journal.read_from(1)
    rebuilt = verify_chain(recs)
    if rebuilt != journal.head():
        raise Refusal("rebuilt head %s != HEAD doc %s" % (rebuilt, journal.head()), code="HEAD_DIVERGES_FROM_CHAIN")
    return rebuilt
