"""ONE order authority: tracker_component.ClaimService (ORDER_ISSUED / ORDER_PROVENANCE / ORDER_REVOKED / CLAIM_* on the claims journal, TrustAnchor + source-binding checks, revocation, expiry, reserve/consume) which TrackerPipeline consumes.
This module is a FACADE: it runs the Composer V9 s7A intake disposition, derives the complete applicable order constraints, and appends through ClaimService. It owns no order table and no gate of its own.
UNADMITTED INPUTS (supplied, never invented here): `issued_by` and `source_binding_hash` (ClaimService verifies them against the deployment TrustAnchor at USE; the anchor's own source is an open governance decision), and `subject_key` (the mapping from a
pre-build CANDIDATE_IDENTITY to the pipeline's content-key subject is not source-defined, so it is supplied and ClaimService re-checks it at reserve). A merge or a PROCEED/ISSUED result clears no gate and starts no build."""
from ..errors import Refusal
from ..storage.byte_primitives import canonical_bytes, domain_hash
from tracker_component.claims import Refusal as ClaimRefusal
from .intake import evaluate_intake, PROCEED, CONSUMER_LOCAL_ORDER_FIELDS, COMMON_FIELDS_ORDER

ORDER_BINDING_FIELDS = ("REQUEST_SCHEMA_VERSION", "REQUEST_CLASS", "REQUESTER_TYPE", "REQUESTER_ID", "TARGET_CONSUMER", "REQUEST_CONTEXT", "PURPOSE_STATEMENT", "OUTCOME_INFORMATION_ACCESS", "RESEARCH_FAMILY_REFERENCE") + COMMON_FIELDS_ORDER
NON_MATERIAL = frozenset({"TARGET_CONSUMER", "REQUESTER_ID", "REQUESTER_TYPE", "REQUEST_CONTEXT", "PURPOSE_STATEMENT", "REQUESTED_AT", "lookup_refs", "applicability"})      # who asked / when / why does not split or change the order

def constraints_of(rec: dict, lookups: dict, applicability: dict) -> dict:
    """Every applicable order field present on the request: s8 bindings, REQUESTED_AT, and ALL consumer-local fields (plain and FW_LOCAL:/ML_LOCAL: prefixed). Lookup refs and derived applicability are recorded alongside."""
    c = {k: rec[k] for k in ORDER_BINDING_FIELDS if k in rec}
    for k in rec:                           # only APPLICABLE local contracts are bound: plain fields when any side applies; FW_LOCAL:/ML_LOCAL: only for their own applicable side. No plain-vs-prefixed precedence is invented: keys are stored exactly as supplied.
        if k in CONSUMER_LOCAL_ORDER_FIELDS and "CONSUMER_LOCAL_REQUIRED" in (applicability.get("FW_LOCAL"), applicability.get("ML_LOCAL")): c[k] = rec[k]
        for side in ("FW_LOCAL", "ML_LOCAL"):
            if applicability.get(side) == "CONSUMER_LOCAL_REQUIRED" and k.startswith(side + ":") and k[len(side) + 1:] in CONSUMER_LOCAL_ORDER_FIELDS: c[k] = rec[k]
    c["lookup_refs"] = {k: lookups[k]["ref"] for k in sorted(lookups) if isinstance(lookups[k], dict)}
    c["applicability"] = dict(applicability)
    return c

def local_family(k) -> bool:
    return k in CONSUMER_LOCAL_ORDER_FIELDS or (isinstance(k, str) and k.partition(":")[0] in ("FW_LOCAL", "ML_LOCAL") and k.partition(":")[2] in CONSUMER_LOCAL_ORDER_FIELDS)

def ambiguous_local(d: dict) -> list:
    """Fields carried both plain and side-prefixed with different values. Which one governs is not source-defined here, so it is never resolved: it is reported."""
    return sorted(f for f in CONSUMER_LOCAL_ORDER_FIELDS if f in d and any(s + ":" + f in d and d[s + ":" + f] != d[f] for s in ("FW_LOCAL", "ML_LOCAL")))

def order_id_for(candidate_identity) -> str:
    return domain_hash("TRK/CONSTRUCTION_ORDER_PROTOTYPE", canonical_bytes({"identity": candidate_identity}))       # INTERNAL prototype digest: no source-defined ORDER_ID composition; candidate identity alone, TARGET_CONSUMER excluded

def issue_order(claims, rec: dict, lookups: dict, *, subject_key: str, source_binding_hash: str, issued_by: str, valid_until_seq=None) -> dict:
    from tracker_component.order import ConstructionOrder
    for n, v in (("subject_key", subject_key), ("source_binding_hash", source_binding_hash), ("issued_by", issued_by)):
        if not (isinstance(v, str) and v): raise Refusal(n, code="ORDER_AUTHORITY_INPUT_MISSING")
    d = evaluate_intake(rec, "ORDER", lookups)
    if d.disposition != PROCEED: return {"status": d.disposition, "reasons": list(d.reasons), "order_id": None}
    amb = ambiguous_local(rec)
    if amb: return {"status": "REVIEW_REQUIRED", "reasons": ["CONSUMER_LOCAL_AMBIGUOUS_PLAIN_VS_PREFIXED:" + ",".join(amb)], "order_id": None}
    cons = constraints_of(rec, lookups, d.field_applicability); oid = order_id_for(rec["CANDIDATE_IDENTITY"])
    for _ in range(2):
        ex = claims.order(oid)
        if ex is None:
            try: claims.issue_order(ConstructionOrder(oid, subject_key, source_binding_hash, issued_by, valid_until_seq, cons))
            except ClaimRefusal as e:
                if e.code == "ORDER_ID_EXISTS": continue               # raced: re-read and coalesce
                raise
            return {"status": "ISSUED", "order_id": oid, "reasons": list(d.reasons)}
        ec = ex.get("constraints")
        if ec is None: return {"status": "REVIEW_REQUIRED", "reasons": ["EXISTING_ORDER_CARRIES_NO_CONSTRAINTS"], "order_id": None}
        mc = {k: v for k, v in cons.items() if k not in NON_MATERIAL}; me = {k: v for k, v in ec.items() if k not in NON_MATERIAL}
        diff = sorted(k for k in set(mc) | set(me) if (k in mc) != (k in me) or mc.get(k) != me.get(k))       # symmetric: added, removed or changed material fields are all reviewed, never discarded
        if diff or ex["subject_key"] != subject_key: return {"status": "REVIEW_REQUIRED", "reasons": ["ORDER_CONSTRAINTS_CONFLICT:" + ",".join(diff or ["subject_key"])], "order_id": oid}         # never silently coalesce a changed contract
        ctx = {"requester_id": rec["REQUESTER_ID"], "requester_type": rec["REQUESTER_TYPE"], "target_consumer": rec["TARGET_CONSUMER"], "constraints": cons}
        same = lambda p: (p.get("requester_id"), p.get("target_consumer")) == (ctx["requester_id"], ctx["target_consumer"])
        if same({"requester_id": ec.get("REQUESTER_ID"), "target_consumer": ec.get("TARGET_CONSUMER")}) or any(same(p) for p in claims.order_provenance(oid)):
            return {"status": "ATTACHED_EXISTING_IDEMPOTENT", "order_id": oid, "reasons": list(d.reasons)}
        claims.attach_provenance(oid, ctx)
        return {"status": "ATTACHED_AS_PROVENANCE", "order_id": oid, "reasons": list(d.reasons)}
    raise Refusal(oid, code="ORDER_ISSUE_RACE_EXHAUSTED")
