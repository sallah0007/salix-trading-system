from .journal_port import HeadMismatch
from .order import (ConstructionOrder, TrustAnchor, CLAIM_BOUND, CLAIM_CONSUMED,
                    CLAIM_RELEASED, ORDER_ISSUED, ORDER_REVOKED)
from .projection import Projection
from .lookup_adapter import construction_gate, PROCEED, INCOMPLETE_LOOKUP, DUPLICATE_OR_NEAR

class Refusal(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__("%s %s" % (code, detail))
        self.code = code

class ClaimService:
    """Authority = journal records verified immediately before each commit
    (compare-and-append on the journal head). No caller-supplied authority."""
    def __init__(self, journal, anchor: TrustAnchor, max_fence_retries: int = 3):
        self._j = journal
        self._anchor = anchor
        self._p = Projection()
        self._max = max_fence_retries

    # -- verification, always against the synced journal view ---------------
    def _verify_order(self, order_id: str, subject_key: str, head_seq: int) -> ConstructionOrder:
        raw = self._p.orders.get(order_id)
        if raw is None:
            raise Refusal("NO_ORDER", order_id)
        order = ConstructionOrder.from_body(raw)
        if order_id in self._p.revoked:
            raise Refusal("ORDER_REVOKED", order_id)
        if order.issued_by not in self._anchor.issuer_ids:
            raise Refusal("ISSUER_NOT_ANCHORED", order.issued_by)
        if order.source_binding_hash != self._anchor.source_binding_hash:
            raise Refusal("SOURCE_BINDING_MISMATCH")
        if order.subject_key != subject_key:
            raise Refusal("ORDER_SUBJECT_MISMATCH")
        if order.valid_until_seq is not None and head_seq > order.valid_until_seq:
            raise Refusal("ORDER_EXPIRED", order_id)
        return order

    def _commit(self, build):
        """build(head) verifies against self._p and returns (kind, body); retried on head race."""
        for _ in range(self._max):
            self._p.sync(self._j)
            head = self._j.head()
            kind, body = build(head)
            if kind is None:
                return None
            try:
                rec = self._j.append(head, kind, body)
            except HeadMismatch:
                continue
            self._p.apply(rec)
            return rec
        raise Refusal("FENCE_RACE_EXHAUSTED")

    # -- public operations ----------------------------------------------------
    def issue_order(self, order: ConstructionOrder):
        """Appends an ORDER_ISSUED record. Who may append is the journal backend's access
        control plus anchor verification at use; issuing is not itself authority."""
        def build(head):
            if order.order_id in self._p.orders:
                raise Refusal("ORDER_ID_EXISTS", order.order_id)
            return ORDER_ISSUED, order.to_body()
        return self._commit(build)

    def revoke_order(self, order_id: str, reason: str):
        def build(head):
            if order_id not in self._p.orders:
                raise Refusal("NO_ORDER", order_id)
            return ORDER_REVOKED, {"order_id": order_id, "reason": reason}
        return self._commit(build)

    def reserve(self, *, subject_key: str, request_id: str, order_id: str, lookup_outcome):
        gate = construction_gate(lookup_outcome)
        if gate == INCOMPLETE_LOOKUP:
            raise Refusal("INCOMPLETE_LOOKUP")
        if gate == DUPLICATE_OR_NEAR:
            raise Refusal("DUPLICATE_OR_NEAR")
        claim_id = "CLAIM:" + request_id
        existing = None

        def build(head):
            nonlocal existing
            existing = None
            self._verify_order(order_id, subject_key, head.seq)
            prior = self._p.request_claim.get(request_id)
            if prior is not None:
                c = self._p.claims[prior]
                if c["subject_key"] != subject_key or c["order_id"] != order_id:
                    raise Refusal("REQUEST_ID_CONFLICT", request_id)
                existing = c
                return None, None
            if subject_key in self._p.subject_claim:
                raise Refusal("SUBJECT_ALREADY_CLAIMED", subject_key)
            return CLAIM_BOUND, {"claim_id": claim_id, "subject_key": subject_key,
                                 "request_id": request_id, "order_id": order_id,
                                 "bound_at_head_seq": head.seq}
        # idempotent replay path: no append when an identical live claim exists
        self._p.sync(self._j)
        build(self._j.head())
        if existing is not None:
            return dict(existing)
        self._commit(build)
        if existing is not None:
            return dict(existing)
        return dict(self._p.claims[claim_id])

    def consume(self, claim_id: str, identity_ref: str):
        def build(head):
            c = self._p.claims.get(claim_id)
            if c is None:
                raise Refusal("CLAIM_NOT_FOUND", claim_id)
            if c["state"] != "BOUND":
                raise Refusal("CLAIM_NOT_BOUND", c["state"])
            self._verify_order(c["order_id"], c["subject_key"], head.seq)
            return CLAIM_CONSUMED, {"claim_id": claim_id, "identity_ref": identity_ref,
                                    "verified_at_head_seq": head.seq}
        self._commit(build)
        return dict(self._p.claims[claim_id])

    def release(self, claim_id: str, reason: str):
        def build(head):
            c = self._p.claims.get(claim_id)
            if c is None:
                raise Refusal("CLAIM_NOT_FOUND", claim_id)
            if c["state"] != "BOUND":
                raise Refusal("CLAIM_NOT_BOUND", c["state"])
            return CLAIM_RELEASED, {"claim_id": claim_id, "reason": reason}
        self._commit(build)
        return dict(self._p.claims[claim_id])

    def verify_projection(self):
        self._p.verify_against(self._j)

    def claim(self, claim_id: str):
        """Fresh-synced copy of a claim row, or None."""
        self._p.sync(self._j)
        c = self._p.claims.get(claim_id)
        return None if c is None else dict(c)

    def lineage(self, order_id: str, request_id: str = ""):
        """Read-only governed lineage for an order id / request id on the freshly synced journal: [] if none, else reasons (ORDER_ISSUED, ORDER_REVOKED, REQUEST_CLAIM_EXISTS).
        Used to refuse a caller-supplied 'no quant requested' flag that contradicts failed/revoked requested-build lineage (TR-06 / D8). Never authority."""
        self._p.sync(self._j)
        out = []
        if order_id in self._p.orders:
            out.append("ORDER_REVOKED" if order_id in self._p.revoked else "ORDER_ISSUED")
        if request_id and request_id in self._p.request_claim:
            out.append("REQUEST_CLAIM_EXISTS")
        return out

    def consumed_record(self, claim_id: str):
        """The journal record that consumed this claim (the exercised-authority witness), or None."""
        self._p.sync(self._j)
        for rec in self._j.read_from(1):
            if rec.kind == CLAIM_CONSUMED and rec.body().get("claim_id") == claim_id:
                return rec
        return None

    def authorizes(self, subject_key: str, request_id: str) -> bool:
        """True only if, on the freshly synced journal, a BOUND claim for exactly this subject and request
        exists under an order that still verifies. Never raises: any doubt is False (fail-closed)."""
        try:
            self._p.sync(self._j)
            cid = self._p.subject_claim.get(subject_key)
            if cid is None:
                return False
            c = self._p.claims[cid]
            if c["state"] != "BOUND" or c["request_id"] != request_id:
                return False
            self._verify_order(c["order_id"], subject_key, self._j.head().seq)
            return True
        except Exception:
            return False
