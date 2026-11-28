"""R53 stored PendingRow + committed-predecessor receipt. SIM profile/codec (UNADMITTED); candidate storage keys; no persisted-authority claim."""
import pytest
from stage_a.errors import Refusal, IntegrityFailure
from stage_a.schema import objects as O, independent as X
from stage_a.schema.encoding import Ref
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.tracker.materialization import row_store as RS
from stage_a.tracker.materialization.state_rows import StateRowBuilder
from tests.trk_stage_a.test_r53_state_rows import SCHEMA, T, FIXED, enc, dec, step_fn, kw, H

def rig(store=None):
    s = store or InMemoryObjectStore(); b = StateRowBuilder(SCHEMA, T, enc, dec, FIXED)
    return s, b, RS.PendingRowStore(s, T), None
def chain_of(s, b, rows, xs, start=None, first=0):
    c = RS.CommittedRowChain(b, rows); out, ph = [], start
    for i, x in enumerate(xs, start=first):
        r, rc = c.step(step_fn, ph, {"x": x}, **kw(i, origin=ph is None)); out.append((r, rc)); ph = rc.row_hash
    return out

def test_chain_through_store_positive_reload_and_receipts():
    s, b, rows, _ = rig(); out = chain_of(s, b, rows, [1.0, 2.0, 4.0])
    for r, rc in out:
        assert rc.row_hash == O.row_content_hash(T, r).hex() and rc.independent_hash_equal and rc.byte_length == len(O.row_content_bytes(T, r))
        assert rows.load(rc.row_hash) == r and rows.receipt_for(rc.row_hash) == rc
    assert out[1][0].predecessor_row_hash == bytes.fromhex(out[0][1].row_hash)

def test_restart_with_fresh_objects_over_same_store_equals_uninterrupted():
    s, b, rows, _ = rig(); full = chain_of(s, b, rows, [1.0, 2.0, 4.0, 8.0])
    s2, b2, rows2, _ = rig(); part = chain_of(s2, b2, rows2, [1.0, 2.0])
    _, b3, rows3, _ = rig(s2)                                              # new builder/store wrappers; only the object store survives
    last = chain_of(s2, b3, rows3, [4.0, 8.0], start=part[-1][1].row_hash, first=2)
    assert [rc.row_hash for _, rc in last] == [full[2][1].row_hash, full[3][1].row_hash]

def test_uncommitted_predecessor_is_refused_even_if_self_consistent():
    s, b, rows, _ = rig(); [(r0, rc0)] = chain_of(s, b, rows, [1.0])
    s2, b2, rows2, _ = rig()                                               # a DIFFERENT store: r0 is a perfectly valid object/hash but not committed here
    with pytest.raises(Refusal) as e: RS.CommittedRowChain(b2, rows2).step(step_fn, rc0.row_hash, {"x": 1.0}, **kw(1))
    assert e.value.code == "PREDECESSOR_NOT_COMMITTED"
    nxt = b2.step(step_fn, r0, {"x": 1.0}, **kw(1))                        # builder alone accepts the caller object; the STORE must refuse to commit its successor
    with pytest.raises(Refusal) as e: rows2.commit(nxt)
    assert e.value.code == "PREDECESSOR_NOT_COMMITTED"

def test_fork_refused_same_row_idempotent_origin_fork_refused():
    s, b, rows, _ = rig(); [(r0, rc0)] = chain_of(s, b, rows, [1.0])
    c = RS.CommittedRowChain(b, rows)
    a, ra = c.step(step_fn, rc0.row_hash, {"x": 2.0}, **kw(1)); a2, ra2 = c.step(step_fn, rc0.row_hash, {"x": 2.0}, **kw(1))
    assert ra == ra2                                                       # same successor again: idempotent
    with pytest.raises(Refusal) as e: c.step(step_fn, rc0.row_hash, {"x": 3.0}, **kw(1))
    assert e.value.code == "PENDING_ROW_FORK"
    with pytest.raises(Refusal) as e: c.step(step_fn, None, {"x": 9.0}, **kw(0, origin=True))       # second, different origin for the same profile identity
    assert e.value.code == "PENDING_ROW_FORK"

