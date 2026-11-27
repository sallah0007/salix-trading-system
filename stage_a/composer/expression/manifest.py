from dataclasses import dataclass
from .schema import validate_manifest

@dataclass(frozen=True)
class Manifest:
    """Validated, normalised manifest (declaration-order invariant). Construct only via from_dict."""
    data: dict

    @staticmethod
    def from_dict(d) -> "Manifest":
        return Manifest(validate_manifest(d))

    @property
    def feature_id(self): return self.data["feature_id"]
    @property
    def feature_version(self): return self.data["feature_version"]
    @property
    def instrument(self): return self.data["instrument"]
    @property
    def timeframe(self): return self.data["timeframe"]
