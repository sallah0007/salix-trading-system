"""Authority is a reference to an accepted journal transition, never a caller assertion."""
from dataclasses import dataclass
from .errors import Refusal

@dataclass(frozen=True)
class AuthorityRef:
    namespace: str
    seq: int
    record_hash: str
    def to_str(self) -> str:
        return "ACCEPTED:%s#%d:%s" % (self.namespace, self.seq, self.record_hash)
    @staticmethod
    def parse(s: str) -> "AuthorityRef":
        try:
            tag, rest = s.split(":", 1)
            ns_seq, h = rest.rsplit(":", 1)
            ns, seq = ns_seq.rsplit("#", 1)
            if tag != "ACCEPTED" or len(h) != 64:
                raise ValueError
            return AuthorityRef(ns, int(seq), h)
        except ValueError:
            raise Refusal(repr(s), code="MALFORMED_AUTHORITY_REF")
