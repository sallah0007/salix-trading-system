"""Version-relationship diff-schema checks (Registry candidate, version-relationship layer; frozen Tracker core preserved). REFERENCE_ONLY pure validators: nothing here
stores, compares versions or authorizes a successor. The FIELD->DIMENSION map rule is pure set logic over the five source-named dimensions; it does NOT define the FEATURE_VERSION_RELATIONSHIP
object bytes, the diff engine, the diff-schema instance, or how CORRECTION's predecessor-defect evidence is verified (named gaps: no accepted schema/API in any source read).
PARTITION_TOTAL: every admitted field is mapped. PARTITION_DISJOINT: each admitted field maps to exactly one dimension. Nothing is silently skipped, dual-homed or invented."""
from typing import Iterable, Tuple
from ..errors import Refusal

DIMENSIONS = ("DEFINITION_SEMANTICS", "CAUSAL_TIME", "PROVENANCE_SOURCE", "SCOPE_ELIGIBILITY_DEFINITION", "FITTED_LEARNED_STATE")
# Required mapping for the fitting-manifest fields the architecture already names (paraphrased keys; attempt identity is OUTSIDE the version-content diff).
REQUIRED_FITTING_MAPPING = {"fitting_window": "FITTED_LEARNED_STATE", "target_outcome_information_consulted": "FITTED_LEARNED_STATE", "holdout_exposure_state": "FITTED_LEARNED_STATE",
                            "data_vintage": "PROVENANCE_SOURCE", "instrument_set": "SCOPE_ELIGIBILITY_DEFINITION", "code_formula_hash": "DEFINITION_SEMANTICS"}
OUTSIDE_VERSION_CONTENT_DIFF = ("attempt_identity",)
UNCOMPUTED, UNCOMPUTABLE = "RELATIONSHIP_UNCOMPUTED", "RELATIONSHIP_UNCOMPUTABLE"

def check_field_dimension_map(admitted_fields: Iterable[str], pairs: Iterable[Tuple[str, str]]) -> None:
    """Raises Refusal with the FIRST defect code (DIFF_PARTITION_INCOMPLETE | DIFF_PARTITION_NOT_DISJOINT | SCHEMA_MISMATCH | UNKNOWN_DIMENSION | ATTEMPT_IDENTITY_IN_DIFF |
    FITTING_FIELD_MISMAPPED | DIFF_SCHEMA_EMPTY). `pairs` is a sequence of (field, dimension) so dual-homing is detectable (a dict would hide it)."""
    admitted = list(admitted_fields); pairs = list(pairs)
    if not admitted:
        raise Refusal("admitted_fields", code="DIFF_SCHEMA_EMPTY")
    for f in admitted:
        if f in OUTSIDE_VERSION_CONTENT_DIFF:
            raise Refusal(f, code="ATTEMPT_IDENTITY_IN_DIFF")
    for f, d in pairs:
        if d not in DIMENSIONS:
            raise Refusal("%s->%s" % (f, d), code="UNKNOWN_DIMENSION")          # the engine may not invent or self-authorize a category
    seen = {}
    for f, d in pairs:
        if f in seen:
            raise Refusal(f, code="DIFF_PARTITION_NOT_DISJOINT")
        seen[f] = d
    aset = set(admitted)
    if set(seen) - aset:
        raise Refusal(",".join(sorted(set(seen) - aset)), code="SCHEMA_MISMATCH")  # one-sided field
    if aset - set(seen):
        raise Refusal(",".join(sorted(aset - set(seen))), code="DIFF_PARTITION_INCOMPLETE")
    for f, d in REQUIRED_FITTING_MAPPING.items():
        if f in seen and seen[f] != d:
            raise Refusal("%s->%s (required %s)" % (f, seen[f], d), code="FITTING_FIELD_MISMAPPED")

def relationship_consequences(state: str) -> dict:
    """Operational consequences of a relationship state (source-stated only). Anything else refuses (fail closed on unknown)."""
    if state == UNCOMPUTED:
        return {"blocks_supersession_claim": True, "blocks_gateway_delivery_of_existing_eligible_version": False, "may_yield_correction": False}
    if state == UNCOMPUTABLE:
        return {"blocks_supersession_claim": False, "blocks_gateway_delivery_of_existing_eligible_version": False, "may_yield_correction": False, "routes_to": "MATERIAL_ALTERNATIVE"}
    raise Refusal(repr(state), code="UNKNOWN_RELATIONSHIP_STATE")
