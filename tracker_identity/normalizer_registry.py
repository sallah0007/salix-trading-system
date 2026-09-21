from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Tuple

from .models import SUPPORTED_EQUIVALENCE_CLASSES, NormalizerSpec

NORMALIZER_ID = "tracker.identity.normalizer"
NORMALIZER_VERSION = "1"

@dataclass(frozen=True)
class GovernedNormalizerEntry:
    """One governed, versioned normalizer owned by Tracker.

    NormalizerSpec.computed_hash() is derived from the caller's own field
    values, exactly like SearchPolicy: a caller can name any normalizer, list
    any equivalence classes, self-hash the result and pass completeness. Which
    equivalences a lookup is entitled to apply is a governed property, so the
    identity of the normalizer must resolve against Tracker-owned definitions
    rather than against itself.
    """
    normalizer_id:str
    version:str
    equivalence_classes:Tuple[str,...]

    def __post_init__(self):
        object.__setattr__(self,"equivalence_classes",tuple(self.equivalence_classes))

    @property
    def key(self)->tuple:
        return (self.normalizer_id,self.version)

    def canonical_spec(self)->NormalizerSpec:
        provisional=NormalizerSpec(
            normalizer_id=self.normalizer_id,version=self.version,
            normalizer_hash="",equivalence_classes=self.equivalence_classes,
        )
        return NormalizerSpec(
            normalizer_id=provisional.normalizer_id,version=provisional.version,
            normalizer_hash=provisional.computed_hash(),
            equivalence_classes=provisional.equivalence_classes,
        )

    @property
    def normalizer_hash(self)->str:
        return self.canonical_spec().normalizer_hash

    def registry_errors(self)->Tuple[str,...]:
        e=[]
        if not self.normalizer_id or not self.version:
            e.append("GOVERNED_NORMALIZER_ID_VERSION_REQUIRED")
        if not self.equivalence_classes:
            e.append("GOVERNED_NORMALIZER_EQUIVALENCE_CLASSES_REQUIRED")
        unsupported=sorted(set(self.equivalence_classes)-set(SUPPORTED_EQUIVALENCE_CLASSES))
        if unsupported:
            # A governed entry may not widen equivalence capability. Algebraic
            # equivalence is NOT implemented and NOT validated; the registry
            # refuses to hold an entry that claims otherwise.
            e.append("GOVERNED_NORMALIZER_UNSUPPORTED_EQUIVALENCE_CLASS:"+",".join(unsupported))
        e.extend("GOVERNED_NORMALIZER_"+x for x in self.canonical_spec().completeness_errors())
        return tuple(e)

# Future normalizer versions are added HERE as separate entries. An existing
# entry is never edited in place.
_ENTRIES:Tuple[GovernedNormalizerEntry,...]=(
    GovernedNormalizerEntry(
        normalizer_id=NORMALIZER_ID,
        version=NORMALIZER_VERSION,
        equivalence_classes=("EXACT_STRUCTURAL_IDENTITY",),
    ),
)

def _build_registry()->Mapping[tuple,GovernedNormalizerEntry]:
    """Build the registry from FUNCTION-LOCAL state.

    The dict never becomes a module attribute, so there is no backing object
    left behind for a caller to reach and mutate. Only the read-only view
    escapes this function.
    """
    built={}
    defects=[]
    for entry in _ENTRIES:
        defects.extend(f"{entry.normalizer_id}@{entry.version}:{x}"
                       for x in entry.registry_errors())
        if entry.key in built:
            defects.append("DUPLICATE_GOVERNED_NORMALIZER_KEY:"+str(entry.key))
        built[entry.key]=entry
    if defects:
        raise RuntimeError("GOVERNED_NORMALIZER_REGISTRY_INVALID:"+";".join(defects))
    return MappingProxyType(built)

GOVERNED_NORMALIZERS:Mapping[tuple,GovernedNormalizerEntry]=_build_registry()

def governed_normalizer(normalizer_id:str=NORMALIZER_ID,
                        version:str=NORMALIZER_VERSION)->NormalizerSpec:
    entry=GOVERNED_NORMALIZERS.get((normalizer_id,version))
    if entry is None:
        raise KeyError("NORMALIZER_NOT_GOVERNED:"+str(normalizer_id)+"@"+str(version))
    return entry.canonical_spec()

def _entry_or_errors(normalizer_id,version):
    entry=GOVERNED_NORMALIZERS.get((normalizer_id,version))
    if entry is None:
        return None,("NORMALIZER_NOT_GOVERNED:"+str(normalizer_id)+"@"+str(version),)
    # Integrity is REVALIDATED, never assumed from membership alone.
    entry_defects=entry.registry_errors()
    if entry_defects:
        return None,("GOVERNED_NORMALIZER_ENTRY_INTEGRITY_FAILED:"+",".join(entry_defects),)
    return entry,()

def resolve_governed_normalizer(normalizer)->Tuple[str,...]:
    """Bind a caller-presented NormalizerSpec to governed authority."""
    if normalizer is None:
        return ("NORMALIZER_REQUIRED",)
    entry,errors=_entry_or_errors(getattr(normalizer,"normalizer_id",None),
                                  getattr(normalizer,"version",None))
    if errors:
        return errors
    e=[]
    if tuple(normalizer.equivalence_classes)!=tuple(entry.equivalence_classes):
        e.append("NORMALIZER_EQUIVALENCE_CLASSES_NOT_GOVERNED")
    if str(normalizer.normalizer_hash)!=entry.normalizer_hash:
        e.append("NORMALIZER_HASH_NOT_GOVERNED")
    return tuple(e)

def resolve_governed_normalizer_binding(normalizer_id,version,normalizer_hash)->Tuple[str,...]:
    """Resolve a recorded (id, version, hash) triple against the registry."""
    entry,errors=_entry_or_errors(normalizer_id,version)
    if errors:
        return errors
    if str(normalizer_hash)!=entry.normalizer_hash:
        return ("NORMALIZER_HASH_NOT_GOVERNED",)
    return ()
