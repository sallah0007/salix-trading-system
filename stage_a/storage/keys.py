"""Object-store key layout. Journal records are content-addressed per (seq, hash) so an orphan from a
fenced-out writer can never block the accepted record for the same seq."""
from ..errors import Refusal

def _ns(ns: str) -> str:
    if not ns or ".." in ns or ns.startswith("/") or "\x00" in ns or "//" in ns:
        raise Refusal(repr(ns), code="BAD_NAMESPACE")
    return ns

def head_key(ns): return "head/%s" % _ns(ns)
def journal_prefix(ns): return "journal/%s/" % _ns(ns)
def journal_key(ns, seq, rec_hash):
    if not isinstance(seq, int) or seq < 1 or len(rec_hash) != 64:
        raise Refusal("%r %r" % (seq, rec_hash), code="BAD_JOURNAL_KEY")
    return "%s%020d/%s" % (journal_prefix(ns), seq, rec_hash)
def artifact_key(manifest_hash):
    if len(manifest_hash) != 64 or any(c not in "0123456789abcdef" for c in manifest_hash):
        raise Refusal(manifest_hash, code="BAD_ARTIFACT_KEY")
    return "artifact/%s" % manifest_hash
