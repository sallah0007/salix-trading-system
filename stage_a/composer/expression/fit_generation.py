"""Immutable fit-generation references (Q9/Q10 boundary; no fitting happens here). A reference names a generation and
the content hash of the fitted state; the intake boundary refuses stale/future/unknown generations."""
from ...errors import Refusal

def check_fit_refs(manifest_fit_refs, accepted_generations: dict):
    """accepted_generations: generation -> ref_hash currently accepted. Every manifest ref must match exactly; a
    superseded generation (below the newest accepted) is STALE."""
    newest = max(accepted_generations) if accepted_generations else None
    for f in manifest_fit_refs:
        g, h = f["generation"], f["ref_hash"]
        if g not in accepted_generations:
            raise Refusal("generation %s" % g, code="FIT_GENERATION_UNKNOWN")
        if accepted_generations[g] != h:
            raise Refusal("generation %s" % g, code="FIT_REF_HASH_MISMATCH")
        if newest is not None and g < newest:
            raise Refusal("generation %s < %s" % (g, newest), code="FIT_GENERATION_STALE")
