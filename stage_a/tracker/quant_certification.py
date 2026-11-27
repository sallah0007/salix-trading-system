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
    def deterministic():
        a = evaluate(manifest, probe)
        b = evaluate(manifest, probe)
        return a == b
    chk("repeat_evaluation_identical", deterministic)
    def causal():
        # truncating the future must not change any earlier output value
        n = check_series(manifest, probe)
        full = evaluate(manifest, probe)
        cut = n // 2
        part = evaluate(manifest, {k: v[:cut] for k, v in probe.items()})
        return full[:cut] == part
    chk("prefix_causality", causal)
    status = "CERTIFIED" if all(ok for _, ok in checks) else "REFUSED"
    h = domain_hash(CERT_DOMAIN, canonical_bytes({"status": status, "checks": [[a, b] for a, b in checks],
                                                  "manifest_hash": manifest_hash(manifest)}))
    return Certification(status, tuple(checks), tuple(reasons), h)
