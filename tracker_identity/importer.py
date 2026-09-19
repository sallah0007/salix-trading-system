from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Tuple

from .models import FeatureIdentity, NormalizerSpec, SearchPolicy
from .catalogue import FeatureDefinitionCatalogue
from .stale_sweep import StaleSweepResult, stale_state_sweep
from .store import CanonicalIdentityStore

PERMITTED_IDENTITY_ROW_AUTHORITY_CLASSES = (
    "CANONICAL",
    "CURRENT_CANONICAL_REGISTRY",
    "CURRENT_FEATURE_DEFINITION_CATALOGUE",
)

def _hash_payload(payload) -> str:
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

@dataclass(frozen=True)
class ImportSourceRef:
    source_id: str
    title: str
    authority_class: str
    searched: bool
    importable_identity_rows: int
    era_id: str
    notes: str = ""

@dataclass(frozen=True)
class SourceUniverseAuthority:
    source_universe_id: str
    version: str
    source_universe_hash: str
    authority_source_id: str
    expected_source_ids: Tuple[str, ...]
    universe_complete: bool
    era_id: str
    unresolved_source_classes: Tuple[str, ...] = ()

    def computed_hash(self) -> str:
        return _hash_payload({
            "source_universe_id": self.source_universe_id,
            "version": self.version,
            "authority_source_id": self.authority_source_id,
            "expected_source_ids": list(self.expected_source_ids),
            "universe_complete": self.universe_complete,
            "era_id": self.era_id,
            "unresolved_source_classes": list(self.unresolved_source_classes),
        })

    def completeness_errors(self) -> Tuple[str, ...]:
        errors=[]
        if not self.source_universe_id or not self.version or not self.source_universe_hash:
            errors.append("SOURCE_UNIVERSE_ID_VERSION_HASH_REQUIRED")
        if not self.authority_source_id:
            errors.append("SOURCE_UNIVERSE_AUTHORITY_SOURCE_REQUIRED")
        if not self.era_id:
            errors.append("SOURCE_UNIVERSE_ERA_ID_REQUIRED")
        if len(set(self.expected_source_ids)) != len(self.expected_source_ids):
            errors.append("DUPLICATE_EXPECTED_SOURCE_ID")
        if self.source_universe_hash and self.source_universe_hash != self.computed_hash():
            errors.append("SOURCE_UNIVERSE_HASH_MISMATCH")
        if self.universe_complete and self.unresolved_source_classes:
            errors.append("COMPLETE_SOURCE_UNIVERSE_WITH_UNRESOLVED_CLASSES")
        return tuple(errors)

@dataclass(frozen=True)
class CanonicalEraBoundary:
    era_id: str
    version: str
    boundary_hash: str
    effective_ts: str
    predecessor_era_id: str
    registry_id: str
    catalogue_id: str
    source_universe_id: str
    pre_era_content_default: str
    historical_gap_status: str
    historical_gap_owner: str
    revisit_trigger: str
    absent_proven: bool
    created_by: str
    approval_authority: str
    created_ts: str

    def computed_hash(self) -> str:
        return _hash_payload({
            "era_id": self.era_id,
            "version": self.version,
            "effective_ts": self.effective_ts,
            "predecessor_era_id": self.predecessor_era_id,
            "registry_id": self.registry_id,
            "catalogue_id": self.catalogue_id,
            "source_universe_id": self.source_universe_id,
            "pre_era_content_default": self.pre_era_content_default,
            "historical_gap_status": self.historical_gap_status,
            "historical_gap_owner": self.historical_gap_owner,
            "revisit_trigger": self.revisit_trigger,
            "absent_proven": self.absent_proven,
            "created_by": self.created_by,
            "approval_authority": self.approval_authority,
            "created_ts": self.created_ts,
        })

    def completeness_errors(self) -> Tuple[str, ...]:
        errors=[]
        for name,value in (
            ("ERA_ID",self.era_id),("ERA_VERSION",self.version),
            ("ERA_BOUNDARY_HASH",self.boundary_hash),("ERA_EFFECTIVE_TS",self.effective_ts),
            ("REGISTRY_ID",self.registry_id),("CATALOGUE_ID",self.catalogue_id),
            ("SOURCE_UNIVERSE_ID",self.source_universe_id),
            ("HISTORICAL_GAP_STATUS",self.historical_gap_status),
            ("HISTORICAL_GAP_OWNER",self.historical_gap_owner),
            ("REVISIT_TRIGGER",self.revisit_trigger),("CREATED_BY",self.created_by),
            ("APPROVAL_AUTHORITY",self.approval_authority),("CREATED_TS",self.created_ts),
        ):
            if not str(value).strip():
                errors.append(name+"_REQUIRED")
        if self.boundary_hash and self.boundary_hash != self.computed_hash():
            errors.append("ERA_BOUNDARY_HASH_MISMATCH")
        if self.pre_era_content_default != "UNRESOLVED_NON_IMPORTABLE":
            errors.append("PRE_ERA_CONTENT_DEFAULT_INVALID")
        if self.absent_proven:
            errors.append("HISTORICAL_ABSENT_MUST_REMAIN_UNPROVEN")
        return tuple(errors)

