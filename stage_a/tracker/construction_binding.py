"""D1 (prepared for review, NOT installed): the protected explicit composition binding between the baseline's single construction-authority seam and the freshly synced ClaimService.
It composes `authority_bridge.make_construction_authority_resolver` (claim validity, order revocation, one-shot consumption, journal-synced concurrency/recovery are ClaimService behaviour, already tested) and adds
the one missing precondition as an EXPLICIT HOLD: the accepted principal/source ADMISSION (who may sign a construction order) is source-owned and unbound.
  * a QUALIFIED claim service -> the resolver is ALWAYS False: typed status HELD_PRINCIPAL_SOURCE_ADMISSION_UNBOUND, or HELD_ADMISSION_CALLER_ASSERTED_UNVERIFIED when a carrier is supplied (an asserted carrier never releases it; R23);
  * a SIMULATION claim service resolves for explicit simulation evidence only (status SIMULATION_EVIDENCE);
  * `installed` is ALWAYS False: replacing tracker_identity.store._governed_construction_authority is a governance decision (D1) recorded by the Manager, never by this repository code. The baseline function
    stays hard-False; no globally true resolver, no flag, no Manager-issued ordinary order shortcut; the Tracker stays sole ordinary construction-order issuer."""
from dataclasses import dataclass
from ..errors import Refusal
from ..storage.authority_class import authority_class_of, QUALIFIED
from .authority_bridge import make_construction_authority_resolver

@dataclass(frozen=True)
class PrincipalSourceAdmission:
    """Carrier for the (unbound) accepted principal/source admission record. A non-empty carrier is CALLER-ASSERTED, not verification."""
    record_ref: str
    admitted_principal: str
    def __post_init__(self):
        if not isinstance(self.record_ref, str) or not self.record_ref or not isinstance(self.admitted_principal, str) or not self.admitted_principal:
            raise Refusal("admission", code="ADMISSION_INCOMPLETE")

HELD_ADMISSION = "HELD_PRINCIPAL_SOURCE_ADMISSION_UNBOUND"
SIMULATION_EVIDENCE = "SIMULATION_EVIDENCE"
ADMISSION_ASSERTED = "HELD_ADMISSION_CALLER_ASSERTED_UNVERIFIED"      # R23: a carrier is NOT the accepted admission; it never releases the resolver

class ConstructionAuthorityBinding:
    installed = False
    def __init__(self, claim_service, admission=None):
        if admission is not None and not isinstance(admission, PrincipalSourceAdmission):
            raise Refusal(type(admission).__name__, code="ADMISSION_NOT_TYPED")
        self._cls = authority_class_of(claim_service); self._adm = admission
        self._inner = make_construction_authority_resolver(claim_service)
    def status(self) -> str:
        if self._cls != QUALIFIED: return SIMULATION_EVIDENCE
        return HELD_ADMISSION if self._adm is None else ADMISSION_ASSERTED
    def resolver(self, verified) -> bool:
        """Qualified: ALWAYS False. No verifier exists that resolves an admission record and binds its principal/source/scope to the order, and none is invented; a caller-supplied carrier proves nothing.
        Only a SIMULATION claim service delegates, as explicit simulation evidence."""
        if self.status() != SIMULATION_EVIDENCE: return False
        return self._inner(verified) is True

# PREPARED WRAPPER vs INSTALLED PATH: this wrapper is not installed. An installed composition would additionally need (a) the accepted admission resolved from its governed source and bound to the order's
# principal/source/scope, (b) atomic registration of the resolver at the baseline seam together with its acceptance record, and (c) the Manager recording the install. Those are source-owned and unbound.
