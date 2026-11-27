"""Admitted opcode table (generic kernel). SPEC (this implementation's definition; source admission OPEN):
  all values are IEEE-754 binary64 or UNDEFINED(None); any UNDEFINED argument gives UNDEFINED.
  div: divisor == 0.0 -> UNDEFINED.  sqrt: x < 0 -> UNDEFINED.  log: x <= 0 -> UNDEFINED.
  lag(x, n)           : value of x at t-n (UNDEFINED while t < n).
  rolling_sum(x, n)   : s = 0.0; for the n values ending at t, oldest to newest: s = s + v; UNDEFINED if any undefined/short.
  rolling_mean(x, n)  : rolling_sum / float(n).
  A finite operation that overflows to inf/nan is a REFUSAL (non-finite), never a value.
Opcodes outside this table are refused; EMULATED ones are refused distinctly (no silent software emulation)."""
from collections import namedtuple

OpSpec = namedtuple("OpSpec", "arity windowed capability")

OPCODES = {
    "input":        OpSpec(0, False, "INPUT_SERIES"),
    "const":        OpSpec(0, False, "CONST_BINARY64"),
    "add":          OpSpec(2, False, "ARITH_BINARY64"),
    "sub":          OpSpec(2, False, "ARITH_BINARY64"),
    "mul":          OpSpec(2, False, "ARITH_BINARY64"),
    "div":          OpSpec(2, False, "ARITH_BINARY64"),
    "min":          OpSpec(2, False, "ARITH_BINARY64"),
    "max":          OpSpec(2, False, "ARITH_BINARY64"),
    "neg":          OpSpec(1, False, "ARITH_BINARY64"),
    "abs":          OpSpec(1, False, "ARITH_BINARY64"),
    "sqrt":         OpSpec(1, False, "ELEMENTARY_BINARY64"),
    "log":          OpSpec(1, False, "ELEMENTARY_BINARY64"),
    "lag":          OpSpec(1, True, "WINDOW_LAG"),
    "rolling_sum":  OpSpec(1, True, "WINDOW_ROLLING"),
    "rolling_mean": OpSpec(1, True, "WINDOW_ROLLING"),
}
EMULATED = frozenset({"exp", "pow", "tanh", "sin", "cos", "tan", "erf"})
