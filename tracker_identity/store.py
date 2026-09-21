import hashlib
import json
import uuid
import weakref
from dataclasses import dataclass, field, fields, replace
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Iterable, Optional
from .models import (
    CLAIMABLE_LOOKUP_OUTCOMES, ClaimProvenance, ClaimRecord,
    DEFAULT_CLAIM_TTL_SECONDS, FeatureIdentity,
)
from .normalizer_registry import (
    resolve_governed_normalizer, resolve_governed_normalizer_binding,
)
from .policy_registry import (
    resolve_governed_search_policy, resolve_governed_search_policy_binding,
)

def _hash_facts(payload)->str:
    """Hash over exactly the facts the STORE verified at issuance."""
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def _provenance_facts(prov):
    if prov is None:
        return None
    if type(prov) is not ClaimProvenance:
        return {"__untrusted_type__":repr(type(prov))}
    return {f.name:getattr(prov,f.name) for f in fields(prov)}

def _claim_snapshot(rec)->str:
    """Canonical serialization of EVERY bound issuance fact of a claim.

    Covers claim id, content key, request id, issuer, both timestamps and the
    full provenance — including the authority bit, the policy and normalizer
    bindings, the lookup result id and the issuance evidence hash. Changing any
    one of them after issuance changes this string.

    Lifecycle (state, release_reason) is deliberately excluded: it changes
    legitimately after issuance, so it is held authoritatively in the ledger
    and the record's copy is compared against that separately.
    """
    return json.dumps({
        "claim_id":rec.claim_id,
        "content_key_composite":rec.content_key_composite,
        "request_id":rec.request_id,
        "issuer":rec.issuer,
        "issued_ts":rec.issued_ts,
        "expires_ts":rec.expires_ts,
        "provenance":_provenance_facts(rec.provenance),
    },sort_keys=True,separators=(",",":"),default=repr)

