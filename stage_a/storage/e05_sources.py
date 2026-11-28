"""R40: SOURCE ADAPTERS from the ACTUAL canonical journals into the E05 logical tables (`e05_index`). Candidate mapping only: which transition fields feed which index column beyond the primary keys is HELD source detail, so columns the journal does not record are filled from an explicit SUPPLIED value or refused, never guessed.
  * `journal_source(journal, namespace, epoch, accepted_at_of)`: `stagea_transition_index` (one row per chain record: ref `journal:<ns>/<seq>`, hash = the record hash) and `stagea_current_status` (the projected transition HEAD per version via the existing `replay`: status, transition ref+hash of the journal HEAD). `epoch` is the journal's CURRENT epoch (records do not carry their own epoch); `accepted_at_of(record)` must be supplied (the journal does not store a time) or the rows are refused.
  * `journal_resolver(journals)`: ref -> record hash re-read from the journal itself (what `lookup` checks a row against).
Legacy E09/E10 history is only read; nothing is rekeyed. SIMULATION and QUALIFIED journals are NOT mixed by this module (the caller supplies one journal set per call; no class inference here)."""
import json
from ..errors import Refusal
from ..replay import replay
from tracker_component.journal_port import GENESIS_HEAD
def _ref(ns, seq): return "journal:%s/%d" % (ns, seq)
def journal_source(journal, namespace, *, epoch, accepted_at_of, vintage_mode="HELD_UNMAPPED_VINTAGE_MODE", materialization_version_of=None):
    if not (isinstance(namespace, str) and namespace and type(epoch) is int and callable(accepted_at_of)): raise Refusal("source", code="E05_SOURCE_INPUT_INVALID")
    def head():
        h = journal.head(); return (h.seq, h.hash)
    def rows():
        recs = journal.read_from(1) if journal.head() != GENESIS_HEAD else []
        for r in recs:
            at = accepted_at_of(r)
            if at is None: raise Refusal(str(r.seq), code="E05_SOURCE_TIME_NOT_SUPPLIED")
            body = json.loads(r.body_json); subj = body.get("feature_key") or body.get("subject") or namespace
            yield "stagea_transition_index", dict(transition_hash=r.record_hash, namespace_id=namespace, epoch=epoch, sequence=r.seq, subject_id=subj, accepted_at=at, ref=_ref(namespace, r.seq), ref_hash=r.record_hash, data_vintage_mode=vintage_mode)
        if recs:
            last = recs[-1]
            for v, st in sorted(replay(namespace, recs).items()):
                yield "stagea_current_status", dict(subject_id=namespace, materialization_version=v, ref=_ref(namespace, last.seq), ref_hash=last.record_hash, data_vintage_mode=vintage_mode, payload={"status": st.status, "head_seq": last.seq})
    return head, rows
def journal_resolver(journals):
    """journals: {namespace: journal}. Resolves `journal:<ns>/<seq>` to the record hash AS FOUND, None if absent/foreign."""
    def res(ref):
        if not (isinstance(ref, str) and ref.startswith("journal:")): return None
        ns, _, seq = ref[len("journal:"):].rpartition("/"); j = journals.get(ns)
        if j is None or not seq.isdigit(): return None
        for r in j.read_from(int(seq)):
            if r.seq == int(seq): return r.record_hash
        return None
    return res
