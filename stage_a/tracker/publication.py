"""PUBLISHABLE / WITHDRAWN status transitions. Publication status is eligibility evidence only: nothing here calls,
signals or bypasses a Gateway, FW, ML or Health component, and no delivery occurs."""
from dataclasses import dataclass
from tracker_component.journal_port import HeadMismatch
from ..errors import Refusal, StaleFence
from ..coordination import transition_record as T
from ..replay import replay
from .verification.verification_result import SCOPE_MATERIALIZATION

@dataclass(frozen=True)
class PublicationRecord:
    namespace: str
    feature_version: str
    seq: int
    record_hash: str
    delivered: bool = False          # structurally constant: publication is not delivery

def _commit(journal, namespace, build, retries=3):
    for _ in range(retries):
        head = journal.head()
        recs = journal.read_from(1)
        states = replay(namespace, recs)
        kind, body = build(states)
        try:
            if not journal.epoch_is_current():
                raise StaleFence("fence lost before commit")
            return journal.append(head, kind, body)
        except HeadMismatch:
            continue
    raise Refusal("head race exhausted", code="FENCE_RACE_EXHAUSTED")

def publish(journal, feature_key, verification) -> PublicationRecord:
    verification.require_pass(SCOPE_MATERIALIZATION)
    ns, ver = feature_key.namespace(), feature_key.feature_version
    def build(states):
        st = states.get(ver)
        if st is None:
            raise Refusal(ver, code="NOT_ACCEPTED")
        if st.status != T.CANONICAL_ACCEPTED:
            raise Refusal("status %s" % st.status, code="ILLEGAL_TRANSITION")
        if st.accepted_body["verification_hash"] != verification.result_hash:
            raise Refusal("verification differs from the one accepted", code="VERIFICATION_NOT_THE_ACCEPTED_ONE")
        return T.PUBLISHABLE, {"feature_key": feature_key.key(), "feature_version": ver,
                               "accepted_seq": st.accepted_seq, "accepted_hash": st.accepted_hash,
                               "verification_hash": verification.result_hash}
    rec = _commit(journal, ns, build)
    return PublicationRecord(ns, ver, rec.seq, rec.record_hash)

def withdraw(journal, feature_key, reason: str):
    ns, ver = feature_key.namespace(), feature_key.feature_version
    def build(states):
        st = states.get(ver)
        if st is None:
            raise Refusal(ver, code="NOT_ACCEPTED")
        return T.WITHDRAWN, {"feature_key": feature_key.key(), "feature_version": ver, "reason": reason}
    return _commit(journal, ns, build)
