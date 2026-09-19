from dataclasses import dataclass, field
from threading import RLock
from typing import Iterable
from .models import FeatureIdentity

@dataclass
class CanonicalIdentityStore:
    records:list[FeatureIdentity]=field(default_factory=list)
    registry_id:str="SALIX-ERA1-REGISTRY"
    active_era_id:str="ERA_1"
    creation_records:list[object]=field(default_factory=list)
    transitions:list[object]=field(default_factory=list)
    _transition_lock:RLock=field(default_factory=RLock,repr=False,compare=False)

    def add(self,record:FeatureIdentity)->None: self.records.append(record)
    def extend(self,records:Iterable[FeatureIdentity])->None: self.records.extend(records)
    def add_creation(self,record)->None: self.creation_records.append(record)
    def add_transition(self,record)->None: self.transitions.append(record)
    def list_scope(self,scope:str,era_id:str|None=None):
        return tuple(r for r in self.records if r.scope==scope and (era_id is None or r.era_id==era_id))
    def enumerate_scopes(self,era_id:str|None=None):
        return tuple(sorted({r.scope for r in self.records if era_id is None or r.era_id==era_id}))
    def all(self): return tuple(self.records)
    def all_creation_records(self): return tuple(self.creation_records)
    def all_transitions(self): return tuple(self.transitions)

    def creation_for_key(self,key):
        matches=[r for r in self.creation_records if (r.object_id,r.object_version,r.era_id)==key]
        return matches[0] if len(matches)==1 else None

    def latest_transition_for_key(self,key):
        matches=[r for r in self.transitions if (r.object_id,r.object_version,r.era_id)==key]
        if not matches:
            return None
        by_id={r.transition_id:r for r in matches}
        referenced={r.prior_transition_id for r in matches if r.prior_transition_id in by_id}
        heads=[r for r in matches if r.transition_id not in referenced]
        return heads[0] if len(heads)==1 else None
