"""Canonical bytes for a validated manifest. Keyed canonical ordering: object keys sorted, nodes by id, inputs and
declarations sorted, fit_refs by generation; args order preserved (it is semantic). No floats anywhere:
binary64 constants are 16-hex-digit big-endian IEEE bit patterns."""
import json
from ...errors import Refusal
from .manifest import Manifest

def _dump(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")

def encode_manifest(m: Manifest) -> bytes:
    if not isinstance(m, Manifest):
        raise Refusal("unvalidated manifest", code="UNVALIDATED_MANIFEST")
    return _dump(m.data)

def encode_graph(m: Manifest) -> bytes:
    """Topology + operators + window params only; const values and input names excluded."""
    g = [{k: v for k, v in n.items() if k in ("id", "op", "args", "n")} for n in m.data["nodes"]]
    return _dump({"nodes": g, "output": m.data["output"]})

def encode_program(m: Manifest) -> bytes:
    """Everything that determines computed values; excludes identity metadata and declarations."""
    d = m.data
    return _dump({"inputs": d["inputs"], "nodes": d["nodes"], "output": d["output"], "fit_refs": d["fit_refs"]})
