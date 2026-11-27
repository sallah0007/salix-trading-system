"""INDEPENDENT hash derivations. Domain strings are re-declared here on purpose (not imported)."""
import hashlib

_D_MANIFEST = "SALIX_EXPR_MANIFEST_V1"
_D_GRAPH = "SALIX_EXPR_GRAPH_V1"
_D_PROGRAM = "SALIX_EXPR_PROGRAM_V1"
_D_MATERIALIZATION = "SALIX_MATERIALIZATION_V1"       # INTERNAL PROTOTYPE record domain (re-declared; not a normative byte layout)

def _h(domain, payload):
    x = hashlib.new("sha256")
    x.update(domain.encode("ascii"))
    x.update(b"\x00")
    x.update(payload)
    return x.hexdigest()

def materialization_digest(record, enc_bytes):
    """Re-derives the prototype record hash over every record field except the hash itself."""
    return _h(_D_MATERIALIZATION, enc_bytes({k: v for k, v in record.items() if k != "materialization_hash"}))

def manifest_digest(canonical_bytes):
    return _h(_D_MANIFEST, canonical_bytes)

def graph_digest(parsed, enc_bytes):
    nodes = []
    for n in parsed["nodes"]:
        nodes.append({k: n[k] for k in ("id", "op", "args", "n") if k in n})
    return _h(_D_GRAPH, enc_bytes({"nodes": nodes, "output": parsed["output"]}))

def program_digest(parsed, enc_bytes):
    return _h(_D_PROGRAM, enc_bytes({"inputs": parsed["inputs"], "nodes": parsed["nodes"],
                                     "output": parsed["output"], "fit_refs": parsed["fit_refs"]}))
