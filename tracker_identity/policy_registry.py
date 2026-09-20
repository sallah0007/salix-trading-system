from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping, Tuple

from .models import SearchPolicy

SEARCH_POLICY_ID = "tracker.identity.search"
SEARCH_POLICY_VERSION = "1"

# Duplicate control is only meaningful if it covers every lifecycle scope in
# which a governed duplicate can exist. These are NOT merely "the scopes V1
# happens to search": a policy version that fails to search any one of them
# cannot certify a structural absence at all, so the registry refuses to hold
# such an entry and the resolver refuses to accept one.
MANDATORY_DUPLICATE_CONTROL_SCOPES: Tuple[str, ...] = (
    "current_active","active_on_demand","validation","experimental_unclassified",
    "quarantined","dormant","suppressed","deprecated","retired","rejected_invalid",
    "historical_prior_version","canonical_survivor_discarded","pending_claimed_in_flight",
)

@dataclass(frozen=True)
class GovernedSearchPolicyEntry:
    """One governed, versioned duplicate-control policy owned by Tracker.

    The entry — not the caller — defines what a complete search is for this
    (SEARCH_POLICY_ID, SEARCH_POLICY_VERSION). SEARCH_POLICY_HASH is DERIVED
    from these governed semantics, never accepted from outside.
    """
    policy_id:str
    version:str
    required_scopes:Tuple[str,...]
    searched_scopes:Tuple[str,...]
    # scope -> the reason codes that MAY be used to exclude it. A scope absent
    # from this mapping may not be excluded at all, for any reason whatsoever.
    permitted_exclusions:Mapping[str,Tuple[str,...]]=field(default_factory=dict)

    def __post_init__(self):
        # Normalised and made read-only at construction. A governed entry whose
        # scope tuples or permitted exclusions could be edited in place after
        # import would be a live policy-authority mutation, so the mapping is
        # wrapped rather than stored as a caller-owned dict. This is a hardening
        # measure, not the primary control: the mandatory-scope checks in
        # resolve_governed_search_policy() are evaluated independently of any
        # entry and hold even if an entry is wrong.
        object.__setattr__(self,"required_scopes",tuple(self.required_scopes))
        object.__setattr__(self,"searched_scopes",tuple(self.searched_scopes))
        object.__setattr__(self,"permitted_exclusions",MappingProxyType(
            {str(k):tuple(v) for k,v in dict(self.permitted_exclusions).items()}))

    @property
    def key(self)->tuple:
        return (self.policy_id,self.version)

    def canonical_policy(self)->SearchPolicy:
        """The governed SearchPolicy object for this version, self-consistent."""
        provisional=SearchPolicy(
            policy_id=self.policy_id,version=self.version,policy_hash="",
            required_scopes=self.required_scopes,
            searched_scopes=self.searched_scopes,
            scope_exclusions={},
        )
        return SearchPolicy(
            policy_id=provisional.policy_id,version=provisional.version,
            policy_hash=provisional.computed_hash(),
            required_scopes=provisional.required_scopes,
            searched_scopes=provisional.searched_scopes,
            scope_exclusions=provisional.scope_exclusions,
        )

    @property
    def policy_hash(self)->str:
        return self.canonical_policy().policy_hash

    def registry_errors(self)->Tuple[str,...]:
        """Validate the governed ENTRY itself.

        A malformed governed entry is worse than a malformed caller policy: it
        would launder an incomplete search as authoritative. The registry is
        therefore validated at import time and refuses to load if defective.
        """
        e=[]
        if not self.policy_id or not self.version:
            e.append("GOVERNED_POLICY_ID_VERSION_REQUIRED")
        missing_required=[s for s in MANDATORY_DUPLICATE_CONTROL_SCOPES
                          if s not in self.required_scopes]
        if missing_required:
            e.append("GOVERNED_POLICY_MISSING_MANDATORY_REQUIRED_SCOPE:"
                     +",".join(sorted(missing_required)))
        missing_searched=[s for s in MANDATORY_DUPLICATE_CONTROL_SCOPES
                          if s not in self.searched_scopes]
        if missing_searched:
            e.append("GOVERNED_POLICY_MISSING_MANDATORY_SEARCHED_SCOPE:"
                     +",".join(sorted(missing_searched)))
        outside=sorted(set(self.permitted_exclusions)-set(self.required_scopes))
        if outside:
            e.append("GOVERNED_POLICY_EXCLUSION_OUTSIDE_REQUIRED:"+",".join(outside))
        excludable_mandatory=sorted(
            set(self.permitted_exclusions)&set(MANDATORY_DUPLICATE_CONTROL_SCOPES))
        if excludable_mandatory:
            e.append("GOVERNED_POLICY_MANDATORY_SCOPE_EXCLUDABLE:"
                     +",".join(excludable_mandatory))
        for scope,reasons in self.permitted_exclusions.items():
            if not reasons or any(not str(r).strip() for r in reasons):
                e.append("GOVERNED_POLICY_EXCLUSION_REASON_CODES_REQUIRED:"+str(scope))
        e.extend("GOVERNED_POLICY_"+x for x in self.canonical_policy().completeness_errors())
        return tuple(e)

