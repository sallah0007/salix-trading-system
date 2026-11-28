"""R53 per-ROW typed acceptance bridge. SIM profile/codec/time/commit-point rule (all UNADMITTED, test-only): no qualified clock, no normative commit-point id, no gate clearance."""
import hashlib, json, struct
import pytest
from stage_a.errors import Refusal, IntegrityFailure
from stage_a.schema import objects as O, independent as X
from stage_a.schema.encoding import Ref
from stage_a.schema.candidate_code_tables import candidate_tables
from stage_a.storage.object_store import InMemoryObjectStore
from stage_a.tracker.registry import FeatureJournalSet
from stage_a.tracker import row_acceptance as RA
from stage_a.tracker.verification import row_step_verifier as VR
from stage_a.tracker.materialization import row_store as RS
from stage_a.tracker.materialization.state_rows import StateRowBuilder
from tests.trk_stage_a.test_r53_state_rows import SCHEMA, FIXED, enc, dec, step_fn, I, H

T = candidate_tables()
def R(t, n): return Ref(t, n.encode(), b"v1", None)
FX = dict(FIXED, step_class_ref=R("STEP_CLASS_SET_REF", "sc"), speculation_mode="OFF")
EVID = R("VERIFICATION_EVIDENCE_REF", "ev")
def kw(i, origin=False): return dict(step_index=i, event_time=1000 + i, input_refs_and_hashes=((R("INPUT_REF", "in%d" % i), H),), **({"state_origin_ref": R("STATE_ORIGIN_REF", "o")} if origin else {}))
class Time:
    def __init__(self, start=100, hook=None): self.n = start; self.calls = 0; self.hook = hook
    def mint(self):
        self.calls += 1; self.n += 1
        if self.hook: self.hook(self.calls)
        return self.n
class CP:                                                         # SIM commit-point rule (NOT source-defined)
    def derive(self, h): return hashlib.sha256(b"SIM" + h.encode()).digest()[:16]
def rig(time=None, cp=None):
    s = InMemoryObjectStore(); b = StateRowBuilder(SCHEMA, T, enc, dec, FX); rows = RS.PendingRowStore(s, T); js = FeatureJournalSet(s, "acceptor-1")
    ch = RS.CommittedRowChain(b, rows); out, ph = [], None
    for i, x in enumerate([1.0, 2.0, 4.0]):
        r, rc = ch.step(step_fn, ph, {"x": x}, **kw(i, origin=ph is None)); out.append((r, rc)); ph = rc.row_hash
    return s, js, rows, out, RA.RowAcceptor(js, rows, T, time or Time(), cp or CP())
def _ref_step(prior, inputs):
    acc_ = (0.0 if prior is None else prior["acc"]) + inputs["x"]; return {"acc": acc_, "vec": [acc_, acc_ * 2.0]}
def _i_enc(st): return struct.pack(">3d", st["acc"], *st["vec"])
def _i_dec(b): v = struct.unpack(">3d", b); return {"acc": v[0], "vec": [v[1], v[2]]}
def evidence_for(a, h):
    """ACTUAL independent verification of the stored row against its stored predecessor; returns (result, evidence ref naming it)."""
    row = a._rows.load(h); pred = None if row.predecessor_row_hash is None else a._rows.load(row.predecessor_row_hash.hex()); xs = {"in0": 1.0, "in1": 2.0, "in2": 4.0}
    res = VR.verify_row_step(row=row, predecessor=pred, schema=SCHEMA, reference_step=_ref_step, decode=_i_dec, encode=_i_enc,
        resolve_inputs=lambda d: {"declared": [(r, hh, xs[r.target_id.decode()]) for r, hh in d], "values": {"x": xs[d[0][0].target_id.decode()]}},
        recompute_row_hash=lambda r: X.row_hash(RS.independent_dict(T, r), T.enums).hex(), expect_row_hash=h)
    return res, Ref("VERIFICATION_EVIDENCE_REF", b"row-step", b"v1", bytes.fromhex(res.result_hash))
def acc(a, h, **kw):
    res, ev = evidence_for(a, h)
    d = dict(verification_result=res, verification_evidence_ref=ev, currentness_state="CURRENT", status_event="PUBLISHABLE"); d.update(kw)
    return a.accept(h, **d)

