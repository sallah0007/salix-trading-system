import hashlib
from .canonical_encoding import encode_manifest, encode_graph, encode_program

MANIFEST_DOMAIN = b"SALIX_EXPR_MANIFEST_V1\x00"
GRAPH_DOMAIN = b"SALIX_EXPR_GRAPH_V1\x00"
PROGRAM_DOMAIN = b"SALIX_EXPR_PROGRAM_V1\x00"

def manifest_hash(m): return hashlib.sha256(MANIFEST_DOMAIN + encode_manifest(m)).hexdigest()
def graph_hash(m): return hashlib.sha256(GRAPH_DOMAIN + encode_graph(m)).hexdigest()
def program_hash(m): return hashlib.sha256(PROGRAM_DOMAIN + encode_program(m)).hexdigest()
