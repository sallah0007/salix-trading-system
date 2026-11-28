"""R40: a LABELLED TEST persistence adapter implementing the ObjectStore port over a directory, so SEPARATE OS processes can share one store (put_if_absent / put_if_match are atomic under one `flock` on the directory). NOT a provider, NOT durable-storage qualification (no fsync/ordering claims, no Postgres/S3 semantics). It must be wrapped in `SimulationStore` for any simulation carrier and is registered as an approved TEST adapter by its user (`approve_test_adapter`), never by default."""
import fcntl, hashlib, os, struct
class FileObjectStore:
    def __init__(self, root): self._r = str(root); os.makedirs(self._r, exist_ok=True); self._lk = os.path.join(self._r, ".lock")
    def _p(self, key): return os.path.join(self._r, "o_" + hashlib.sha256(key.encode("utf-8")).hexdigest())        # R43: a fixed-length file name (hex-encoding the key exceeded the 255-byte name limit for long content-addressed keys); the key itself is stored INSIDE the file
    def _locked(self):
        f = open(self._lk, "a+"); fcntl.flock(f, fcntl.LOCK_EX); return f
    def _read(self, p, key=None):
        try:
            with open(p, "rb") as f: b = f.read()
        except FileNotFoundError: return None
        etag, kl = struct.unpack(">QI", b[:12]); k = b[12:12 + kl].decode("utf-8")
        if key is not None and k != key: raise OSError("file object key mismatch")          # a name collision can never return another key's bytes
        return b[12 + kl:], etag
    def get(self, key):
        with self._locked(): return self._read(self._p(key), key)
    def _write(self, p, key, data, etag):
        t = p + ".tmp"; kb = key.encode("utf-8")
        with open(t, "wb") as f: f.write(struct.pack(">QI", etag, len(kb)) + kb + bytes(data))
        os.replace(t, p)
    def put_if_absent(self, key, data):
        with self._locked():
            p = self._p(key)
            if self._read(p, key) is not None: return False
            self._write(p, key, data, 1); return True
    def put_if_match(self, key, data, etag):
        with self._locked():
            p = self._p(key); cur = self._read(p, key)
            if cur is None or cur[1] != etag: return False
            self._write(p, key, data, etag + 1); return True
    def list_prefix(self, prefix):
        with self._locked():
            out = []
            for n in os.listdir(self._r):
                if not n.startswith("o_") or n.endswith(".tmp"): continue
                with open(os.path.join(self._r, n), "rb") as f: h = f.read(12); kl = struct.unpack(">QI", h)[1]; k = f.read(kl).decode("utf-8")
                if k.startswith(prefix): out.append(k)
            return sorted(out)
