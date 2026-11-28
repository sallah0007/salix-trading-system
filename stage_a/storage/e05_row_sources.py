"""R53: E05 source adapters for the PER-ROW owning objects (candidate mapping only): committed PendingRows -> `stagea_pending_row_index`; ROW_ACCEPTED journal records -> `stagea_transition_index`
(PK = the typed transition hash carried in the accepted body) and `stagea_current_status` (projected row-transition head only). Every row is rebuilt from the canonical objects: the pending row is
RE-LOADED (bytes + producer/independent hash) from the row store, never trusted from its key or sidecar; the transition row names the journal record (ref + record hash) and its row must itself be
a committed row. Column values the sources do not define (the pending-row `state` vocabulary) are SUPPLIED callbacks and refused when absent: nothing is mapped by guess. Index presence grants no authority."""
import json
from ..errors import Refusal
from ..tracker.materialization import row_store as RS
from ..tracker import row_acceptance as RA
from .e05_sources import object_prefix_source
from tracker_component.journal_port import GENESIS_HEAD

def pending_row_source(store, rows, state_of, *, vintage_mode="HELD_UNMAPPED_VINTAGE_MODE"):
    """`pending-row/<hash>` objects -> stagea_pending_row_index. `state_of(row_hash)` is supplied (the E05 plan names the column; its vocabulary is not defined here)."""
    if not callable(state_of): raise Refusal("state_of", code="E05_SOURCE_INPUT_INVALID")
    def row_of(key, raw):
        h = key.rsplit("/", 1)[-1]; row = rows.load(h)                       # re-verified canonical row; a key that does not hash to its bytes cannot project
        st = state_of(h)
        if not (isinstance(st, str) and st): raise Refusal(h, code="E05_SOURCE_PENDING_ROW_STATE_NOT_SUPPLIED")
        return dict(row_content_hash=h, feature_id=row.feature_id.hex(), materialization_version=row.materialization_version, event_time=row.event_time, state=st)
    return object_prefix_source(store, "stagea_pending_row_index", "pending-row/", row_of, vintage_mode=vintage_mode)

def row_transition_source(journal, namespace, rows, *, vintage_mode="HELD_UNMAPPED_VINTAGE_MODE"):
    if not (isinstance(namespace, str) and namespace): raise Refusal("namespace", code="E05_SOURCE_INPUT_INVALID")
    def head():
        h = journal.head(); return (h.seq, h.hash)
    def rows_():
        recs = journal.read_from(1) if journal.head() != GENESIS_HEAD else []
        last = {}
        for r in recs:
            if r.kind != RA.KIND: raise Refusal(r.kind, code="ROW_NAMESPACE_FOREIGN_KIND")
            b = json.loads(r.body_json); row = rows.load(b["row_content_hash"])
            if RA.row_namespace(row) != namespace: raise Refusal(r.record_hash, code="E05_SOURCE_ROW_NOT_OF_THIS_NAMESPACE")
            subj = row.feature_id.hex()
            yield "stagea_transition_index", dict(transition_hash=b["transition_hash"], namespace_id=namespace, epoch=b["sifp_fencing_epoch"], sequence=r.seq, subject_id=subj,
                                                  accepted_at=b["canonical_accepted_at"], ref="journal:%s/%d" % (namespace, r.seq), ref_hash=r.record_hash, data_vintage_mode=vintage_mode)
            last[(subj, row.materialization_version)] = (r, b)
        for (subj, mv), (r, b) in sorted(last.items()):
            yield "stagea_current_status", dict(subject_id=subj, materialization_version=mv, ref="journal:%s/%d" % (namespace, r.seq), ref_hash=r.record_hash, data_vintage_mode=vintage_mode,
                                                payload={"head_row": b["row_content_hash"], "head_seq": r.seq})
    return head, rows_
