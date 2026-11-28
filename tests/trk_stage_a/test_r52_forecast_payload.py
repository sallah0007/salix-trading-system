import unittest
from stage_a.ml.forecast_payload import FIELDS, SOURCE_LAYERS, check_forecast_payload
from stage_a.errors import Refusal

def rec(**kw):
    r = {f: "x" for f in FIELDS}; r["SOURCE_LAYER"] = "ML_STANDALONE"; r.update(kw); return r
def code(r, na=()):
    try: return check_forecast_payload(r, na)
    except Refusal as e: return e.code

class ForecastPayload(unittest.TestCase):
    def test_all_seventeen_source_fields_and_three_layers(self):
        self.assertEqual(len(FIELDS), 17); self.assertEqual(SOURCE_LAYERS, ("FW", "ML_STANDALONE", "ML_FW_AUGMENTED"))
    def test_complete_record_passes_for_each_layer_and_extra_fields_are_allowed(self):
        for l in SOURCE_LAYERS: self.assertEqual(check_forecast_payload(rec(SOURCE_LAYER=l, EXTRA="y")), ())
    def test_every_missing_or_none_field_is_refused(self):
        for f in FIELDS:
            r = rec(); del r[f]; self.assertEqual(code(r), "FORECAST_PAYLOAD_FIELD_MISSING", f)
            self.assertEqual(code(rec(**{f: None})), "FORECAST_PAYLOAD_FIELD_MISSING", f)
    def test_omission_only_when_declared_and_absent(self):
        r = rec(); del r["SUPPORT_STATE"]
        self.assertEqual(check_forecast_payload(r, ("SUPPORT_STATE",)), ("SUPPORT_STATE",))
        self.assertEqual(code(rec(), ("SUPPORT_STATE",)), "FORECAST_PAYLOAD_FIELD_BOTH_PRESENT_AND_NOT_APPLICABLE")
        self.assertEqual(code(rec(), ("NOT_A_FIELD",)), "FORECAST_PAYLOAD_UNKNOWN_NOT_APPLICABLE_FIELD")
    def test_layer_domain_and_non_record(self):
        self.assertEqual(code(rec(SOURCE_LAYER="ML")), "FORECAST_PAYLOAD_SOURCE_LAYER_INVALID")
        self.assertEqual(code(None), "FORECAST_PAYLOAD_NOT_A_RECORD")
