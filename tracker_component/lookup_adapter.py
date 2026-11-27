"""Maps baseline lookup outcomes to the construction boundary. Only certified global
absence (ABSENT) may proceed; ERA_1 structural absence is NOT global absence."""
from tracker_identity.models import LookupOutcome

PROCEED = "PROCEED"
INCOMPLETE_LOOKUP = "INCOMPLETE_LOOKUP"
DUPLICATE_OR_NEAR = "DUPLICATE_OR_NEAR"

def construction_gate(outcome) -> str:
    try:
        o = LookupOutcome(outcome)
    except ValueError:
        return INCOMPLETE_LOOKUP
    if o is LookupOutcome.ABSENT:
        return PROCEED
    if o in (LookupOutcome.EXACT_CANONICAL_IDENTITY, LookupOutcome.NEAR_MATCH):
        return DUPLICATE_OR_NEAR
    return INCOMPLETE_LOOKUP
