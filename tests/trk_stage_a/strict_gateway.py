"""R27 test helper: a STRICT simulated Gateway (health_source = the issuing Core, shape-only snapshots denied) and the explicit subject association a bound snapshot needs."""
from stage_a.gateway import contracts as G
from .test_boundaries import _gw, I
def sgw(core, ver="1", **kw):
    gw = _gw(ver=ver, **kw); gw.health_source = core; gw.allow_shape_only_health = False; return gw
def bind(core, subject, ver="1", assoc=True, fid=I, instr=I, tf=I):
    b = G.HealthBinding(fid, ver, instr, tf)
    if assoc: core.associate_subject(subject, b, "test-supplied-association")
    return b
