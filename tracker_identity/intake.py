from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from .importer import CanonicalEraBoundary
from .catalogue import FeatureDefinitionRecord
from .models import FeatureIdentity, LookupOutcome, NormalizerSpec, SearchPolicy
from .stale_sweep import StaleSweepResult, stale_state_sweep
from .store import CanonicalIdentityStore

@dataclass(frozen=True)
class BuiltIdentityCandidate:
    feature_id: str
    feature_version: str
    definition_hash: str
    graph_hash: str
    semantic_definition: str
    formula: str
    lifecycle_state: str
    is_current: bool
    scope: str
    aliases: Tuple[str, ...] = ()
    dependencies: Tuple[str, ...] = ()
    canonical_survivor: Optional[str] = None
    instrument: Optional[str] = None
    timeframe: Optional[str] = None
    source_provider: Optional[str] = None
    lineage_ref: Optional[str] = None

@dataclass(frozen=True)
class SafeIntakeResult:
    accepted: bool
    assigned_era_id: Optional[str]
    identity: Optional[FeatureIdentity]
    definition: Optional[FeatureDefinitionRecord]
    stale_sweep: StaleSweepResult
    errors: Tuple[str, ...]

def safe_intake_built_identity(
    *,
    target_store: CanonicalIdentityStore,
    candidate: BuiltIdentityCandidate,
    era_boundary: Optional[CanonicalEraBoundary],
    search_policy: SearchPolicy,
    normalizer: NormalizerSpec,
) -> SafeIntakeResult:
    errors=[]

    if era_boundary is None:
        errors.append("ACTIVE_ERA_BOUNDARY_REQUIRED")
    else:
        errors.extend(era_boundary.completeness_errors())
        if target_store.registry_id != era_boundary.registry_id:
            errors.append("ERA_BOUNDARY_REGISTRY_ID_MISMATCH")
        if target_store.active_era_id != era_boundary.era_id:
            errors.append("STORE_ACTIVE_ERA_MISMATCH")

    if not candidate.feature_id or not candidate.feature_version:
        errors.append("BUILT_IDENTITY_ID_VERSION_REQUIRED")
    if not candidate.definition_hash or not candidate.graph_hash:
        errors.append("BUILT_IDENTITY_HASHES_REQUIRED")
    if candidate.lifecycle_state.upper() == "VALIDATION_ONLY" and candidate.scope != "validation":
        errors.append("VALIDATION_ONLY_REQUIRES_VALIDATION_SCOPE")

    if errors:
        sweep=stale_state_sweep(store=target_store,search_policy=search_policy,normalizer=normalizer)
        return SafeIntakeResult(False,None,None,None,sweep,tuple(errors))

    # Era is deliberately not accepted from Composer/build output. Tracker assigns it
    # solely from the verified active CanonicalEraBoundary, then recomputes the
    # definition and dependency graph bindings under that era before registry mutation.
    definition=FeatureDefinitionRecord(
        feature_id=candidate.feature_id,
        feature_version=candidate.feature_version,
        semantic_definition=candidate.semantic_definition,
        formula=candidate.formula,
        dependencies=candidate.dependencies,
        era_id=era_boundary.era_id,
        definition_hash=candidate.definition_hash,
        graph_hash=candidate.graph_hash,
        instrument=candidate.instrument,
        timeframe=candidate.timeframe,
        authority="SAFE_INTAKE_BUILD_OUTPUT",
        purpose="TRACKER_SAFE_INTAKE",
    )
    definition_errors=definition.completeness_errors()
    if definition_errors:
        sweep=stale_state_sweep(store=target_store,search_policy=search_policy,normalizer=normalizer)
        return SafeIntakeResult(False,era_boundary.era_id,None,None,sweep,definition_errors)

    identity=FeatureIdentity(
        feature_id=candidate.feature_id,
        feature_version=candidate.feature_version,
        definition_hash=candidate.definition_hash,
        graph_hash=candidate.graph_hash,
        lifecycle_state=candidate.lifecycle_state,
        is_current=candidate.is_current,
        scope=candidate.scope,
        era_id=era_boundary.era_id,
        aliases=candidate.aliases,
        dependencies=candidate.dependencies,
        canonical_survivor=candidate.canonical_survivor,
        instrument=candidate.instrument,
        timeframe=candidate.timeframe,
        source_provider=candidate.source_provider,
        lineage_ref=candidate.lineage_ref,
    )

    staged=CanonicalIdentityStore(
        list(target_store.all())+[identity],
        registry_id=target_store.registry_id,
        active_era_id=target_store.active_era_id,
    )
    sweep=stale_state_sweep(store=staged,search_policy=search_policy,normalizer=normalizer)
    if not sweep.clean:
        return SafeIntakeResult(False,era_boundary.era_id,None,None,sweep,("STALE_STATE_SWEEP_FAILED",))

    target_store.add(identity)
    return SafeIntakeResult(True,era_boundary.era_id,identity,definition,sweep,())

def composer_boundary_outcome(outcome: LookupOutcome) -> LookupOutcome:
    """Map Tracker era-qualified lookup semantics to the frozen Composer boundary.

    Composer has no era concept. Therefore an ERA_1-scoped absence cannot be
    represented as global ABSENT at that boundary.
    """
    if outcome == LookupOutcome.ABSENT_IN_ERA_1:
        return LookupOutcome.INCOMPLETE_LOOKUP
    return outcome
