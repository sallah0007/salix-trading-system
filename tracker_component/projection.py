from .journal_port import GENESIS_HASH, JournalIntegrityError, record_hash
from . import order as O

class ProjectionDrift(Exception):
    pass

class Projection:
    """Read model rebuilt from the journal. The journal is the only authority."""
    def __init__(self):
        self.seq = 0
        self.hash = GENESIS_HASH
        self.orders = {}
        self.revoked = {}
        self.claims = {}
        self.subject_claim = {}
        self.request_claim = {}

    def apply(self, rec):
        if rec.seq != self.seq + 1 or rec.prev_hash != self.hash:
            raise ProjectionDrift("sequence/hash discontinuity at %s" % rec.seq)
        if rec.record_hash != record_hash(rec.seq, rec.prev_hash, rec.kind, rec.body_json):
            raise ProjectionDrift("record hash mismatch at %s" % rec.seq)
        if rec.kind not in O.KINDS:
            raise ProjectionDrift("unknown record kind %r" % rec.kind)
        b = rec.body()
        if rec.kind == O.ORDER_ISSUED:
            if b["order_id"] in self.orders:
                raise ProjectionDrift("duplicate order id")
            self.orders[b["order_id"]] = dict(b, issued_seq=rec.seq)
        elif rec.kind == O.ORDER_REVOKED:
            if b["order_id"] not in self.orders:
                raise ProjectionDrift("revocation of unknown order")
            self.revoked.setdefault(b["order_id"], rec.seq)
        elif rec.kind == O.CLAIM_BOUND:
            cid = b["claim_id"]
            if cid in self.claims or b["subject_key"] in self.subject_claim:
                raise ProjectionDrift("claim/subject already bound")
            self.claims[cid] = dict(b, state="BOUND", bound_seq=rec.seq)
            self.subject_claim[b["subject_key"]] = cid
            self.request_claim[b["request_id"]] = cid
        elif rec.kind in (O.CLAIM_CONSUMED, O.CLAIM_RELEASED):
            c = self.claims.get(b["claim_id"])
            if c is None or c["state"] != "BOUND":
                raise ProjectionDrift("transition of non-bound claim")
            c["state"] = "CONSUMED" if rec.kind == O.CLAIM_CONSUMED else "RELEASED"
            if rec.kind == O.CLAIM_RELEASED:
                self.subject_claim.pop(c["subject_key"], None)
        self.seq, self.hash = rec.seq, rec.record_hash

    def sync(self, journal):
        for rec in journal.read_from(self.seq + 1):
            self.apply(rec)

    def state(self):
        return {"seq": self.seq, "hash": self.hash, "orders": self.orders, "revoked": self.revoked,
                "claims": self.claims, "subject_claim": self.subject_claim,
                "request_claim": self.request_claim}

    def verify_against(self, journal):
        fresh = Projection()
        fresh.sync(journal)
        if fresh.state() != self.state():
            raise ProjectionDrift("projection differs from journal replay")