@dataclass(frozen=True)
class IdentityImportManifest:
    manifest_id: str
    version: str
    era_id: str
    source_refs: Tuple[ImportSourceRef, ...]

    def completeness_errors(self, source_universe: SourceUniverseAuthority) -> Tuple[str, ...]:
        errors = list(source_universe.completeness_errors())
        if not self.manifest_id or not self.version:
            errors.append("IMPORT_MANIFEST_ID_VERSION_REQUIRED")
        if not self.era_id:
            errors.append("IMPORT_MANIFEST_ERA_ID_REQUIRED")
        if self.era_id != source_universe.era_id:
            errors.append("MANIFEST_SOURCE_UNIVERSE_ERA_MISMATCH")
        if not self.source_refs:
            errors.append("IMPORT_SOURCE_REFS_REQUIRED")
        if any(not ref.source_id or not ref.title for ref in self.source_refs):
            errors.append("IMPORT_SOURCE_REF_ID_TITLE_REQUIRED")
        if any(not ref.era_id for ref in self.source_refs):
            errors.append("IMPORT_SOURCE_REF_ERA_REQUIRED")
        if any(ref.era_id != self.era_id for ref in self.source_refs):
            errors.append("IMPORT_SOURCE_REF_ERA_MISMATCH")
        if any(ref.importable_identity_rows < 0 for ref in self.source_refs):
            errors.append("IMPORTABLE_IDENTITY_ROWS_INVALID")
        ids=[ref.source_id for ref in self.source_refs]
        if len(set(ids)) != len(ids):
            errors.append("DUPLICATE_IMPORT_SOURCE_ID")
        expected=set(source_universe.expected_source_ids)
        declared=set(ids)
        missing=sorted(expected-declared)
        extra=sorted(declared-expected)
        if missing:
            errors.append("UNENUMERATED_SOURCE:"+",".join(missing))
        if extra:
            errors.append("SOURCE_OUTSIDE_UNIVERSE_AUTHORITY:"+",".join(extra))
        if source_universe.universe_complete and any(not ref.searched for ref in self.source_refs):
            errors.append("COMPLETE_SOURCE_UNIVERSE_WITH_UNSEARCHED_SOURCE")
        for ref in self.source_refs:
            if ref.importable_identity_rows and ref.authority_class not in PERMITTED_IDENTITY_ROW_AUTHORITY_CLASSES:
                errors.append("NONCANONICAL_SOURCE_HAS_IMPORTABLE_ROWS:"+ref.source_id)
        return tuple(errors)

    @property
    def expected_importable_rows(self) -> int:
        return sum(ref.importable_identity_rows for ref in self.source_refs)

    def evidence_hash(self) -> str:
        return _hash_payload({
            "manifest_id": self.manifest_id,
            "version": self.version,
            "era_id": self.era_id,
            "source_refs": [
                {
                    "source_id": r.source_id,
                    "title": r.title,
                    "authority_class": r.authority_class,
                    "searched": r.searched,
                    "importable_identity_rows": r.importable_identity_rows,
                    "era_id": r.era_id,
                    "notes": r.notes,
                }
                for r in self.source_refs
            ],
        })

@dataclass(frozen=True)
class IdentityImportResult:
    import_manifest_hash: str
    source_universe_hash: str
    era_boundary_hash: str
    imported_row_count: int
    expected_importable_rows: int
    row_count_reconciled: bool
    population_complete: bool
    stale_sweep: StaleSweepResult
    errors: Tuple[str, ...]

