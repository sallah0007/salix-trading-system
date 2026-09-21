"""CONTENT_IDENTITY_KEY — structured, ID-independent content identity.

Single responsibility: derive the five governed version-content subkeys from
declared candidate content, using a typed, versioned, deterministic encoding.

Governed rationale
------------------
`FeatureDefinitionRecord.computed_definition_hash()` and
`computed_graph_hash()` both include `feature_id` and `feature_version`. They
are ID-contaminated and cannot serve as a cross-ID content key. Those hashes
are NOT redefined here; CONTENT_IDENTITY_KEY is strictly additive.

The five subkeys mirror the frozen Tracker version-content dimensions. A flat
hash could only answer identical / not identical; the structured form lets a
lookup distinguish EXACT from RELATED (same definition, different provenance,
scope, causal-time or fitted state), which is the disposition the frozen
registry requires.

Encoding rules, explicit
------------------------
Mapping keys are STRINGS ONLY. Non-string keys are rejected, never coerced
through str(): coercion would preserve value types while destroying key types,
so {1:"x"} and {"1":"x"} would collapse into one identity. String keys are
NFC-normalized, and two distinct source keys that normalize to the same key are
rejected as ambiguous rather than silently overwriting each other.

Unordered dimensions are SETS, not multisets. Duplicate elements are rejected
as malformed declared content rather than silently deduplicated, so a
declaration error surfaces instead of being absorbed into an identity.

Content vs process
------------------
Content is anything that changes the artifact's behaviour or its
reproducibility from stated inputs. Process provenance — attempt id, run id,
ledger refs, operator, timestamps, job names — is NEVER content: including it
would make an identical re-run derive a different key, which is the exact
false-non-duplicate this key exists to prevent.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Mapping, Tuple

ENCODING_ID = "SALIX-TYPED-CONTENT-ENCODING"
ENCODING_VERSION = "1"
# V2 (DC-006): the DIRECT bound-instrument field is SCOPE identity content only
# where the governed definition declares instrument-specific applicability. V1
# hashed it unconditionally, over-splitting instrument-agnostic definitions.
# V2 alone did NOT close alternate leakage through other identity fields
# (scope_universe, causal_time_semantics, dependency_closure, ...); DC-006R
# addresses those with the fail-closed leakage guard below. The id is
# bumped because the derivation changed: a V1-labelled key must never be
# silently reinterpreted. No V1 key is persisted in population/**.
CONTENT_KEY_ALGORITHM_ID = "SALIX-CONTENT-IDENTITY-KEY-V2"

UNFITTED_TOKEN = "NONE"

SUBKEY_DIMENSIONS = {
    "DEFINITION_SEMANTICS": (
        "normalized_definition_graph",
        "dependency_closure",
        "parameters",
        "declared_normalization",
    ),
    "CAUSAL_TIME": (
        "causal_time_semantics",
        "completion_semantics",
        "availability_class",
    ),
    "PROVENANCE_SOURCE": (
        "source_provider",
        "price_basis",
        "data_vintage_mode",
    ),
    "SCOPE_ELIGIBILITY": (
        "instrument_applicability",
        "timeframe",
        "scope_universe",
    ),
    "FITTED_LEARNED_STATE": (
        "fitted_state",
    ),
}

# INSTRUMENT IDENTITY RULE — frozen Tracker five-dimension model + Composer
# §39.4 (verified at source, Composer V9 line 2054):
#   "INSTRUMENT / UNIVERSE / SCOPE difference = PAYLOAD_BINDING unless
#    semantics change; if semantics change or are unclear, REVIEW_REQUIRED."
# Frozen Tracker Core: SCOPE / ELIGIBILITY-DEFINITION holds instrument only
# "where encoded in the governed feature definition".
#
# So the bound instrument is ALWAYS declared (it is binding/lineage), but it
# becomes identity content only when the definition itself declares that its
# semantics are instrument-specific. Unclear applicability yields no key.
INSTRUMENT_AGNOSTIC = "INSTRUMENT_AGNOSTIC"
INSTRUMENT_SPECIFIC = "INSTRUMENT_SPECIFIC"
INSTRUMENT_APPLICABILITY_VALUES = (INSTRUMENT_AGNOSTIC, INSTRUMENT_SPECIFIC)

# Declared on every payload, but identity content only conditionally.
BINDING_DIMENSIONS = ("instrument",)

# DC-006R (CR015 H-1). DC-006 V2 fixed only the DIRECT bound-instrument field.
# An instrument token could still enter identity through other fields, so:
#
#   SEMANTIC_APPLICABILITY_SCOPE = identity content. Carried by the existing
#       `scope_universe` dimension (name kept for catalogue compatibility):
#       the population a definition's SEMANTICS apply to, e.g. "FX_METALS".
#   BOUND_UNIVERSE = binding / lineage. Optional `bound_universe`: the concrete
#       runtime universe a request is bound to. Never hashed into any subkey.
SEMANTIC_APPLICABILITY_SCOPE_DIMENSION = "scope_universe"
BOUND_UNIVERSE_DIMENSION = "bound_universe"

# Governed canonical-row representation of an INSTRUMENT_AGNOSTIC, UNFITTED
# definition (CR015 M-1): the row's semantic instrument scope is ANY, never
# the first runtime binding. The concrete bound instrument lives in lookup and
# claim lineage (bound_instrument).
AGNOSTIC_INSTRUMENT_SCOPE = "ANY"

# INSTRUMENT-TOKEN LEAKAGE (fail closed, never stripped).
# For INSTRUMENT_AGNOSTIC definitions every identity-bearing field below must
# be instrument-neutral. Time semantics must name the server/feed clock, not a
# symbol ("SALIX-BROKER-UTC-TRANSITION-V1", not "...-XAUUSD-..."); dependencies
# must be role references ("BOUND_ROLE:close"), not "XAUUSD.close". A leaked
# token is REVIEW_REQUIRED: the field is NOT rewritten, because silently
# stripping it could erase meaningful semantics.
#
# DETECTOR BOUNDARY (declared): lexical. It catches the payload's own bound
# instrument anywhere in a field, any currency/metal PAIR symbol (6-letter
# token, 6-letter prefix of a longer token such as "XAUUSDm", or two adjacent
# code tokens such as "XAU/USD"), metal codes and metal names. It cannot catch
# an arbitrary alias ("CABLE") or an unknown symbology.
LEAKAGE_CHECKED_DIMENSIONS = (
    "normalized_definition_graph", "dependency_closure", "parameters",
    "declared_normalization", "causal_time_semantics", "completion_semantics",
    "availability_class", "source_provider", "price_basis",
    "data_vintage_mode", "timeframe", "scope_universe",
)
_CURRENCY_CODES = frozenset("""
USD EUR JPY GBP AUD NZD CAD CHF SEK NOK DKK PLN HUF CZK TRY ZAR MXN BRL CNY CNH
HKD SGD INR KRW TWD THB IDR MYR PHP RUB ILS SAR AED KWD QAR BHD OMR CLP COP PEN
ARS RON BGN HRK ISK UAH KZT EGP NGN KES MAD VND PKR BDT LKR
XAU XAG XPT XPD BTC ETH
""".split())
_METAL_TOKENS = frozenset({"XAU", "XAG", "XPT", "XPD",
                           "GOLD", "SILVER", "PLATINUM", "PALLADIUM"})


def _strings_in(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for k, v in value.items():
            yield str(k)
            yield from _strings_in(v)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for v in value:
            yield from _strings_in(v)
    elif value is not None and not isinstance(value, (bool, int, float)):
        yield str(value)


def _is_pair(token: str) -> bool:
    return (len(token) >= 6 and token[:3] in _CURRENCY_CODES
            and token[3:6] in _CURRENCY_CODES)


def instrument_token_leaks(value: Any, bound_instrument: Any) -> Tuple[str, ...]:
    """Instrument tokens found in `value`. Empty tuple = instrument-neutral."""
    bound = re.sub(r"[^A-Z0-9]", "", str(bound_instrument or "").upper())
    if bound == AGNOSTIC_INSTRUMENT_SCOPE:
        bound = ""
    found = []
    for text in _strings_in(value):
        text = unicodedata.normalize("NFKC", text).upper()
        tokens = re.findall(r"[A-Z0-9]+", text)
        if bound and bound in re.sub(r"[^A-Z0-9]", "", text):
            found.append(bound)
        for i, tok in enumerate(tokens):
            if _is_pair(tok) or tok in _METAL_TOKENS:
                found.append(tok)
            if (i + 1 < len(tokens) and tok in _CURRENCY_CODES
                    and tokens[i + 1] in _CURRENCY_CODES):
                found.append(tok + tokens[i + 1])
    return tuple(dict.fromkeys(found))

REQUIRED_DIMENSIONS = tuple(
    name for dims in SUBKEY_DIMENSIONS.values() for name in dims
) + BINDING_DIMENSIONS

# Dimensions whose collection semantics are declared UNORDERED. A dependency
# closure is a set: two orderings of the same closure are the same content and
# must not split into two identities.
UNORDERED_DIMENSIONS = ("dependency_closure",)

# Fitted-state content. Anything outside this list is process provenance.
FITTED_CONTENT_FIELDS = (
    "fitted_parameters",
    "fitting_window",
    "training_data_binding",
    "training_vintage",
    "fitting_method",
    "fitting_method_version",
    "acceptance_criteria",
)

# Never permitted anywhere in declared content, at any nesting depth.
FORBIDDEN_IDENTITY_KEYS = (
    "feature_id",
    "feature_version",
    "canonical_feature_id",
)
FORBIDDEN_PROCESS_KEYS = (
    "research_attempt_id",
    "attempt_id",
    "run_id",
    "ledger_ref",
    "operator",
    "timestamp",
    "job_name",
)


class ContentEncodingError(ValueError):
    """Raised when declared content cannot be deterministically encoded."""


def _encode(value: Any, *, unordered: bool = False) -> Any:
    """Type-tagged recursive encoding.

    Tags prevent the collapses an untyped str() produces: 1 vs "1",
    True vs "True", 1.0 vs "1.0". Tags also prevent the splits: list vs
    tuple, and nested mapping key order.
    """
    if value is None:
        return {"t": "null"}
    if isinstance(value, bool):
        return {"t": "bool", "v": value}
    if isinstance(value, int):
        return {"t": "int", "v": str(value)}
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ContentEncodingError("NON_FINITE_NUMERIC_REJECTED")
        if value == 0.0:
            value = 0.0  # collapse -0.0 to 0.0
        return {"t": "float", "v": repr(float(value))}
    if isinstance(value, str):
        return {"t": "str", "v": unicodedata.normalize("NFC", value)}
    if isinstance(value, Mapping):
        # GOVERNED RULE: mapping keys are STRINGS ONLY, explicitly.
        # Arbitrary keys are never coerced through str(): that would destroy
        # key type identity while values keep theirs, so {1:"x"} and {"1":"x"}
        # would collapse. Non-string keys are rejected, not stringified.
        items = []
        seen = {}
        for k, v in value.items():
            if not isinstance(k, str):
                raise ContentEncodingError(
                    "NON_STRING_MAPPING_KEY_REJECTED:" + type(k).__name__)
            normalized_key = unicodedata.normalize("NFC", k)
            if normalized_key in seen and seen[normalized_key] != k:
                # Two distinct source keys that NFC-normalize to one key would
                # silently overwrite each other. Ambiguity is rejected.
                raise ContentEncodingError(
                    "UNICODE_NORMALIZED_KEY_COLLISION:" + normalized_key)
            seen[normalized_key] = k
            items.append([normalized_key, _encode(v)])
        items.sort(key=lambda kv: kv[0])
        return {"t": "map", "v": items}
    if isinstance(value, (list, tuple)):
        encoded = [_encode(v) for v in value]
        if unordered:
            # GOVERNED RULE: an unordered dimension is a SET, not a multiset.
            # Duplicates are rejected as malformed declared content rather than
            # silently deduplicated, so a declaration error is surfaced instead
            # of being absorbed into an identity.
            rendered = [json.dumps(e, sort_keys=True) for e in encoded]
            if len(set(rendered)) != len(rendered):
                raise ContentEncodingError("DUPLICATE_ELEMENT_IN_UNORDERED_DIMENSION")
            encoded = [e for _, e in sorted(zip(rendered, encoded), key=lambda p: p[0])]
            return {"t": "set", "v": encoded}
        return {"t": "seq", "v": encoded}
    raise ContentEncodingError("UNSUPPORTED_CONTENT_TYPE:" + type(value).__name__)


def _hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _scan_forbidden(value: Any, errors: list) -> None:
    if isinstance(value, Mapping):
        for k, v in value.items():
            key = str(k).strip().lower()
            if key in FORBIDDEN_IDENTITY_KEYS:
                errors.append("CONTENT_IDENTITY_CONTAMINATION:" + key)
            if key in FORBIDDEN_PROCESS_KEYS:
                errors.append("CONTENT_PROCESS_PROVENANCE_REJECTED:" + key)
            _scan_forbidden(v, errors)
    elif isinstance(value, (list, tuple)):
        for v in value:
            _scan_forbidden(v, errors)


@dataclass(frozen=True)
class ContentIdentityKey:
    """Five governed subkeys plus a composite. No identity fields."""

    definition_semantics: str
    causal_time: str
    provenance_source: str
    scope_eligibility: str
    fitted_learned_state: str
    composite: str
    algorithm_id: str = CONTENT_KEY_ALGORITHM_ID

    def subkeys(self) -> Tuple[str, ...]:
        return (
            self.definition_semantics,
            self.causal_time,
            self.provenance_source,
            self.scope_eligibility,
            self.fitted_learned_state,
        )

    def exact_match(self, other: "ContentIdentityKey") -> bool:
        return bool(other) and self.composite == other.composite

    def definition_match(self, other: "ContentIdentityKey") -> bool:
        return bool(other) and self.definition_semantics == other.definition_semantics


def _fitted_errors(fitted: Any) -> list:
    """FITTED_LEARNED_STATE is either the single token NONE, or content."""
    errors = []
    if isinstance(fitted, str):
        if fitted != UNFITTED_TOKEN:
            errors.append("FITTED_STATE_TOKEN_INVALID:" + fitted)
        return errors
    if isinstance(fitted, Mapping):
        if not fitted:
            errors.append("FITTED_STATE_EMPTY_MAPPING_IS_NOT_NONE")
        unknown = sorted(
            str(k) for k in fitted.keys() if str(k) not in FITTED_CONTENT_FIELDS
        )
        if unknown:
            errors.append("FITTED_STATE_NON_CONTENT_FIELD:" + ",".join(unknown))
        return errors
    errors.append("FITTED_STATE_TYPE_INVALID")
    return errors


def completeness_errors(payload: Mapping[str, Any]) -> Tuple[str, ...]:
    """Every required dimension must be explicitly declared.

    Absence is never read as an empty value, and never as NONE.
    """
    errors = []
    declared = {str(k) for k in payload.keys()}

    for name in REQUIRED_DIMENSIONS:
        if name not in declared:
            errors.append("CONTENT_DIMENSION_MISSING:" + name)
            continue
        if name in ("dependency_closure", "parameters", "fitted_state"):
            continue
        value = payload.get(name)
        if value is None or (isinstance(value, str) and not value.strip()):
            errors.append("CONTENT_DIMENSION_EMPTY:" + name)

    if "fitted_state" in declared:
        errors.extend(_fitted_errors(payload.get("fitted_state")))

    if "instrument_applicability" in declared:
        applicability = payload.get("instrument_applicability")
        if applicability not in INSTRUMENT_APPLICABILITY_VALUES:
            # Unclear applicability must never silently choose a shared or a
            # split identity. It yields no key, so lookup cannot resolve and
            # the candidate is routed to review.
            errors.append("INSTRUMENT_APPLICABILITY_REVIEW_REQUIRED:" + str(applicability))
        instrument = payload.get("instrument")
        unfitted = payload.get("fitted_state") == UNFITTED_TOKEN
        if instrument == AGNOSTIC_INSTRUMENT_SCOPE:
            # ANY is the canonical-row scope of an agnostic UNFITTED definition
            # only. Specific semantics and learned state need a real binding.
            if applicability != INSTRUMENT_AGNOSTIC:
                errors.append("INSTRUMENT_SCOPE_ANY_REQUIRES_AGNOSTIC_APPLICABILITY")
            elif not unfitted:
                errors.append("FITTED_STATE_REQUIRES_CONCRETE_INSTRUMENT")
        if applicability == INSTRUMENT_AGNOSTIC:
            for name in LEAKAGE_CHECKED_DIMENSIONS:
                if name in declared:
                    for tok in instrument_token_leaks(payload.get(name), instrument):
                        errors.append("INSTRUMENT_TOKEN_LEAKAGE_REVIEW_REQUIRED:"
                                      + name + ":" + tok)

    _scan_forbidden(payload, errors)

    # Encoding rules are part of completeness: a payload that cannot be
    # canonically encoded has no key, and the reason is reported rather than
    # surfacing later as an opaque failure.
    if not errors:
        for name in REQUIRED_DIMENSIONS:
            try:
                _encode(payload.get(name), unordered=(name in UNORDERED_DIMENSIONS))
            except ContentEncodingError as exc:
                errors.append("CONTENT_ENCODING_ERROR:" + name + ":" + str(exc))
    return tuple(errors)


def build_content_identity_key(payload: Mapping[str, Any]):
    """Return (ContentIdentityKey | None, errors)."""
    errors = list(completeness_errors(payload))
    if errors:
        return None, tuple(errors)

    def _identity_fields(name: str) -> Tuple[str, ...]:
        dims = SUBKEY_DIMENSIONS[name]
        if name == "SCOPE_ELIGIBILITY" and payload.get("instrument_applicability") == INSTRUMENT_SPECIFIC:
            # Applicability is encoded in the governed definition: instrument
            # IS scope identity content.
            dims = dims + ("instrument",)
        if name == "FITTED_LEARNED_STATE" and payload.get("fitted_state") != UNFITTED_TOKEN:
            # Learned state is ALWAYS instrument-qualified, whatever the
            # definition's applicability: a fitted transform, calibrator or
            # cache may never silently cross instruments.
            dims = dims + ("instrument",)
        return dims

    def sub(name: str) -> str:
        dims = _identity_fields(name)
        try:
            body = {
                d: _encode(payload.get(d), unordered=(d in UNORDERED_DIMENSIONS))
                for d in dims
            }
        except ContentEncodingError as exc:
            raise
        return _hash(
            {
                "algorithm_id": CONTENT_KEY_ALGORITHM_ID,
                "encoding_id": ENCODING_ID,
                "encoding_version": ENCODING_VERSION,
                "subkey": name,
                "body": body,
            }
        )

    try:
        parts = {name: sub(name) for name in SUBKEY_DIMENSIONS}
    except ContentEncodingError as exc:
        return None, ("CONTENT_ENCODING_ERROR:" + str(exc),)

    composite = _hash(
        {
            "algorithm_id": CONTENT_KEY_ALGORITHM_ID,
            "subkeys": [parts[n] for n in SUBKEY_DIMENSIONS],
        }
    )
    return (
        ContentIdentityKey(
            definition_semantics=parts["DEFINITION_SEMANTICS"],
            causal_time=parts["CAUSAL_TIME"],
            provenance_source=parts["PROVENANCE_SOURCE"],
            scope_eligibility=parts["SCOPE_ELIGIBILITY"],
            fitted_learned_state=parts["FITTED_LEARNED_STATE"],
            composite=composite,
        ),
        (),
    )
