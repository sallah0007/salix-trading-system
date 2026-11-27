import unittest
from stage_a.errors import Refusal
from stage_a.fw import descriptor_binding as DB
from stage_a.fw.descriptor_crosswalk import FIELDS
def code(f, *a, **k):
    try: f(*a, **k)
    except Refusal as e: return e.code
B = {"scope": "s", "interface_id": "i", "version": "1", "content_hash": "a" * 64, "source_authority": "sa", "acceptance_record": "ar", "validity/supersession": "v"}
DIRECT = ("DEPENDENCY_INTERVAL_START", "DEPENDENCY_INTERVAL_END", "HORIZON_ID", "HORIZON_VERSION", "AUTHORIZED_SEGMENT_SET", "OBSERVATION_REF", "VINTAGE_REF")
PAY = {"s": 10, "e": 20, "h": "H1", "hv": "1", "a": ["seg1", "seg2"], "o": "obs1", "v": "vin1", "ka": 5, "sr": "seg1", "adm": "OK"}
KEYS = {"DEPENDENCY_INTERVAL_START": "s", "DEPENDENCY_INTERVAL_END": "e", "HORIZON_ID": "h", "HORIZON_VERSION": "hv", "AUTHORIZED_SEGMENT_SET": "a", "OBSERVATION_REF": "o", "VINTAGE_REF": "v"}
class D(unittest.TestCase):
    def test_bound_direct_and_partial_fields_are_read_unverified_and_the_unmapped_three_stay_held_even_if_the_payload_carries_them(self):
        d = DB.read_descriptor(PAY, {f: B for f in DIRECT}, dict(KEYS, KNOWABLE_AT="ka", SEGMENT_REF="sr", ADMISSIBILITY_STATE="adm"))
        self.assertEqual(set(d.values), set(DIRECT)); self.assertEqual(d.values["HORIZON_ID"], ("H1", "DIRECT_UNVERIFIED")); self.assertEqual(d.values["VINTAGE_REF"], ("vin1", "PARTIAL_UNVERIFIED"))
        self.assertEqual(d.held, {"SEGMENT_REF": "EXACT_SOURCE_MAPPING_UNBOUND", "KNOWABLE_AT": "EXACT_SOURCE_MAPPING_UNBOUND", "ADMISSIBILITY_STATE": "FW_OWNED_INTERNAL_DERIVATION_UNBOUND"}); self.assertFalse(d.complete)
    def test_no_binding_means_everything_is_held_and_each_field_needs_its_own_binding_and_key(self):
        d = DB.read_descriptor(PAY, {}, KEYS); self.assertEqual(d.values, {}); self.assertEqual(len(d.held), len(FIELDS))
        for f in DIRECT:
            d = DB.read_descriptor(PAY, {g: B for g in DIRECT if g != f}, KEYS); self.assertEqual(d.held[f], "UNDECLARED_REAL_PAYLOAD_BINDING"); self.assertEqual(len(d.values), len(DIRECT) - 1)
            k = {g: v for g, v in KEYS.items() if g != f}; self.assertEqual(DB.read_descriptor(PAY, {g: B for g in DIRECT}, k).held[f], "PAYLOAD_KEY_NOT_SUPPLIED_OR_ABSENT")
    def test_substitutions_malformed_values_bad_bindings_and_unordered_interval_are_refused(self):
        for bad in ("AVAILABLE_ASOF", "decision_cutoff", "POLICY_ID"): self.assertEqual(code(DB.read_descriptor, PAY, {f: B for f in DIRECT}, dict(KEYS, HORIZON_ID=bad)), "DESCRIPTOR_SUBSTITUTION_NOT_PERMITTED")
        for k, v in (("s", -1), ("h", ""), ("a", []), ("a", ["x", "x"]), ("o", 3)): self.assertEqual(code(DB.read_descriptor, dict(PAY, **{k: v}), {f: B for f in DIRECT}, KEYS), "DESCRIPTOR_VALUE_MALFORMED", (k, v))
        self.assertEqual(code(DB.read_descriptor, dict(PAY, s=30), {f: B for f in DIRECT}, KEYS), "DESCRIPTOR_INTERVAL_NOT_ORDERED")
        self.assertIsNotNone(code(DB.read_descriptor, PAY, {"HORIZON_ID": {"scope": "s"}}, KEYS)); self.assertEqual(code(DB.read_descriptor, PAY, {"BOGUS": B}, KEYS), "UNKNOWN_DESCRIPTOR_FIELD")
        self.assertEqual(code(DB.read_descriptor, [], {}, {}), "DESCRIPTOR_INPUT_INVALID")