def import_identity_content(
    *,
    target_store: CanonicalIdentityStore,
    rows: Iterable[FeatureIdentity],
    manifest: IdentityImportManifest,
    source_universe: SourceUniverseAuthority,
    era_boundary: CanonicalEraBoundary,
    catalogue: FeatureDefinitionCatalogue,
    search_policy: SearchPolicy,
    normalizer: NormalizerSpec,
) -> IdentityImportResult:
    errors = list(era_boundary.completeness_errors())
    errors.extend(manifest.completeness_errors(source_universe))
    errors.extend(catalogue.completeness_errors())
    incoming = tuple(rows)
    refs={ref.source_id:ref for ref in manifest.source_refs}

    if catalogue.catalogue_id != era_boundary.catalogue_id:
        errors.append("ERA_BOUNDARY_CATALOGUE_ID_MISMATCH")
    if catalogue.era_id != era_boundary.era_id:
        errors.append("CATALOGUE_BOUNDARY_ERA_MISMATCH")
    if target_store.registry_id != era_boundary.registry_id:
        errors.append("ERA_BOUNDARY_REGISTRY_ID_MISMATCH")
    if target_store.active_era_id != era_boundary.era_id:
        errors.append("STORE_ACTIVE_ERA_MISMATCH")
    if source_universe.source_universe_id != era_boundary.source_universe_id:
        errors.append("ERA_BOUNDARY_SOURCE_UNIVERSE_ID_MISMATCH")
    if source_universe.era_id != era_boundary.era_id:
        errors.append("SOURCE_UNIVERSE_BOUNDARY_ERA_MISMATCH")
    if manifest.era_id != era_boundary.era_id:
        errors.append("MANIFEST_BOUNDARY_ERA_MISMATCH")

    if len(incoming) != manifest.expected_importable_rows:
        errors.append(
            f"IMPORT_ROW_COUNT_MISMATCH:expected={manifest.expected_importable_rows},actual={len(incoming)}"
        )

    per_source=Counter(r.import_source_id for r in incoming)
    for ref in manifest.source_refs:
        actual=per_source.get(ref.source_id,0)
        if actual != ref.importable_identity_rows:
            errors.append(
                f"IMPORT_SOURCE_ROW_COUNT_MISMATCH:{ref.source_id}:expected={ref.importable_identity_rows},actual={actual}"
            )

    for row in incoming:
        definition=catalogue.find(row.feature_id,row.feature_version)
        if definition is None:
            errors.append("ROW_DEFINITION_NOT_IN_CATALOGUE:"+row.feature_id+":"+row.feature_version)
        else:
            if row.definition_hash != definition.definition_hash:
                errors.append("ROW_DEFINITION_HASH_MISMATCH:"+row.feature_id)
            if row.graph_hash != definition.graph_hash:
                errors.append("ROW_GRAPH_HASH_MISMATCH:"+row.feature_id)
            if tuple(row.dependencies) != tuple(definition.dependencies):
                errors.append("ROW_DEPENDENCY_GRAPH_MISMATCH:"+row.feature_id)
            if row.instrument != definition.instrument:
                errors.append("ROW_CATALOGUE_INSTRUMENT_MISMATCH:"+row.feature_id)
            if row.timeframe != definition.timeframe:
                errors.append("ROW_CATALOGUE_TIMEFRAME_MISMATCH:"+row.feature_id)
        if row.era_id != era_boundary.era_id:
            errors.append("ROW_ERA_MISMATCH:"+row.feature_id)
        if not row.import_source_id or not row.import_source_authority_class:
            errors.append("ROW_IMPORT_PROVENANCE_REQUIRED:"+row.feature_id)
            continue
        ref=refs.get(row.import_source_id)
        if ref is None:
            errors.append("ROW_SOURCE_NOT_IN_MANIFEST:"+row.import_source_id)
            continue
        if ref.era_id != row.era_id:
            errors.append("ROW_SOURCE_ERA_MISMATCH:"+row.import_source_id)
        if row.import_source_authority_class != ref.authority_class:
            errors.append("ROW_SOURCE_AUTHORITY_MISMATCH:"+row.import_source_id)
        if row.import_source_authority_class not in PERMITTED_IDENTITY_ROW_AUTHORITY_CLASSES:
            errors.append("ROW_SOURCE_AUTHORITY_NOT_PERMITTED:"+row.import_source_id)

    if errors:
        sweep = stale_state_sweep(
            store=target_store,
            search_policy=search_policy,
            normalizer=normalizer,
        )
        return IdentityImportResult(
            import_manifest_hash=manifest.evidence_hash(),
            source_universe_hash=source_universe.source_universe_hash,
            era_boundary_hash=era_boundary.boundary_hash,
            imported_row_count=0,
            expected_importable_rows=manifest.expected_importable_rows,
            row_count_reconciled=False,
            population_complete=False,
            stale_sweep=sweep,
            errors=tuple(errors),
        )

    staged = CanonicalIdentityStore(
        list(target_store.all()) + list(incoming),
        registry_id=target_store.registry_id,
        active_era_id=target_store.active_era_id,
    )
    sweep = stale_state_sweep(
        store=staged,
        search_policy=search_policy,
        normalizer=normalizer,
    )

    if not sweep.clean:
        return IdentityImportResult(
            import_manifest_hash=manifest.evidence_hash(),
            source_universe_hash=source_universe.source_universe_hash,
            era_boundary_hash=era_boundary.boundary_hash,
            imported_row_count=0,
            expected_importable_rows=manifest.expected_importable_rows,
            row_count_reconciled=True,
            population_complete=False,
            stale_sweep=sweep,
            errors=("STALE_STATE_SWEEP_FAILED",),
        )

    target_store.extend(incoming)

    population_complete = (
        source_universe.universe_complete
        and not source_universe.unresolved_source_classes
        and len(incoming) == manifest.expected_importable_rows
    )

    return IdentityImportResult(
        import_manifest_hash=manifest.evidence_hash(),
        source_universe_hash=source_universe.source_universe_hash,
        era_boundary_hash=era_boundary.boundary_hash,
        imported_row_count=len(incoming),
        expected_importable_rows=manifest.expected_importable_rows,
        row_count_reconciled=True,
        population_complete=population_complete,
        stale_sweep=sweep,
        errors=(),
    )
