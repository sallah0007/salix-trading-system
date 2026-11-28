"""Stateful materializer: stores the content-addressed artifact and records what it computed on the verifier-authored
probe via BOTH a batch path and an incremental (bar-by-bar, per-node state) path. It does not certify, accept or publish."""
from ...errors import Refusal, IntegrityFailure
from ...storage.keys import artifact_key
from ...storage.byte_primitives import canonical_bytes, domain_hash
from ...identifiers import Scope, FeatureKey
from ...composer.expression.manifest import Manifest
from ...composer.expression.artifacts import build_artifact
from ...composer.expression.evaluator import evaluate, op_value, topo_order, check_series, check_constants, canon
import struct

MATERIALIZATION_DOMAIN = "SALIX_MATERIALIZATION_V1"
# Recorded error categories. Specific domain codes are collapsed to ONE category so that batch (node-major) and incremental (row-major)
# paths agree on the category even when two different domain failures exist in one probe (a mixed NON_FINITE/DOMAIN probe can still
# differ by order: that yields a verifier FAIL, never a false PASS).
_ERR_CATEGORY = {"NON_FINITE_RESULT": "NON_FINITE", "DOMAIN_DIV_ZERO": "DOMAIN_FAILURE", "DOMAIN_SQRT_NEGATIVE": "DOMAIN_FAILURE"}

def _bits(x):
    return None if x is None else struct.pack(">d", x).hex()

class IncrementalEvaluator:
    """Holds per-node value history; push() computes only the newest index."""
    def __init__(self, manifest: Manifest):
        self._m = manifest; check_constants(manifest)
        self._by = {n["id"]: n for n in manifest.data["nodes"]}
        self._order = topo_order(manifest)
        self._hist = {nid: [] for nid in self._by}
        self.n = 0
        self._lazy = any(n["op"] == "select" for n in self._by.values())     # R47: with select the incremental path is DEMAND-driven (same semantics as evaluate_lazy)
        self._rows, self._memo = [], {}

    def push(self, row: dict):
        if set(row) != set(self._m.data["inputs"]):
            raise Refusal("row inputs %s" % sorted(row), code="INPUT_SET_MISMATCH")
        check_series(self._m, {k: [v] for k, v in row.items()})
        t = self.n
        if self._lazy:
            self._rows.append({k: canon(v) for k, v in row.items()}); self.n += 1
            return self._demand(self._m.data["output"], t)
        for nid in self._order:
            node = self._by[nid]
            if node["op"] == "input":
                v = canon(row[node["name"]])
            else:
                v = op_value(node, t, lambda k, i: self._hist[k][i])
            self._hist[nid].append(v)
        self.n += 1
        return self._hist[self._m.data["output"]][t]

    def _demand(self, k, i):
        if i < 0 or i >= self.n: return None
        key = (k, i)
        if key not in self._memo:
            node = self._by[k]
            self._memo[key] = self._rows[i][node["name"]] if node["op"] == "input" else op_value(node, i, self._demand)
        return self._memo[key]

class StatefulMaterializer:
    def __init__(self, store):
        self._store = store

    def materialize(self, manifest: Manifest, probe: dict) -> dict:
        art = build_artifact(manifest)
        key = artifact_key(art.manifest_hash)
        if not self._store.put_if_absent(key, art.manifest_bytes):
            got = self._store.get(key)
            if got is None or got[0] != art.manifest_bytes:
                raise IntegrityFailure("artifact key %s holds different bytes" % key)
        try:
            batch = [_bits(x) for x in evaluate(manifest, probe)]
        except Refusal as e:
            if e.code not in _ERR_CATEGORY: raise
            batch = {"error": _ERR_CATEGORY[e.code]}
        inc = IncrementalEvaluator(manifest)
        try:
            length = len(next(iter(probe.values())))
            incremental = [_bits(inc.push({k: v[t] for k, v in probe.items()})) for t in range(length)]
        except Refusal as e:
            if e.code not in _ERR_CATEGORY: raise
            incremental = {"error": _ERR_CATEGORY[e.code]}
        fk = FeatureKey(Scope(manifest.instrument, manifest.timeframe), manifest.feature_id, manifest.feature_version)
        rec = {"feature_key": fk.key(), "feature_version": manifest.feature_version, "instrument": manifest.instrument,
               "timeframe": manifest.timeframe, "object_key": key, "manifest_hash": art.manifest_hash,
               "graph_hash": art.graph_hash, "program_hash": art.program_hash, "byte_length": len(art.manifest_bytes),
               "probe_batch": batch, "probe_incremental": incremental}
        rec["materialization_hash"] = domain_hash(MATERIALIZATION_DOMAIN, canonical_bytes(rec))
        return rec