def _make_issuance_authority():
    """Build the store-owned issuance authority from FUNCTION-LOCAL state.

    WHY THIS EXISTS (CR-1 / CR-2). The previous revision proved issuance with
    `store._issued_claim_ids`, an ordinary set: a caller could add any claim id
    to it (CR-1), or replace the provenance of a genuinely issued claim in the
    public `claims` list while its id stayed "issued" (CR-2). Both reached a
    canonical row write. Membership in a mutable container is not proof, and
    an underscore is not access control.

    DESIGN. The ledger below is a dict that lives only in this closure — it is
    never a store attribute and never a module attribute, so no ordinary
    container mutation can reach it. For every claim it records an exact
    canonical snapshot of the issued facts plus the authoritative lifecycle.
    A claim is authentic only if its current contents reproduce that snapshot
    EXACTLY and its lifecycle matches the ledger's. No key, no MAC, no secret:
    authenticity is equality with a record only the issuer can write.

    There is exactly ONE writer, `issue`, and it accepts only the raw inputs a
    lookup is entitled to supply. It re-derives every authority-bearing fact
    from the store's own records and generates the claim id, the lookup result
    id, both timestamps and the evidence hash itself. There is deliberately NO
    function that accepts a caller-built record or provenance to "seal": such a
    function would be a signer, and any in-process signer is callable by the
    caller too. Invoking `issue` directly is therefore indistinguishable from
    a legitimate issuance — it cannot mint construction authority.

    Ledgers are per store, keyed by object identity and dropped when the store
    is collected, so a claim issued by one store is unknown to every other.

    STATED BOUNDARY. This defends against mutation of any ordinary
    caller-reachable DATA: lists, sets, dicts, record fields, provenance
    fields, frozen-record reconstruction, copying, cross-store replay. It does
    NOT defend against replacing CODE — rebinding store methods or module
    functions — nor against reflection on closure cells (fn.__closure__), gc,
    or ctypes. No pure in-process Python design can; none is claimed.
    """
    ledgers={}

    def _entries(store,create=False):
        key=id(store)
        led=ledgers.get(key)
        if led is None and create:
            led={}
            ledgers[key]=led
            weakref.finalize(store,ledgers.pop,key,None)
        return led

    def _mirror(store,claim_id,entry):
        # Keep the public, display-only lifecycle copy in step with the ledger.
        for i,c in enumerate(store.claims):
            if isinstance(c,ClaimRecord) and c.claim_id==claim_id:
                store.claims[i]=replace(c,state=entry["state"],release_reason=entry["reason"])

    def expire_due(store,now_iso):
        for claim_id,entry in (_entries(store) or {}).items():
            if entry["state"]=="ACTIVE" and now_iso>=entry["expires_ts"]:
                entry["state"]="EXPIRED"
                entry["reason"]="TTL_EXPIRED"
                _mirror(store,claim_id,entry)

    def active_claim_id(store,content_key_composite):
        for claim_id,entry in (_entries(store) or {}).items():
            if entry["content_key"]==content_key_composite and entry["state"]=="ACTIVE":
                return claim_id
        return None

    def authenticate(store,rec):
        """(True, None) only for an unaltered claim THIS store issued."""
        if type(rec) is not ClaimRecord:
            return False,"CLAIM_RECORD_TYPE_NOT_AUTHENTIC"
        entry=(_entries(store) or {}).get(rec.claim_id)
        if entry is None:
            return False,"CLAIM_NOT_ISSUED_BY_THIS_STORE"
        if rec.provenance is not None and type(rec.provenance) is not ClaimProvenance:
            return False,"CLAIM_PROVENANCE_TYPE_NOT_AUTHENTIC"
        if _claim_snapshot(rec)!=entry["snapshot"]:
            return False,"CLAIM_CONTENT_ALTERED_SINCE_ISSUANCE"
        if rec.state!=entry["state"] or rec.release_reason!=entry["reason"]:
            return False,"CLAIM_LIFECYCLE_ALTERED_SINCE_ISSUANCE"
        return True,None

    def terminate(store,claim_id,to_state,reason):
        """Monotonic: ACTIVE -> terminal only. Nothing is ever revived, so this
        grants no power beyond the public release_claim()."""
        if to_state not in ("EXPIRED","RELEASED"):
            return False
        entry=(_entries(store) or {}).get(claim_id)
        if entry is None or entry["state"]!="ACTIVE":
            return False
        entry["state"]=to_state
        entry["reason"]=reason
        _mirror(store,claim_id,entry)
        return True

    def issue(store,*,content_key_composite,request_id,search_policy,normalizer,
              include_validation_scope,issuer,ttl_seconds):
        content_key_composite=str(content_key_composite or "").strip()
        request_id=str(request_id or "").strip()
        if not content_key_composite:
            return None,"CLAIM_CONTENT_KEY_REQUIRED"
        if not request_id:
            return None,"CLAIM_REQUEST_ID_REQUIRED"
        policy_errors=resolve_governed_search_policy(search_policy)
        if policy_errors:
            return None,"CLAIM_SEARCH_POLICY_NOT_GOVERNED:"+",".join(policy_errors)
        normalizer_errors=resolve_governed_normalizer(normalizer)
        if normalizer_errors:
            return None,"CLAIM_NORMALIZER_NOT_GOVERNED:"+",".join(normalizer_errors)

        # Scope reachability and absence are RE-DERIVED from this store.
        active_era_id=store.active_era_id
        unproven=sorted(sc for sc,st in store.scope_status_report(
            search_policy.searched_scopes,active_era_id)
            if st in ("UNREACHABLE","UNKNOWN"))
        if unproven:
            return None,"CLAIM_SCOPE_NOT_PROVEN_REACHABLE:"+",".join(unproven)
        for scope in search_policy.searched_scopes:
            for r in store.list_scope(scope,active_era_id):
                if not include_validation_scope and r.scope=="validation":
                    continue
                if not r.has_content_key:
                    return None,"CLAIM_CONTENT_KEY_UNRESOLVED_ROWS:"+r.feature_id
                if r.content_key_composite==content_key_composite:
                    return None,"CLAIM_CONTENT_IDENTITY_ALREADY_PRESENT:"+r.feature_id

        verified={
            "request_id":request_id,
            "content_key_composite":content_key_composite,
            "registry_id":store.registry_id,
            "active_era_id":active_era_id,
            "search_policy":[search_policy.policy_id,search_policy.version,
                             search_policy.policy_hash],
            "normalizer":[normalizer.normalizer_id,normalizer.version,
                          normalizer.normalizer_hash],
            "searched_scopes":list(search_policy.searched_scopes),
            "include_validation_scope":bool(include_validation_scope),
            "outcome":CLAIMABLE_LOOKUP_OUTCOMES[0],
        }
        provenance=ClaimProvenance(
            request_id=request_id,
            content_key_composite=content_key_composite,
            lookup_outcome=CLAIMABLE_LOOKUP_OUTCOMES[0],
            lookup_complete=True,
            search_policy_id=search_policy.policy_id,
            search_policy_version=search_policy.version,
            search_policy_hash=search_policy.policy_hash,
            normalizer_id=normalizer.normalizer_id,
            normalizer_version=normalizer.version,
            normalizer_hash=normalizer.normalizer_hash,
            semantic_uniqueness="UNRESOLVED_NOT_CERTIFIED",
            # Construction authority is never granted here. ERA_1 structural
            # absence is not global absence and semantic uniqueness is not
            # certified. When a governed construction ORDER exists, THIS is the
            # single place it is resolved — from the order, never from a
            # caller-supplied flag, which is why no such parameter exists.
            authorizes_construction=False,
            lookup_result_id=str(uuid.uuid4()),
            issuance_evidence_hash=_hash_facts(verified),
        )
        now_iso=store._now_iso()
        now=datetime.fromisoformat(now_iso)
        with store._claim_lock:
            expire_due(store,now_iso)
            existing=active_claim_id(store,content_key_composite)
            if existing is not None:
                return None,"PENDING_CLAIM_EXISTS:"+existing
            rec=ClaimRecord(
                claim_id=f"claim-{uuid.uuid4()}",
                content_key_composite=content_key_composite,
                request_id=request_id,issuer=str(issuer),
                issued_ts=now_iso,
                expires_ts=(now+timedelta(seconds=ttl_seconds)).isoformat(),
                state="ACTIVE",
                provenance=provenance,
            )
            _entries(store,create=True)[rec.claim_id]={
                "snapshot":_claim_snapshot(rec),
                "state":"ACTIVE","reason":None,
                "expires_ts":rec.expires_ts,
                "content_key":content_key_composite,
            }
            store.claims.append(rec)
            return rec,None

    return issue,authenticate,terminate,expire_due,active_claim_id

