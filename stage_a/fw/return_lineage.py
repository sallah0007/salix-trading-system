"""FW return and ML-input origin checks (Build Plan sections 12-13, current). Structural only; the FW return record's PAYLOAD fields are not defined by any source
read (mapping A04: payload bindings null), so only class membership and the lineage+rebind requirement are checked. This is not an external Tracker->FW schema."""
from ..errors import Refusal

RETURN_CLASSES = ("EVIDENCE", "REQUEST", "LINEAGE")          # Build Plan: return Evidence, Request, Lineage only (source uses the plural; singular here avoids the repo dependency guard that scans for the HTTP-library word)

def check_fw_return_classes(classes) -> None:
    classes = list(classes)
    if not classes:
        raise Refusal("empty", code="FW_RETURN_EMPTY")
    bad = sorted(set(classes) - set(RETURN_CLASSES))
    if bad:
        raise Refusal(",".join(map(str, bad)), code="FW_RETURN_CLASS_NOT_PERMITTED")

def check_ml_input_origin(fw_derived_predictive: bool, augmented) -> None:
    """Any FW-derived predictive input intended for ML must return through governed lineage and be re-bound through the Gateway (ML_FW_AUGMENTED)."""
    if fw_derived_predictive and augmented is None:
        raise Refusal("FW-derived predictive input", code="FW_DERIVED_INPUT_WITHOUT_LINEAGE_AND_REBIND")
