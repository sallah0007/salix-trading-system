"""Authority class of a store/journal. No canonical record field is added or invented: the class is a property of WHERE records live. A SimulationStore keeps every key under its own
'SIMULATION/' prefix, so a reader of the ordinary (QUALIFIED) store can never see a simulated record, and a reader holding a simulation journal/store can always tell (the class travels with the
journal object and is recomputed from the store on every restart/rebuild: it is not an in-memory flag on an outcome). Non-QUALIFIED journals are never eligible for publication, read-model rebuild
or status projection. An object that declares no class is treated as QUALIFIED (the only production class); a simulated rig must therefore wrap its store in SimulationStore."""
from ..errors import Refusal

QUALIFIED, SIMULATION = "QUALIFIED", "SIMULATION"
_PREFIX = "SIMULATION/"

def authority_class_of(obj) -> str:
    c = getattr(obj, "authority_class", QUALIFIED)
    if c not in (QUALIFIED, SIMULATION):
        raise Refusal(repr(c), code="UNKNOWN_AUTHORITY_CLASS")           # unknown class fails closed
    return c

def require_qualified(obj, what: str) -> None:
    if authority_class_of(obj) != QUALIFIED:
        raise Refusal("%s on a %s journal/store" % (what, authority_class_of(obj)), code="SIMULATION_NOT_ELIGIBLE")

class SimulationStore:
    authority_class = SIMULATION
    def __init__(self, inner):
        if authority_class_of(inner) != QUALIFIED or isinstance(inner, SimulationStore):
            raise Refusal("nested simulation store", code="BAD_SIMULATION_STORE")
        self._i = inner
    def get(self, key): return self._i.get(_PREFIX + key)
    def put_if_absent(self, key, data): return self._i.put_if_absent(_PREFIX + key, data)
    def put_if_match(self, key, data, etag): return self._i.put_if_match(_PREFIX + key, data, etag)
    def list_prefix(self, prefix): return [k[len(_PREFIX):] for k in self._i.list_prefix(_PREFIX + prefix)]
    def __getattr__(self, name):                       # fault-injection knobs etc. of the inner store
        return getattr(self._i, name)
