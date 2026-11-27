"""ML Integration Binding Addendum V1 (Matrix V3 current) section 5 FAMILY LEDGER BINDING and section 7 FEED ERA / REVOCATION, generic and ML-side only.
 s5: every authority-bearing ML consumption/claim references the immutable FAMILY_LEDGER_STATE_REF actually consulted, INCLUDING ledger version, hash and AVAILABLE_ASOF; later family exposure never rewrites the historical binding.
 s7: DATA_FEED_ERA_ID is load-bearing for era isolation; contributor revocation propagates through generation/derived lineage (CONTRIBUTOR_LATER_REVOKED / DERIVED_FROM_REVOKED_GENERATION_ID where applicable).
Not source-defined, so NOT invented: the family-ledger content/hash encoding, which claims are 'authority-bearing' beyond the caller declaring the claim authority-bearing, the era vocabulary, and any era-compatibility relation beyond EXACT EQUALITY of supplied era ids. The reason-code split below is the AUTHOR'S READING
(direct contributor revoked -> CONTRIBUTOR_LATER_REVOKED; revoked further up the derived chain -> DERIVED_FROM_REVOKED_GENERATION_ID) and is labelled so. Unresolved lineage is UNKNOWN (fail closed), never clean. Nothing here is qualified and nothing admits a claim."""
from dataclasses import dataclass
from typing import Optional
from ..errors import Refusal
def _s(x): return isinstance(x, str) and bool(x)
def _i(x): return type(x) is int and x >= 0

@dataclass(frozen=True)
class FamilyLedgerRef:
    state_ref: str; version: str; ledger_hash: str; available_asof: int
    def __post_init__(self):
        if not (_s(self.state_ref) and _s(self.version) and _s(self.ledger_hash) and _i(self.available_asof)): raise Refusal("family ledger ref", code="FAMILY_LEDGER_REF_INCOMPLETE")

@dataclass(frozen=True)
class ConsumptionClaim:
    claim_id: str; consumer_binding_id: str; manifest_id: str; claim_ts: int; authority_bearing: bool; feed_era_id: Optional[str]; family_ledger: Optional[FamilyLedgerRef]

class ClaimLedger:
    def __init__(self): self._c = {}; self._order = []
    def record(self, claim: ConsumptionClaim, *, manifest_feed_era_id: Optional[str] = None) -> ConsumptionClaim:
        c = claim
        if not (isinstance(c, ConsumptionClaim) and _s(c.claim_id) and _s(c.consumer_binding_id) and _s(c.manifest_id) and _i(c.claim_ts) and type(c.authority_bearing) is bool): raise Refusal("claim", code="CONSUMPTION_CLAIM_MALFORMED")
        if c.authority_bearing:
            if not isinstance(c.family_ledger, FamilyLedgerRef): raise Refusal(c.claim_id, code="AUTHORITY_BEARING_CLAIM_WITHOUT_FAMILY_LEDGER_REF")
            if c.family_ledger.available_asof > c.claim_ts: raise Refusal(c.claim_id, code="FAMILY_LEDGER_NOT_AVAILABLE_AT_CLAIM_TIME")      # a ledger state first available after the claim cannot have been consulted
        elif c.family_ledger is not None and not isinstance(c.family_ledger, FamilyLedgerRef): raise Refusal(c.claim_id, code="FAMILY_LEDGER_REF_INCOMPLETE")
        if not _s(c.feed_era_id): raise Refusal(c.claim_id, code="FEED_ERA_ID_MISSING")
        if manifest_feed_era_id is None: raise Refusal(c.claim_id, code="MANIFEST_FEED_ERA_UNSUPPLIED_HELD")                          # era isolation cannot be checked without the manifest's era: held, not assumed equal
        if manifest_feed_era_id != c.feed_era_id: raise Refusal(c.claim_id, code="FEED_ERA_MISMATCH")
        old = self._c.get(c.claim_id)
        if old is not None:
            if old != c: raise Refusal(c.claim_id, code="CONSUMPTION_CLAIM_IMMUTABLE")           # later exposure/ledger changes never rewrite the historical binding
            return old
        self._c[c.claim_id] = c; self._order.append(c.claim_id); return c
    def bound_ledger(self, claim_id): c = self._c.get(claim_id); return None if c is None else c.family_ledger
    def claims(self): return tuple(self._c[i] for i in self._order)

CONTRIBUTOR_LATER_REVOKED, DERIVED_FROM_REVOKED = "CONTRIBUTOR_LATER_REVOKED", "DERIVED_FROM_REVOKED_GENERATION_ID"
def revocation_report(manifest_id, derived_from: dict, is_revoked) -> dict:
    """Walk `derived_from` {manifest_id: [contributor manifest ids]} (ML-owned lineage, supplied). is_revoked(mid)->True/False/None (None = unknown). Result status: CLEAN only if every reachable ancestor resolved and none is revoked;
    AFFECTED with the revoked ancestors and their reason codes; UNKNOWN if any ancestor is unresolved/unknown (fail closed). A cycle or a lineage entry that is not a list refuses."""
    if not isinstance(derived_from, dict) or not callable(is_revoked) or not _s(manifest_id): raise Refusal("inputs", code="REVOCATION_INPUT_INVALID")
    seen, affected, unknown = set(), {}, set(); stack = [(manifest_id, 0, ())]
    def walk(mid, depth, path):
        if mid in path: raise Refusal(mid, code="LINEAGE_CYCLE")
        if mid in seen: return
        seen.add(mid)
        if mid != manifest_id:
            r = is_revoked(mid)
            if r is None: unknown.add(mid)
            elif r is True: affected[mid] = CONTRIBUTOR_LATER_REVOKED if depth == 1 else DERIVED_FROM_REVOKED
        if mid not in derived_from:
            unknown.add(mid); return                  # a node absent from the lineage map is unresolved, including the root
        ps = derived_from[mid]
        if not isinstance(ps, (list, tuple)): raise Refusal(mid, code="LINEAGE_ENTRY_MALFORMED")
        for p in ps: walk(p, depth + 1, path + (mid,))
    walk(manifest_id, 0, ())
    status = "AFFECTED" if affected else ("UNKNOWN" if unknown else "CLEAN")
    return {"manifest_id": manifest_id, "status": status, "affected": dict(sorted(affected.items())), "unresolved": tuple(sorted(unknown)), "reason_code_split": "AUTHOR_READING", "qualified": False}