# Future policy versions are added HERE as separate entries. An existing entry
# is never edited in place: changing the semantics of a published version would
# silently re-interpret every historical lookup evidence hash that cited it.
_ENTRIES:Tuple[GovernedSearchPolicyEntry,...]=(
    GovernedSearchPolicyEntry(
        policy_id=SEARCH_POLICY_ID,
        version=SEARCH_POLICY_VERSION,
        required_scopes=MANDATORY_DUPLICATE_CONTROL_SCOPES,
        searched_scopes=MANDATORY_DUPLICATE_CONTROL_SCOPES,
        permitted_exclusions={},
    ),
)

GOVERNED_SEARCH_POLICIES:Mapping[tuple,GovernedSearchPolicyEntry]={
    e.key:e for e in _ENTRIES
}

_registry_defects=tuple(
    f"{e.policy_id}@{e.version}:{x}" for e in _ENTRIES for x in e.registry_errors()
)
if len(GOVERNED_SEARCH_POLICIES)!=len(_ENTRIES):
    _registry_defects=_registry_defects+("DUPLICATE_GOVERNED_POLICY_KEY",)
if _registry_defects:
    raise RuntimeError("GOVERNED_SEARCH_POLICY_REGISTRY_INVALID:"
                       +";".join(_registry_defects))

def governed_search_policy(policy_id:str=SEARCH_POLICY_ID,
                           version:str=SEARCH_POLICY_VERSION)->SearchPolicy:
    """Return the Tracker-owned policy object for a registered version."""
    entry=GOVERNED_SEARCH_POLICIES.get((policy_id,version))
    if entry is None:
        raise KeyError("SEARCH_POLICY_NOT_GOVERNED:"+str(policy_id)+"@"+str(version))
    return entry.canonical_policy()

def resolve_governed_search_policy(search_policy)->Tuple[str,...]:
    """Bind a caller-presented SearchPolicy to governed authority.

    Returns () only when the presented policy matches a registered governed
    entry EXACTLY. Everything else fails closed.

    A caller policy is NOT authoritative merely because its own self-hash is
    internally consistent: SearchPolicy.computed_hash() is computed from the
    caller's own field values, so a caller can invent any scope set and produce
    a matching hash for it. The hash is therefore compared against the GOVERNED
    hash, which is derived from Tracker-owned scope semantics.
    """
    if search_policy is None:
        return ("SEARCH_POLICY_REQUIRED",)
    entry=GOVERNED_SEARCH_POLICIES.get(
        (getattr(search_policy,"policy_id",None),getattr(search_policy,"version",None)))
    if entry is None:
        return ("SEARCH_POLICY_NOT_GOVERNED:"
                +str(getattr(search_policy,"policy_id",""))+"@"
                +str(getattr(search_policy,"version","")),)
    e=[]
    if tuple(search_policy.required_scopes)!=tuple(entry.required_scopes):
        e.append("SEARCH_POLICY_REQUIRED_SCOPES_NOT_GOVERNED")
    if tuple(search_policy.searched_scopes)!=tuple(entry.searched_scopes):
        e.append("SEARCH_POLICY_SEARCHED_SCOPES_NOT_GOVERNED")
    for scope,reason in dict(search_policy.scope_exclusions).items():
        permitted=entry.permitted_exclusions.get(scope)
        if permitted is None:
            e.append("SEARCH_POLICY_EXCLUSION_NOT_PERMITTED:"+str(scope))
        elif str(reason) not in tuple(permitted):
            e.append("SEARCH_POLICY_EXCLUSION_REASON_NOT_PERMITTED:"
                     +str(scope)+"="+str(reason))
    # Evaluated independently of the comparisons above, so that a mandatory
    # scope cannot go unsearched even if a registry entry were ever wrong.
    missing=[s for s in MANDATORY_DUPLICATE_CONTROL_SCOPES
             if s not in tuple(search_policy.searched_scopes)]
    if missing:
        e.append("MANDATORY_SCOPE_NOT_SEARCHED:"+",".join(sorted(missing)))
    excluded=sorted(set(search_policy.scope_exclusions)
                    &set(MANDATORY_DUPLICATE_CONTROL_SCOPES))
    if excluded:
        e.append("MANDATORY_SCOPE_EXCLUDED:"+",".join(excluded))
    if str(search_policy.policy_hash)!=entry.policy_hash:
        e.append("SEARCH_POLICY_HASH_NOT_GOVERNED")
    return tuple(e)