def test_accepts_rows_in_order_with_typed_transition_and_independent_hash():
    s, js, rows, out, a = rig(); recs = [acc(a, rc.row_hash) for _, rc in out]
    for (r, rc), rec in zip(out, recs):
        b = json.loads(rec.body_json); j = js.journal(RA.row_namespace(r))
        c = O.CanonicalTransition(bytes.fromhex(rc.row_hash), Ref(*[b["verification_evidence_ref"][0], bytes.fromhex(b["verification_evidence_ref"][1]), bytes.fromhex(b["verification_evidence_ref"][2]), bytes.fromhex(b["verification_evidence_ref"][3])]), j.epoch, bytes.fromhex(b["canonical_commit_point_id"]), b["canonical_accepted_at"], b["available_asof"], None, "CURRENT", "PUBLISHABLE")
        assert b["transition_hash"] == O.transition_hash(T, c).hex() == X.transition_hash(RA.transition_independent_dict(T, c), T.enums).hex()
        assert b["available_asof"] == b["canonical_accepted_at"] and b["sifp_fencing_epoch"] == j.epoch and b["version"] == RA.VERSION_TAG
    assert [json.loads(r.body_json)["canonical_accepted_at"] for r in recs] == [101, 102, 103]
    assert [r.seq for r in recs] == [1, 2, 3]

def test_idempotent_replay_returns_same_record_without_new_time():
    t = Time(); s, js, rows, out, a = rig(time=t); r1 = acc(a, out[0][1].row_hash); n = t.calls
    assert acc(a, out[0][1].row_hash) == r1 and t.calls == n

def test_predecessor_must_be_accepted_and_row_must_be_committed():
    s, js, rows, out, a = rig()
    with pytest.raises(Refusal) as e: acc(a, out[1][1].row_hash)
    assert e.value.code == "PREDECESSOR_ROW_NOT_ACCEPTED"
    with pytest.raises(Refusal) as e: acc(a, "ab" * 32)
    assert e.value.code == "PREDECESSOR_NOT_COMMITTED"

def test_unbound_or_bad_ports_and_symbols_fail_closed():
    s, js, rows, out, _ = rig()
    with pytest.raises(Refusal) as e: RA.RowAcceptor(js, rows, T, None, CP())
    assert e.value.code == "ATTEMPT_TIME_PORT_UNBOUND_HELD"
    with pytest.raises(Refusal) as e: RA.RowAcceptor(js, rows, T, Time(), None)
    assert e.value.code == "COMMIT_POINT_RULE_NOT_SUPPLIED_HELD"
    class Short:
        def derive(self, h): return b"x"
    with pytest.raises(Refusal) as e: acc(RA.RowAcceptor(js, rows, T, Time(), Short()), out[0][1].row_hash)
    assert e.value.code == "COMMIT_POINT_ID_INVALID"
    a = RA.RowAcceptor(js, rows, T, Time(), CP())
    with pytest.raises(Refusal): acc(a, out[0][1].row_hash, currentness_state="BOGUS")
    with pytest.raises(Refusal): acc(a, out[0][1].row_hash, status_event="WITHDRAWN")
    assert js.journal(RA.row_namespace(out[0][0])).read_from(1) == []         # nothing was accepted by any refusal

def test_head_race_reconstructs_with_a_fresh_time_and_one_acceptance():
    s, js, rows, out, a0 = rig(); acc(a0, out[0][1].row_hash); j = js.journal(RA.row_namespace(out[0][0]))
    def rival(n):
        if n == 1: j.append(j.head(), RA.KIND, {"row_content_hash": "ab" * 32, "version": "RIVAL"})
    t = Time(start=200, hook=rival); a = RA.RowAcceptor(js, rows, T, t, CP()); rec = acc(a, out[1][1].row_hash)
    b = json.loads(rec.body_json)
    assert t.calls == 2 and b["canonical_accepted_at"] == 202 and rec.seq == 3          # first attempt's time 201 was discarded with its body
    assert sum(1 for r in j.read_from(1) if json.loads(r.body_json)["row_content_hash"] == out[1][1].row_hash) == 1

from stage_a.coordination.object_store_journal import ObjectStoreJournal
from stage_a.errors import UnknownCommit
def _wrap(monkeypatch, landed):
    real = ObjectStoreJournal.append; st = {"n": 0}
    def w(self, head, kind, body):
        st["n"] += 1
        if st["n"] == 1:
            if landed: real(self, head, kind, body)
            raise UnknownCommit("ack lost" if landed else "dropped")
        return real(self, head, kind, body)
    monkeypatch.setattr(ObjectStoreJournal, "append", w)

def test_landed_unknown_commit_returns_same_record_and_time_without_remint(monkeypatch):
    s, js, rows, out, _ = rig(); t = Time(start=300); a = RA.RowAcceptor(js, rows, T, t, CP()); _wrap(monkeypatch, True)
    rec = acc(a, out[0][1].row_hash)
    assert t.calls == 1 and json.loads(rec.body_json)["canonical_accepted_at"] == 301
    assert len(js.journal(RA.row_namespace(out[0][0])).read_from(1)) == 1

def test_dropped_unknown_commit_reminted_and_exactly_one_acceptance(monkeypatch):
    s, js, rows, out, _ = rig(); t = Time(start=300); a = RA.RowAcceptor(js, rows, T, t, CP()); _wrap(monkeypatch, False)
    rec = acc(a, out[0][1].row_hash)
    assert t.calls == 2 and json.loads(rec.body_json)["canonical_accepted_at"] == 302
    assert len(js.journal(RA.row_namespace(out[0][0])).read_from(1)) == 1

