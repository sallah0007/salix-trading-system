"""SALIX Type-1 Tracker identity lookup reference implementation.

Scope is deliberately narrow: canonical identity lookup only.
No materialization, eligibility, health, package production, FW/ML execution,
or production trading authority is implemented here.
"""

from .models import AbsentClaimToken, ClaimProvenance, ClaimRecord, CLAIMABLE_LOOKUP_OUTCOMES, FeatureIdentity, IdentityLookupResult, LookupOutcome, NormalizerSpec, SearchPolicy
from .normalizer_registry import (
    GOVERNED_NORMALIZERS,
    NORMALIZER_ID,
    NORMALIZER_VERSION,
    GovernedNormalizerEntry,
    governed_normalizer,
    resolve_governed_normalizer,
    resolve_governed_normalizer_binding,
)
from .policy_registry import (
    GOVERNED_SEARCH_POLICIES,
    MANDATORY_DUPLICATE_CONTROL_SCOPES,
    SEARCH_POLICY_ID,
    SEARCH_POLICY_VERSION,
    GovernedSearchPolicyEntry,
    governed_search_policy,
    resolve_governed_search_policy,
    resolve_governed_search_policy_binding,
)
from .search import identity_lookup
from .catalogue import FeatureDefinitionCatalogue, FeatureDefinitionRecord
from .content_identity import (
    CONTENT_KEY_ALGORITHM_ID, REQUIRED_DIMENSIONS, UNFITTED_TOKEN,
    BINDING_DIMENSIONS, INSTRUMENT_AGNOSTIC, INSTRUMENT_SPECIFIC,
    AGNOSTIC_INSTRUMENT_SCOPE, BOUND_UNIVERSE_DIMENSION,
    SEMANTIC_APPLICABILITY_SCOPE_DIMENSION, instrument_token_leaks,
    INSTRUMENT_APPLICABILITY_VALUES,
    ContentIdentityKey, build_content_identity_key,
)
from .intake import BuiltIdentityCandidate, SafeIntakeResult, composer_boundary_outcome, safe_intake_built_identity
from .stale_sweep import stale_state_sweep
from .store import CanonicalIdentityStore
from .transition import (
    CreationProvenanceRecord,
    GovernedStateTransitionRecord,
    TransitionClass,
    TransitionResult,
    transition_authority_state,
)

from .importer import (
    CanonicalEraBoundary,
    IdentityImportManifest,
    IdentityImportResult,
    ImportSourceRef,
    SourceUniverseAuthority,
    import_identity_content,
)
