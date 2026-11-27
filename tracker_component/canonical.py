import hashlib, json

class CanonicalError(ValueError):
    pass

def _check(o, path="$"):
    if o is None or isinstance(o, (str, bool, int)):
        return
    if isinstance(o, float):
        raise CanonicalError("float not permitted at %s" % path)
    if isinstance(o, (list, tuple)):
        for i, v in enumerate(o):
            _check(v, "%s[%d]" % (path, i))
        return
    if isinstance(o, dict):
        for k, v in o.items():
            if not isinstance(k, str):
                raise CanonicalError("non-string key at %s" % path)
            _check(v, "%s.%s" % (path, k))
        return
    raise CanonicalError("unsupported type %s at %s" % (type(o).__name__, path))

def canonical_json(o) -> str:
    _check(o)
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
