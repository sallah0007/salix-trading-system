"""Feature->feature dependency lineage DERIVED from admitted QuantManifests (frozen Annex INPUT_DEPENDENCIES, source-present; code: schema.objects.QuantManifest.input_dependencies).
This is the source the blast-radius module needs; it is NOT invented from prototype input names. Three things stay distinct (assessed, not assumed):
 1. normative mapping: INPUT_DEPENDENCIES exists in the Annex, but the REF_TYPE vocabulary (which ref types denote a FEATURE identity) is the open D3 code table - so the caller
    must pass `feature_ref_types` explicitly; there is no default and an empty set refuses.
 2. persistence/adapter: the pipeline admits the expression-kernel Manifest and journals only hashes; no QuantManifest is persisted or read back by Tracker code yet. This function
    takes manifests the caller has already resolved (it cannot prove they are the ACCEPTED ones - that join needs the registry/journal read path, not built).
 3. instances: no real manifest instance exists in this repository.
Output feeds health.blast_radius.downstream_features/blast_radius; a dependency target with no supplied manifest makes lineage INCOMPLETE there (UNDETERMINED), never 'unaffected'."""
from typing import Dict, Iterable, Tuple
from ..errors import Refusal
from ..schema.objects import QuantManifest

def feature_deps_from_quant_manifests(manifests: Iterable[QuantManifest], feature_ref_types) -> Dict[bytes, Tuple[bytes, ...]]:
    ft = frozenset(feature_ref_types or ())
    if not ft:
        raise Refusal("feature_ref_types", code="FEATURE_REF_TYPES_REQUIRED_D3_VOCABULARY")
    deps: Dict[bytes, set] = {}
    for m in manifests:
        if not isinstance(m, QuantManifest):
            raise Refusal(type(m).__name__, code="NOT_A_QUANT_MANIFEST")
        own = deps.setdefault(m.feature_id, set())                   # every supplied feature appears as a key even with no feature dependencies
        for _name, ref in m.input_dependencies:
            if ref.ref_type in ft:
                if ref.target_id == m.feature_id:
                    raise Refusal(m.feature_id.hex(), code="FEATURE_DEPENDS_ON_ITSELF")
                own.add(ref.target_id)
    return {f: tuple(sorted(d)) for f, d in deps.items()}
