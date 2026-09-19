from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Optional, Tuple

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
