from dataclasses import dataclass, field
from typing import Iterable
from .models import FeatureIdentity

@dataclass
class CanonicalIdentityStore:
    records:list[FeatureIdentity]=field(default_factory=list)
    def add(self,record:FeatureIdentity)->None: self.records.append(record)
    def extend(self,records:Iterable[FeatureIdentity])->None: self.records.extend(records)
    def list_scope(self,scope:str): return tuple(r for r in self.records if r.scope==scope)
    def enumerate_scopes(self): return tuple(sorted({r.scope for r in self.records}))
    def all(self): return tuple(self.records)
