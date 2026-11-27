"""TrackerCore: ONE composition path for source-backed Core mechanics over a single fenced journal (reuses ObjectStoreJournal, canonical_bytes/domain_hash, half-open fence; no second registry or lifecycle).

SOURCE-BACKED (registry 1eZThdek... s5; frozen DOCX s5/s6/s9/s21): observation idempotence / conflict quarantine; exactly-one source-contract match + freshness; half-open snapshot fence, MIXED_VINTAGE invalid,
MIXED_DECLARED default-deny; semantic-epoch dependent invalidation; multi-reason quarantine with reopen != reactivation and reconstructability; as-of eligibility from QUALIFIED journals only;
L2_REQUIREMENT / L2_STATUS / RECORDING_HEALTH; reviewer-input guard (finding-only, creator != certifier).
CANDIDATE / UNBOUND (never defaulted): the observation identity BYTE encoding (fact NAMES are source-present; `OBS_FACTS_CANDIDATE` + canonical_bytes is an internal carrier, NOT a production key), manifest bytes,
DATA_VINTAGE_MODE values, calendar/DST segmentation, per-provider contract instances, L2 appointment. Nothing here qualifies a provider or authorizes any gate."""
import json
from ..errors import Refusal
from ..storage.byte_primitives import canonical_bytes, domain_hash
from ..storage.authority_class import authority_class_of, QUALIFIED

OBS_FACTS_CANDIDATE = ("instrument", "timeframe", "bar_identity", "broker_time", "utc_time", "broker_utc_rule", "source_provider", "raw_source_version", "schema_version")
REQ = ("REQUIRED", "NOT_APPLICABLE_BY_GOVERNED_DEFINITION")
L2_ST = ("PASS", "FAIL", "UNAVAILABLE")
L1_ST = ("PASS", "FAIL")
HEALTH = ("HEALTHY", "NOT_HEALTHY", "UNKNOWN")
NEW, REPEAT, CONFLICT = "NEW", "IDEMPOTENT_REPEAT", "CONFLICT_QUARANTINED"

def _s(x): return json.loads(canonical_bytes(x).decode("ascii"))

