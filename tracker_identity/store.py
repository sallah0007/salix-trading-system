from dataclasses import dataclass, field
from typing import Iterable
from .models import FeatureIdentity

@dataclass
class CanonicalIdentityStore:
    records:list[FeatureIdentity]=field(default_factory=list)
    registry_id:str="SALIX-ERA1-REGISTRY"
    active_era_id:str="ERA_1"

    def add(self,record:FeatureIdentity)->None: self.records.append(record)
    def extend(self,records:Iterable[FeatureIdentity])->None: self.records.extend(records)
    def list_scope(self,scope:str,era_id:str|None=None):
        return tuple(r for r in self.records if r.scope==scope and (era_id is None or r.era_id==era_id))
    def enumerate_scopes(self,era_id:str|None=None):
        return tuple(sorted({r.scope for r in self.records if era_id is None or r.era_id==era_id}))
    def all(self): return tuple(self.records)
