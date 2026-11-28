"""R7 PROPOSED SUCCESSOR lifecycle semantics on the ONE owning journal HEAD (CANDIDATE; Composer_Binding_V2_R7 Drive 17s4MY6_..., sha256 464724759119a752...ba282,
status in its own words: NOT ADOPTED / NOT CURRENT SOURCE / NO CODING OR RUN AUTHORITY). No principal, grant authority, clock, provider or deadline is appointed or proven here:
grant ids are OPAQUE strings and a revocation is a journal fact, not a security control. Implemented (R7 section -> method):
  s3 R5 terminal rule      revoke_grant + derived refusal in _verify_order (issuer/builder grant revocation REVOKES every nonterminal affected order, claim ABANDONED, no same-order revival;
                           accepted/consumed history immutable; verifier/intake/acceptance-origin grant revocation only refuses NEW dispositions, no order consequence).
  s3 creation lineage      replace_creation (terminal unsuccessful lineage never relabelled/reused; new creation id + explicit parent link; fresh lookup gate; consumed lineage => reuse, never recreate).
  s4 RD4a                  admit_attempt / reject_attempt (distinct BUILDER_BUILD_ID, bound to order/claim/creation/builder grant/reservation generation/correction parent).
  s5 RD4b                  record_review / dispose (REVIEW_REQUIRED nonterminal, immutable old report, one current disposition, final accept/reuse unique, no revival).
NOT implemented (named): s6 Branch A trusted-clock deadline predicate (no clock authority/domain/duration exists; Branch B is never a fallback); staged-report NON-ALLOCATION is by construction
(nothing here allocates FEATURE_ID/FEATURE_VERSION/REGISTRY_ENTRY_REF and a report has no visibility before its REPORT_DISPOSITION record); wiring to the real principals/grants.
This module changes no governance state; a merge or test pass clears no gate."""
from .claims import ClaimService, Refusal
from .order import (CLAIM_ABANDONED, GRANT_REVOKED, ATTEMPT_ADMITTED, ATTEMPT_REJECTED, LINEAGE_REPLACED, REVIEW_DECIDED, REPORT_DISPOSITION, ORDER_REVOKED)
from .lookup_adapter import construction_gate, INCOMPLETE_LOOKUP, DUPLICATE_OR_NEAR

ISSUER, BUILDER = "issuer", "builder"
NO_ORDER_CONSEQUENCE = frozenset({"verifier", "intake", "acceptance-origin"})
GRANT_ROLES = frozenset({ISSUER, BUILDER}) | NO_ORDER_CONSEQUENCE
FINAL = frozenset({"ACCEPT_FOR_REGISTRY", "REUSE_EXISTING"})
VERDICTS = FINAL | {"REVIEW_REQUIRED"}


