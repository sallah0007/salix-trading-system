"""Byte-level primitives shared by storage/coordination. (The independent verifier deliberately does not use these.)"""
import hashlib, json

def canonical_bytes(obj) -> bytes:
    def chk(o, p="$"):
        if o is None or isinstance(o, (str, bool, int)):
            return
        if isinstance(o, float):
            raise ValueError("float not permitted at %s" % p)
        if isinstance(o, (list, tuple)):
            for i, v in enumerate(o):
                chk(v, "%s[%d]" % (p, i))
            return
        if isinstance(o, dict):
            for k, v in o.items():
                if not isinstance(k, str):
                    raise ValueError("non-string key at %s" % p)
                chk(v, p + "." + k)
            return
        raise ValueError("unsupported type at %s" % p)
    chk(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")

def domain_hash(domain: str, payload: bytes) -> str:
    return hashlib.sha256(domain.encode("ascii") + b"\x00" + payload).hexdigest()
