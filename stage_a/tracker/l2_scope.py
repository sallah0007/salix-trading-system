"""R40: the fail-closed RESOLVER SLOT for the stored-value (L2) applicability scope (Registry 208-210; Master Health validity). A caller flag `required=False` plus non-empty refs is NOT a governed definition that stored-value comparison is non-applicable. This module defines no scope vocabulary, no NA rule and no admission authority; it only JUDGES what a supplied resolver returns, against the EXACT feature key/version and the exact scope+contract refs named:
  * no resolver bound                         -> UNAVAILABLE `L2_SCOPE_RESOLVER_UNBOUND_HELD`
  * resolver returns nothing / refuses        -> UNAVAILABLE `L2_SCOPE_UNKNOWN`
  * subject/version/scope/contract differ     -> UNAVAILABLE `L2_SCOPE_FOREIGN`
  * `admitted` is not True (candidate only)   -> UNAVAILABLE `L2_SCOPE_CANDIDATE_NOT_ADMITTED` (a candidate scope may be REPRESENTED but never promotes prototype recomputation into stored-value health)
  * not `current` / `revoked`                 -> UNAVAILABLE `L2_SCOPE_STALE` / `L2_SCOPE_REVOKED`
  * only an admitted, current, unrevoked, exactly-matching scope that says required=False => NOT_REQUIRED_ADMITTED; required=True => REQUIRED.
`admitted/current/revoked` are the RESOLVER's assertions about an instance a source owner must supply; nothing here mints one. Even NOT_REQUIRED_ADMITTED asserts no Health: the Core keeps its own calculation. No qualified/live claim."""
from dataclasses import dataclass
from ..errors import Refusal
@dataclass(frozen=True)
class ResolvedL2Scope:
    scope_ref: str; contract_ref: str; feature_key: str; feature_version: str; required: bool; admitted: bool; current: bool; revoked: bool
def judge_l2_scope(resolver, scope_ref, contract_ref, feature_key, feature_version):
    """Returns (state, reason): state in REQUIRED / NOT_REQUIRED_ADMITTED / UNAVAILABLE."""
    if resolver is None: return "UNAVAILABLE", "L2_SCOPE_RESOLVER_UNBOUND_HELD"
    try: s = resolver(scope_ref, contract_ref, feature_key, feature_version)
    except Refusal: return "UNAVAILABLE", "L2_SCOPE_UNKNOWN"
    if not isinstance(s, ResolvedL2Scope): return "UNAVAILABLE", "L2_SCOPE_UNKNOWN"
    if (s.scope_ref, s.contract_ref, s.feature_key, s.feature_version) != (scope_ref, contract_ref, feature_key, feature_version): return "UNAVAILABLE", "L2_SCOPE_FOREIGN"
    if s.revoked is not False: return "UNAVAILABLE", "L2_SCOPE_REVOKED"
    if s.current is not True: return "UNAVAILABLE", "L2_SCOPE_STALE"
    if s.admitted is not True: return "UNAVAILABLE", "L2_SCOPE_CANDIDATE_NOT_ADMITTED"
    if type(s.required) is not bool: return "UNAVAILABLE", "L2_SCOPE_UNKNOWN"
    return ("REQUIRED" if s.required else "NOT_REQUIRED_ADMITTED"), ""
