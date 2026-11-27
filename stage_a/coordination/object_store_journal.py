"""Journal over an ObjectStore with conditional writes.

Layout: immutable records at journal/<ns>/<seq>/<hash>; one mutable HEAD doc head/<ns> = {seq,hash,epoch}.
A record is ACCEPTED only when the HEAD conditional replace succeeds. Objects not reachable from HEAD are
orphans and carry no authority. Epoch fencing: acquire_epoch bumps the epoch in HEAD, so a fenced-out writer's
conditional replace fails (etag changed) and its pre-written record stays an unreferenced orphan.

PROVIDER-GATED (R5): correctness here is relative to the ObjectStore contract (strong reads, linearizable
conditional writes). Nothing in this file qualifies any real provider."""
import json
from typing import List
from tracker_component.journal_port import (Head, JournalRecord, HeadMismatch, GENESIS_HEAD,
                                           GENESIS_HASH, record_hash)
from tracker_component.canonical import canonical_json
from ..errors import Refusal, StaleFence, IntegrityFailure, UnknownCommit
from ..storage.byte_primitives import canonical_bytes
from ..storage.keys import head_key, journal_key

class ObjectStoreJournal:
    def __init__(self, store, namespace: str, writer_id: str):
        head_key(namespace)  # validates namespace
        if not writer_id:
            raise Refusal("writer_id required", code="NO_WRITER_ID")
        self._s, self._ns, self._w = store, namespace, writer_id
        self._epoch = None

    # -- HEAD doc -------------------------------------------------------------
    def _read_head_doc(self):
        got = self._s.get(head_key(self._ns))
        if got is None:
            return None, None
        data, etag = got
        try:
            doc = json.loads(data.decode("ascii"))
            assert set(doc) == {"seq", "hash", "epoch"} and isinstance(doc["seq"], int) \
                and isinstance(doc["epoch"], int) and isinstance(doc["hash"], str)
        except Exception:
            raise IntegrityFailure("malformed HEAD doc for %s" % self._ns)
        return doc, etag

    def acquire_epoch(self) -> int:
        for _ in range(8):
            doc, etag = self._read_head_doc()
            if doc is None:
                new = {"seq": 0, "hash": GENESIS_HASH, "epoch": 1}
                if self._s.put_if_absent(head_key(self._ns), canonical_bytes(new)):
                    self._epoch = 1
                    return 1
                continue
            new = dict(doc, epoch=doc["epoch"] + 1)
            if self._s.put_if_match(head_key(self._ns), canonical_bytes(new), etag):
                self._epoch = new["epoch"]
                return self._epoch
        raise Refusal("epoch acquisition contended", code="EPOCH_CONTENTION")

    def head(self) -> Head:
        doc, _ = self._read_head_doc()
        return GENESIS_HEAD if doc is None else Head(doc["seq"], doc["hash"])

    def epoch_is_current(self) -> bool:
        doc, _ = self._read_head_doc()
        return doc is not None and self._epoch is not None and doc["epoch"] == self._epoch

    # -- write ----------------------------------------------------------------
    def append(self, expected_head: Head, kind: str, body: dict) -> JournalRecord:
        if self._epoch is None:
            raise Refusal("acquire_epoch first", code="NO_EPOCH")
        doc, etag = self._read_head_doc()
        if doc is None or doc["epoch"] != self._epoch:
            raise StaleFence("writer %s epoch %s" % (self._w, self._epoch))
        if Head(doc["seq"], doc["hash"]) != expected_head:
            raise HeadMismatch(expected_head, Head(doc["seq"], doc["hash"]))
        body_json = canonical_json(body)
        seq = doc["seq"] + 1
        rh = record_hash(seq, doc["hash"], kind, body_json)
        rec = JournalRecord(seq, doc["hash"], kind, body_json, rh)
        blob = canonical_bytes({"seq": seq, "prev_hash": doc["hash"], "kind": kind, "body_json": body_json,
                                "record_hash": rh, "epoch": self._epoch, "writer": self._w})
        self._s.put_if_absent(journal_key(self._ns, seq, rh), blob)   # False = identical content already there
        new_head = canonical_bytes({"seq": seq, "hash": rh, "epoch": self._epoch})
        if self._s.put_if_match(head_key(self._ns), new_head, etag):
            return rec
        cur, _ = self._read_head_doc()
        if cur is not None and cur["seq"] == seq and cur["hash"] == rh and cur["epoch"] == self._epoch:
            return rec                                   # own earlier attempt already landed
        if cur is None or cur["epoch"] != self._epoch:
            raise StaleFence("fenced out during append")
        raise HeadMismatch(expected_head, Head(cur["seq"], cur["hash"]))

    # -- read -----------------------------------------------------------------
    def read_from(self, seq: int) -> List[JournalRecord]:
        doc, _ = self._read_head_doc()
        if doc is None:
            return []
        out, h, s, last_epoch = [], doc["hash"], doc["seq"], doc["epoch"]
        while s >= 1:
            got = self._s.get(journal_key(self._ns, s, h))
            if got is None:
                raise IntegrityFailure("HEAD references missing record %s/%s" % (self._ns, s))
            r = json.loads(got[0].decode("ascii"))
            if r["seq"] != s or r["record_hash"] != h or \
               record_hash(r["seq"], r["prev_hash"], r["kind"], r["body_json"]) != h:
                raise IntegrityFailure("record hash mismatch at %s/%s" % (self._ns, s))
            if r["epoch"] > last_epoch:
                raise IntegrityFailure("epoch regression at %s/%s" % (self._ns, s))
            last_epoch = r["epoch"]
            out.append(JournalRecord(r["seq"], r["prev_hash"], r["kind"], r["body_json"], r["record_hash"]))
            h, s = r["prev_hash"], s - 1
        if h != GENESIS_HASH:
            raise IntegrityFailure("chain does not reach genesis in %s" % self._ns)
        out.reverse()
        return [r for r in out if r.seq >= seq]
