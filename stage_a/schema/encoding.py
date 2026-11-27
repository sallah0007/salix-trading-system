"""Frozen Typed Schema Annex V1.2 §I primitive byte writers (producer/materializer side).
All integers big-endian. Optional = 0x00 | 0x01+value. Lists = UINT32 count + elements in declared order.

OPEN (D3): the Annex says ENUM and REF_TYPE are 'closed numeric code under schema version' but the sources read
define NO code tables. CodeTables must therefore be supplied by an admitted source; until then every encoding made
with an unadmitted table is PROVISIONAL and the pipeline refuses to treat it as canonical."""
import struct
from dataclasses import dataclass
from typing import Dict, Optional
from ..errors import Refusal

@dataclass(frozen=True)
class CodeTables:
    enums: Dict[str, Dict[str, int]]          # enum name -> {symbol: UINT16 code}
    ref_types: Dict[str, int]                 # ref type name -> UINT16 code
    admitted_source: Optional[str] = None     # None = NOT admitted (test/provisional)
    @property
    def provisional(self):
        return self.admitted_source is None

@dataclass(frozen=True)
class Ref:
    ref_type: str
    target_id: bytes
    target_version: bytes = b""
    target_hash: Optional[bytes] = None       # 32 raw bytes or None

def _chk_int(x, lo, hi, name):
    if isinstance(x, bool) or not isinstance(x, int) or not lo <= x <= hi:
        raise Refusal("%s=%r" % (name, x), code="INTEGER_OUT_OF_RANGE")
    return x

def u8(x): return struct.pack(">B", _chk_int(x, 0, 255, "u8"))
def u16(x): return struct.pack(">H", _chk_int(x, 0, 65535, "u16"))
def u32(x): return struct.pack(">I", _chk_int(x, 0, 2**32 - 1, "u32"))
def u64(x): return struct.pack(">Q", _chk_int(x, 0, 2**64 - 1, "u64"))
def i64(x): return struct.pack(">q", _chk_int(x, -2**63, 2**63 - 1, "i64"))
def boolean(x):
    if x is not True and x is not False:
        raise Refusal(repr(x), code="NOT_A_BOOL")
    return b"\x01" if x else b"\x00"
timestamp_utc = i64

def byte_string(b, max_len=2**32 - 1):
    if not isinstance(b, (bytes, bytearray)) or len(b) > max_len:
        raise Refusal("byte string", code="BAD_BYTE_STRING")
    return u32(len(b)) + bytes(b)

def version_id(s):
    if not isinstance(s, str):
        raise Refusal(repr(s), code="BAD_VERSION_ID")
    b = s.encode("utf-8")
    if not 1 <= len(b) <= 128:
        raise Refusal(s, code="VERSION_ID_LENGTH")
    return u32(len(b)) + b

def id128(b):
    if not isinstance(b, (bytes, bytearray)) or len(b) != 16:
        raise Refusal("ID128 must be 16 raw bytes", code="BAD_ID128")
    return bytes(b)

def hash256(b):
    if not isinstance(b, (bytes, bytearray)) or len(b) != 32:
        raise Refusal("HASH256 must be 32 raw bytes", code="BAD_HASH256")
    return bytes(b)

def binary64_bits(b):
    if not isinstance(b, (bytes, bytearray)) or len(b) != 8:
        raise Refusal("BINARY64_BITS must be 8 raw bytes", code="BAD_BINARY64_BITS")
    return bytes(b)

def enum(tables: CodeTables, name, symbol):
    try:
        return u16(tables.enums[name][symbol])
    except KeyError:
        raise Refusal("%s.%s" % (name, symbol), code="UNKNOWN_ENUM_CODE")

def ref(tables: CodeTables, r: Ref):
    if r.ref_type not in tables.ref_types:
        raise Refusal(r.ref_type, code="UNKNOWN_REF_TYPE")
    out = u16(tables.ref_types[r.ref_type]) + byte_string(r.target_id) + byte_string(r.target_version)
    if r.target_hash is None:
        return out + u8(0)
    return out + u8(1) + hash256(r.target_hash)

def optional(enc):
    return b"\x00" if enc is None else b"\x01" + enc

def lst(encs):
    return u32(len(encs)) + b"".join(encs)

def tagged_enum_or_ref(tables, v):
    """v = ('ENUM', enum_name, symbol) | ('REF', Ref)"""
    if v[0] == "ENUM":
        return b"\x01" + enum(tables, v[1], v[2])
    if v[0] == "REF":
        return b"\x02" + ref(tables, v[1])
    raise Refusal(repr(v[0]), code="BAD_TAGGED_UNION")
