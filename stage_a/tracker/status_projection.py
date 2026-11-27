"""Chain-status PROJECTION over committed journal records (R7 section 2: sole constrained canonical commit; Build Plan: no independently authoritative status HEAD).
The projection has NO write path of its own. It rebuilds a private ChainStatusAuthority by replaying the journal reachable from HEAD (orphans and uncommitted
objects are never read: ObjectStoreJournal.read_from verifies the chain to genesis). It is consumer-authoritative only while its built head equals the current
journal head; otherwise it reports not-authoritative and refuses reads (fail closed), so a stale or never-refreshed projection cannot answer for a fence.
UNRESOLVED CLAUSE (not invented here): which committed record kind/body carries a status fact, i.e. the mapping record -> StatusFact. R7 does not define it
and names no status-origin principal. The mapping is therefore a REQUIRED caller-supplied decoder (the authority boundary); there is no default. Origin and
grant validation likewise belong to that boundary. No principal is appointed here."""
from typing import Callable, Optional
from tracker_component.journal_port import GENESIS_HEAD, Head
from ..errors import Refusal
from .chain_status import ChainStatusAuthority, StatusFact

class StatusProjection:
    def __init__(self, journal, decode_fact: Callable):
        if not callable(decode_fact):
            raise Refusal("decoder", code="STATUS_DECODER_REQUIRED")
        self._j, self._decode = journal, decode_fact
        self._auth = ChainStatusAuthority()
        self._built: Optional[Head] = None
        self._invalid: Optional[str] = None

    def refresh(self) -> Head:
        """Replay committed records into a FRESH authority; swap it in only on success. Any bad record makes the projection invalid (fail closed)."""
        head = self._j.head()
        recs = self._j.read_from(1) if head != GENESIS_HEAD else []
        fresh = ChainStatusAuthority()
        try:
            for r in recs:
                f = self._decode(r)
                if f is None:
                    continue                                  # a committed record that carries no status fact
                if not isinstance(f, StatusFact):
                    raise Refusal(type(f).__name__, code="STATUS_DECODER_RETURNED_NON_FACT")
                fresh.append(f)
        except Refusal as e:
            self._invalid, self._built = e.code, None
            raise
        self._auth, self._built, self._invalid = fresh, head, None
        return head

    @property
    def authoritative(self) -> bool:
        """True only when built from the CURRENT committed head and valid. Re-checked on every read."""
        return self._invalid is None and self._built is not None and self._built == self._j.head()

    def status_at(self, mv, fence: int):
        if self._invalid is not None:
            raise Refusal(self._invalid, code="STATUS_PROJECTION_INVALID")
        if not self.authoritative:
            raise Refusal("projection head != committed head", code="STATUS_PROJECTION_STALE")
        return self._auth.status_at(mv, fence)

    @property
    def built_head(self) -> Optional[Head]:
        return self._built