class TrackerCore:
    def __init__(self, journal, *, simulation: bool):
        self._j = journal; self.simulation = bool(simulation)
        cls = authority_class_of(journal)
        if (cls == QUALIFIED) == self.simulation:
            raise Refusal("journal class %s vs simulation=%s" % (cls, simulation), code="AUTHORITY_CLASS_MISMATCH")

    # ---- replay: pure function of the journal -------------------------------------------------
    def _replay(self, upto=None):
        st = dict(obs={}, amb={}, contracts={}, snaps={}, policies={}, epoch={}, deps={}, inval={}, q={}, qlog=[], health={}, findings=[], quar_raw={})
        for r in self._j.read_from(0):
            if upto is not None and r.seq > upto: break
            b = json.loads(r.body_json); k = r.kind
            if k == "OBS_ADMITTED": st["obs"][b["key"]] = b["digest"]
            elif k == "OBS_AMBIGUOUS": st["amb"][b["key"]] = sorted(set(st["amb"].get(b["key"], []) + b["digests"]))
            elif k == "OBS_AMBIGUITY_RESOLVED": st["amb"].pop(b["key"], None); st["obs"][b["key"]] = b["digest"]
            elif k == "CONTRACT_REGISTERED": st["contracts"][(b["id"], b["version"])] = b
            elif k == "CONTRACT_QUARANTINED": st["quar_raw"][b["raw_digest"]] = b["why"]
            elif k == "SNAPSHOT_SEALED": st["snaps"][b["hash"]] = b
            elif k == "MIXED_POLICY": st["policies"][b["id"]] = b
            elif k == "DEPENDENCY": st["deps"].setdefault(b["upstream"], []).append(b["dependent"])
            elif k == "EPOCH": 
                st["epoch"][b["key"]] = b["epoch"]
                stack = list(st["deps"].get(b["key"], []))
                while stack:
                    d = stack.pop()
                    if d not in st["inval"]: st["inval"][d] = b["key"]; stack += st["deps"].get(d, [])
            elif k == "RERESOLVED": st["inval"].pop(b["key"], None)
            elif k == "Q_REASON": st["q"].setdefault(b["subject"], {"reasons": set(), "status": "QUARANTINED"})["reasons"].add(b["reason"]); st["q"][b["subject"]]["status"] = "QUARANTINED"
            elif k == "Q_CLEAR": st["q"][b["subject"]]["reasons"].discard(b["reason"])
            elif k == "Q_REOPEN": st["q"][b["subject"]]["status"] = "REOPENED"
            elif k == "Q_REACTIVATE": st["q"][b["subject"]]["status"] = "ACTIVE"
            elif k == "HEALTH": st["health"][b["key"]] = b
            elif k == "FINDING": st["findings"].append(b)
        return st

    def _app(self, kind, body):
        self._j.append(self._j.head(), kind, _s(body))

    # ---- B01 observation identity ---------------------------------------------------------------
    @staticmethod
    def obs_key(facts: dict) -> str:
        if set(facts) != set(OBS_FACTS_CANDIDATE) or any(not isinstance(v, str) or not v for v in facts.values()):
            raise Refusal("observation facts", code="OBSERVATION_FACTS_INVALID")
        return domain_hash("TRK/OBS_CANDIDATE", canonical_bytes({k: facts[k] for k in OBS_FACTS_CANDIDATE}))

    def admit_observation(self, facts: dict, payload: bytes) -> str:
        key, dg = self.obs_key(facts), domain_hash("TRK/PAYLOAD", payload); st = self._replay()
        if key in st["amb"]:
            if dg not in st["amb"][key]: self._app("OBS_AMBIGUOUS", {"key": key, "digests": [dg]})
            return CONFLICT
        if key in st["obs"]:
            if st["obs"][key] == dg: return REPEAT
            self._app("OBS_AMBIGUOUS", {"key": key, "digests": sorted({st["obs"][key], dg})}); return CONFLICT   # never overwritten
        self._app("OBS_ADMITTED", {"key": key, "digest": dg}); return NEW

    def resolve_ambiguity(self, key: str, chosen_digest: str, creator: str, certifier: str):
        if not creator or not certifier or creator == certifier: raise Refusal("creator!=certifier", code="CREATOR_IS_CERTIFIER")
        st = self._replay()
        if key not in st["amb"] or chosen_digest not in st["amb"][key]: raise Refusal(key, code="NOT_A_PENDING_CANDIDATE")
        self._app("OBS_AMBIGUITY_RESOLVED", {"key": key, "digest": chosen_digest, "certifier": certifier})

    def observation_usable(self, key: str) -> bool:
        st = self._replay(); return key in st["obs"] and key not in st["amb"]

    # ---- B04 source contract: exactly one match + freshness -------------------------------------
    @staticmethod
    def derive_fingerprint(envelope: dict) -> str:       # derived from structure, never from the provider's own label
        shape = {k: type(v).__name__ for k, v in envelope.items() if k not in ("label", "contract_label", "watermark")}
        return domain_hash("TRK/ENVELOPE_SHAPE", canonical_bytes(shape))

    def register_contract(self, cid: str, version: str, fingerprint: str, max_staleness: int, battery_passed: bool):
        self._app("CONTRACT_REGISTERED", {"id": cid, "version": version, "fingerprint": fingerprint, "max_staleness": max_staleness, "battery_passed": bool(battery_passed)})

    def resolve_contract(self, envelope: dict, raw: bytes, now: int):
        st = self._replay(); fp = self.derive_fingerprint(envelope); rd = domain_hash("TRK/RAW", raw)
        hits = [c for c in st["contracts"].values() if c["fingerprint"] == fp]
        if len(hits) != 1:
            self._app("CONTRACT_QUARANTINED", {"raw_digest": rd, "why": "ZERO_MATCH" if not hits else "MULTI_MATCH", "raw_hex": raw.hex()}); return ("QUARANTINED", "ZERO_MATCH" if not hits else "MULTI_MATCH")
        c = hits[0]
        if not c["battery_passed"]: return ("NOT_USABLE", "CHALLENGE_BATTERY_NOT_PASSED")
        wm = envelope.get("watermark")
        if not isinstance(wm, int) or isinstance(wm, bool) or now - wm > c["max_staleness"]: return ("HELD", "STALE_OR_MISSING_WATERMARK")
        return ("RESOLVED", (c["id"], c["version"]))

    # ---- B03 snapshot: half-open fence, vintage, default-deny -----------------------------------
    def register_mixed_policy(self, pid: str, declared_by: str):
        if not pid or not declared_by: raise Refusal("policy", code="POLICY_INCOMPLETE")
        self._app("MIXED_POLICY", {"id": pid, "declared_by": declared_by})

    def seal(self, instrument: str, query_asof: int, fence: int, members: list, mixed_policy_id=None):
        st = self._replay()
        if query_asof > fence: raise Refusal("query_asof after fence", code="ASOF_AFTER_FENCE")
        inc = []
        for m in members:
            if m["instrument"] != instrument: raise Refusal(m["key"], code="CROSS_INSTRUMENT_MEMBER")
            if m["key"] in st["amb"] or m["key"] not in st["obs"]: raise Refusal(m["key"], code="MEMBER_NOT_USABLE_OBSERVATION")
            if m["available_asof"] < fence: inc.append(m)                  # half-open: equality excluded
        by_tf = {}
        for m in inc: by_tf.setdefault(m["timeframe"], set()).add(m["vintage"])
        if len({v for vs in by_tf.values() for v in vs}) > 1 or any(len(v) > 1 for v in by_tf.values()):
            if mixed_policy_id is None or mixed_policy_id not in st["policies"]: return ("MIXED_VINTAGE_REFUSED", None)
        body = {"instrument": instrument, "query_asof": query_asof, "fence": fence, "members": sorted(({k: m[k] for k in ("key", "timeframe", "vintage", "available_asof")} for m in inc), key=lambda x: x["key"]),
                "mixed_policy": mixed_policy_id}
        h = domain_hash("TRK/SNAPSHOT_CANDIDATE", canonical_bytes(body))
        if h not in st["snaps"]: self._app("SNAPSHOT_SEALED", dict(body, hash=h))
        return ("SEALED", h)

    def verify_snapshot(self, h: str, instrument, query_asof, fence, members, mixed_policy_id=None) -> bool:
        st = self._replay(); return h in st["snaps"] and st["snaps"][h]["fence"] == fence and h == self._hash_only(instrument, query_asof, fence, members, mixed_policy_id)

    def _hash_only(self, instrument, query_asof, fence, members, mixed_policy_id):
        inc = [m for m in members if m["available_asof"] < fence]
        body = {"instrument": instrument, "query_asof": query_asof, "fence": fence, "members": sorted(({k: m[k] for k in ("key", "timeframe", "vintage", "available_asof")} for m in inc), key=lambda x: x["key"]), "mixed_policy": mixed_policy_id}
        return domain_hash("TRK/SNAPSHOT_CANDIDATE", canonical_bytes(body))

    # ---- B05 semantic epoch / dependent invalidation ----------------------------------------------
    def declare_dependency(self, dependent: str, upstream: str):
        if dependent == upstream: raise Refusal(dependent, code="SELF_DEPENDENCY")
        self._app("DEPENDENCY", {"dependent": dependent, "upstream": upstream})

    def advance_epoch(self, key: str, epoch: int):
        if epoch <= self._replay()["epoch"].get(key, 0): raise Refusal(key, code="EPOCH_NOT_ADVANCING")
        self._app("EPOCH", {"key": key, "epoch": epoch})

    def reresolve(self, key: str):
        st = self._replay()
        if key not in st["inval"]: raise Refusal(key, code="NOT_INVALIDATED")
        self._app("RERESOLVED", {"key": key})

    # ---- quarantine: multi-reason, retry suppression, reopen != reactivation ------------------------
    def quarantine(self, subject: str, reason: str): self._app("Q_REASON", {"subject": subject, "reason": reason})
    def clear_reason(self, subject: str, reason: str, certifier: str, creator: str):
        if not certifier or certifier == creator: raise Refusal("creator!=certifier", code="CREATOR_IS_CERTIFIER")
        if reason not in self._replay()["q"].get(subject, {"reasons": set()})["reasons"]: raise Refusal(reason, code="REASON_NOT_OPEN")
        self._app("Q_CLEAR", {"subject": subject, "reason": reason})
    def retry_allowed(self, subject: str) -> bool:
        q = self._replay()["q"].get(subject); return q is None or (not q["reasons"] and q["status"] == "ACTIVE")
    def reopen(self, subject: str):
        if subject not in self._replay()["q"]: raise Refusal(subject, code="NOT_QUARANTINED")
        self._app("Q_REOPEN", {"subject": subject})               # reopen alone never reactivates
    def reactivate(self, subject: str, upstream_keys: list):
        st = self._replay(); q = st["q"].get(subject)
        if q is None or q["reasons"]: raise Refusal(subject, code="REASONS_STILL_OPEN")
        bad = [k for k in upstream_keys if k not in st["obs"] or k in st["amb"]]
        if bad: raise Refusal(",".join(bad), code="NOT_RECONSTRUCTABLE")
        self._app("Q_REACTIVATE", {"subject": subject})
    def blocked(self, key: str) -> list:
        st = self._replay(); out = []
        q = st["q"].get(key)
        if q and (q["reasons"] or q["status"] != "ACTIVE"): out.append("QUARANTINED")
        if key in st["inval"]: out.append("EPOCH_INVALIDATED")
        if key in st["amb"]: out.append("OBSERVATION_AMBIGUOUS")
        return out

    # ---- B14 verification / Recording Health --------------------------------------------------------
    def record_verification(self, key: str, l2_requirement: str, l2_status: str, l1: str, at: int, max_age: int):
        if l2_requirement not in REQ or l2_status not in L2_ST or l1 not in L1_ST: raise Refusal("vocabulary", code="HEALTH_VOCABULARY_UNKNOWN")
        self._app("HEALTH", {"key": key, "req": l2_requirement, "l2": l2_status, "l1": l1, "at": at, "max_age": max_age})
    def recording_health(self, key: str, now: int) -> str:
        h = self._replay()["health"].get(key)
        if h is None or now - h["at"] > h["max_age"]: return "UNKNOWN"          # absent / stale health can never certify
        if h["l1"] == "FAIL" or h["l2"] == "FAIL": return "NOT_HEALTHY"
        if h["req"] == "REQUIRED": return "HEALTHY" if h["l2"] == "PASS" else "UNKNOWN"   # UNAVAILABLE L2 never falls back to L1
        return "HEALTHY"

    # ---- as-of eligibility (qualified journals only) ----------------------------------------------
    def eligible_asof(self, key: str, asof_seq: int, now: int) -> dict:
        if self.simulation: return {"eligible": False, "reasons": ["SIMULATION_NOT_ELIGIBLE"], "mode": "SIMULATION_EVIDENCE_ONLY"}
        st = self._replay(asof_seq); reasons = []
        q = st["q"].get(key)
        if q and (q["reasons"] or q["status"] != "ACTIVE"): reasons.append("QUARANTINED")
        if key in st["inval"]: reasons.append("EPOCH_INVALIDATED")
        if key in st["amb"]: reasons.append("OBSERVATION_AMBIGUOUS")
        h = st["health"].get(key)
        if h is None or now - h["at"] > h["max_age"] or h["l1"] == "FAIL" or h["l2"] == "FAIL" or (h["req"] == "REQUIRED" and h["l2"] != "PASS"): reasons.append("RECORDING_HEALTH_NOT_HEALTHY")
        return {"eligible": not reasons, "reasons": reasons, "mode": "QUALIFIED"}

    # ---- composition output: the health decision the downstream Gateway actually consumes ----------------
    def gateway_health(self, key: str, now: int, ref, resolved_at: int, *, asof_seq: int = None):
        from ..gateway.contracts import HealthSnapshot
        blocked = self.blocked(key); health = self.recording_health(key, now)
        ok = not blocked and health == "HEALTHY"
        return HealthSnapshot(ref, resolved_at, ok)

    # ---- reviewer / write-plane boundary ------------------------------------------------------------
    FINDING_FIELDS = ("finding_id", "task_origin", "summary", "author")
    def accept_finding(self, finding: dict):
        if set(finding) != set(self.FINDING_FIELDS) or any(not isinstance(finding[k], str) or not finding[k] for k in self.FINDING_FIELDS):
            raise Refusal("finding carries non-finding fields or lacks task origin", code="REVIEW_INPUT_NOT_FINDING_ONLY")
        self._app("FINDING", dict(finding))                                   # recorded only; mutates no state, authorizes nothing
