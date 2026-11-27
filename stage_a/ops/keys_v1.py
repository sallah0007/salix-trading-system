"""E-09: the CANDIDATE `stage-a/v1/...` object-store key plan as pure builders. Candidate and NON-NORMATIVE for bytes: it does not replace `storage.keys` (the repository prototype layout differs and legacy data is neither remapped nor deleted; `LEGACY_KEY_FAMILIES` names the old prefixes so a reader can accept both). Rules enforced here:
keys are content/identity addressed and never overwritten; HEAD is the only mutable key and is written only by conditional CAS with an epoch/fence check (`head_cas_allowed`); listing order is never authority (a caller that sorts by key to pick a head is wrong: `sequence_key` zero-pads only for human listing).
Note (R7 single commit): no independently authoritative status HEAD is created by this module; `status_head_key` exists only to name the Build Plan text key and is marked LEGACY_E09_TEXT_NOT_ADOPTED until the Manager reconciles it with the selected R7 overlay."""
import re
from ..errors import Refusal
_H = re.compile(r"[0-9a-f]{64}\Z"); _ID = re.compile(r"[A-Za-z0-9_.\-]{1,128}\Z")
LEGACY_KEY_FAMILIES = ("head/", "journal/", "artifact/", "accepted-materialization/", "final-resolution/")
def _h(x): 
    if not isinstance(x, str) or not _H.match(x): raise Refusal(repr(x), code="KEY_HASH_INVALID")
    return x
def _i(x):
    if not isinstance(x, str) or not _ID.match(x) or x in (".", ".."): raise Refusal(repr(x), code="KEY_COMPONENT_INVALID")
    return x
def artifact_key(kind, sha): return "stage-a/v1/artifacts/%s/%s/%s.bin" % (_i(kind), _h(sha)[:2], sha)
def golden_key(set_id, sha): return "stage-a/v1/goldens/%s/%s.bin" % (_i(set_id), _h(sha))
def fit_key(fid, ver, gen, sha): return "stage-a/v1/fits/%s/%s/%s/%s.bin" % (_i(fid), _i(ver), _i(gen), _h(sha))
def coordination_head_key(ns): return "stage-a/v1/coordination/%s/HEAD" % _i(ns)
def transition_key(ns, epoch, seq, thash):
    if not (type(epoch) is int and epoch >= 0 and type(seq) is int and seq >= 1): raise Refusal("epoch/seq", code="KEY_EPOCH_SEQUENCE_INVALID")
    return "stage-a/v1/coordination/%s/epochs/%d/transitions/%020d-%s.bin" % (_i(ns), epoch, seq, _h(thash))
def status_head_key(fid, ver, mv): return "stage-a/v1/status/%s/%s/%s/HEAD" % (_i(fid), _i(ver), _i(mv))   # LEGACY_E09_TEXT_NOT_ADOPTED (see module note)
def binding_key(bid, final_hash): return "stage-a/v1/gateway/bindings/%s/%s.bin" % (_i(bid), _h(final_hash))
def non_delivery_key(rid, h): return "stage-a/v1/gateway/non-delivery/%s/%s.bin" % (_i(rid), _h(h))
def health_key(subject_type, subject_id, available_asof_ns, ehash):
    if not (type(available_asof_ns) is int and available_asof_ns >= 0): raise Refusal("asof", code="KEY_TIME_INVALID")
    return "stage-a/v1/health/%s/%s/%d-%s.bin" % (_i(subject_type), _i(subject_id), available_asof_ns, _h(ehash))
def head_cas_allowed(current_epoch: int, writer_epoch: int, current_seq: int, new_seq: int) -> bool:
    """Mutable HEAD may advance only for a writer holding the CURRENT epoch and only by exactly +1 within that epoch; a stale epoch can create no accepted write."""
    return writer_epoch == current_epoch and new_seq == current_seq + 1
