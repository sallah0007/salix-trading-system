from dataclasses import dataclass
from typing import Tuple
from .manifest import Manifest
from .canonical_encoding import encode_manifest
from .hashing import manifest_hash, graph_hash, program_hash
from .capability import extract_opcodes, required_capabilities

@dataclass(frozen=True)
class ExpressionArtifact:
    manifest_bytes: bytes
    manifest_hash: str
    graph_hash: str
    program_hash: str
    opcodes: Tuple[str, ...]
    capabilities: Tuple[str, ...]

def build_artifact(m: Manifest) -> ExpressionArtifact:
    ops = extract_opcodes(m)
    return ExpressionArtifact(encode_manifest(m), manifest_hash(m), graph_hash(m), program_hash(m),
                              tuple(ops), tuple(required_capabilities(ops)))
