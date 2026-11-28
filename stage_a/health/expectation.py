"""R40: generic per-subject EXPECTATION carry/validation (Master Health V3 B0 p60: EXPECTED | NOT_EXPECTED | EXPECTATION_UNKNOWN; p80 validity is load-bearing; D117-123: unknown is not not-expected; silence is interpreted only under a governed expectation; expired absence is never healthy). CORRECTS the E03 row-48 claim that the rule is undefined: the enum and the silence derivation exist (`envelope.derive_silence`); the ONLY missing input is the per-subject/profile/time ADMITTED expectation instance, which a source owner must supply.
This module defines no producer, profile, threshold or admission. An assertion is usable only if (a) it names exactly this subject, (b) the instant lies inside its validity window (half-open [valid_from, valid_until)), (c) its `admitted_ref` RESOLVES through the SUPPLIED resolver. Anything else, a conflict between two usable assertions, or no assertion => EXPECTATION_UNKNOWN (never NOT_EXPECTED, never EXPECTED). Facts only; no Health verdict."""
from dataclasses import dataclass
from ..errors import Refusal
from .envelope import EXPECTATION, derive_silence
@dataclass(frozen=True)
class ExpectationAssertion:
    subject: str; state: str; valid_from: int; valid_until: int; admitted_ref: str
    def __post_init__(self):
        if not (isinstance(self.subject, str) and self.subject and self.state in EXPECTATION and all(type(x) is int and x >= 0 for x in (self.valid_from, self.valid_until)) and self.valid_from < self.valid_until and isinstance(self.admitted_ref, str) and self.admitted_ref): raise Refusal("assertion", code="EXPECTATION_ASSERTION_INVALID")
def expectation_for(assertions, subject, at, resolver):
    """-> (state, reason). `resolver(admitted_ref) -> bool` (True only for an admitted, current, unrevoked instance)."""
    if type(at) is not int or not isinstance(subject, str) or not subject: raise Refusal("input", code="EXPECTATION_INPUT_INVALID")
    usable = []
    for a in assertions or ():
        if not isinstance(a, ExpectationAssertion) or a.subject != subject or not (a.valid_from <= at < a.valid_until): continue
        try: ok = resolver is not None and resolver(a.admitted_ref) is True
        except Refusal: ok = False
        if ok: usable.append(a)
    if not usable: return "EXPECTATION_UNKNOWN", "NO_ADMITTED_VALID_ASSERTION_FOR_SUBJECT_AT_TIME"
    if len({a.state for a in usable}) > 1: return "EXPECTATION_UNKNOWN", "CONFLICTING_ASSERTIONS"
    return usable[0].state, ""
def silence_for(now, validity_expires_at, subject, assertions, resolver):
    """derive_silence under the RESOLVED expectation; returns (silence_state_or_None, expectation, reason)."""
    exp, why = expectation_for(assertions, subject, now, resolver)
    return derive_silence(now, validity_expires_at, exp), exp, why
