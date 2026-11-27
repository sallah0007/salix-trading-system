import json, unittest
from stage_a.errors import Refusal
from stage_a.tracker import chain_status as C
from stage_a.tracker.status_decoder import make_decoder
from stage_a.tracker.status_projection import StatusProjection
from stage_a.gateway import contracts as G
from .test_r12_status_projection import jr, gw, res
from tests.trk_stage_a import test_boundaries as B
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
SPEC = dict(record_kind="STATUS_X", mv=("fid", "fver", "instr", "tf", "mver"), bytes_fields={"fid": 16, "instr": 16, "tf": 16}, status_field="st", status_map={"CUR": C.CURRENT}, sequence_field="seq", available_asof_field="asof", correction_field="corr")
def body(**o):
    d = {"fid": B.I.hex(), "fver": "f1", "instr": B.I.hex(), "tf": B.I.hex(), "mver": "m1", "st": "CUR", "seq": 1, "asof": 1, "corr": False}; d.update(o); return d
class Rec:
    def __init__(self, kind, b): self.kind, self.body_json = kind, json.dumps(b)
class Decoder(unittest.TestCase):
    def test_spec_is_required_whole_and_nothing_is_defaulted(self):
        for bad in ({}, dict(SPEC, status_map={}), dict(SPEC, status_map={"CUR": "NOT_A_STATUS"}), dict(SPEC, mv=("a", "b")), dict(SPEC, bytes_fields={"zzz": 16}), {k: v for k, v in SPEC.items() if k != "status_field"}, dict(SPEC, extra=1)): self.assertEqual(code(make_decoder, bad), "STATUS_MAPPING_SPEC_INVALID")
    def test_mapped_record_decodes_other_kinds_are_not_status_and_misfits_refuse(self):
        d = make_decoder(SPEC); f = d(Rec("STATUS_X", body())); self.assertEqual((f.mv, f.status, f.sequence), ((B.I, "f1", B.I, B.I, "m1"), C.CURRENT, 1)); self.assertIsNone(d(Rec("OTHER", body())))
        for o, c in ((dict(fid="ab"), "STATUS_RECORD_ID_WIDTH"), (dict(fid="zz" * 16), "STATUS_RECORD_ID_NOT_HEX"), (dict(st="PUBLISHABLE"), "STATUS_RECORD_STATUS_UNMAPPED"), (dict(st=None), "STATUS_RECORD_STATUS_UNMAPPED"), (dict(seq=True), "STATUS_RECORD_NUMBERS_INVALID"), (dict(corr=0), "STATUS_RECORD_NUMBERS_INVALID"), (dict(fver=""), "STATUS_RECORD_FIELD_INVALID")):
            self.assertEqual(code(d, Rec("STATUS_X", body(**o))), c, o)
        self.assertEqual(code(d, type("R", (), {"kind": "STATUS_X", "body_json": "{"})()), "STATUS_RECORD_NOT_JSON")
    def test_through_the_real_projection_and_gateway_a_mapped_commit_binds_and_a_misfit_invalidates_the_projection(self):
        j = jr(); j.append(j.head(), "STATUS_X", body()); p = StatusProjection(j, make_decoder(SPEC)); p.refresh(); self.assertTrue(p.authoritative); self.assertIsInstance(res(gw(p)), G.Binding)
        j.append(j.head(), "STATUS_X", body(st="PUBLISHABLE", seq=2)); self.assertEqual(code(p.refresh), "STATUS_RECORD_STATUS_UNMAPPED"); self.assertFalse(p.authoritative)
if __name__ == "__main__": unittest.main()
