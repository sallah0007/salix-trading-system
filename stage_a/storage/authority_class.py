"""Authority class of a store/journal/claims/pipeline carrier. It is DERIVED STRUCTURALLY FROM THE CARRIER'S ACTUAL TYPE AND PHYSICAL KEYSPACE, never from a public label: an `authority_class`
attribute, whether present, deleted, assigned or spoofed, is IGNORED. A carrier is
  * SIMULATION  iff its root store is EXACTLY a `SimulationStore` (exact type, no subclass): every key it can touch is physically under 'SIMULATION/' in the inner store, so a reader of the
                ordinary keyspace can never see it, with or without the wrapper (wrapper loss, restart, rebuild and cache rebuild all read the same physical keys);
  * QUALIFIED   iff its root store is one of QUALIFIED_STORE_TYPES (a code-level whitelist of real store adapters, extended only by changing this module under review);
  * anything else (unknown/foreign/subclassed-wrapper carriers, missing roots) is REFUSED UNKNOWN_CARRIER: fail closed, never default-to-qualified.
No canonical record field is added or invented. This is NOT a provider or security qualification: a process that can write the raw store directly can still write any key; the guarantee is that
code paths in this repository cannot cross classes by relabelling."""
from ..errors import Refusal

QUALIFIED, SIMULATION = "QUALIFIED", "SIMULATION"
_PREFIX = "SIMULATION/"

class SimulationStore:
    """Physical isolation adapter: all keys are prefixed. Exact-type only (see authority_class_of)."""
    def __init__(self, inner):
        if _root_class(inner) != QUALIFIED:
            raise Refusal("simulation store must wrap one ordinary store", code="BAD_SIMULATION_STORE")
        self._i = inner
    def get(self, key): return self._i.get(_PREFIX + key)
    def put_if_absent(self, key, data): return self._i.put_if_absent(_PREFIX + key, data)
    def put_if_match(self, key, data, etag): return self._i.put_if_match(_PREFIX + key, data, etag)
    def list_prefix(self, prefix): return [k[len(_PREFIX):] for k in self._i.list_prefix(_PREFIX + prefix)]

def _qualified_store_types():
    from .object_store import InMemoryObjectStore
    return (InMemoryObjectStore,)

def _root_class(obj, depth=0) -> str:
    if depth > 4:
        raise Refusal("carrier nesting", code="UNKNOWN_CARRIER")
    from ..coordination.object_store_journal import ObjectStoreJournal
    from ..tracker.registry import FeatureJournalSet
    from tracker_component.claims import ClaimService
    t = type(obj)                                                       # TYPE-level dispatch: instance attributes cannot shadow it
    if t is SimulationStore:
        return SIMULATION
    if t in _qualified_store_types() or any(t is q or issubclass(t, q) for q in _qualified_store_types()):
        return QUALIFIED
    if t is ObjectStoreJournal:
        return _root_class(obj._s, depth + 1)
    if t is FeatureJournalSet:
        return _root_class(obj._store, depth + 1)
    if t is ClaimService:
        return _root_class(obj._j, depth + 1)
    raise Refusal(t.__name__, code="UNKNOWN_CARRIER")

def authority_class_of(obj) -> str:
    return _root_class(obj)

def require_qualified(obj, what: str) -> None:
    if authority_class_of(obj) != QUALIFIED:
        raise Refusal("%s on a %s journal/store" % (what, authority_class_of(obj)), code="SIMULATION_NOT_ELIGIBLE")
