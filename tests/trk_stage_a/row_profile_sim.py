"""SIM row profile PORT for the separated per-row handlers (TEST ONLY; every piece UNADMITTED: schema, program, codec, input values, clock, commit-point rule)."""
import copy, hashlib, time
from tests.trk_stage_a.test_r53_row_acceptance import T, SCHEMA, _ref_step, _i_enc, _i_dec
class _Time:
    def __init__(self): self.n = 20
    def mint(self): self.n += 1; return self.n          # fresh per call WITHIN a process; SIM clock (small ints so the test fence applies); UNADMITTED
class _CP:
    def derive(self, h): return hashlib.sha256(b"SIM" + h.encode()).digest()[:16]
XS = {"in0": 1.0, "in1": 2.0, "in2": 4.0}
def profile():
    return dict(tables=T, schema=copy.deepcopy(SCHEMA), schema_registry=lambda v: copy.deepcopy(SCHEMA), reference_step=_ref_step, decode=_i_dec, encode=_i_enc,
                resolve_inputs=lambda d: {"declared": [(r, hh, XS[r.target_id.decode()]) for r, hh in d]}, input_symbols={"x": 0}, time_port=_Time(), commit_point_port=_CP())
