from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Optional, Tuple

NORMALIZER_ALGORITHM_ID = "SALIX_TYPE1_NORMALIZER_V1"
SUPPORTED_EQUIVALENCE_CLASSES = ("EXACT_STRUCTURAL_IDENTITY",)
LOOKUP_ERA_SCOPES = ("ERA_1_ONLY","ALL_ERAS")
SUBJECT_MODES = ("CANONICAL_ID","PRE_ID")
SCOPE_STATUSES = ("LOADED","EMPTY_VERIFIED","UNREACHABLE","UNKNOWN")
CLAIM_STATES = ("ACTIVE","RELEASED","EXPIRED","ABANDONED")
DEFAULT_CLAIM_TTL_SECONDS = 900

def _sha256_json(payload) -> str:
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

class LookupOutcome(str, Enum):
    EXACT_CANONICAL_IDENTITY="EXACT_CANONICAL_IDENTITY"
    NEAR_MATCH="NEAR_MATCH"
    ABSENT="ABSENT"
    ABSENT_IN_ERA_1="ABSENT_IN_ERA_1"
    ABSENT_EXACT_STRUCTURAL_IN_ERA_1="ABSENT_EXACT_STRUCTURAL_IN_ERA_1"
    INCOMPLETE_LOOKUP="INCOMPLETE_LOOKUP"
    ERROR_UNRESOLVED="ERROR_UNRESOLVED"

@dataclass(frozen=True)
class FeatureIdentity:
    feature_id:str
    feature_version:str
    definition_hash:str
    graph_hash:str
    lifecycle_state:str
    is_current:bool
    scope:str
    era_id:str="ERA_1"
    aliases:Tuple[str,...]=()
    dependencies:Tuple[str,...]=()
    canonical_survivor:Optional[str]=None
    instrument:Optional[str]=None
    timeframe:Optional[str]=None
    source_provider:Optional[str]=None
    lineage_ref:Optional[str]=None
    import_source_id:Optional[str]=None
    import_source_authority_class:Optional[str]=None
    content_key_composite:Optional[str]=None
    content_key_definition:Optional[str]=None
    content_key_causal_time:Optional[str]=None
    content_key_provenance:Optional[str]=None
    content_key_scope:Optional[str]=None
    content_key_fitted:Optional[str]=None
    content_key_algorithm_id:Optional[str]=None
    definition_record_ref:Optional[str]=None
    proxy_status:Optional[str]=None

    @property
    def content_subkeys(self):
        return (
            self.content_key_definition,self.content_key_causal_time,
            self.content_key_provenance,self.content_key_scope,
            self.content_key_fitted,
        )

    @property
    def has_content_key(self)->bool:
        return bool(self.content_key_composite) and all(self.content_subkeys)

    @property
    def canonical_key(self):
        return (self.feature_id,self.feature_version,self.definition_hash,self.graph_hash,self.instrument,self.timeframe)

@dataclass(frozen=True)
class SearchPolicy:
    policy_id:str
    version:str
    policy_hash:str
    required_scopes:Tuple[str,...]
    searched_scopes:Tuple[str,...]
    scope_exclusions:Mapping[str,str]=field(default_factory=dict)

    def computed_hash(self) -> str:
        return _sha256_json({
            "policy_id":self.policy_id,
            "version":self.version,
            "required_scopes":list(self.required_scopes),
            "searched_scopes":list(self.searched_scopes),
            "scope_exclusions":dict(sorted(self.scope_exclusions.items())),
        })

    def completeness_errors(self):
        e=[]
        if not self.policy_id or not self.version or not self.policy_hash:
            e.append("SEARCH_POLICY_ID_VERSION_HASH_REQUIRED")
        required,searched,excluded=set(self.required_scopes),set(self.searched_scopes),set(self.scope_exclusions)
        if searched-required: e.append("UNKNOWN_SEARCH_SCOPE:"+",".join(sorted(searched-required)))
        if excluded-required: e.append("UNKNOWN_EXCLUDED_SCOPE:"+",".join(sorted(excluded-required)))
        if required-searched-excluded: e.append("UNENUMERATED_SCOPE:"+",".join(sorted(required-searched-excluded)))
        if searched & excluded: e.append("SCOPE_BOTH_SEARCHED_AND_EXCLUDED:"+",".join(sorted(searched & excluded)))
        if any(not str(v).strip() for v in self.scope_exclusions.values()):
            e.append("EXCLUSION_REASON_CODE_REQUIRED")
        if self.policy_hash and self.policy_hash != self.computed_hash():
            e.append("SEARCH_POLICY_HASH_MISMATCH")
        return tuple(e)

@dataclass(frozen=True)
class NormalizerSpec:
    normalizer_id:str
    version:str
    normalizer_hash:str
    equivalence_classes:Tuple[str,...]

    def computed_hash(self) -> str:
        return _sha256_json({
            "normalizer_id":self.normalizer_id,
            "version":self.version,
            "algorithm_id":NORMALIZER_ALGORITHM_ID,
            "equivalence_classes":list(self.equivalence_classes),
        })

    def completeness_errors(self):
        e=[]
        if not self.normalizer_id or not self.version or not self.normalizer_hash:
            e.append("NORMALIZER_ID_VERSION_HASH_REQUIRED")
        if not self.equivalence_classes:
            e.append("EQUIVALENCE_CLASSES_REQUIRED")
        unsupported=sorted(set(self.equivalence_classes)-set(SUPPORTED_EQUIVALENCE_CLASSES))
        if unsupported:
            e.append("UNSUPPORTED_EQUIVALENCE_CLASS:"+",".join(unsupported))
        if self.normalizer_hash and self.normalizer_hash != self.computed_hash():
            e.append("NORMALIZER_HASH_MISMATCH")
        return tuple(e)

@dataclass(frozen=True)
class ClaimRecord:
    """A persisted, atomically reserved claim on a CONTENT_IDENTITY_KEY."""
    claim_id:str
    content_key_composite:str
    request_id:str
    issuer:str
    issued_ts:str
    expires_ts:str
    state:str="ACTIVE"
    release_reason:Optional[str]=None

    def is_active_at(self,now_iso:str)->bool:
        return self.state=="ACTIVE" and now_iso < self.expires_ts

@dataclass(frozen=True)
class AbsentClaimToken:
    claim_id:str
    owner:str
    bound_request_id:str
    mode:str="TYPE1_REFERENCE_ONLY"
    authorizes_construction:bool=False

@dataclass(frozen=True)
class IdentityLookupResult:
    lookup_result_id:str
    request_id:str
    lookup_subject_hash:str
    normalized_definition_graph_id_or_hash:str
    outcome:LookupOutcome
    lookup_complete:bool
    scopes_searched:Tuple[str,...]
    scope_exclusions:Tuple[Tuple[str,str],...]
    search_policy_id:str
    search_policy_version:str
    search_policy_hash:str
    normalizer_id:str
    normalizer_version:str
    normalizer_hash:str
    pending_collision_result:str
    exact_match:Optional[FeatureIdentity]
    near_match_candidates:Tuple[FeatureIdentity,...]
    absent_claim_token:Optional[AbsentClaimToken]
    lookup_evidence_hash:str
    verdict_ts:str
    lookup_era_scope:str="ALL_ERAS"
    active_era_id:Optional[str]=None
    issuer:str="TRACKER"
    subject_mode:str="CANONICAL_ID"
    content_key_composite:str=""
    content_key_algorithm_id:str=""
    semantic_uniqueness:str="UNRESOLVED_NOT_CERTIFIED"
    scope_status:Tuple[Tuple[str,str],...]=()
    errors:Tuple[str,...]=()
