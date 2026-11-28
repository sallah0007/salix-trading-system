"""R38 B19 (Registry p185-188 evidence-resolution interface; cited by range, no source text copied): resolver / receipt / evidence-store interface for AUTHORITATIVE-CURRENT evidence behind an authority transition. It sits ON TOP of `evidence_truth.judge_transition_evidence` (the exact per-dimension predicate) and adds what that predicate lacks:
  * an evidence STORE interface whose records are re-derived (content hash recomputed from the stored body; chain-verified journal read), never trusted fields;
  * every referenced evidence ref is PINNED to an expected content hash by the caller's claim record (`pins`), so a swapped/altered record is detected;
  * a WATERMARK bound (evidence must have been available at or before the supplied watermark), freshness at `now`, revocation records, duplicate/ambiguous refs;
  * a typed RECEIPT (claim hash, store id + exact store head, per-ref content hashes, verdict, watermark, valid-until). A signer, `signed_by` field or authorized actor alone is never evidence: a claim with no resolving refs is INVALID.
HELD (source-owned, NOT invented): which store is AUTHORITATIVE (an admission), the real admitted evidence schemas, the freshness/watermark VALUES, appointments and principals. `JournalEvidenceStore` uses a CANDIDATE record encoding (own kinds `EVIDENCE_RECORD`/`EVIDENCE_REVOCATION`; no normative bytes). Because no admission exists, every receipt is `authoritative=False` and `require_authoritative_current()` refuses: a VALID verdict here is a candidate, simulation-class result and clears nothing.
A receipt is a snapshot: the consumer must call `use(...)` which re-resolves at use time against the then-current store head."""
import json
from dataclasses import dataclass
from typing import Optional, Tuple
from ..errors import Refusal
from ..storage.byte_primitives import canonical_bytes, domain_hash
from tracker_component.journal_port import GENESIS_HEAD
from .evidence_truth import EvidenceRecord, TransitionClaim, judge_transition_evidence, VALID, INVALID, UNPROVABLE
REC_KIND, REV_KIND = "EVIDENCE_RECORD", "EVIDENCE_REVOCATION"
_FIELDS = ("ref", "subject", "version_or_hash", "instrument", "timeframe", "battery", "vintage", "dependencies", "result", "available_at", "max_age", "current", "approval_state")
def content_hash(body: dict) -> str: return domain_hash("SALIX_EVIDENCE_RECORD_CANDIDATE_V1", canonical_bytes({k: body[k] for k in _FIELDS}))
class JournalEvidenceStore:
    """Append-only evidence store over a journal (chain verified on every read). `store_id` names it; admission as AUTHORITATIVE is a held slot (None here)."""
    admission = None
    def __init__(self, journal, store_id: str):
        if not (isinstance(store_id, str) and store_id): raise Refusal("store_id", code="EVIDENCE_STORE_ID_INVALID")
        self._j, self.store_id = journal, store_id
    def head(self): return self._j.head()
    def put(self, rec: EvidenceRecord):
        if not isinstance(rec, EvidenceRecord) or rec.revoked is not False: raise Refusal("record", code="EVIDENCE_RECORD_INVALID")
        body = {k: (list(getattr(rec, k)) if k == "dependencies" else getattr(rec, k)) for k in _FIELDS}; body["content_hash"] = content_hash(body)
        return self._j.append(self._j.head(), REC_KIND, body)
    def revoke(self, ref: str, reason: str): return self._j.append(self._j.head(), REV_KIND, {"ref": ref, "reason": reason})
    def snapshot(self):
        """(head, {ref: (EvidenceRecord, content_hash) | AMBIGUOUS | ALTERED}, revoked refs) read at ONE head."""
        head = self._j.head(); recs = {}; revoked = set()
        for r in (self._j.read_from(1) if head != GENESIS_HEAD else []):
            b = json.loads(r.body_json)
            if r.kind == REV_KIND: revoked.add(b["ref"]); continue
            if r.kind != REC_KIND: continue
            ref = b.get("ref")
            try: ok = b["content_hash"] == content_hash(b)
            except (KeyError, TypeError): ok = False
            if not ok: recs[ref] = "ALTERED"; continue
            if ref in recs and (recs[ref] == "ALTERED" or recs[ref][1] != b["content_hash"]): recs[ref] = "AMBIGUOUS"; continue
            recs[ref] = (EvidenceRecord(**{k: (tuple(b[k]) if k == "dependencies" else b[k]) for k in _FIELDS}, revoked=False), b["content_hash"])
        return head, recs, revoked
