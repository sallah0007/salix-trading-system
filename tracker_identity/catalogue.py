from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Tuple

from .content_identity import UNFITTED_TOKEN, build_content_identity_key

def _hash(payload) -> str:
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

@dataclass(frozen=True)
class FeatureDefinitionRecord:
    feature_id: str
    feature_version: str
    semantic_definition: str
    formula: str
    dependencies: Tuple[str, ...]
    era_id: str
    definition_hash: str
    graph_hash: str
    instrument: Optional[str] = None
    timeframe: Optional[str] = None
    authority: str = ""
    purpose: str = ""
    declared_normalization: Optional[str] = None
    causal_time_semantics: Optional[str] = None
    completion_semantics: Optional[str] = None
    availability_class: Optional[str] = None
    source_provider: Optional[str] = None
    price_basis: Optional[str] = None
    data_vintage_mode: Optional[str] = None
    scope_universe: Optional[str] = None
    parameters: Optional[Mapping[str, Any]] = None
    fitted_state: Optional[Any] = None
    proxy_status: Optional[str] = None
    # Governed declaration of whether this definition's SEMANTICS are specific
    # to its instrument. INSTRUMENT_AGNOSTIC: the bound instrument is payload
    # binding only. INSTRUMENT_SPECIFIC: instrument is scope identity content.
    # Undeclared (None) is unclear and yields no content key.
    instrument_applicability: Optional[str] = None

    def declared_content(self) -> dict:
        """Governed content with NO identity and NO process provenance.

        Dimensions never declared on the record are OMITTED, so an
        under-populated legacy record yields completeness errors rather than
        a silently partial key.
        """
        declared = {
            "normalized_definition_graph": self.formula,
            "dependency_closure": tuple(self.dependencies),
            "parameters": dict(self.parameters) if self.parameters is not None else None,
            "declared_normalization": self.declared_normalization,
            "causal_time_semantics": self.causal_time_semantics,
            "completion_semantics": self.completion_semantics,
            "availability_class": self.availability_class,
            "source_provider": self.source_provider,
            "price_basis": self.price_basis,
            "data_vintage_mode": self.data_vintage_mode,
            "instrument": self.instrument,
            "timeframe": self.timeframe,
            "scope_universe": self.scope_universe,
            "fitted_state": self.fitted_state,
            "instrument_applicability": self.instrument_applicability,
        }
        return {k: v for k, v in declared.items() if v is not None}

    def content_identity_key(self):
        """(ContentIdentityKey | None, errors) — recomputed, never stored-only."""
        return build_content_identity_key(self.declared_content())

    def computed_definition_hash(self) -> str:
        return _hash({
            "era_id": self.era_id,
            "feature_id": self.feature_id,
            "feature_version": self.feature_version,
            "formula": self.formula,
            "instrument": self.instrument,
            "semantic_definition": self.semantic_definition,
            "timeframe": self.timeframe,
        })

    def computed_graph_hash(self) -> str:
        return _hash({
            "dependencies": list(self.dependencies),
            "era_id": self.era_id,
            "feature_id": self.feature_id,
            "feature_version": self.feature_version,
        })

    def completeness_errors(self) -> Tuple[str, ...]:
        errors=[]
        if not self.feature_id or not self.feature_version or not self.era_id:
            errors.append("CATALOGUE_IDENTITY_FIELDS_REQUIRED")
        if not self.semantic_definition or not self.formula:
            errors.append("CATALOGUE_DEFINITION_FORMULA_REQUIRED")
        if self.definition_hash != self.computed_definition_hash():
            errors.append("CATALOGUE_DEFINITION_HASH_MISMATCH:"+self.feature_id)
        if self.graph_hash != self.computed_graph_hash():
            errors.append("CATALOGUE_GRAPH_HASH_MISMATCH:"+self.feature_id)
        return tuple(errors)

@dataclass(frozen=True)
class FeatureDefinitionCatalogue:
    catalogue_id: str
    era_id: str
    definitions: Tuple[FeatureDefinitionRecord, ...]

    def completeness_errors(self) -> Tuple[str, ...]:
        errors=[]
        if not self.catalogue_id:
            errors.append("CATALOGUE_ID_REQUIRED")
        if not self.era_id:
            errors.append("CATALOGUE_ERA_ID_REQUIRED")
        keys=[(d.feature_id,d.feature_version) for d in self.definitions]
        if len(set(keys)) != len(keys):
            errors.append("DUPLICATE_CATALOGUE_IDENTITY")
        for d in self.definitions:
            errors.extend(d.completeness_errors())
            if d.era_id != self.era_id:
                errors.append("CATALOGUE_DEFINITION_ERA_MISMATCH:"+d.feature_id)
        return tuple(errors)

    def find(self, feature_id: str, feature_version: str):
        matches=[d for d in self.definitions if d.feature_id==feature_id and d.feature_version==feature_version]
        return matches[0] if len(matches)==1 else None
