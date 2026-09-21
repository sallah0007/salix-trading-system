"""APPROVED_IMPORT_PACKAGE_REGISTRY — governed import authority (DC-006R, CR015 H-2).

Internal consistency is not governed package authorization. The era boundary,
source universe, manifest and catalogue are all self-hashed, caller-
constructible objects: a caller can build a mutually consistent package whose
hashes all verify. So an import is permitted ONLY when the exact package —
identified by its COMPUTED hashes, never its declared ones — is pinned in this
Tracker-owned registry together with a governed approval reference.

Authorization is PRESENCE IN THIS SOURCE FILE. No caller field confers it:
`approval_authority="OWNER"` on a boundary, or any other string on any package
object, is data, not approval.

PRODUCTION STATE: EMPTY. IMPORT_PRODUCTION_PACKAGE_REGISTRATION_BLOCKED = YES.
The Owner Era-1 activation (Drive 13ltUNSo7rXLoNGfrCDO35XghyRzJ-2_Z__0z0skPnco)
freezes the Era-1 baseline and names PR4/PR5 as implementation basis, but pins
no import-manifest hash, no catalogue hash and no import-package approval. No
entry is invented from it, so every production import refuses.

Entries are added only by a reviewed governed change to _ENTRIES below, exactly
like the search-policy and normalizer registries. The registry is a read-only
view over a FUNCTION-LOCAL dict: there is no module-level backing container to
insert into, replace in, or delete from. Rebinding module attributes or
reflecting on closures/gc/ctypes is code replacement — the declared
out-of-boundary residual — and is what tests use to register fixture packages.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Tuple

_HEX64 = re.compile(r"[0-9a-f]{64}")
# A bare role or status word names WHO might approve; it is not a reference to
# a governed approval record, so it is refused as an approval reference.
_NON_REFERENCE_APPROVALS = frozenset({
    "OWNER", "MANAGER", "APPROVED", "YES", "TRUE", "ADMIN", "SALIX_MANAGER",
    "SALIX_OWNER", "GOVERNED", "AUTHORIZED",
})


@dataclass(frozen=True)
class ApprovedImportPackageEntry:
    package_id: str
    era_boundary_hash: str
    source_universe_hash: str
    import_manifest_hash: str
    catalogue_hash: str
    approval_ref: str

    @property
    def key(self) -> tuple:
        return (self.era_boundary_hash, self.source_universe_hash,
                self.import_manifest_hash, self.catalogue_hash)

    def registry_errors(self) -> Tuple[str, ...]:
        e = []
        if not str(self.package_id).strip():
            e.append("IMPORT_PACKAGE_ID_REQUIRED")
        for name in ("era_boundary_hash", "source_universe_hash",
                     "import_manifest_hash", "catalogue_hash"):
            value = getattr(self, name)
            if not isinstance(value, str) or not _HEX64.fullmatch(value):
                e.append("IMPORT_PACKAGE_HASH_INVALID:" + name)
        ref = self.approval_ref
        if not isinstance(ref, str) or not ref.strip():
            e.append("IMPORT_PACKAGE_APPROVAL_REF_REQUIRED")
        elif ref.strip().upper() in _NON_REFERENCE_APPROVALS:
            e.append("IMPORT_PACKAGE_APPROVAL_REF_NOT_A_REFERENCE:" + ref.strip())
        return tuple(e)


# PRODUCTION: no governed evidence pins a complete import package. Empty.
_ENTRIES: Tuple[ApprovedImportPackageEntry, ...] = ()


def _build_registry(entries) -> Mapping[tuple, ApprovedImportPackageEntry]:
    """Read-only view over a function-local dict. Refuses a defective entry."""
    built = {}
    defects = []
    for entry in entries:
        if type(entry) is not ApprovedImportPackageEntry:
            defects.append("IMPORT_PACKAGE_ENTRY_TYPE_INVALID")
            continue
        defects.extend(f"{entry.package_id}:{x}" for x in entry.registry_errors())
        if entry.key in built:
            defects.append("DUPLICATE_APPROVED_IMPORT_PACKAGE:" + entry.package_id)
        built[entry.key] = entry
    if defects:
        raise RuntimeError("APPROVED_IMPORT_PACKAGE_REGISTRY_INVALID:" + ";".join(defects))
    return MappingProxyType(built)


APPROVED_IMPORT_PACKAGE_REGISTRY: Mapping[tuple, ApprovedImportPackageEntry] = _build_registry(_ENTRIES)


def package_hashes(*, era_boundary, source_universe, manifest, catalogue) -> tuple:
    """The package's identity: COMPUTED hashes only. Declared hash fields are
    never used, so copying an approved package's hash strings onto a different
    package does not make it approved."""
    return (era_boundary.computed_hash(), source_universe.computed_hash(),
            manifest.evidence_hash(), catalogue.computed_hash())


def resolve_approved_import_package(*, era_boundary, source_universe, manifest,
                                    catalogue) -> Tuple[str, ...]:
    """() only when this exact package is pinned in the governed registry."""
    try:
        key = package_hashes(era_boundary=era_boundary, source_universe=source_universe,
                             manifest=manifest, catalogue=catalogue)
    except Exception as exc:  # an unhashable package is not an approved one
        return ("IMPORT_PACKAGE_UNHASHABLE:" + type(exc).__name__,)
    entry = APPROVED_IMPORT_PACKAGE_REGISTRY.get(key)
    if entry is None:
        return ("IMPORT_PACKAGE_NOT_APPROVED",)
    # Integrity REVALIDATED at use, never assumed from membership.
    if type(entry) is not ApprovedImportPackageEntry:
        return ("IMPORT_PACKAGE_ENTRY_TYPE_INVALID",)
    defects = entry.registry_errors()
    if defects:
        return ("IMPORT_PACKAGE_ENTRY_INTEGRITY_FAILED:" + ",".join(defects),)
    if entry.key != key:
        return ("IMPORT_PACKAGE_ENTRY_KEY_MISMATCH",)
    return ()
