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
# ---- R41: object-store-backed and queue-backed source adapters (canonical OWNING objects -> E05 rows; owner-specific column values are CALLBACKS, never invented here) ----
import hashlib
from ..tracker.verification.independent_hashing import manifest_digest
from ..tracker.verification.independent_encoding import parse
def object_prefix_source(store, table, prefix, row_of, *, vintage_mode="HELD_UNMAPPED_VINTAGE_MODE"):
    """One owning-object family under `prefix`. head = (count, sha256 over the sorted (key, etag) listing) so ANY write/replace moves it; rows = row_of(key, bytes) -> (column dict) for each object, plus the canonical ref `object:<key>` and ref_hash = sha256(bytes) unless `row_of` supplies ref_hash. Rows are read twice-bracketed by `E05Index.rebuild` (bounded retry on a moving head)."""
    if not (isinstance(prefix, str) and prefix and callable(row_of)): raise Refusal("source", code="E05_SOURCE_INPUT_INVALID")
    def _listing():
        out = []
        for k in sorted(store.list_prefix(prefix)):
            g = store.get(k)
            if g is not None: out.append((k, g[1], g[0]))
        return out
    def head():
        l = _listing(); return (len(l), hashlib.sha256("|".join("%s:%d" % (k, e) for k, e, _ in l).encode()).hexdigest())
    def rows():
        for k, e, b in _listing():
            r = dict(row_of(k, b)); r.setdefault("ref", "object:" + k); r.setdefault("ref_hash", hashlib.sha256(b).hexdigest()); r.setdefault("data_vintage_mode", vintage_mode); yield table, r
    return head, rows
def object_resolver(store):
    """`object:<key>` -> sha256 of the bytes AS FOUND (None if absent). A replaced object therefore surfaces as E05 DRIFT."""
    def res(ref):
        if not (isinstance(ref, str) and ref.startswith("object:")): return None
        g = store.get(ref[len("object:"):]); return None if g is None else hashlib.sha256(g[0]).hexdigest()
    return res
def manifest_row_of(currentness_of):
    """stagea_manifest_index mapping for `artifact/<manifest_hash>` objects: manifest_hash/feature identity come from the CANONICAL bytes (re-derived, not trusted from the key); `status_currentness` is supplied by the caller (the currentness authority is not this module's)."""
    def f(key, raw):
        mh = key.rsplit("/", 1)[-1]
        if manifest_digest(raw) != mh: raise Refusal(key, code="E05_SOURCE_OBJECT_NOT_CONTENT_ADDRESSED")
        p = parse(raw); c = currentness_of(mh)
        if not (isinstance(c, str) and c): raise Refusal(mh, code="E05_SOURCE_CURRENTNESS_NOT_SUPPLIED")
        return dict(manifest_hash=mh, feature_id=p["feature_id"], feature_version=p["feature_version"], status_currentness=c)
    return f
def queue_source(table, queue, fields_of, *, vintage_mode="HELD_UNMAPPED_VINTAGE_MODE"):
    """stagea_scheduler_queue / stagea_replay_queue mirror of the NON-canonical `workers.JobQueue`: the rows are a read model of PENDING jobs; ref = `job:<idempotency_key>`, ref_hash = sha256 over the job's exact governing refs. Column values are `fields_of(job)` (scheduler/replay policy is not defined here). A queue loss is recovered from canonical journals by `workers.recover_pending`, not from this index."""
    def head():
        p = queue.pending(); return (len(p), hashlib.sha256("|".join(j.idempotency_key for j in p).encode()).hexdigest())
    def rows():
        for j in queue.pending():
            r = dict(fields_of(j)); r.update(ref="job:" + j.idempotency_key, ref_hash=_job_hash(j), data_vintage_mode=vintage_mode); yield table, r
    return head, rows
def _job_hash(j): return hashlib.sha256(json.dumps([j.job_id, j.kind, [list(x) for x in j.governing_refs]], sort_keys=True).encode()).hexdigest()
def queue_resolver(queue):
    def res(ref):
        if not (isinstance(ref, str) and ref.startswith("job:")): return None
        for j in queue.pending():
            if "job:" + j.idempotency_key == ref: return _job_hash(j)
        return None
    return res
def combined_resolver(*resolvers):
    def res(ref):
        for r in resolvers:
            v = r(ref)
            if v is not None: return v
        return None
    return res
def ledger_source(journal, namespace, *, accepted_at_of, epoch_of=None, vintage_mode="HELD_UNMAPPED_VINTAGE_MODE"):
    """R42: `stagea_transition_index` rows for ANY chain-verified journal whose record kinds are NOT the feature transition kinds (e.g. the LifecycleFramework ledger): no replay, no current-status. The per-record epoch is `epoch_of(record)` if the owner supplies one, else the explicit marker EPOCH_NOT_RECORDED (never the current epoch applied to old records)."""
    if not (isinstance(namespace, str) and namespace and callable(accepted_at_of)): raise Refusal("source", code="E05_SOURCE_INPUT_INVALID")
    def head():
        h = journal.head(); return (h.seq, h.hash)
    def rows():
        for r in (journal.read_from(1) if journal.head() != GENESIS_HEAD else []):
            at = accepted_at_of(r)
            if at is None: raise Refusal(str(r.seq), code="E05_SOURCE_TIME_NOT_SUPPLIED")
            b = json.loads(r.body_json)
            yield "stagea_transition_index", dict(transition_hash=r.record_hash, namespace_id=namespace, epoch=("EPOCH_NOT_RECORDED" if epoch_of is None else epoch_of(r)), sequence=r.seq, subject_id=b.get("subject", namespace), accepted_at=at, ref=_ref(namespace, r.seq), ref_hash=r.record_hash, data_vintage_mode=vintage_mode)
    return head, rows