@dataclass(frozen=True)
class ResolutionReceipt:
    claim_hash: str; store_id: str; store_head_seq: int; store_head_hash: str; refs: Tuple[Tuple[str, str], ...]; status: str; reasons: Tuple[str, ...]; now: int; watermark: int; valid_until: Optional[int]
    authoritative: bool = False                        # no admitted authoritative store exists: ALWAYS False here
    def require_authoritative_current(self): raise Refusal("no admitted authoritative evidence store", code="EVIDENCE_STORE_NOT_ADMITTED_HELD")
def claim_hash(claim: TransitionClaim) -> str:
    return domain_hash("SALIX_TRANSITION_CLAIM_CANDIDATE_V1", canonical_bytes({"s": claim.subject, "v": claim.version_or_hash, "i": claim.instrument, "t": claim.timeframe, "b": claim.battery, "vin": claim.vintage, "d": list(claim.dependencies), "r": claim.expected_result, "a": claim.required_approval, "e": list(claim.evidence_refs)}))
class EvidenceResolver:
    def __init__(self, store): 
        if not (hasattr(store, "snapshot") and hasattr(store, "store_id")): raise Refusal("store", code="EVIDENCE_STORE_INTERFACE_INVALID")
        self._s = store
    def resolve(self, claim: TransitionClaim, pins: dict, now: int, watermark: int) -> ResolutionReceipt:
        """pins: {evidence ref: expected content hash} from the claim's own record. Fail closed on anything unpinned, unresolved, altered, ambiguous, revoked, beyond the watermark, stale or mismatched."""
        head, recs, revoked = self._s.snapshot(); ch = claim_hash(claim) if isinstance(claim, TransitionClaim) else ""
        def out(status, reasons, refs=(), vu=None): return ResolutionReceipt(ch, self._s.store_id, head.seq, head.hash, tuple(refs), status, tuple(reasons), now, watermark, vu)
        if not isinstance(claim, TransitionClaim) or not isinstance(pins, dict) or any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in (now, watermark)): return out(UNPROVABLE, ("INPUT_INVALID",))
        if not claim.evidence_refs: return out(INVALID, ("NO_EVIDENCE_REFERENCED",))                 # signer / authorized actor alone is never evidence
        bad, index, refs = [], {}, []
        for ref in claim.evidence_refs:
            g = recs.get(ref)
            if g is None: bad.append("EVIDENCE_MISSING:" + str(ref)); continue
            if g in ("ALTERED", "AMBIGUOUS"): bad.append("EVIDENCE_%s:%s" % (g, ref)); continue
            rec, h = g
            if pins.get(ref) != h: bad.append("EVIDENCE_HASH_NOT_PINNED_OR_MISMATCH:" + ref); continue
            if rec.available_at > watermark: bad.append("EVIDENCE_BEYOND_WATERMARK:" + ref)
            index[ref] = EvidenceRecord(**{**{k: getattr(rec, k) for k in _FIELDS}, "revoked": ref in revoked}); refs.append((ref, h))
        if bad: return out(INVALID, bad, refs)
        v = judge_transition_evidence(claim, index, now)
        if v.status != VALID: return out(v.status, v.reasons, refs)
        return out(VALID, (), refs, min(r.available_at + r.max_age for r in index.values()))
    def use(self, receipt: ResolutionReceipt, claim: TransitionClaim, pins: dict, now: int, watermark: int) -> ResolutionReceipt:
        """Re-resolve at USE time; the earlier receipt is only a claim about the past. Returns the fresh receipt when it is VALID and binds the same claim and the same per-ref content hashes."""
        fresh = self.resolve(claim, pins, now, watermark)
        if fresh.status != VALID: raise Refusal(",".join(fresh.reasons) or fresh.status, code="EVIDENCE_NOT_VALID_AT_USE")
        if receipt.claim_hash != fresh.claim_hash or receipt.refs != fresh.refs or receipt.store_id != fresh.store_id: raise Refusal("receipt", code="EVIDENCE_RECEIPT_DOES_NOT_BIND_CURRENT_EVIDENCE")
        return fresh
