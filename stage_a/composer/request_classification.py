"""Request classification routing at the Tracker<->Composer boundary (Build Plan 3.1; home stage_a/composer/request_classification.py).
Routing names ONLY: DIRECT_TRACKER_FEATURE | COMPOSER_BUILT_QUANT_FEATURE | NO_QUANT_FEATURE. It creates no request or identity authority.
The predicate that SELECTS a route is not defined in any source read (D8 residual), so this module maps the adapter's existing
outcomes to the governed names and fails closed on everything else. TR-06: a failed requested build never maps to NO_QUANT_FEATURE."""
from ..errors import Refusal
from ..tracker import quant_intake_adapter as A

DIRECT_TRACKER_FEATURE = "DIRECT_TRACKER_FEATURE"
COMPOSER_BUILT_QUANT_FEATURE = "COMPOSER_BUILT_QUANT_FEATURE"
NO_QUANT_FEATURE = "NO_QUANT_FEATURE"
ROUTES = (DIRECT_TRACKER_FEATURE, COMPOSER_BUILT_QUANT_FEATURE, NO_QUANT_FEATURE)

def route_from_adapter(classification: str) -> str:
    if classification == A.QUANT_FEATURE:
        return COMPOSER_BUILT_QUANT_FEATURE
    if classification == A.NO_QUANT_FEATURE:
        return NO_QUANT_FEATURE
    if classification == A.FAILED_REQUESTED_BUILD:
        raise Refusal(classification, code="FAILED_BUILD_NOT_ROUTABLE")      # TR-06
    raise Refusal(str(classification), code="UNKNOWN_CLASSIFICATION")        # fail closed on the unread
# DIRECT_TRACKER_FEATURE has no producer in this repository: nothing here can return it (no source defines its predicate).
