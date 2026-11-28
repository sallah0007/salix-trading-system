"""BuildPlan s25 (OBSERVABILITY / AUDIT) generic owning interface: every authority-bearing journal transition yields ONE structured evidence record with the eleven required items. Derived fields
(subject, operation, predecessor/new hash, sequence) come from the journal record itself; the rest (actor/service identity, idempotency key, epoch/fence, decision timestamp, available-as-of, evidence refs)
are SUPPLIED by the caller and a missing one is carried as the explicit marker UNBOUND (never invented, never silently empty). `complete` is True only when no field is UNBOUND, so a reader that ignores the
marker still cannot treat an unbound record as complete. Logs are observability; the journal record stays the authority source (this record is non-authoritative: authoritative=False)."""
from .claims import Refusal

UNBOUND = "UNBOUND"
SUPPLIED_FIELDS = ("actor_service_identity", "idempotency_key", "epoch_fence", "decision_accepted_timestamp", "available_as_of", "evidence_refs")
SUBJECT_KEY = {"ORDER_ISSUED": "order_id", "ORDER_REVOKED": "order_id", "ORDER_PROVENANCE": "order_id", "CLAIM_BOUND": "claim_id", "CLAIM_CONSUMED": "claim_id", "CLAIM_RELEASED": "claim_id",
               "CLAIM_ABANDONED": "claim_id", "GRANT_REVOKED": "grant_id", "ATTEMPT_ADMITTED": "build_id", "ATTEMPT_REJECTED": "build_id", "LINEAGE_REPLACED": "new_creation_id",
               "REVIEW_DECIDED": "package_id", "REPORT_DISPOSITION": "package_id"}      # the subject of a transition is the object whose state it changes


def transition_evidence(rec, *, prev_hash=None, **supplied):
    extra = set(supplied) - set(SUPPLIED_FIELDS)
    if extra:
        raise Refusal("AUDIT_UNKNOWN_FIELD", ",".join(sorted(extra)))
    body = rec.body()
    subject = body.get(SUBJECT_KEY.get(rec.kind, ""))
    if subject is None:
        raise Refusal("AUDIT_SUBJECT_NOT_DERIVABLE", rec.kind)       # fail closed: a transition with no recognised subject yields no evidence record
    if prev_hash is not None and prev_hash != rec.prev_hash:
        raise Refusal("AUDIT_PREDECESSOR_MISMATCH", str(rec.seq))
    out = {"subject": subject, "operation": rec.kind, "predecessor_hash": rec.prev_hash, "new_hash": rec.record_hash, "sequence": rec.seq}
    for f in SUPPLIED_FIELDS:
        v = supplied.get(f)
        out[f] = UNBOUND if v is None or v == "" or v == () else v
    out["complete"] = all(out[f] != UNBOUND for f in SUPPLIED_FIELDS)
    out["authoritative"] = False
    return out


def journal_evidence(journal, **supplied):
    """One evidence record per journal record, chain-checked (predecessor hash of each equals the previous record's hash)."""
    prev, res = None, []
    for r in journal.read_from(1):
        res.append(transition_evidence(r, prev_hash=prev, **supplied)); prev = r.record_hash
    return res
