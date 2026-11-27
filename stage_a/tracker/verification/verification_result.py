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

COMPOSED_VERIFIER_ID = "tracker.verification.stateful_verifier.verify_materialization"
_L2_CHECKS = ("equivalence_probe_batch", "equivalence_probe_incremental")        # the independent numeric recomputation; everything else is L1 structure/identity

PASS_PROFILE = frozenset(("record_field_set", "artifact_present", "object_key_is_content_address", "byte_length", "manifest_field_set", "artifact_is_canonical_bytes",
                          "manifest_hash_recomputed", "graph_hash_recomputed", "program_hash_recomputed", "materialization_hash_recomputed", "declared_manifest_hash", "declared_graph_hash", "declared_program_hash",
                          "identity_binding_artifact_vs_request", "identity_binding_record_vs_request", "structure_sound", "opcode_declaration_equals_extracted", "capability_declaration_equals_extracted",
                          "equivalence_probe_batch", "equivalence_probe_incremental"))      # the complete check profile a genuine PASS of verify_materialization carries (a test pins it to the real verifier)

def split_levels(result):
    """(l1, l2) from the verifier's typed result. The TYPED STATUS wins: a non-PASS status can never yield PASS at either level, an unknown status or an incomplete PASS profile is never PASS, and L2 is UNAVAILABLE
    (never PASS, never a fallback to L1) when the verifier never reached the recomputation."""
    names = dict(result.checks)
    if result.status == INSUFFICIENT_EVIDENCE or result.status not in (PASS, FAIL): return "FAIL", "UNAVAILABLE"
    l1 = "PASS" if all(ok for n, ok in result.checks if n not in _L2_CHECKS) else "FAIL"
    if not all(n in names for n in _L2_CHECKS): l2 = "UNAVAILABLE"
    else: l2 = "PASS" if all(names[n] for n in _L2_CHECKS) else "FAIL"
    if result.status == FAIL and (l1, l2) == ("PASS", "PASS"): return "FAIL", "FAIL"             # FAIL status over an all-True check list: the failure is preserved, never converted
    if result.status == PASS and not PASS_PROFILE <= set(names): return "FAIL", "UNAVAILABLE"       # a truncated all-True result is not a PASS receipt
    return l1, l2

def result_is_self_consistent(result) -> bool:
    """True only if `result` is a VerificationResult whose hash is re-derived from its own typed fields (a forged digest or edited checks is detected). Not a security boundary: in-process code can build any object."""
    if not isinstance(result, VerificationResult): return False
    try: return make_result(result.status, result.scope, dict(result.subject), result.checks, result.reasons).result_hash == result.result_hash
    except Exception: return False

def make_result(status, scope, subject: dict, checks, reasons) -> VerificationResult:
    subj = tuple(sorted(subject.items()))
    chk = tuple(checks)
    rs = tuple(reasons)
    payload = {"status": status, "scope": scope, "subject": [list(x) for x in subj],
               "checks": [[a, bool(b)] for a, b in chk], "reasons": list(rs)}
    return VerificationResult(status, scope, subj, chk, rs, _h("SALIX_VERIFICATION_RESULT_V1", enc_bytes(payload)))
