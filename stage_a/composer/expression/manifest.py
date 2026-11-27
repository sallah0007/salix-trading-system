from dataclasses import dataclass
from .schema import validate_manifest

@dataclass(frozen=True)
class Manifest:
    """Validated, normalised manifest (declaration-order invariant). Construct only via from_dict."""
    data: dict

    @staticmethod
    def from_dict(d, ceilings=None) -> "Manifest":
        """ceilings: validated governed ceilings (ceilings.check_ceilings). None = structural parse only (no bound is assumed)."""
        m = Manifest(validate_manifest(d))
        if ceilings is not None:
            from .ceilings import check_program_within
            check_program_within(m, ceilings)
        return m

    @property
    def feature_id(self): return self.data["feature_id"]
    @property
    def feature_version(self): return self.data["feature_version"]
    @property
    def instrument(self): return self.data["instrument"]
    @property
    def timeframe(self): return self.data["timeframe"]
