"""R53 E05 rebuild over per-row owning objects: pending rows re-loaded from the row store, transitions from the ROW_ACCEPTED journal, drift, unsupplied state, foreign kind."""
import json
import pytest
from stage_a.errors import Refusal, IntegrityFailure
from stage_a.storage import e05_sources as S, e05_row_sources as RW
from stage_a.storage.e05_index import E05Index
from stage_a.tracker import row_acceptance as RA
from tests.trk_stage_a.test_r53_row_acceptance import rig, acc

def setup():
    s, js, rows, out, a = rig()
    for _, rc in out[:2]: acc(a, rc.row_hash)
    ns = RA.row_namespace(out[0][0]); j = js.journal(ns)
    src = {"rows": RW.pending_row_source(s, rows, lambda h: "HELD_STATE_" + h[:4]), "tx": RW.row_transition_source(j, ns, rows)}
    res = S.combined_resolver(S.object_resolver(s), lambda ref: None)
    from stage_a.storage.e05_sources import journal_resolver
    res = S.combined_resolver(S.object_resolver(s), journal_resolver({ns: j}))
    return s, js, rows, out, a, ns, j, src, res

def test_rebuild_projects_pending_rows_and_transitions_with_ref_and_hash_and_head_only_status():
    s, js, rows, out, a, ns, j, src, res = setup(); ix = E05Index(); heads = ix.rebuild(src)
    assert set(heads) == {"rows", "tx"}
    for _, rc in out:                                                                     # all three rows are committed; only the first two were accepted
        r = ix.lookup("stagea_pending_row_index", {"row_content_hash": rc.row_hash}, res); assert not r.authoritative and r["ref"] == "object:pending-row/" + rc.row_hash
    recs = j.read_from(1); assert len(recs) == 2
    for rec in recs:
        b = json.loads(rec.body_json); t = ix.lookup("stagea_transition_index", {"transition_hash": b["transition_hash"]}, res)
        assert t["ref"] == "journal:%s/%d" % (ns, rec.seq) and t["ref_hash"] == rec.record_hash and t["accepted_at"] == str(b["canonical_accepted_at"])
    st = ix.current_status(out[0][0].feature_id.hex(), out[0][0].materialization_version, "tx", heads["tx"], res)
    assert json.loads(st["payload"])["head_row"] == out[1][1].row_hash and json.loads(st["payload"])["head_seq"] == 2     # head only
    assert ix.verify_all(res) >= 6

def test_drift_stale_head_unsupplied_state_and_tampered_row_are_refused():
    s, js, rows, out, a, ns, j, src, res = setup(); ix = E05Index(); heads = ix.rebuild(src)
    acc(a, out[2][1].row_hash)                                                            # the journal head moves after the rebuild
    with pytest.raises(Refusal) as e: ix.current_status(out[0][0].feature_id.hex(), out[0][0].materialization_version, "tx", src["tx"][0](), res)      # caller passes the CURRENT source head
    assert e.value.code == "STALE_INDEX"
    with pytest.raises(Refusal) as e: E05Index().rebuild({"rows": RW.pending_row_source(s, rows, lambda h: None)})
    assert e.value.code == "E05_SOURCE_PENDING_ROW_STATE_NOT_SUPPLIED"
    k = "pending-row/" + out[0][1].row_hash; g = s._d[k]; s._d[k] = (g[0][:-1] + bytes([g[0][-1] ^ 1]), g[1])
    with pytest.raises(IntegrityFailure): E05Index().rebuild({"rows": RW.pending_row_source(s, rows, lambda h: "x")})      # tampered canonical bytes never project

def test_foreign_kind_and_foreign_namespace_row_refused():
    s, js, rows, out, a, ns, j, src, res = setup()
    j.append(j.head(), "CANONICAL_ACCEPTED", {"x": 1})
    with pytest.raises(Refusal) as e: E05Index().rebuild({"tx": RW.row_transition_source(j, ns, rows)})
    assert e.value.code == "ROW_NAMESPACE_FOREIGN_KIND"
    s2, js2, rows2, out2, a2, ns2, j2, src2, res2 = setup()
    with pytest.raises(Refusal) as e: E05Index().rebuild({"tx": RW.row_transition_source(j2, ns2 + "x", rows2)})
    assert e.value.code == "E05_SOURCE_ROW_NOT_OF_THIS_NAMESPACE"