(_issue_claim,_authenticate_claim,_terminate_claim,
 _expire_due_claims,_active_claim_id)=_make_issuance_authority()

@dataclass
class CanonicalIdentityStore:
    records:list[FeatureIdentity]=field(default_factory=list)
    registry_id:str="SALIX-ERA1-REGISTRY"
    active_era_id:str="ERA_1"
    creation_records:list[object]=field(default_factory=list)
    # Display-only lifecycle mirror. NOT authority: every decision is taken
    # against the closure-held issuance ledger, and this list is checked
    # against it. Anything a caller appends or replaces here is inert.
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
        # Expiry is decided from the LEDGER's issued expires_ts, never from the
        # mirror record, so editing a record's timestamp cannot extend a claim.
        _expire_due_claims(self,now_iso)

    def _active_claim_at_locked(self,content_key_composite:str,now_iso:str)->Optional[ClaimRecord]:
        """Caller MUST already hold _claim_lock and MUST have obtained now_iso
        from _now_iso(). Private: the timestamp may only come from the
        store-owned clock, never from outside the store.

        'Active' is the LEDGER's verdict, not the mirror's. Flipping a mirror
        record's state cannot hide a pending claim or fake one.
        """
        self._expire_due(now_iso)
        claim_id=_active_claim_id(self,content_key_composite)
        if claim_id is None:
            return None
        for c in self.claims:
            if isinstance(c,ClaimRecord) and c.claim_id==claim_id:
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
                      search_policy=None,normalizer=None,
                      include_validation_scope:bool=False,
                      issuer:str="TRACKER",
                      ttl_seconds:int=DEFAULT_CLAIM_TTL_SECONDS):
        """Store-owned claim ISSUANCE. Returns (ClaimRecord|None, error|None).

        The caller supplies only what it wants looked up. Every fact that could
        confer authority — governed bindings, scope reachability, the absence
        itself, the claim id, the lookup result id, both timestamps and the
        evidence hash — is established by the issuance authority from this
        store's own records. The issued claim's exact contents are recorded in
        a closure-held ledger that no caller-reachable container can alter, and
        registration later requires the presented claim to reproduce them.

        The reservation is PERSISTED inside the lock. A claim that is not
        persisted was never issued. A second active claim on the same content
        key is refused, never granted.
        """
        now_iso=self._now_iso()
        with self._claim_lock:
            # Private locked helper: lock ownership and time ownership are both
            # explicit, and no public method is re-entered while holding a lock.
            existing=self._active_claim_at_locked(
                str(content_key_composite or "").strip(),now_iso)
            if existing is not None:
                return None,"PENDING_CLAIM_EXISTS:"+existing.claim_id
            return _issue_claim(
                self,content_key_composite=content_key_composite,
                request_id=request_id,search_policy=search_policy,
                normalizer=normalizer,
                include_validation_scope=include_validation_scope,
                issuer=issuer,ttl_seconds=ttl_seconds)

    def claim_authenticity(self,rec):
        """Read-only. (True, None) only for an unaltered claim THIS store issued."""
        with self._claim_lock:
            return _authenticate_claim(self,rec)

    def _authentic_match_locked(self,content_key_composite,request_id):
        """First AUTHENTIC claim for (key, request). Caller holds _claim_lock.

        Scans past lookalikes rather than stopping at the first textual match,
        so a planted record cannot shadow a genuine claim. Returns
        (claim|None, error|None); when only inauthentic matches exist, the
        first authentication failure is reported.
        """
        first_error=None
        for c in self.claims:
            if not isinstance(c,ClaimRecord):
                continue
            if c.content_key_composite!=content_key_composite or c.request_id!=request_id:
                continue
            ok,error=_authenticate_claim(self,c)
            if ok:
                return c,None
            if first_error is None:
                first_error=error
        return None,(first_error or "CLAIM_NOT_FOUND")

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
            c,error=self._authentic_match_locked(content_key_composite,request_id)
            if c is None:
                return None,error
            if c.state=="ACTIVE" and c.is_active_at(now_iso):
                return c,None
            return None,"CLAIM_NOT_ACTIVE:"+c.state

    def release_claim(self,*,claim_id:str,reason:str)->bool:
        # Only a claim this store issued can be released, and only once.
        with self._claim_lock:
            return _terminate_claim(self,claim_id,"RELEASED",reason)

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
                # AUTHENTICITY FIRST (CR-1 / CR-2). The claim must reproduce,
                # exactly, the contents this store recorded when it issued it,
                # and its lifecycle must match the ledger. Membership of an id
                # in any caller-reachable container proves nothing; a record
                # whose provenance was replaced after issuance fails here.
                held,auth_error=self._authentic_match_locked(
                    content_key_composite,request_id)
                if held is None:
                    return False,auth_error
                # Safe to read from `held` now: its timestamps and state have
                # just been proven equal to the ledger's.
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
                # Everything below re-checks facts the authenticity check has
                # already bound to the issuance record. It is retained as
                # defence in depth, not relied upon as the proof.
                prov=held.provenance
                if prov is None:
                    return False,"CLAIM_PROVENANCE_MISSING"
                if not prov.store_issued:
                    return False,"CLAIM_PROVENANCE_NOT_STORE_ISSUED"
                prov_errors=prov.completeness_errors()
                if prov_errors:
                    return False,"CLAIM_PROVENANCE_INVALID:"+",".join(prov_errors)
                if str(prov.request_id)!=request_id:
                    return False,"CLAIM_PROVENANCE_REQUEST_ID_MISMATCH"
                if str(prov.content_key_composite)!=content_key_composite:
                    return False,"CLAIM_PROVENANCE_CONTENT_KEY_MISMATCH"
                binding_errors=resolve_governed_search_policy_binding(
                    prov.search_policy_id,prov.search_policy_version,
                    prov.search_policy_hash)
                if binding_errors:
                    return False,"CLAIM_PROVENANCE_POLICY_NOT_GOVERNED:"+",".join(binding_errors)
                normalizer_errors=resolve_governed_normalizer_binding(
                    prov.normalizer_id,prov.normalizer_version,prov.normalizer_hash)
                if normalizer_errors:
                    return False,"CLAIM_PROVENANCE_NORMALIZER_NOT_GOVERNED:"+",".join(normalizer_errors)
                if not prov.authorizes_construction:
                    # An ACTIVE, fully provenance-bound claim still does not
                    # authorize construction. ERA_1 structural absence is not
                    # global absence and semantic uniqueness is not certified,
                    # so the governed lookup path issues no construction
                    # authority and this fails closed.
                    return False,"CLAIM_NOT_CONSTRUCTION_AUTHORIZED"

                self.records.append(identity)
                self.creation_records.append(creation)

                # Consumption goes through the ledger, so a consumed claim is
                # terminal there and cannot be presented again by any copy.
                _terminate_claim(self,held.claim_id,"RELEASED","REGISTRATION_COMPLETED")
                return True,None
