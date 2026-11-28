"""R50: TYPED, IMMUTABLE H1 CONSUMER_BINDING record (Connected Contract V0.37 H1 as carried by V0.38). Reuses `gateway.v038.check_h1` (field presence/vocabulary/consumer-package class/ML applicability derived from the record) and
`check_binding_matches_identity`; adds only the TYPE: the record is validated at construction, deep-frozen (a caller mutating the dict it passed in, or a nested list, changes nothing), and is the one place the H1 CONSUMER_BINDING_ID is read from.
CONSUMER_BINDING_ID (H1, package field) and MANIFEST_OR_DATASET_BINDING_ID (final-resolution identity field) stay DISTINCT fields and are never compared as if equal. H1 does not list MANIFEST_OR_DATASET_BINDING_ID as required, so a record that does not
carry it CANNOT be correlated to a final-resolution identity: `correlation()` refuses (HELD; never derived from the CBID). Who issues H1 is the Gateway per the contract; this module issues nothing, appoints no principal and defines no byte encoding (D13)."""
from types import MappingProxyType
from ..errors import Refusal
from .v038 import check_h1, check_binding_matches_identity, h1_is_ml


def _freeze(x):
    if isinstance(x, dict): return MappingProxyType({k: _freeze(v) for k, v in x.items()})
    if isinstance(x, (list, tuple)): return tuple(_freeze(v) for v in x)
    return x


class TypedH1:
    __slots__ = ("_f",)
    def __init__(self, fields: dict, decision_window: bool = True):
        if not isinstance(fields, dict): raise Refusal(type(fields).__name__, code="H1_RECORD_NOT_A_MAPPING")
        d = fields                                                       # read only here: _freeze below builds NEW nested containers, so nothing aliases the caller's dict
        check_h1(d, decision_window)                                    # presence, vocabulary, class mismatch, ML applicability: the existing checker, unchanged
        for k in ("CONSUMER_BINDING_ID", "CONSUMER_ID", "REQUEST_ID"):
            if not (isinstance(d[k], str) and d[k]): raise Refusal(k, code="H1_ID_FIELD_NOT_A_NONEMPTY_STRING")
        object.__setattr__(self, "_f", _freeze(d))
    def __setattr__(self, k, v): raise Refusal(k, code="H1_RECORD_IMMUTABLE")
    def __delattr__(self, k): raise Refusal(k, code="H1_RECORD_IMMUTABLE")
    def __eq__(self, o): return isinstance(o, TypedH1) and self.thaw() == o.thaw()
    def __hash__(self): return hash(repr(sorted(self.thaw().items(), key=lambda kv: kv[0])))
    @property
    def fields(self): return self._f
    def thaw(self):
        def t(x):
            if isinstance(x, MappingProxyType): return {k: t(v) for k, v in x.items()}
            if isinstance(x, tuple): return [t(v) for v in x]
            return x
        return t(self._f)
    @property
    def is_ml(self): return h1_is_ml(self.thaw())
    def correlation(self, identity):
        """The ConsumerBindingRecord for THIS issued final-resolution identity, or a refusal. The relation CBID <-> MANIFEST_OR_DATASET_BINDING_ID exists only if this H1 record itself carries the latter and it equals the identity's."""
        if self._f.get("MANIFEST_OR_DATASET_BINDING_ID") in (None, ""): raise Refusal(self._f["CONSUMER_BINDING_ID"], code="H1_MANIFEST_OR_DATASET_BINDING_ID_HELD")
        check_binding_matches_identity(self.thaw(), identity)           # same consumer, same manifest/dataset binding id
        from ..fw.outcome_desk import ConsumerBindingRecord
        return ConsumerBindingRecord(self._f["CONSUMER_BINDING_ID"], self._f["CONSUMER_ID"], self._f["REQUEST_ID"], self._f["MANIFEST_OR_DATASET_BINDING_ID"])
