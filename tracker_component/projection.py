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
        self.order_prov = {}
        self.grants_revoked = {}      # grant_id -> seq
        self.grant_roles = {}         # grant_id -> role (first revocation fixes the role)
        self.attempts = {}            # build_id -> row
        self.lineage_parent = {}      # new creation id -> parent creation id
        self.reviews = {}             # (package_id, prior_report_hash) -> decision row
        self.dispositions = {}        # package_id -> list of rows (append-only, last = current)

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
        elif rec.kind == O.ORDER_PROVENANCE:
            if b["order_id"] not in self.orders:
                raise ProjectionDrift("provenance for unknown order")
            self.order_prov.setdefault(b["order_id"], []).append(dict(b, seq=rec.seq))
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
        elif rec.kind == O.CLAIM_ABANDONED:
            c = self.claims.get(b["claim_id"])
            if c is None or c["state"] != "BOUND":
                raise ProjectionDrift("abandon of non-bound claim")
            c["state"] = "ABANDONED"
            self.subject_claim.pop(c["subject_key"], None)
        elif rec.kind == O.GRANT_REVOKED:
            if self.grant_roles.setdefault(b["grant_id"], b["role"]) != b["role"]:
                raise ProjectionDrift("grant role conflict")
            self.grants_revoked.setdefault(b["grant_id"], rec.seq)
        elif rec.kind == O.ATTEMPT_ADMITTED:
            if b["build_id"] in self.attempts:
                raise ProjectionDrift("duplicate build id")
            self.attempts[b["build_id"]] = dict(b, state="ADMITTED", seq=rec.seq)
        elif rec.kind == O.ATTEMPT_REJECTED:
            a = self.attempts.get(b["build_id"])
            if a is None or a["state"] != "ADMITTED":
                raise ProjectionDrift("reject of non-admitted attempt")
            a["state"] = "REJECTED"
        elif rec.kind == O.LINEAGE_REPLACED:
            if b["new_creation_id"] in self.lineage_parent:
                raise ProjectionDrift("creation id already linked")
            self.lineage_parent[b["new_creation_id"]] = b["parent_creation_id"]
        elif rec.kind == O.REVIEW_DECIDED:
            self.reviews[(b["package_id"], b["prior_report_hash"])] = dict(b, seq=rec.seq)
        elif rec.kind == O.REPORT_DISPOSITION:
            self.dispositions.setdefault(b["package_id"], []).append(dict(b, seq=rec.seq))
        self.seq, self.hash = rec.seq, rec.record_hash

    def sync(self, journal):
        for rec in journal.read_from(self.seq + 1):
            self.apply(rec)

    def state(self):
        return {"seq": self.seq, "hash": self.hash, "orders": self.orders, "revoked": self.revoked,
                "claims": self.claims, "subject_claim": self.subject_claim,
                "request_claim": self.request_claim, "order_prov": self.order_prov,
                "grants_revoked": self.grants_revoked, "grant_roles": self.grant_roles, "attempts": self.attempts, "lineage_parent": self.lineage_parent,
                "reviews": self.reviews, "dispositions": self.dispositions}

    def verify_against(self, journal):
        fresh = Projection()
        fresh.sync(journal)
        if fresh.state() != self.state():
            raise ProjectionDrift("projection differs from journal replay")
