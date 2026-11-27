"""Event/Context causal SIDE EDGE guard (TR-12). Declared edge only; Context ingestion stays independent of feature construction.
BLOCKED (not built): any Event/Context field layout. The plan states the implementation may not invent layouts; they are owned by
News Hub Event/Context Delivery Contract V2, Decision Context V4 and Connected Contract V0.38 H2, none of which is admitted
into this repository. This module only refuses undeclared Context use."""
from ..errors import Refusal

def assert_declared(declared_edges, used_edges):
    """Both are iterables of (feature_id, context_ref_id). Any used edge not declared is refused; nothing is inferred."""
    d = set(declared_edges)
    undeclared = [u for u in used_edges if u not in d]
    if undeclared:
        raise Refusal(repr(undeclared[0]), code="UNDECLARED_CONTEXT_EDGE")
    return tuple(used_edges)