class ReplicaLifecycle(ClaimService):
    def _need_grant(self, gid):
        if not isinstance(gid, str) or not gid:
            raise Refusal("GRANT_ID_REQUIRED")
        if gid in self._p.grants_revoked:
            raise Refusal("GRANT_REVOKED", gid)

    # -- s3 R5 -------------------------------------------------------------------------------------------------------
    def revoke_grant(self, grant_id: str, role: str):
        if role not in GRANT_ROLES:
            raise Refusal("GRANT_ROLE_UNKNOWN", role)
        def build(head):
            prior = self._p.grant_roles.get(grant_id)
            if prior is not None and prior != role:
                raise Refusal("GRANT_ROLE_CONFLICT", grant_id)
            if grant_id in self._p.grants_revoked:
                return None, None                               # exact replay
            return GRANT_REVOKED, {"grant_id": grant_id, "role": role}
        self._commit(build)
        return self.settle()

    def settle(self):
        """Reconcile OUTSTANDING consequences of issuer/builder grant revocation after any partial phase (idempotent, restart-safe): revoke a still-live affected order AND abandon every
        still-BOUND claim of every grant-affected order, including orders already revoked by an earlier partial run. Consumed (accepted) history is never touched. Authority never depends on
        this having run: ClaimService._verify_order derives the refusal from the same HEAD."""
        self._p.sync(self._j)
        done = []
        for oid, raw in list(self._p.orders.items()):
            if self._order_terminal(oid) or not self._order_grant_revoked(oid, raw["issued_by"]):
                continue
            acted = False
            if oid not in self._p.revoked:
                self.revoke_order(oid, "GRANT_REVOCATION"); acted = True
            for c in list(self._p.claims.values()):
                if c["order_id"] == oid and c["state"] == "BOUND":
                    self._commit(lambda head, cid=c["claim_id"]: (CLAIM_ABANDONED, {"claim_id": cid, "reason": "GRANT_REVOCATION"})); acted = True
            if acted: done.append(oid)
        return done

    def replace_creation(self, *, old_creation_id: str, new_creation_id: str, subject_key: str, order_id: str, lookup_outcome):
        gate = construction_gate(lookup_outcome)
        if gate == INCOMPLETE_LOOKUP:
            raise Refusal("INCOMPLETE_LOOKUP")
        if gate == DUPLICATE_OR_NEAR:
            raise Refusal("DUPLICATE_OR_NEAR_REUSE_CANONICAL_IDENTITY")
        self._p.sync(self._j)
        old = self._p.request_claim.get(old_creation_id)
        if old is None:
            raise Refusal("OLD_CREATION_UNKNOWN", old_creation_id)
        st = self._p.claims[old]["state"]
        old_order = self._p.claims[old]["order_id"]
        if st == "CONSUMED":
            raise Refusal("OLD_LINEAGE_SUCCEEDED_REUSE_NOT_RECREATE", old_creation_id)
        if st == "BOUND" and old_order not in self._p.revoked and not self._order_grant_revoked(old_order, self._p.orders[old_order]["issued_by"]):
            raise Refusal("OLD_LINEAGE_NOT_TERMINAL", old_creation_id)
        if new_creation_id in self._p.request_claim or new_creation_id in self._p.lineage_parent:
            raise Refusal("CREATION_ID_REUSED", new_creation_id)
        if order_id == old_order:
            raise Refusal("REPLACEMENT_NEEDS_NEW_ORDER", order_id)       # no same-order revalidation/resumption
        self._verify_order_now(order_id, subject_key)
        self._commit(lambda head: (LINEAGE_REPLACED, {"new_creation_id": new_creation_id, "parent_creation_id": old_creation_id}))
        return self.reserve(subject_key=subject_key, request_id=new_creation_id, order_id=order_id, lookup_outcome=lookup_outcome)

    def _verify_order_now(self, order_id, subject_key):
        self._p.sync(self._j)
        return self._verify_order(order_id, subject_key, self._j.head().seq)

    def parent_of(self, creation_id):
        self._p.sync(self._j)
        return self._p.lineage_parent.get(creation_id)

    # -- s4 RD4a -----------------------------------------------------------------------------------------------------
    def admit_attempt(self, *, build_id, order_id, claim_id, creation_request_id, builder_grant, correction_parent=None):
        binding = {"build_id": build_id, "order_id": order_id, "claim_id": claim_id, "creation_request_id": creation_request_id,
                   "builder_grant": builder_grant, "correction_parent": correction_parent}
        if not isinstance(build_id, str) or not build_id:
            raise Refusal("BUILD_ID_REQUIRED")
        def build(head):
            self._need_grant(builder_grant)
            self._verify_order(order_id, None, head.seq)
            c = self._p.claims.get(claim_id)
            if c is None or c["order_id"] != order_id or c["request_id"] != creation_request_id:
                raise Refusal("ATTEMPT_BINDING_MISMATCH")      # CREATION_REQUEST_ID == claim request id is a CANDIDATE reading
            if c["state"] != "BOUND":
                raise Refusal("CLAIM_NOT_BOUND", c["state"])
            prev = self._p.attempts.get(build_id)
            if prev is not None:
                if {k: prev[k] for k in binding if k != "correction_parent"} != {k: v for k, v in binding.items() if k != "correction_parent"} or prev["correction_parent"] != correction_parent:
                    raise Refusal("BUILD_ID_CONFLICT", build_id)
                return None, None                               # exact replay returns existing
            mine = sorted((a for a in self._p.attempts.values() if a["order_id"] == order_id), key=lambda a: a["seq"])
            if any(a["state"] == "ADMITTED" for a in mine):
                raise Refusal("ATTEMPT_ALREADY_LIVE")
            if mine and correction_parent != mine[-1]["build_id"]:
                raise Refusal("CORRECTION_PARENT_REQUIRED")
            if not mine and correction_parent is not None:
                raise Refusal("CORRECTION_PARENT_UNKNOWN")
            return ATTEMPT_ADMITTED, dict(binding, reservation_generation=len(mine) + 1)
        self._commit(build)
        return dict(self._p.attempts[build_id])

    def reject_attempt(self, build_id, reason):
        def build(head):
            a = self._p.attempts.get(build_id)
            if a is None or a["state"] != "ADMITTED":
                raise Refusal("ATTEMPT_NOT_ADMITTED", build_id)
            return ATTEMPT_REJECTED, {"build_id": build_id, "reason": reason}
        self._commit(build)
        return dict(self._p.attempts[build_id])

    def attempt(self, build_id):
        self._p.sync(self._j)
        a = self._p.attempts.get(build_id)
        return None if a is None else dict(a)

    # -- s5 RD4b -----------------------------------------------------------------------------------------------------
    def _final(self, package_id):
        return next((d for d in self._p.dispositions.get(package_id, []) if d["verdict"] in FINAL), None)

    def record_review(self, *, package_id, package_hash, prior_report_hash, build_id, expected_review_generation, decision, origin_grant, decision_evidence_hash):
        def build(head):
            self._need_grant(origin_grant)
            a = self._p.attempts.get(build_id)
            if a is None or a["state"] != "ADMITTED":
                raise Refusal("ATTEMPT_NOT_ADMITTED", build_id)
            self._verify_order(a["order_id"], None, head.seq)
            if self._final(package_id):
                raise Refusal("FINAL_DISPOSITION_EXISTS")
            ds = self._p.dispositions.get(package_id, [])
            if ds and ds[0]["build_id"] != build_id:
                raise Refusal("PACKAGE_OWNED_BY_ANOTHER_ATTEMPT", package_id)      # the review must come from the SAME owning order/claim/creation/attempt/reservation generation
            if not ds or ds[-1]["report_hash"] != prior_report_hash or ds[-1]["verdict"] != "REVIEW_REQUIRED" or ds[-1]["package_hash"] != package_hash:
                raise Refusal("REVIEW_NOT_AGAINST_CURRENT_REVIEW_REQUIRED_REPORT")
            have = sum(1 for k in self._p.reviews if k[0] == package_id)
            if expected_review_generation != have:
                raise Refusal("REVIEW_GENERATION_MISMATCH")
            if (package_id, prior_report_hash) in self._p.reviews:
                return None, None
            return REVIEW_DECIDED, {"package_id": package_id, "package_hash": package_hash, "prior_report_hash": prior_report_hash, "build_id": build_id,
                                    "decision": decision, "origin_grant": origin_grant, "decision_evidence_hash": decision_evidence_hash,
                                    "review_generation": have + 1}
        self._commit(build)
        return dict(self._p.reviews[(package_id, prior_report_hash)])

    def dispose(self, *, package_id, package_hash, report_id, report_hash, verdict, build_id, origin_grant, prior_report_hash=None):
        if verdict not in VERDICTS:
            raise Refusal("VERDICT_NOT_ADMITTED_HERE", str(verdict))     # REJECT is an attempt rejection (reject_attempt), not a package disposition
        def build(head):
            self._need_grant(origin_grant)
            a = self._p.attempts.get(build_id)
            if a is None or a["state"] != "ADMITTED":
                raise Refusal("ATTEMPT_NOT_ADMITTED", build_id)
            self._verify_order(a["order_id"], None, head.seq)
            c = self._p.claims.get(a["claim_id"])
            if c is None or c["state"] != "BOUND":
                raise Refusal("CLAIM_NOT_BOUND")
            ds = self._p.dispositions.get(package_id, [])
            if ds and ds[0]["build_id"] != build_id:
                raise Refusal("PACKAGE_OWNED_BY_ANOTHER_ATTEMPT", package_id)
            same = next((d for d in ds if d["report_id"] == report_id), None)
            if same is not None:
                if same["report_hash"] != report_hash or same["verdict"] != verdict or same["package_hash"] != package_hash:
                    raise Refusal("REPORT_ID_REBOUND_TO_DIFFERENT_BYTES")
                return None, None                                       # exact replay returns the recorded result
            if self._final(package_id):
                raise Refusal("FINAL_DISPOSITION_EXISTS")               # a new operation or report id cannot make a second effect
            if any(d["report_hash"] == report_hash for d in ds):
                raise Refusal("REPORT_HASH_REUSED")
            if verdict in FINAL and any(d["build_id"] == build_id and d["verdict"] in FINAL for dd in self._p.dispositions.values() for d in dd):
                raise Refusal("ATTEMPT_ALREADY_HAS_FINAL_EFFECT", build_id)      # one final effect per admitted attempt, not merely per package string
            if ds:
                if ds[0]["package_hash"] != package_hash:
                    raise Refusal("PACKAGE_HASH_CHANGED")
                if prior_report_hash != ds[-1]["report_hash"] or ds[-1]["verdict"] != "REVIEW_REQUIRED":
                    raise Refusal("SUCCESSOR_MUST_FOLLOW_CURRENT_REVIEW_REQUIRED")
                if (package_id, prior_report_hash) not in self._p.reviews:
                    raise Refusal("SUCCESSOR_NEEDS_REVIEW_DECISION")
            elif prior_report_hash is not None:
                raise Refusal("NO_PRIOR_REPORT")
            return REPORT_DISPOSITION, {"package_id": package_id, "package_hash": package_hash, "report_id": report_id, "report_hash": report_hash,
                                        "verdict": verdict, "build_id": build_id, "origin_grant": origin_grant, "prior_report_hash": prior_report_hash}
        self._commit(build)
        return self.current_disposition(package_id)

    def current_disposition(self, package_id):
        self._p.sync(self._j)
        ds = self._p.dispositions.get(package_id, [])
        return dict(ds[-1]) if ds else None

    def report_readback(self, package_id, report_hash):
        """Exact old-report readback returns the OLD record; the current disposition resolves through the chain (current_disposition)."""
        self._p.sync(self._j)
        r = next((d for d in self._p.dispositions.get(package_id, []) if d["report_hash"] == report_hash), None)
        return None if r is None else dict(r)
