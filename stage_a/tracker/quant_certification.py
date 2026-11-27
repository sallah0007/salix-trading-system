"""Component-side certification: checks the producer-side kernel itself can make. It is NOT independent evidence;
the independent verifier re-derives the same facts separately and the pipeline requires both."""
from dataclasses import dataclass
from typing import Tuple
import copy, random
from ..errors import Refusal
from ..storage.byte_primitives import canonical_bytes, domain_hash
from ..composer.expression.manifest import Manifest
from ..composer.expression.hashing import manifest_hash
from ..composer.expression.capability import check_declared
from ..composer.expression.evaluator import evaluate, check_series

CERT_DOMAIN = "SALIX_QUANT_CERTIFICATION_V1"

@dataclass(frozen=True)
class Certification:
    status: str          # CERTIFIED | REFUSED
    checks: Tuple[Tuple[str, bool], ...]
    reasons: Tuple[str, ...]
    cert_hash: str

def certify(manifest: Manifest, probe: dict) -> Certification:
    checks, reasons = [], []
    def chk(name, fn):
        try:
            ok = bool(fn())
            why = ""
        except Refusal as e:
            ok, why = False, e.code
        checks.append((name, ok))
        if not ok:
            reasons.append(name + (":" + why if why else ""))
    chk("operator_set_and_capability_declared_equals_extracted", lambda: check_declared(manifest))
    def perm():
        d = copy.deepcopy(manifest.data)
        rng = random.Random(7)
        rng.shuffle(d["nodes"]); rng.shuffle(d["inputs"]); rng.shuffle(d["declared_opcodes"])
        rng.shuffle(d["declared_capabilities"])
        return manifest_hash(Manifest.from_dict(d)) == manifest_hash(manifest)
    chk("declaration_order_invariance", perm)
    def dup():
        d = copy.deepcopy(manifest.data)
        d["nodes"].append(dict(d["nodes"][0]))
        try:
            Manifest.from_dict(d)
        except Refusal:
            return True
        return False
    chk("duplicate_node_refused", dup)
    def _outcome(series):
        """Evaluation outcome as comparable data: values, or the arithmetic refusal code (domain failure / non-finite is a deterministic outcome)."""
        try:
            return ("OK", evaluate(manifest, series))
        except Refusal as e:
            if e.code not in ("NON_FINITE_RESULT", "DOMAIN_DIV_ZERO", "DOMAIN_SQRT_NEGATIVE"): raise
            return ("REFUSED", e.code)
    def deterministic():
        return _outcome(probe) == _outcome(probe)
    chk("repeat_evaluation_identical", deterministic)
    def causal():
        # truncating the future must not change any earlier output value
        n = check_series(manifest, probe)
        cut = n // 2
        def prefix_ok(series):
            full = _outcome(series)
            if full[0] != "OK":
                return None                                        # no values to compare on this series
            part = _outcome({k: v[:cut] for k, v in series.items()})
            return part[0] == "OK" and full[1][:cut] == part[1]
        r = prefix_ok(probe)
        if r is None:   # the edge probe hit an arithmetic refusal: prove causality on a domain-safe transform of the SAME probe (positive, None pattern kept)
            r = prefix_ok({k: [None if x is None else abs(x) + 1.0 for x in v] for k, v in probe.items()})
        return bool(r)                                             # still None (refused even when domain-safe) => not proven => False
    chk("prefix_causality", causal)
    status = "CERTIFIED" if all(ok for _, ok in checks) else "REFUSED"
    h = domain_hash(CERT_DOMAIN, canonical_bytes({"status": status, "checks": [[a, b] for a, b in checks],
                                                  "manifest_hash": manifest_hash(manifest)}))
    return Certification(status, tuple(checks), tuple(reasons), h)
