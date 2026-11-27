"""Deterministic replay of a feature-namespace journal into lifecycle state. The journal is the only authority;
everything else (read models, caches) is derived from this function and must equal it."""
from dataclasses import dataclass
from typing import Dict, List, Optional
from tracker_component.journal_port import verify_chain, JournalIntegrityError
from .errors import Refusal, IntegrityFailure
from .coordination import transition_record as T

@dataclass
class VersionState:
    version: str
    status: str
    accepted_seq: int
    accepted_hash: str
    accepted_body: dict
    publishable_seq: Optional[int] = None
    withdrawn_seq: Optional[int] = None
    legacy_binding_absent: bool = False     # True: accepted before R34, no materialization_hash in the committed record (maintenance HOLD; nothing fabricated)

def replay(namespace: str, records: List) -> Dict[str, VersionState]:
    try:
        verify_chain(records)
    except JournalIntegrityError as e:
        raise IntegrityFailure(str(e))
    out: Dict[str, VersionState] = {}
    for r in records:
        body = r.body()
        T.validate_body(r.kind, body, legacy_read=True)      # R35: committed pre-R34 accepted bodies stay readable (legacy_binding_absent); new writes still validate strictly
        if body["feature_key"] != "%s/%s" % (namespace, body["feature_version"]):
            raise Refusal("record %d key %s not in namespace %s" % (r.seq, body["feature_key"], namespace),
                          code="CROSS_NAMESPACE_RECORD")
        v = body["feature_version"]
        prior = out[v].status if v in out else None
        T.check_transition(prior, r.kind)
        if r.kind == T.CANONICAL_ACCEPTED:
            out[v] = VersionState(v, T.CANONICAL_ACCEPTED, r.seq, r.record_hash, body, legacy_binding_absent=T.body_generation(r.kind, body) != "CURRENT")
        elif r.kind == T.PUBLISHABLE:
            st = out[v]
            if body["accepted_seq"] != st.accepted_seq or body["accepted_hash"] != st.accepted_hash:
                raise Refusal("publishable references wrong accepted record", code="PUBLISHABLE_BINDING_MISMATCH")
            if body["verification_hash"] != st.accepted_body["verification_hash"]:
                raise Refusal("publishable verification differs from accepted", code="PUBLISHABLE_VERIFICATION_MISMATCH")
            st.status, st.publishable_seq = T.PUBLISHABLE, r.seq
        else:
            st = out[v]
            st.status, st.withdrawn_seq = T.WITHDRAWN, r.seq
    return out
