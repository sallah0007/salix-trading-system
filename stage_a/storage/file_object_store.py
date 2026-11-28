"""R40: a LABELLED TEST persistence adapter implementing the ObjectStore port over a directory, so SEPARATE OS processes can share one store (put_if_absent / put_if_match are atomic under one `flock` on the directory). NOT a provider, NOT durable-storage qualification (no fsync/ordering claims, no Postgres/S3 semantics). It must be wrapped in `SimulationStore` for any simulation carrier and is registered as an approved TEST adapter by its user (`approve_test_adapter`), never by default."""
import fcntl, os, struct
class FileObjectStore:
    def __init__(self, root): self._r = str(root); os.makedirs(self._r, exist_ok=True); self._lk = os.path.join(self._r, ".lock")
    def _p(self, key): return os.path.join(self._r, "o_" + key.encode("utf-8").hex())
    def _locked(self):
        f = open(self._lk, "a+"); fcntl.flock(f, fcntl.LOCK_EX); return f
    def _read(self, p):
        try:
            with open(p, "rb") as f: b = f.read()
        except FileNotFoundError: return None
        return b[8:], struct.unpack(">Q", b[:8])[0]
    def get(self, key):
        with self._locked(): return self._read(self._p(key))
    def _write(self, p, data, etag):
        t = p + ".tmp"
        with open(t, "wb") as f: f.write(struct.pack(">Q", etag) + bytes(data))
        os.replace(t, p)
    def put_if_absent(self, key, data):
        with self._locked():
            p = self._p(key)
            if self._read(p) is not None: return False
            self._write(p, data, 1); return True
    def put_if_match(self, key, data, etag):
        with self._locked():
            p = self._p(key); cur = self._read(p)
            if cur is None or cur[1] != etag: return False
            self._write(p, data, etag + 1); return True
    def list_prefix(self, prefix):
        with self._locked(): return sorted(k for k in (bytes.fromhex(n[2:]).decode("utf-8") for n in os.listdir(self._r) if n.startswith("o_") and not n.endswith(".tmp")) if k.startswith(prefix))
