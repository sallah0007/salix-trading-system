"""CANDIDATE (proposed, NOT admitted) ENUM / REF_TYPE code tables for Annex V1.2 — the D3 proposal.
SYMBOLS are the closed sets written in the Annex text. NUMBERS are the author's proposal only: the Annex says 'closed numeric code under
schema version' but the sources read assign no numbers. Convention proposed: codes start at 1 in the order the Annex lists the symbols;
0 is reserved/invalid. Until a source owner admits a table, `provisional` is True and no hash made with it is a canonical identity.
Enums whose members the sources read do not list (e.g. DATA_VINTAGE_MODE beyond the three named in the ML profile, opcode codes,
reason-code members) are deliberately ABSENT rather than invented."""
from .encoding import CodeTables

_SETS = {
    "INPUT_SPECULATION_CLASS": ("CANONICAL_ONLY", "ONE_HOP_NON_SPECULATIVE_SOURCE_STAGE"),
    "PRIORITY_CLASS": ("P0_LIVE_HEAD", "P1_LIVE_CRITICAL", "P2_HISTORICAL_REPLAY"),
    "PROGRAM_CAPABILITY_CLASS": ("SCALAR_RECURRENCE", "ELEMENTWISE_FIXED_SHAPE_RECURRENCE", "BOUNDED_REDUCTION",
                                 "BOUNDED_STATE_TABLE", "SCALAR_CLOSED_FORM_RATIO"),
    "REFIT_MODE": ("PARAMETERS_FIXED", "SCHEDULED_REFIT"),
    "COMPONENT_TYPE": ("BINARY64_SCALAR", "FIXED_VECTOR_BINARY64", "FIXED_MATRIX_BINARY64"),
    "SPECULATION_MODE": ("OFF", "GATED_ONE_STEP"),
    "ROW_CANDIDATE_STATUS": ("STAGED", "PENDING_VERIFICATION", "VERIFIED", "REJECTED", "DISCARDED"),
    "GATE_STATE": ("NONE", "WAITING", "SATISFIED", "FAILED"),
    "RESULT": ("PASS", "FAIL"),
    "FIT_GENERATION_CHECK_RESULT": ("PASS", "FAIL", "NOT_APPLICABLE"),
    "CURRENTNESS_STATE": ("CURRENT", "CATCHING_UP", "DEGRADED_NOT_CURRENT", "HALTED", "SUPERSEDED"),
    "CHAIN_STATUS": ("CURRENT", "CATCHING_UP", "DEGRADED_NOT_CURRENT", "HALTED", "SUPERSEDED"),
    "TRANSITION_STATUS_EVENT": ("PUBLISHABLE",),
    "REQUIREMENT_CLASS": ("REQUIRED", "OPTIONAL"),
    "VALUE_TYPE": ("BINARY64_BITS_VALUE", "UINT64_VALUE"),
}
# REF_TYPE names taken from the Annex's *_REF field names (families). Numbering is again the author's proposal.
_REFS = ("PROGRAM_REF", "STEP_CLASSIFIER_REF", "PROJECTION_PROGRAM_REF", "INVARIANT_PROGRAM_REF", "HEALTH_METRIC_PROGRAM_REF",
         "GOLDEN_VECTOR_SET_REF", "STEP_CLASS_SET_REF", "RESOURCE_CEILING_REF", "REFIT_RULE_REF", "PARAMETER_GENERATION_SOURCE_REF",
         "INITIALIZATION_RULE_SET_REF", "PUBLISHED_PROJECTION_SET_REF", "VERIFICATION_RULE_SET_REF", "HEALTH_PROFILE_REF",
         "DATA_VINTAGE_POLICY_REF", "FIT_GENERATION_REF", "STATE_ORIGIN_REF", "VERIFICATION_EVIDENCE_REF", "EVIDENCE_REF",
         "MV_REF", "INPUT_REF", "SOURCE_OR_CAUSAL_POLICY_REF", "HEALTH_RESOLUTION_REF", "CANONICAL_TRANSITION_REF",
         "REASON_REF", "WINDOW_REF", "SCOPE_REF", "TEMPORAL_CONTRACT_REF", "HEALTH_ACCEPTANCE_RULE_REF", "ABSENCE_HANDLING_RULE_REF")

def candidate_tables() -> CodeTables:
    return CodeTables(enums={k: {s: i for i, s in enumerate(v, 1)} for k, v in _SETS.items()},
                      ref_types={n: i for i, n in enumerate(_REFS, 1)}, admitted_source=None)
