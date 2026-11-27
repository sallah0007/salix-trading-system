"""Operator-set and capability extraction (TR-09). Declared == extracted, both ways; provider must support all."""
from ...errors import Refusal
from .opcodes import OPCODES
from .manifest import Manifest

PROVIDED = frozenset(spec.capability for spec in OPCODES.values())

def extract_opcodes(m: Manifest):
    return sorted({n["op"] for n in m.data["nodes"]})

def required_capabilities(opcodes):
    return sorted({OPCODES[o].capability for o in opcodes})

def check_declared(m: Manifest, provided=PROVIDED):
    ops = extract_opcodes(m)
    caps = required_capabilities(ops)
    if m.data["declared_opcodes"] != ops:
        raise Refusal("declared=%s extracted=%s" % (m.data["declared_opcodes"], ops), code="OPCODE_DECLARATION_MISMATCH")
    if m.data["declared_capabilities"] != caps:
        raise Refusal("declared=%s extracted=%s" % (m.data["declared_capabilities"], caps), code="CAPABILITY_DECLARATION_MISMATCH")
    missing = [c for c in caps if c not in provided]
    if missing:
        raise Refusal(str(missing), code="CAPABILITY_NOT_PROVIDED")
    return ops, caps
