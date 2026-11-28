"""R38: a GENERIC lifecycle framework with safeguards (Registry p267-279 names lifecycle states 'as applicable'; the TRANSITION POLICY - which state may follow which, which are terminal, which evidence a move needs - is SOURCE-OWNED and UNBOUND). This module supplies the MECHANICS and nothing of the policy:
  * the state vocabulary and the policy are SUPPLIED (`LifecyclePolicy`); no 12-state graph, initial state, terminal set or mapping (PUBLISHABLE=>CURRENT, WITHDRAWN=>HALTED, ...) is defined here. With `policy=None` every operation refuses `LIFECYCLE_POLICY_HELD` (fail closed on the unbound slot);
  * safeguards that hold for ANY policy: exact-HEAD compare-and-append (a stale writer refuses), the current state is DERIVED by replaying the chain-verified journal (never a cache), a transition must name its prior state (a lie about 'from' refuses), is idempotent by transition id (identical retry = no-op, a different body under the same id refuses), requires an `evidence_ref` and, when a checker is supplied, that checker must accept (e.g. an `EvidenceResolver.use` receipt wrapper); a subject in a policy-declared terminal state accepts nothing further; unknown states refuse; a failed attempt writes nothing;
  * `quarantine/withdraw` style moves are just policy transitions: nothing here auto-reopens or rolls back.
The ACTUAL caller is `LifecycleFramework.apply(...)`, used by the composition caller (`composition.py`) to record a status event for a subject. A committed transition changes NO gate; mapping a lifecycle state to chain-status/currentness remains the source-owned mapping (HELD)."""
import json
from dataclasses import dataclass
from typing import Callable, FrozenSet, Optional, Tuple
from ..errors import Refusal
from tracker_component.journal_port import GENESIS_HEAD, HeadMismatch
KIND = "LIFECYCLE_TRANSITION"
@dataclass(frozen=True)
class LifecyclePolicy:
    states: Tuple[str, ...]; allowed: FrozenSet[Tuple[Optional[str], str]]; terminal: FrozenSet[str]; policy_ref: str          # allowed: {(from or None for entry, to)}; ALL SUPPLIED by the source owner
    def __post_init__(self):
        if not (isinstance(self.states, tuple) and self.states and all(isinstance(s, str) and s for s in self.states) and len(set(self.states)) == len(self.states) and isinstance(self.policy_ref, str) and self.policy_ref
                and all(isinstance(p, tuple) and len(p) == 2 and (p[0] is None or p[0] in self.states) and p[1] in self.states for p in self.allowed) and set(self.terminal) <= set(self.states)): raise Refusal("policy", code="LIFECYCLE_POLICY_INVALID")
class LifecycleFramework:
    def __init__(self, journal, policy: Optional[LifecyclePolicy] = None, evidence_check: Optional[Callable] = None):
        if policy is not None and not isinstance(policy, LifecyclePolicy): raise Refusal("policy", code="LIFECYCLE_POLICY_INVALID")
        self._j, self._p, self._ev = journal, policy, evidence_check
    def _need(self):
        if self._p is None: raise Refusal("transition policy unbound", code="LIFECYCLE_POLICY_HELD")
        return self._p
    def _replay(self):
        cur, ids = {}, {}; head = self._j.head()
        for r in (self._j.read_from(1) if head != GENESIS_HEAD else []):
            if r.kind != KIND: raise Refusal(r.kind, code="LIFECYCLE_UNKNOWN_RECORD_KIND")
            b = json.loads(r.body_json); cur[b["subject"]] = b["to"]; ids[b["transition_id"]] = b
        return head, cur, ids
    def state_of(self, subject):
        self._need(); return self._replay()[1].get(subject)
    def apply(self, subject, transition_id, from_state, to_state, evidence_ref, *, expected_head=None):
        p = self._need()
        if not all(isinstance(x, str) and x for x in (subject, transition_id, evidence_ref)) or from_state not in (None,) + p.states or to_state not in p.states: raise Refusal("transition", code="LIFECYCLE_INPUT_INVALID")
        head, cur, ids = self._replay(); body = {"subject": subject, "transition_id": transition_id, "from": from_state, "to": to_state, "evidence_ref": evidence_ref, "policy_ref": p.policy_ref}
        if transition_id in ids:
            if ids[transition_id] != body: raise Refusal(transition_id, code="LIFECYCLE_TRANSITION_ID_REUSED_DIFFERENTLY")
            return None
        if expected_head is not None and expected_head != head: raise Refusal("head moved", code="LIFECYCLE_STALE_HEAD")
        have = cur.get(subject)
        if have != from_state: raise Refusal("subject is %r not %r" % (have, from_state), code="LIFECYCLE_FROM_STATE_MISMATCH")
        if have in p.terminal: raise Refusal(have, code="LIFECYCLE_TERMINAL_STATE")
        if (from_state, to_state) not in p.allowed: raise Refusal("%s->%s" % (from_state, to_state), code="LIFECYCLE_TRANSITION_NOT_ALLOWED_BY_POLICY")
        if self._ev is None: raise Refusal("evidence check unbound", code="LIFECYCLE_EVIDENCE_CHECK_HELD")
        try: ok = self._ev(subject, from_state, to_state, evidence_ref) is True
        except Refusal: ok = False
        if not ok: raise Refusal(evidence_ref, code="LIFECYCLE_EVIDENCE_NOT_ACCEPTED")
        try: return self._j.append(head, KIND, body)
        except HeadMismatch: raise Refusal("head moved", code="LIFECYCLE_STALE_HEAD")