def test_foreign_kind_in_row_namespace_refused():
    s, js, rows, out, a = rig(); j = js.journal(RA.row_namespace(out[0][0])); j.append(j.head(), "CANONICAL_ACCEPTED", {"x": 1})
    with pytest.raises(Refusal) as e: acc(a, out[0][1].row_hash)
    assert e.value.code == "ROW_NAMESPACE_FOREIGN_KIND"

def test_independent_transition_hash_disagreement_blocks_acceptance(monkeypatch):
    s, js, rows, out, a = rig(); monkeypatch.setattr(X, "transition_hash", lambda d, e: bytes(32))
    with pytest.raises(IntegrityFailure): acc(a, out[0][1].row_hash)
    assert js.journal(RA.row_namespace(out[0][0])).read_from(1) == []

def test_fenced_out_acceptor_cannot_accept():
    from stage_a.errors import StaleFence
    s, js, rows, out, a = rig(); acc(a, out[0][1].row_hash)
    FeatureJournalSet(s, "failover-writer").journal(RA.row_namespace(out[0][0]))              # a newer epoch is acquired elsewhere
    with pytest.raises(StaleFence): acc(a, out[1][1].row_hash)
    assert len(FeatureJournalSet(s, "reader").journal(RA.row_namespace(out[0][0])).read_from(1)) == 1


def test_acceptance_requires_the_actual_verification_of_this_row_and_an_evidence_ref_naming_it():
    from stage_a.tracker.verification import verification_result as VRES
    s, js, rows, out, a = rig(); h0, h1 = out[0][1].row_hash, out[1][1].row_hash; acc(a, h0)
    res1, ev1 = evidence_for(a, h1); res0, ev0 = evidence_for(a, h0)
    def code(**kw):
        with pytest.raises(Refusal) as e: a.accept(h1, **dict(dict(verification_result=res1, verification_evidence_ref=ev1, currentness_state="CURRENT", status_event="PUBLISHABLE"), **kw))
        return e.value.code
    assert code(verification_result=res0, verification_evidence_ref=ev0) == "ROW_VERIFICATION_NOT_FOR_THIS_ROW"          # another row's genuine PASS
    assert code(verification_evidence_ref=ev0) == "EVIDENCE_REF_DOES_NOT_NAME_THE_VERIFICATION"                            # a ref naming a different result
    assert code(verification_evidence_ref=Ref("VERIFICATION_EVIDENCE_REF", b"x", b"v1", None)) == "EVIDENCE_REF_DOES_NOT_NAME_THE_VERIFICATION"
    forged = VRES.make_result("PASS", VR.SCOPE_ROW_STEP, dict(res1.subject, hand_built="1"), res1.checks, res1.reasons)          # same checks, never issued by a verifier run
    assert code(verification_result=forged, verification_evidence_ref=Ref("VERIFICATION_EVIDENCE_REF", b"x", b"v1", bytes.fromhex(forged.result_hash))) == "ROW_VERIFICATION_NOT_ISSUED_BY_A_VERIFIER_RUN"
    mat = VRES.make_result("PASS", VRES.SCOPE_MATERIALIZATION, dict(res1.subject), res1.checks, res1.reasons); VRES._RECEIPTS.add(mat.result_hash)
    with pytest.raises(Refusal) as e: a.accept(h1, verification_result=mat, verification_evidence_ref=Ref("VERIFICATION_EVIDENCE_REF", b"x", b"v1", bytes.fromhex(mat.result_hash)), currentness_state="CURRENT", status_event="PUBLISHABLE")
    assert e.value.code == "VERIFICATION_SCOPE_MISMATCH"                                                                    # wrong scope, even with a receipt
    bad = O.PendingRow(**{**rows.load(h1).__dict__, "state_tuple": rows.load(h1).state_tuple[:-1] + b"\x01"})            # a FAIL result (tampered row) is never acceptable
    fres = VR.verify_row_step(row=bad, predecessor=rows.load(h0), schema=SCHEMA, reference_step=_ref_step, decode=_i_dec, encode=_i_enc,
        resolve_inputs=lambda d: {"declared": [(r, hh, 2.0) for r, hh in d], "values": {"x": 2.0}}, recompute_row_hash=lambda r: X.row_hash(RS.independent_dict(T, r), T.enums).hex(), expect_row_hash=O.row_content_hash(T, bad).hex())
    assert fres.status != "PASS"
    with pytest.raises(Refusal): a.accept(h1, verification_result=fres, verification_evidence_ref=Ref("VERIFICATION_EVIDENCE_REF", b"x", b"v1", bytes.fromhex(fres.result_hash)), currentness_state="CURRENT", status_event="PUBLISHABLE")
    assert [r.seq for r in js.journal(RA.row_namespace(out[0][0])).read_from(1)] == [1]                                       # nothing was accepted by any refusal
