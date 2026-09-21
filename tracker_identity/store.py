import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Iterable, Optional
from .models import ClaimProvenance, ClaimRecord, DEFAULT_CLAIM_TTL_SECONDS, FeatureIdentity
from .policy_registry import resolve_governed_search_policy_binding

@dataclass
class CanonicalIdentityStore:
    records:list[FeatureIdentity]=field(default_factory=list)
    registry_id:str="SALIX-ERA1-REGISTRY"
    active_era_id:str="ERA_1"
    creation_records:list[object]=field(default_factory=list)
    claims:list[ClaimRecord]=field(default_factory=list)
    declared_scope_status:dict=field(default_factory=dict)
    _claim_lock:RLock=field(default_factory=RLock,repr=False,compare=False)
    _clock:object=field(default=None,repr=False,compare=False)
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

    # ---- transaction time --------------------------------------------------
    def _now_iso(self)->str:
        """Store-owned transaction time.

        Production callers cannot supply it. Expiry, identity re-check and
        claim consumption all read the SAME internally obtained time, so a
        caller cannot widen an expiry window by passing a past timestamp.
        Deterministic tests inject a store-owned clock, never a per-call value.
        """
        if self._clock is not None:
            return self._clock().isoformat()
        return datetime.now(timezone.utc).isoformat()

    # ---- scope reachability -------------------------------------------------
    def scope_status(self,scope:str,era_id:str|None=None)->str:
        """LOADED | EMPTY_VERIFIED | UNREACHABLE | UNKNOWN.

        An empty store is NOT self-certifying: a scope with no rows is only
        EMPTY_VERIFIED when that has been explicitly declared. Otherwise it is
        UNKNOWN, because 'never loaded' and 'verified empty' are different facts.
        """
        declared=self.declared_scope_status.get(scope)
        if declared=="UNREACHABLE":
            return "UNREACHABLE"
        if self.list_scope(scope,era_id):
            return "LOADED"
        if declared=="EMPTY_VERIFIED":
            return "EMPTY_VERIFIED"
        return "UNKNOWN"

    def scope_status_report(self,scopes,era_id:str|None=None):
        return tuple((s,self.scope_status(s,era_id)) for s in scopes)

    def declare_scope(self,scope:str,status:str)->None:
        self.declared_scope_status[scope]=status

    # ---- atomic claim reservation ------------------------------------------
    def _expire_due(self,now_iso:str)->None:
        for i,c in enumerate(self.claims):
            if c.state=="ACTIVE" and now_iso >= c.expires_ts:
                self.claims[i]=ClaimRecord(c.claim_id,c.content_key_composite,
                    c.request_id,c.issuer,c.issued_ts,c.expires_ts,"EXPIRED","TTL_EXPIRED",
                    c.provenance)

    def _active_claim_at_locked(self,content_key_composite:str,now_iso:str)->Optional[ClaimRecord]:
        """Caller MUST already hold _claim_lock and MUST have obtained now_iso
        from _now_iso(). Private: the timestamp may only come from the
        store-owned clock, never from outside the store."""
        self._expire_due(now_iso)
        for c in self.claims:
            if c.content_key_composite==content_key_composite and c.is_active_at(now_iso):
                return c
        return None

    def active_claim(self,content_key_composite:str)->Optional[ClaimRecord]:
        """Public read. Time is store-owned.

        This method is mutation-capable: _expire_due() transitions due claims
        to EXPIRED. A caller-supplied timestamp could therefore prematurely
        kill a legitimately ACTIVE claim, so no such parameter exists.
        """
        with self._claim_lock:
            return self._active_claim_at_locked(content_key_composite,self._now_iso())

    def reserve_claim(self,*,content_key_composite:str,request_id:str,
                      provenance:Optional[ClaimProvenance]=None,issuer:str="TRACKER",
                      ttl_seconds:int=DEFAULT_CLAIM_TTL_SECONDS):
        """Atomically reserve. Returns (ClaimRecord|None, error|None).

        The reservation is PERSISTED inside the lock. A claim that is not
        persisted was never issued. A second active claim on the same content
        key is refused, never granted.

        GOVERNED PROVENANCE IS MANDATORY. This method stays public because
        privacy by naming convention is not a control, but it can no longer
        mint registration authority on demand: a caller must present a
        ClaimProvenance that is internally complete, bound to this exact
        request_id and content key, and carrying a search-policy binding that
        resolves against the governed registry. A caller who has not run a
        governed lookup cannot produce one.
        """
        if provenance is None:
            return None,"CLAIM_PROVENANCE_REQUIRED"
        provenance_errors=provenance.completeness_errors()
        if provenance_errors:
            return None,"CLAIM_PROVENANCE_INVALID:"+",".join(provenance_errors)
        if str(provenance.request_id)!=str(request_id):
            return None,"CLAIM_PROVENANCE_REQUEST_ID_MISMATCH"
        if str(provenance.content_key_composite)!=str(content_key_composite):
            return None,"CLAIM_PROVENANCE_CONTENT_KEY_MISMATCH"
        binding_errors=resolve_governed_search_policy_binding(
            provenance.search_policy_id,provenance.search_policy_version,
            provenance.search_policy_hash)
        if binding_errors:
            return None,"CLAIM_PROVENANCE_POLICY_NOT_GOVERNED:"+",".join(binding_errors)
        if provenance.authorizes_construction:
            # Construction authority may NOT be asserted by whoever is asking
            # for the claim. The governed lookup path issues authorizes_
            # construction=False, so any True arriving here was authored by the
            # caller — and a policy binding is public knowledge, so binding
            # alone proves nothing about authority. Without this fence a caller
            # could forge a construction-authorized provenance, self-bind
            # evidence and register. Refused at the door instead.
            #
            # When a governed construction ORDER exists, this is the single
            # place that check is replaced: authority must then be verified
            # against that order, never taken on the caller's word.
            return None,"CONSTRUCTION_AUTHORITY_NOT_SELF_ASSERTABLE"
        now_iso=self._now_iso()
        now=datetime.fromisoformat(now_iso)
        with self._claim_lock:
            # Private locked helper: lock ownership and time ownership are both
            # explicit, and no public method is re-entered while holding a lock.
            existing=self._active_claim_at_locked(content_key_composite,now_iso)
            if existing is not None:
                return None,"PENDING_CLAIM_EXISTS:"+existing.claim_id
            rec=ClaimRecord(
                claim_id=f"claim-{uuid.uuid4()}",
                content_key_composite=content_key_composite,
                request_id=request_id,issuer=issuer,
                issued_ts=now_iso,
                expires_ts=(now+timedelta(seconds=ttl_seconds)).isoformat(),
                state="ACTIVE",
                provenance=provenance,
            )
            self.claims.append(rec)
            return rec,None

    def bind_lookup_evidence(self,*,claim_id:str,lookup_result_id:str,
                             lookup_evidence_hash:str):
        """Write the issuing lookup RESULT back onto the claim's provenance.

        Called by identity_lookup once the result it is returning exists. Until
        this has happened the claim is not fully provenance-bound and
        registration refuses it, so a claim reserved but never tied to a real
        emitted lookup result cannot be redeemed.

        The binding is write-once: an already-bound claim is never re-pointed
        at a different lookup result.
        """
        with self._claim_lock:
            for i,c in enumerate(self.claims):
                if c.claim_id!=claim_id:
                    continue
                if c.provenance is None:
                    return False,"CLAIM_HAS_NO_PROVENANCE"
                if c.provenance.lookup_evidence_bound:
                    return False,"CLAIM_LOOKUP_EVIDENCE_ALREADY_BOUND"
                bound=replace(c.provenance,lookup_result_id=str(lookup_result_id),
                              lookup_evidence_hash=str(lookup_evidence_hash))
                self.claims[i]=replace(c,provenance=bound)
                return True,None
            return False,"CLAIM_NOT_FOUND"

    def validate_claim_for_registration(self,*,content_key_composite:str,
                                        request_id:str):
        """Re-check AT REGISTRATION, not only at issuance.

        Blocks the ABA duplicate: A claims -> A stalls -> claim expires ->
        B claims and registers -> A returns. A's expired claim must not
        authorize a late duplicate registration.
        """
        now_iso=self._now_iso()
        with self._claim_lock:
            self._expire_due(now_iso)
            for c in self.claims:
                if c.content_key_composite!=content_key_composite: continue
                if c.request_id!=request_id: continue
                if c.state=="ACTIVE" and c.is_active_at(now_iso):
                    return c,None
                return None,"CLAIM_NOT_ACTIVE:"+c.state
            return None,"CLAIM_NOT_FOUND"

    def release_claim(self,*,claim_id:str,reason:str)->bool:
        with self._claim_lock:
            for i,c in enumerate(self.claims):
                if c.claim_id==claim_id:
                    if c.state!="ACTIVE":
                        return False
                    self.claims[i]=ClaimRecord(c.claim_id,c.content_key_composite,
                        c.request_id,c.issuer,c.issued_ts,c.expires_ts,"RELEASED",reason,
                        c.provenance)
                    return True
            return False

    # ---- migration gate -----------------------------------------------------
    def rows_without_content_key(self,era_id:str|None=None,include_validation:bool=False):
        return tuple(
            r for r in self.records
            if (era_id is None or r.era_id==era_id)
            and (include_validation or r.scope!="validation")
            and not r.has_content_key
        )

    # ---- one atomic registration transaction --------------------------------
    def commit_registration(self,*,identity,creation,content_key_composite:str|None,
                            request_id:str|None):
        """Re-check, append and consume the claim as ONE atomic transition.

        Validation and registry mutation must not be separable. Splitting them
        permits the stale-worker duplicate: A validates, stalls, its claim
        expires, B claims and registers, A resumes and appends on a validation
        that is no longer true.

        A valid active claim is MANDATORY. It is enforced here, not only in
        safe_intake, because a direct caller must not be able to reach the
        registry by skipping the lookup/claim gate entirely. No claim means no
        registration, whatever route the caller took.

        Inside a single acquisition of _transition_lock this method:
          1. requires a non-blank request_id and content key — None, "" and
             whitespace are the absence of a claim, never a claim;
          2. re-checks that the presented claim is still ACTIVE and still bound
             to request_id, evaluated at the CURRENT time;
          3. re-checks that no canonical identity for this content key or
             canonical key appeared since the claim was issued;
          4. appends identity and creation provenance;
          5. terminally consumes the claim.

        LOCK ORDER is fixed and total: _transition_lock is ALWAYS acquired
        before _claim_lock, never the reverse. No public method acquires
        _claim_lock and then _transition_lock, so the two cannot deadlock.

        Returns (True, None) or (False, error).
        """
        now_iso=self._now_iso()   # NOT caller-controlled
        request_id=str(request_id or "").strip()
        content_key_composite=str(content_key_composite or "").strip() or None
        with self._transition_lock:
            with self._claim_lock:
                if not request_id:
                    return False,"CLAIM_REQUIRED_FOR_REGISTRATION"
                if content_key_composite is None:
                    return False,"CONTENT_KEY_REQUIRED_FOR_REGISTRATION"

                self._expire_due(now_iso)
                held=None
                for c in self.claims:
                    if (c.content_key_composite==content_key_composite
                            and c.request_id==request_id):
                        held=c
                        break
                if held is None:
                    return False,"CLAIM_NOT_FOUND"
                if not held.is_active_at(now_iso):
                    return False,"CLAIM_NOT_ACTIVE:"+held.state

                # A competing worker may have registered while this one paused.
                for r in self.records:
                    if r.content_key_composite==content_key_composite and r.is_current:
                        return False,"IDENTITY_APPEARED_SINCE_CLAIM:"+r.feature_id
                for r in self.records:
                    if r.canonical_key==identity.canonical_key:
                        return False,"CANONICAL_KEY_ALREADY_REGISTERED:"+r.feature_id

                # GOVERNED CONSTRUCTION AUTHORITY — the last gate before the
                # registry is written.
                #
                # Deliberately evaluated AFTER the claim, duplicate and
                # canonical-key checks, so each of those remains independently
                # observable and testable rather than being masked by a blanket
                # authority refusal. Nothing has been mutated at this point, so
                # ordering costs no safety.
                prov=held.provenance
                if prov is None:
                    return False,"CLAIM_PROVENANCE_MISSING"
                prov_errors=prov.completeness_errors()
                if prov_errors:
                    return False,"CLAIM_PROVENANCE_INVALID:"+",".join(prov_errors)
                if not prov.lookup_evidence_bound:
                    return False,"CLAIM_LOOKUP_EVIDENCE_NOT_BOUND"
                if str(prov.request_id)!=request_id:
                    return False,"CLAIM_PROVENANCE_REQUEST_ID_MISMATCH"
                if str(prov.content_key_composite)!=content_key_composite:
                    return False,"CLAIM_PROVENANCE_CONTENT_KEY_MISMATCH"
                binding_errors=resolve_governed_search_policy_binding(
                    prov.search_policy_id,prov.search_policy_version,
                    prov.search_policy_hash)
                if binding_errors:
                    return False,"CLAIM_PROVENANCE_POLICY_NOT_GOVERNED:"+",".join(binding_errors)
                if not prov.authorizes_construction:
                    # An ACTIVE, fully provenance-bound claim still does not
                    # authorize construction. ERA_1 structural absence is not
                    # global absence and semantic uniqueness is not certified,
                    # so the governed lookup path issues no construction
                    # authority and this fails closed.
                    return False,"CLAIM_NOT_CONSTRUCTION_AUTHORIZED"

                self.records.append(identity)
                self.creation_records.append(creation)

                for i,c in enumerate(self.claims):
                    if c.claim_id==held.claim_id:
                        self.claims[i]=ClaimRecord(
                            c.claim_id,c.content_key_composite,c.request_id,
                            c.issuer,c.issued_ts,c.expires_ts,
                            "RELEASED","REGISTRATION_COMPLETED",c.provenance)
                        break
                return True,None
