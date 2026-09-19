"""SALIX Type-1 Tracker identity lookup reference implementation.

Scope is deliberately narrow: canonical identity lookup only.
No materialization, eligibility, health, package production, FW/ML execution,
or production trading authority is implemented here.
"""

from .models import AbsentClaimToken, FeatureIdentity, IdentityLookupResult, LookupOutcome, NormalizerSpec, SearchPolicy
from .search import identity_lookup
from .stale_sweep import stale_state_sweep
from .store import CanonicalIdentityStore

from .importer import (
    IdentityImportManifest,
    IdentityImportResult,
    ImportSourceRef,
    import_identity_content,
)
