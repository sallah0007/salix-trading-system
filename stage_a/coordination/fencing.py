"""Fencing helpers. The fence is the epoch held in HEAD; a writer is current only while HEAD still carries its epoch."""
from dataclasses import dataclass
from ..errors import StaleFence

@dataclass(frozen=True)
class Fence:
    namespace: str
    epoch: int

def acquire(journal, namespace: str) -> Fence:
    return Fence(namespace, journal.acquire_epoch())

def assert_current(journal, fence: Fence):
    if not journal.epoch_is_current():
        raise StaleFence("fence %s epoch %d superseded" % (fence.namespace, fence.epoch))
