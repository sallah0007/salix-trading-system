"""Composer V9 section 27 BUILD_OUTPUT_PACKAGE / section 28 conformance, as Tracker-side validation of a SUPPLIED package.
Source: Composer V9 (Drive 1aMYAmh5i7ogdQ0vIInPKki3lCSV4Nwotx48zllZhfVw) sections 27-28, 38.2. Cited by ID, not copied.
Section 27 lists its fields 'where applicable' and names many of them in PROSE only (request context, purpose/hypothesis, research mode, construction graph,
exact input ids, dependency closures, ...). Only token-named fields and the explicitly conditional/mandatory rules are enforced here; no field name is invented for
a prose-only item and none is defaulted. The package is immutable EVIDENCE: it is never a Gateway package, an active FW/ML input or a registry entry.
Conformance outcomes are computed from supplied verification evidence, never authored."""
from ..errors import Refusal

KNOWN_TOKEN_FIELDS = frozenset({
    "CREATION_REQUEST_ID", "ORDER_ID", "CLAIM_ID", "REQUEST_SCHEMA_VERSION", "BUILDER_BUILD_ID", "PURPOSE_PROFILE_ID", "PURPOSE_PROFILE_HASH",
    "SIMULATION_OR_AUTHORITY_CLASS", "INSTRUMENT_PROFILE_ID", "INSTRUMENT_PROFILE_HASH", "SOURCE_CONFIG_ID", "SOURCE_CONFIG_HASH",
    "BUILDER_VERSION", "BUILDER_HASH", "TRACKER_CATALOG_SNAPSHOT_ID", "TRACKER_CATALOG_SNAPSHOT_HASH", "CATALOG_WATERMARK",
    "OUTCOME_INFORMATION_ACCESS", "UPSTREAM_MODEL_ID", "UPSTREAM_GENERATION_ID", "GENERATION_AUTHORITY_CLASS", "BUILT_AT"})
# Section 27: 'The package is never the registry entry' / 'not a Tracker Consumer Gateway package': these identities belong to other objects.
FORBIDDEN_FIELDS = frozenset({"PACKAGE_CLASS", "CONSUMER_BINDING_ID", "CONSUMER_ID", "BOUND_PAYLOAD_OR_PACKAGE_ID", "REGISTRY_ENTRY_REF", "REGISTRY_ENTRY_ID"})
LEARNED_DERIVED_REQUIRED = ("UPSTREAM_MODEL_ID", "UPSTREAM_GENERATION_ID", "GENERATION_AUTHORITY_CLASS")

def _present(v): return isinstance(v, str) and bool(v.strip())

def check_build_output(bo, *, order_id: str, creation_request_id: str, learned_derived: bool) -> None:
    """Refuses (first defect). learned_derived is DERIVED by the caller from the verified manifest (fit_refs), never taken from the package."""
    if not isinstance(bo, dict):
        raise Refusal(type(bo).__name__, code="BUILD_OUTPUT_PACKAGE_MISSING")
    bad = sorted(set(bo) & FORBIDDEN_FIELDS)
    if bad:
        raise Refusal(",".join(bad), code="BUILD_OUTPUT_PACKAGE_CARRIES_OTHER_OBJECT_IDENTITY")
    if bo.get("ORDER_ID") != order_id or not _present(bo.get("ORDER_ID")):
        raise Refusal(str(bo.get("ORDER_ID")), code="BUILD_OUTPUT_ORDER_ID_DIFFERS_FROM_GOVERNED_ORDER")     # sole Tracker order authority
    if bo.get("CREATION_REQUEST_ID") != creation_request_id or not _present(bo.get("CREATION_REQUEST_ID")):
        raise Refusal(str(bo.get("CREATION_REQUEST_ID")), code="BUILD_OUTPUT_CREATION_REQUEST_ID_DIFFERS")
    if learned_derived:
        missing = [k for k in LEARNED_DERIVED_REQUIRED if not _present(bo.get(k))]
        if missing:       # 'A learned-derived construct without upstream generation identity FAILS CONFORMANCE; ancestry cannot be recovered after the fact.'
            raise Refusal(",".join(missing), code="LEARNED_DERIVED_WITHOUT_UPSTREAM_GENERATION_IDENTITY")
    elif any(bo.get(k) is not None for k in ("UPSTREAM_MODEL_ID", "UPSTREAM_GENERATION_ID")):
        raise Refusal("upstream ancestry on a construct with no fit_refs", code="UPSTREAM_ANCESTRY_WITHOUT_LEARNED_DERIVATION")
    for k, v in bo.items():
        if k in KNOWN_TOKEN_FIELDS and not _present(v) and k != "CLAIM_ID":
            raise Refusal(k, code="BUILD_OUTPUT_FIELD_EMPTY")

def check_outcome_access(declared, consulted_by_verification) -> None:
    """A build that consults outcome/label information under OUTCOME_INFORMATION_ACCESS = FORBIDDEN fails conformance. `consulted_by_verification` is the
    Tracker's own verification result (True/False) or None when it could not be determined: FORBIDDEN with an undetermined result fails closed."""
    if declared == "FORBIDDEN":
        if consulted_by_verification is True:
            raise Refusal("FORBIDDEN", code="OUTCOME_INFORMATION_CONSULTED_UNDER_FORBIDDEN")
        if consulted_by_verification is None:
            raise Refusal("FORBIDDEN", code="OUTCOME_ACCESS_UNVERIFIED_UNDER_FORBIDDEN")

def check_inputs_resolve(input_ids, tracker_identities, returned_nodes) -> None:
    """Every input must resolve to a Tracker identity or a returned node; dangling or unresolved input fails."""
    known = set(tracker_identities) | set(returned_nodes)
    dangling = sorted(i for i in input_ids if i not in known)
    if dangling:
        raise Refusal(",".join(dangling), code="DANGLING_INPUT")

def check_reproduction(declared_hash, recomputed_hash, not_possible_governed_reason_ref=None) -> None:
    """Where deterministic recomputation is possible, mismatch fails; where it is not, the reason must be governed and carried (a ref is required)."""
    if recomputed_hash is None:
        if not _present(not_possible_governed_reason_ref):
            raise Refusal("no recomputation and no governed reason", code="RECOMPUTATION_IMPOSSIBLE_WITHOUT_GOVERNED_REASON")
        return
    if declared_hash != recomputed_hash:
        raise Refusal("%s!=%s" % (declared_hash, recomputed_hash), code="DETERMINISTIC_RECOMPUTATION_MISMATCH")
