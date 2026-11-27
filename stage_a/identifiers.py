"""Instrument/timeframe-scoped identifiers (TR-15). Equal feature id/version in different
instrument or timeframe scopes can never share a key, cache entry or namespace."""
import re
from dataclasses import dataclass
from .errors import Refusal

_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,63}$")

def check_token(value, name):
    if not isinstance(value, str) or not _TOKEN.match(value):
        raise Refusal("%s=%r" % (name, value), code="BAD_IDENTIFIER_TOKEN")
    return value

@dataclass(frozen=True)
class Scope:
    instrument: str
    timeframe: str
    def __post_init__(self):
        check_token(self.instrument, "instrument")
        check_token(self.timeframe, "timeframe")
    def key(self) -> str:
        return "%s/%s" % (self.instrument, self.timeframe)

@dataclass(frozen=True)
class FeatureKey:
    scope: Scope
    feature_id: str
    feature_version: str
    def __post_init__(self):
        check_token(self.feature_id, "feature_id")
        check_token(self.feature_version, "feature_version")
    def key(self) -> str:
        return "%s/%s/%s" % (self.scope.key(), self.feature_id, self.feature_version)
    def namespace(self) -> str:
        """One authority namespace (journal + HEAD) per instrument/timeframe/feature id; versions are transitions within it."""
        return "%s/%s" % (self.scope.key(), self.feature_id)
