"""R36 TR-15: DEFAULT CROSS-INSTRUMENT ACCESS = DENY (DOCX s7A); explicit consumer/target/source grant positive; revocation denies new windows; stored outcomes immutable."""
import unittest
from stage_a.errors import Refusal
from stage_a.gateway import contracts as G
from stage_a.gateway.cross_instrument import CrossInstrumentPolicy as P
from stage_a.gateway.v038 import FinalResolutionStore, FinalResolutionIdentity as FI
from .test_boundaries import _gw, _entry, _health, I, J
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
def gw():
    g = _gw(); g.final_store = FinalResolutionStore(); return g
class Deny(unittest.TestCase):
    def test_default_deny_then_explicit_grant_for_exactly_that_consumer_target_and_source(self):
        g = gw(); e = _entry()
        self.assertEqual(g.resolve("a", e, I, I, 3, 10, _health(), target_instrument=J, consumer_id="FW").reason, "CROSS_INSTRUMENT_DENIED")        # no policy at all: denied
        g.cross_instrument = P(); self.assertEqual(g.resolve("b", e, I, I, 3, 10, _health(), target_instrument=J, consumer_id="FW").reason, "CROSS_INSTRUMENT_DENIED")      # empty policy: denied
        self.assertIsInstance(g.resolve("c", e, I, I, 3, 10, _health(), target_instrument=I, consumer_id="FW"), G.Binding)                      # same instrument is not cross-instrument
        g.cross_instrument.grant("FW", J, I, "SRC-GRANT-1")
        self.assertIsInstance(g.resolve("d", e, I, I, 3, 10, _health(), target_instrument=J, consumer_id="FW"), G.Binding)                      # explicit positive control
        self.assertEqual(g.resolve("e", e, I, I, 3, 10, _health(), target_instrument=J, consumer_id="ML").reason, "CROSS_INSTRUMENT_DENIED")   # another consumer
        self.assertEqual(g.resolve("f", e, I, I, 3, 10, _health(), target_instrument=b"\x09" * 16, consumer_id="FW").reason, "CROSS_INSTRUMENT_DENIED")   # another target
    def test_window_path_denies_by_default_pins_the_target_and_revocation_denies_new_windows_only(self):
        g = gw(); g.cross_instrument = P(); g.cross_instrument.grant("FW", J, I, "SRC"); e = _entry(); w1, w2 = FI("FW", "B1", "S", "W1"), FI("FW", "B1", "S", "W2")
        b = g.resolve_window("r1", w1, e, I, I, 3, 10, _health(), target_instrument=J); self.assertIsInstance(b, G.Binding)
        g.cross_instrument.revoke("FW", J, I)
        self.assertIs(g.resolve_window("r2", w1, e, I, I, 3, 10, _health(), target_instrument=J), b)                                          # the stored final outcome is immutable
        self.assertEqual(g.resolve_window("r3", w2, e, I, I, 3, 10, _health(), target_instrument=J).reason, "CROSS_INSTRUMENT_DENIED")         # a NEW window after revocation
        self.assertEqual(code(g.resolve_window, "r4", w1, e, I, I, 3, 10, _health(), target_instrument=I), "RESOLUTION_IDENTITY_PARAMETERS_DIFFER")   # the target instrument is a governing parameter
    def test_grants_are_malformed_conflicting_or_unknown_fail_closed(self):
        p = P(); self.assertEqual(code(p.grant, "FW", J, I, ""), "CROSS_INSTRUMENT_GRANT_MALFORMED"); self.assertEqual(code(p.grant, "FW", I, I, "S"), "CROSS_INSTRUMENT_GRANT_MALFORMED")
        p.grant("FW", J, I, "S1"); self.assertEqual(code(p.grant, "FW", J, I, "S2"), "CROSS_INSTRUMENT_GRANT_EXISTS_DIFFERENT_SOURCE"); self.assertEqual(code(p.revoke, "FW", I, J), "CROSS_INSTRUMENT_GRANT_UNKNOWN")
if __name__ == "__main__": unittest.main()
