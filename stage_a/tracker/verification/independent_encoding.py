"""INDEPENDENT canonical encoder/parser for the manifest byte format. Hand-written; imports nothing from
stage_a.composer or stage_a.storage and does not call json.dumps. Format (V1): ASCII JSON, keys sorted bytewise,
no whitespace, ints decimal, strings escaped as: \\" \\\\ \\b \\f \\n \\r \\t, any other char outside space..~ as \\uXXXX
(lower-case hex, UTF-16 surrogate pairs above U+FFFF)."""
import json

_SHORT = {'"': '\\"', "\\": "\\\\", "\b": "\\b", "\f": "\\f", "\n": "\\n", "\r": "\\r", "\t": "\\t"}

def _esc(s):
    out = ['"']
    for ch in s:
        if ch in _SHORT:
            out.append(_SHORT[ch])
        elif " " <= ch <= "~":
            out.append(ch)
        else:
            cp = ord(ch)
            if cp > 0xFFFF:
                cp -= 0x10000
                out.append("\\u%04x\\u%04x" % (0xD800 + (cp >> 10), 0xDC00 + (cp & 0x3FF)))
            else:
                out.append("\\u%04x" % cp)
    out.append('"')
    return "".join(out)

def enc(o):
    if o is None:
        return "null"
    if o is True:
        return "true"
    if o is False:
        return "false"
    if isinstance(o, int):
        return str(int(o))
    if isinstance(o, str):
        return _esc(o)
    if isinstance(o, (list, tuple)):
        return "[" + ",".join(enc(x) for x in o) + "]"
    if isinstance(o, dict):
        keys = sorted(o)
        for k in keys:
            if not isinstance(k, str):
                raise ValueError("non-string key")
        return "{" + ",".join(_esc(k) + ":" + enc(o[k]) for k in keys) + "}"
    raise ValueError("unencodable type %s" % type(o).__name__)

def enc_bytes(o):
    return enc(o).encode("ascii")

def _no_dupes(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise ValueError("duplicate key %s" % k)
        d[k] = v
    return d

def parse(raw: bytes):
    """Strict parse: duplicate keys, floats, NaN/Infinity tokens are rejected."""
    def bad_const(x):
        raise ValueError("non-finite token")
    def no_float(x):
        raise ValueError("float literal")
    return json.loads(raw.decode("ascii"), object_pairs_hook=_no_dupes, parse_constant=bad_const, parse_float=no_float)
