from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable, Tuple

from .models import FeatureIdentity, NormalizerSpec, SearchPolicy
from .stale_sweep import StaleSweepResult, stale_state_sweep
from .store import CanonicalIdentityStore


@dataclass(frozen=True)
class ImportSourceRef:
    source_id: str
    title: str
    authority_class: str
    searched: bool
    importable_identity_rows: int
    notes: str = ""


@dataclass(frozen=True)
class IdentityImportManifest:
    manifest_id: str
    version: str
    source_refs: Tuple[ImportSourceRef, ...]
    declared_source_universe_complete: bool
    unresolved_source_classes: Tuple[str, ...] = ()

    def completeness_errors(self) -> Tuple[str, ...]:
        errors = []
        if not self.manifest_id or not self.version:
            errors.append("IMPORT_MANIFEST_ID_VERSION_REQUIRED")
        if not self.source_refs:
            errors.append("IMPORT_SOURCE_REFS_REQUIRED")
        if any(not ref.source_id or not ref.title for ref in self.source_refs):
            errors.append("IMPORT_SOURCE_REF_ID_TITLE_REQUIRED")
        if any(ref.importable_identity_rows < 0 for ref in self.source_refs):
            errors.append("IMPORTABLE_IDENTITY_ROWS_INVALID")
        if self.declared_source_universe_complete and self.unresolved_source_classes:
            errors.append("COMPLETE_SOURCE_UNIVERSE_WITH_UNRESOLVED_CLASSES")
        if self.declared_source_universe_complete and any(not ref.searched for ref in self.source_refs):
            errors.append("COMPLETE_SOURCE_UNIVERSE_WITH_UNSEARCHED_SOURCE")
        return tuple(errors)

    @property
    def expected_importable_rows(self) -> int:
        return sum(ref.importable_identity_rows for ref in self.source_refs)

    def evidence_hash(self) -> str:
        payload = {
            "manifest_id": self.manifest_id,
            "version": self.version,
            "declared_source_universe_complete": self.declared_source_universe_complete,
            "unresolved_source_classes": list(self.unresolved_source_classes),
            "source_refs": [
                {
                    "source_id": r.source_id,
                    "title": r.title,
                    "authority_class": r.authority_class,
                    "searched": r.searched,
                    "importable_identity_rows": r.importable_identity_rows,
                    "notes": r.notes,
                }
                for r in self.source_refs
            ],
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class IdentityImportResult:
    import_manifest_hash: str
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
    search_policy: SearchPolicy,
    normalizer: NormalizerSpec,
) -> IdentityImportResult:
    errors = list(manifest.completeness_errors())
    incoming = tuple(rows)

    if len(incoming) != manifest.expected_importable_rows:
        errors.append(
            f"IMPORT_ROW_COUNT_MISMATCH:expected={manifest.expected_importable_rows},actual={len(incoming)}"
        )

    # Do not mutate the target store unless manifest-level evidence is internally consistent.
    if errors:
        sweep = stale_state_sweep(
            store=target_store,
            search_policy=search_policy,
            normalizer=normalizer,
        )
        return IdentityImportResult(
            import_manifest_hash=manifest.evidence_hash(),
            imported_row_count=0,
            expected_importable_rows=manifest.expected_importable_rows,
            row_count_reconciled=False,
            population_complete=False,
            stale_sweep=sweep,
            errors=tuple(errors),
        )

    staged = CanonicalIdentityStore(list(target_store.all()) + list(incoming))
    sweep = stale_state_sweep(
        store=staged,
        search_policy=search_policy,
        normalizer=normalizer,
    )

    if not sweep.clean:
        return IdentityImportResult(
            import_manifest_hash=manifest.evidence_hash(),
            imported_row_count=0,
            expected_importable_rows=manifest.expected_importable_rows,
            row_count_reconciled=True,
            population_complete=False,
            stale_sweep=sweep,
            errors=("STALE_STATE_SWEEP_FAILED",),
        )

    target_store.extend(incoming)

    population_complete = (
        manifest.declared_source_universe_complete
        and not manifest.unresolved_source_classes
        and len(incoming) == manifest.expected_importable_rows
    )

    return IdentityImportResult(
        import_manifest_hash=manifest.evidence_hash(),
        imported_row_count=len(incoming),
        expected_importable_rows=manifest.expected_importable_rows,
        row_count_reconciled=True,
        population_complete=population_complete,
        stale_sweep=sweep,
        errors=(),
    )