def test_tampered_stored_bytes_and_field_document_fail_load():
    s, b, rows, _ = rig(); [(r0, rc0)] = chain_of(s, b, rows, [1.0]); k = RS.row_key(rc0.row_hash); fk = RS.fields_key(rc0.row_hash)
    good = s._d[k]; s._d[k] = (good[0][:-1] + bytes([good[0][-1] ^ 1]), good[1])
    with pytest.raises(IntegrityFailure): rows.load(rc0.row_hash)
    s._d[k] = good; assert rows.load(rc0.row_hash) == r0
    gf = s._d[fk]; s._d[fk] = (gf[0].replace(b'"step_index":0', b'"step_index":7'), gf[1]); assert s._d[fk][0] != gf[0]
    with pytest.raises(IntegrityFailure): rows.load(rc0.row_hash)
    s._d[fk] = gf; del s._d[fk]
    with pytest.raises(Refusal) as e: rows.load(rc0.row_hash)
    assert e.value.code == "PREDECESSOR_NOT_COMMITTED"

def test_independent_verifier_disagreement_blocks_commit(monkeypatch):
    s, b, rows, _ = rig(); r = b.step(step_fn, None, {"x": 1.0}, **kw(0, True))
    monkeypatch.setattr(X, "row_hash", lambda d, e: bytes(32))
    with pytest.raises(IntegrityFailure): rows.commit(r)
    assert s.list_prefix("pending-row") == []                              # nothing written when verification fails

def test_bad_hash_keys_refused():
    s, b, rows, _ = rig()
    for bad in ("", "zz" * 32, "AB" * 32, "ab" * 31, 5): 
        with pytest.raises(Refusal): rows.load(bad)

def test_commit_refuses_when_row_key_already_holds_different_bytes():
    s, b, rows, _ = rig(); r = b.step(step_fn, None, {"x": 1.0}, **kw(0, True)); h = O.row_content_hash(T, r).hex()
    assert s.put_if_absent(RS.row_key(h), b"planted")
    with pytest.raises(IntegrityFailure): rows.commit(r)

def test_commit_refuses_unreadable_or_conflicting_sidecar_and_does_not_overwrite():
    s, b, rows, _ = rig(); r = b.step(step_fn, None, {"x": 1.0}, **kw(0, True)); h = O.row_content_hash(T, r).hex()
    assert s.put_if_absent(RS.fields_key(h), b"{}")
    with pytest.raises(IntegrityFailure): rows.commit(r)                        # no false success receipt
    assert s.get(RS.fields_key(h))[0] == b"{}"                                  # the conflicting object is preserved, not overwritten
    with pytest.raises(IntegrityFailure): rows.load(h)
    s2, b2, rows2, _ = rig(); q = b2.step(step_fn, None, {"x": 5.0}, **kw(0, True)); hq = O.row_content_hash(T, q).hex()
    assert s2.put_if_absent(RS.fields_key(hq), RS._to_json(r))                  # a VALID document of a DIFFERENT row planted under this row's key
    with pytest.raises(IntegrityFailure): rows2.commit(q)

def test_interrupted_commit_recovers_on_exact_retry_without_rewriting():
    s, b, rows, _ = rig(); r = b.step(step_fn, None, {"x": 1.0}, **kw(0, True)); h = O.row_content_hash(T, r).hex()
    real = s.put_if_absent; calls = []
    def crash_on_fields(k, d):
        if k.startswith("pending-row-fields/"): raise RuntimeError("process died before the sidecar landed")
        calls.append(k); return real(k, d)
    s.put_if_absent = crash_on_fields
    with pytest.raises(RuntimeError): rows.commit(r)
    s.put_if_absent = real
    assert s.get(RS.row_key(h)) is not None and s.get(RS.fields_key(h)) is None       # state after the interruption: bytes+claim landed, sidecar did not
    with pytest.raises(Refusal): rows.load(h)                                          # not loadable => not committed
    rc = rows.commit(r)                                                                # exact retry completes it
    assert rc.row_hash == h and rows.load(h) == r and rows.commit(r) == rc             # and a further retry is idempotent
    k = s.get(RS.row_key(h)); rows.commit(r); assert s.get(RS.row_key(h)) == k          # nothing rewritten
