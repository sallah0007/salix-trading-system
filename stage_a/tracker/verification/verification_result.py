"""Typed, scope-qualified verification result. A reader that ignores the scope fails closed: the result has no
truthiness, and require_pass demands the exact scope the reader intends to rely on."""
from dataclasses import dataclass
from typing import Tuple
from ...errors import Refusal
from .independent_encoding import enc_bytes
from .independent_hashing import _h

PASS = "PASS"
FAIL = "FAIL"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
SCOPE_MATERIALIZATION = "COMPONENT_MATERIALIZATION_RECORDING_V1"

@dataclass(frozen=True)
class VerificationResult:
    status: str
    scope: str
    subject: Tuple[Tuple[str, str], ...]
    checks: Tuple[Tuple[str, bool], ...]
    reasons: Tuple[str, ...]
    result_hash: str

    def __bool__(self):
        raise TypeError("VerificationResult has no truthiness; use require_pass(scope)")

    def require_pass(self, scope: str):
        if self.scope != scope:
            raise Refusal("result scope %s != required %s" % (self.scope, scope), code="VERIFICATION_SCOPE_MISMATCH")
        if self.status != PASS:
            raise Refusal("%s %s" % (self.status, list(self.reasons)), code="VERIFICATION_NOT_PASS")
        return self

def make_result(status, scope, subject: dict, checks, reasons) -> VerificationResult:
    subj = tuple(sorted(subject.items()))
    chk = tuple(checks)
    rs = tuple(reasons)
    payload = {"status": status, "scope": scope, "subject": [list(x) for x in subj],
               "checks": [[a, bool(b)] for a, b in chk], "reasons": list(rs)}
    return VerificationResult(status, scope, subj, chk, rs, _h("SALIX_VERIFICATION_RESULT_V1", enc_bytes(payload)))
