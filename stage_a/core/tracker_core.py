"""TrackerCore: ONE composition path for source-backed Core mechanics over a single fenced journal (reuses ObjectStoreJournal, canonical_bytes/domain_hash, the half-open fence, and - for eligibility -
the ONE existing Tracker chain-status authority; it creates no second registry, lifecycle or eligibility source).

HONEST STATUS (R22): these are INTERNAL CANDIDATE mechanics. Journal kinds, observation facts, verification results and health are CALLER-ASSERTED until the exact admitted schemas, authority, role, policy and
actual verifier bindings exist (all source-owned, unbound). Therefore:
  * simulation=True  -> explicit SIMULATION evidence: positive controls run and may report SIMULATION_EVIDENCE_* states; the Gateway health they produce is typed `CoreHealthSnapshot(evidence_class=SIMULATION)`.
  * simulation=False -> mechanics that need no external authority work (observation admission, contract resolution, quarantine opening, snapshot sealing), but anything that would ASSERT eligibility, health,
    reconstruction or a mixed-declared view returns typed HELD/UNDETERMINED with the exact missing prerequisites. An ordinary store keyspace is NOT semantic/source/provider qualification.
Unassigned slots (never defaulted): observation byte encoding (fact NAMES are source-present; `OBS_FACTS_CANDIDATE` + canonical_bytes is an internal carrier), manifest bytes, DATA_VINTAGE_MODE values,
calendar/DST, per-provider contract instances, L2 appointment/profile/interval, governed mixed-declared policy, definition-proof for NOT_APPLICABLE, reconstruction-proof, D25 clear/retry policy."""
import json
from dataclasses import dataclass
from ..errors import Refusal, UnknownCommit, IntegrityFailure
from ..storage.byte_primitives import canonical_bytes, domain_hash
from ..storage.authority_class import authority_class_of, QUALIFIED
from tracker_component.journal_port import HeadMismatch, record_hash
from tracker_component.canonical import canonical_json
from ..context.decision_context import fail_closed_transition, SUBJECT_DOMAIN

OBS_FACTS_CANDIDATE = ("instrument", "timeframe", "bar_identity", "broker_time", "utc_time", "broker_utc_rule", "source_provider", "raw_source_version", "schema_version")
REQ = ("REQUIRED", "NOT_APPLICABLE_BY_GOVERNED_DEFINITION")
L2_ST = ("PASS", "FAIL", "UNAVAILABLE")
L1_ST = ("PASS", "FAIL")
NEW, REPEAT, CONFLICT = "NEW", "IDEMPOTENT_REPEAT", "CONFLICT_QUARANTINED"
REJECTED_KNOWN = "REJECTED_KNOWN_CANDIDATE_NOT_CURRENT"   # R24: a previously REJECTED candidate re-sent after resolution; history only, state unchanged, NO retry/clear policy adopted (D25 unresolved)
HELD = "HELD"
CALLER_ASSERTED, COMPOSED_RECOMPUTATION = "CALLER_ASSERTED", "COMPOSED_RECOMPUTATION_SIMULATION"   # R24: the second is produced by tracker/reverification (real materializer + independent verifier, still simulation-labelled, never qualified)
EVIDENCE_CLASSES = (CALLER_ASSERTED, COMPOSED_RECOMPUTATION)
SIM_ELIGIBLE, SIM_NOT_ELIGIBLE = "SIMULATION_EVIDENCE_ELIGIBLE", "SIMULATION_EVIDENCE_NOT_ELIGIBLE"
QUALIFIED_PREREQS_UNBOUND = ("OBSERVATION_ADMISSION_SCHEMA_UNBOUND", "VERIFIER_BINDING_UNBOUND", "GOVERNED_THRESHOLD_UNBOUND", "L2_APPOINTMENT_PROFILE_UNBOUND")

def _s(x): return json.loads(canonical_bytes(x).decode("ascii"))
def _int(x): return isinstance(x, int) and not isinstance(x, bool)

def _scope_key(*parts) -> str:
    """Unambiguous replay key: a JSON array of typed parts (strings stay strings, the dependency sequence stays a nested array, order preserved). No delimiter or forbidden-character assumption: a value containing
    '|' or ',' cannot collide with a different scope because structure, not concatenation, separates the fields."""
    import json
    return json.dumps(list(parts), separators=(",", ":"), ensure_ascii=True)

class TrackerCore:
    PLANES = ("core_market", "event_context", "market_features", "research")       # source-named planes (DOCX s4/s21; registry s18); the write-role/restore ADMISSION is unbound (D2)

    def __init__(self, journal, *, simulation: bool, chain_status=None, plane: str = None, timeframes=None):
        if plane is not None and plane not in self.PLANES: raise Refusal(str(plane), code="UNKNOWN_PLANE")
        if not isinstance(simulation, bool): raise Refusal("simulation must be a bool", code="SIMULATION_FLAG_INVALID")
        self._j = journal; self._simulation = simulation; self._chain = chain_status; self._plane = plane; self._timeframes = timeframes     # optional governed TimeframeRegistry (core/time_family); when supplied an unregistered timeframe is refused at admission
        cls = authority_class_of(journal)
        if (cls == QUALIFIED) == self._simulation:
            raise Refusal("journal class %s vs simulation=%s" % (cls, simulation), code="AUTHORITY_CLASS_MISMATCH")
        self._replay()          # R24: the established journal identity is checked at attach time, BEFORE any append (omitted/foreign/mixed identity is refused here)

    @property
    def plane(self): return self._plane            # read-only: identity is not mutable-by-label
    @property
    def simulation(self) -> bool: return self._simulation   # read-only: the evidence mode cannot be flipped mid-session

    # ---- replay: pure function of the journal up to a given sequence ---------------------------
    def _replay(self, upto=None):
        st = dict(obs={}, cands={}, amb={}, contracts={}, snaps={}, policies={}, epoch={}, deps={}, ups={}, inval={}, q={}, health={}, findings=[], quar_raw={}, reverify={}, reviews={}, tasks={}, authev={}, xform={}, assoc={}, snapiss={}, anc={}, passes={}, resolved={})
        for r in self._j.read_from(0):
            if upto is not None and r.seq > upto: break
            b = json.loads(r.body_json); k = r.kind
            if b.get("plane") != self._plane: raise IntegrityFailure("record %s carries plane %r but this Core's identity is %r (omitted/foreign/mixed journal identity; legacy untagged history is attachable only by a plane-less Core)" % (r.seq, b.get("plane"), self._plane))
            if k == "OBS_ADMITTED": st["obs"][b["key"]] = b; st["cands"].setdefault(b["key"], {})[b["cid"]] = b
            elif k == "OBS_AMBIGUOUS":
                st["cands"].setdefault(b["key"], {})[b["candidate"]["cid"]] = b["candidate"]
                st["amb"][b["key"]] = sorted(set(st["amb"].get(b["key"], [])) | {b["candidate"]["cid"]} | ({st["obs"][b["key"]]["cid"]} if b["key"] in st["obs"] else set()))
            elif k == "OBS_AMBIGUITY_RESOLVED": st["amb"].pop(b["key"], None); st["obs"][b["key"]] = st["cands"][b["key"]][b["cid"]]     # materialized view = the exact chosen candidate; history stays in the journal
            elif k == "CONTRACT_REGISTERED": st["contracts"][(b["id"], b["version"])] = b
            elif k == "CONTRACT_QUARANTINED": st["quar_raw"][b["raw_digest"]] = b["why"]
            elif k == "SNAPSHOT_SEALED": st["snaps"][b["hash"]] = b
            elif k == "MIXED_POLICY": st["policies"][b["id"]] = b
            elif k == "MIXED_POLICY_REVOKED": st["policies"][b["id"]] = dict(st["policies"].get(b["id"], {}), revoked=True)
            elif k == "DEPENDENCY":
                st["deps"].setdefault(b["upstream"], []).append(b["dependent"]); st["ups"].setdefault(b["dependent"], []).append(b["upstream"])
            elif k == "EPOCH":
                st["epoch"][b["key"]] = b["epoch"]; st["reverify"][b["key"]] = r.seq
                seen, stack = set(), list(st["deps"].get(b["key"], []))
                while stack:                                                    # full closure: `seen` is the traversal guard, NOT 'already invalid'
                    d = stack.pop()
                    if d in seen: continue
                    seen.add(d); st["inval"][d] = (b["key"], r.seq); st["reverify"][d] = r.seq; stack += st["deps"].get(d, [])    # the LATEST invalidation supersedes an earlier one
            elif k == "RERESOLVED": st["inval"].pop(b["key"], None)
            elif k == "REVERIFY_REQUESTED": st["reverify"][b["key"]] = r.seq
            elif k == "Q_REASON": st["q"].setdefault(b["subject"], {"reasons": set(), "status": "QUARANTINED"})["reasons"].add(b["reason"]); st["q"][b["subject"]]["status"] = "QUARANTINED"
            elif k == "Q_REASON_WITH_REVIEW":
                st["q"].setdefault(b["subject"], {"reasons": set(), "status": "QUARANTINED"})["reasons"].add(b["reason"]); st["q"][b["subject"]]["status"] = "QUARANTINED"; st["reviews"].setdefault(b["subject"], []).append(b["review"])
            elif k == "Q_CLEAR": st["q"][b["subject"]]["reasons"].discard(b["reason"])
            elif k == "Q_REOPEN": st["q"][b["subject"]]["status"] = "REOPENED"
            elif k == "Q_REACTIVATE": st["q"][b["subject"]]["status"] = "ACTIVE"; st["reverify"][b["subject"]] = r.seq        # eligibility must be re-evidenced after reactivation
            elif k == "HEALTH": st["health"][b["subject"]] = dict(b, seq=r.seq)
            elif k == "FINDING": st["findings"].append(b)
            elif k == "AUTH_EVIDENCE": st["authev"][_scope_key(b["subject"], b["version"], b["instrument"], b["timeframe"], b["battery"], b["vintage"], list(b["dependencies"]))] = b      # keyed by the FULL claim scope: one version/scope never clears another
            elif k == "TRANSFORM_VERDICT": st["xform"][_scope_key(b["subject"], b["version"], b["kind"], b["transform_version"], b["lineage_ref"])] = b
            elif k == "SUBJECT_ASSOC": st["assoc"].setdefault(b["subject"], []).append(b["binding"])
            elif k == "SNAPSHOT_RESOLVED_MANIFEST": st["resolved"][b["resolved_manifest_hash"]] = b
            elif k == "REVERIFY_PASS": st["passes"][b["pass_id"]] = b
            elif k == "ANCESTRY_COMPLETE": st["anc"][b["subject"]] = b
            elif k == "SNAPSHOT_ISSUED": st["snapiss"][b["snapshot_id"]] = b
            elif k == "REVIEW_TASK": st["tasks"][b["task_origin"]] = b
        return st

    # ---- atomic semantic operation: validate against the EXACT committed head, append with that head, revalidate on any race -----
    def _commit(self, decide):
        """decide(state) -> (result, (kind, body) | None). On HeadMismatch another writer moved the head: re-read and revalidate. On UnknownCommit the ATTEMPTED record is resolved against the
        authoritative chain: if the journal holds exactly this record (same prev head, kind and body) at head.seq+1 the attempt COMMITTED and its stored result is returned (no double effect, no
        re-evaluation as a fresh operation); otherwise it did not land (dropped write / another writer) and the operation is revalidated from the new head. No provider-proof inference."""
        for _ in range(8):
            head = self._j.head(); st = self._replay(head.seq)
            out, rec = decide(st)
            if rec is None: return out
            body = _s(dict(rec[1], plane=self._plane) if self._plane is not None else rec[1]); want = record_hash(head.seq + 1, head.hash, rec[0], canonical_json(body))
            try:
                self._j.append(head, rec[0], body); return out
            except HeadMismatch:
                continue
            except UnknownCommit:
                landed = [r for r in self._j.read_from(0) if r.seq == head.seq + 1]
                if landed and landed[0].record_hash == want: return out
                continue
        raise Refusal("core commit contention", code="CORE_COMMIT_CONTENTION")

    # ---- B01 observation identity -----------------------------------------------------------------
    @staticmethod
    def obs_key(facts: dict) -> str:
        if not isinstance(facts, dict) or set(facts) != set(OBS_FACTS_CANDIDATE) or any(not isinstance(v, str) or not v for v in facts.values()):
            raise Refusal("observation facts", code="OBSERVATION_FACTS_INVALID")
        return domain_hash("TRK/OBS_CANDIDATE", canonical_bytes({k: facts[k] for k in OBS_FACTS_CANDIDATE}))

    @staticmethod
    def _cid(digest, available_asof, vintage):
        return domain_hash("TRK/OBS_CANDIDATE_ID", canonical_bytes({"digest": digest, "available_asof": available_asof, "vintage": vintage}))     # internal engineering identity, not a canonical encoding

    def admit_observation(self, facts: dict, payload: bytes, available_asof: int, vintage: str) -> str:
        key = self.obs_key(facts)
        if self._timeframes is not None: self._timeframes.require(facts["timeframe"])
        if not _int(available_asof) or available_asof < 0 or not isinstance(vintage, str) or not vintage or not isinstance(payload, bytes):
            raise Refusal("observation fields", code="OBSERVATION_FIELDS_INVALID")
        dg = domain_hash("TRK/PAYLOAD", payload); cid = self._cid(dg, available_asof, vintage)
        cand = {"cid": cid, "key": key, "digest": dg, "facts": dict(facts), "available_asof": available_asof, "vintage": vintage, "payload_hex": payload.hex()}
        def decide(st):
            known = st["cands"].get(key, {})
            if key in st["amb"]:                                                  # genuine CURRENT ambiguity: the result agrees with the state
                return CONFLICT, (None if cid in known else ("OBS_AMBIGUOUS", {"key": key, "candidate": cand}))
            if key in st["obs"]:
                if st["obs"][key]["cid"] == cid: return REPEAT, None
                if cid in known: return REJECTED_KNOWN, None                      # history only: NOT current ambiguity; reopening/retry policy is D25 (unadopted), so state is unchanged
                return CONFLICT, ("OBS_AMBIGUOUS", {"key": key, "candidate": cand})     # complete candidate retained; never overwritten
            return NEW, ("OBS_ADMITTED", cand)
        return self._commit(decide)

    def observation_facts(self, key: str):
        """R39: detached copy of the RECORDED facts of one admitted, currently usable observation (None if absent/ambiguous). Recorded facts only: not provider qualification."""
        import copy
        st = self._replay(); o = st["obs"].get(key)
        return None if o is None or key in st["amb"] else copy.deepcopy(o["facts"])
    def observations_for(self, instrument: str) -> list:
        """R54: read-only enumeration of this Core's OWN admitted, currently usable (non-ambiguous) observation receipts for one instrument: [(key, facts, available_asof, vintage)] sorted by key, detached copies. Zero rows is returned as an empty list: it is NOT a completed search for anything."""
        import copy
        st = self._replay(); return [(k, copy.deepcopy(o["facts"]), o["available_asof"], o["vintage"]) for k, o in sorted(st["obs"].items()) if k not in st["amb"] and o["facts"].get("instrument") == instrument]
    def candidates(self, key: str) -> dict:
        """The complete immutable candidate evidence for a key (cid -> record)."""
        return dict(self._replay()["cands"].get(key, {}))

    def resolve_ambiguity(self, key: str, chosen_cid: str, creator: str, certifier: str):
        """Selects the EXACT candidate (by candidate id: payload digest + availability + vintage). Restorative resolution is source-approved evidence; the approval source is unbound, so a QUALIFIED core holds it
        (two caller names are not approval). The materialized view becomes the chosen candidate and the full history stays in the journal."""
        if not self.simulation: raise Refusal("source approval/evidence binding unbound", code="SOURCE_APPROVAL_BINDING_UNBOUND_HELD")
        if not creator or not certifier or creator == certifier: raise Refusal("creator!=certifier", code="CREATOR_IS_CERTIFIER")
        def decide(st):
            if key not in st["amb"] or chosen_cid not in st["amb"][key]: raise Refusal(key, code="NOT_A_PENDING_CANDIDATE")
            if not self._payload_reconstructs(st["cands"][key][chosen_cid]): raise Refusal(key, code="CANDIDATE_INTEGRITY_FAILED")
            return None, ("OBS_AMBIGUITY_RESOLVED", {"key": key, "cid": chosen_cid, "certifier": certifier})
        self._commit(decide)

    def observation_usable(self, key: str) -> bool:
        st = self._replay(); return key in st["obs"] and key not in st["amb"] and self._payload_reconstructs(st["obs"][key])

    @staticmethod
    def _payload_reconstructs(o) -> bool:
        try:
            return domain_hash("TRK/PAYLOAD", bytes.fromhex(o["payload_hex"])) == o["digest"] and TrackerCore._cid(o["digest"], o["available_asof"], o["vintage"]) == o["cid"]
        except Exception: return False

    # ---- B04 source contract: exactly one match + freshness ---------------------------------------
    @staticmethod
    def derive_fingerprint(envelope: dict) -> str:       # derived from structure, never from the provider's own label
        shape = {k: type(v).__name__ for k, v in envelope.items() if k not in ("label", "contract_label", "watermark")}
        return domain_hash("TRK/ENVELOPE_SHAPE", canonical_bytes(shape))

    def register_contract(self, cid: str, version: str, fingerprint: str, max_staleness: int, battery_passed: bool):
        if not all(isinstance(x, str) and x for x in (cid, version, fingerprint)) or not _int(max_staleness) or max_staleness < 0 or not isinstance(battery_passed, bool):
            raise Refusal("contract fields (explicit non-negative integer staleness bound and bool battery result required; no defaults)", code="CONTRACT_FIELDS_INVALID")
        self._commit(lambda st: (None, ("CONTRACT_REGISTERED", {"id": cid, "version": version, "fingerprint": fingerprint, "max_staleness": max_staleness, "battery_passed": bool(battery_passed)})))

    def resolve_contract(self, envelope: dict, raw: bytes, now: int):
        if not isinstance(envelope, dict) or not isinstance(raw, bytes) or not _int(now) or now < 0: raise Refusal("contract resolution inputs", code="CONTRACT_INPUT_INVALID")
        fp = self.derive_fingerprint(envelope); rd = domain_hash("TRK/RAW", raw); out = {}
        def decide(st):
            hits = [c for c in st["contracts"].values() if c["fingerprint"] == fp]
            if len(hits) != 1:
                why = "ZERO_MATCH" if not hits else "MULTI_MATCH"; out["r"] = ("QUARANTINED", why)
                return None, ("CONTRACT_QUARANTINED", {"raw_digest": rd, "why": why, "raw_hex": raw.hex()})
            c = hits[0]
            if not c["battery_passed"]: out["r"] = ("NOT_USABLE", "CHALLENGE_BATTERY_NOT_PASSED"); return None, None
            wm = envelope.get("watermark")
            if not _int(wm) or wm < 0: out["r"] = ("HELD", "MISSING_OR_MALFORMED_WATERMARK"); return None, None
            if wm > now: out["r"] = ("HELD", "FUTURE_WATERMARK"); return None, None             # negative age is never fresh
            if now - wm > c["max_staleness"]: out["r"] = ("HELD", "STALE_WATERMARK"); return None, None
            out["r"] = ("RESOLVED", (c["id"], c["version"])); return None, None
        self._commit(decide); return out["r"]

    # ---- B03 snapshot: members come from STORED observation facts, never from the caller -----------
    def register_mixed_policy(self, pid: str, declared_by: str, expires_at: int):
        """SIMULATION-ONLY convenience: a governed MIXED_DECLARED policy (identity, owner, freshness, revocation) is source-owned and UNBOUND; this records a candidate for simulation evidence only."""
        if not self.simulation: raise Refusal("governed MIXED_DECLARED policy source unbound", code="MIXED_DECLARED_POLICY_UNBOUND_HELD")
        if not pid or not declared_by or not _int(expires_at): raise Refusal("policy", code="POLICY_INCOMPLETE")
        self._commit(lambda st: (None, ("MIXED_POLICY", {"id": pid, "declared_by": declared_by, "expires_at": expires_at, "revoked": False})))

    def revoke_mixed_policy(self, pid: str):
        self._commit(lambda st: (None, ("MIXED_POLICY_REVOKED", {"id": pid})))

    @staticmethod
    def _members_from_store(st, instrument, member_keys, claims):
        out = []
        for k in member_keys:
            o = st["obs"].get(k)
            if o is None or k in st["amb"] or not TrackerCore._payload_reconstructs(o): raise Refusal(k, code="MEMBER_NOT_USABLE_OBSERVATION")
            f = o["facts"]
            if f["instrument"] != instrument: raise Refusal(k, code="CROSS_INSTRUMENT_MEMBER")
            m = {"key": k, "timeframe": f["timeframe"], "vintage": o["vintage"], "available_asof": o["available_asof"], "digest": o["digest"], "schema_version": f["schema_version"]}
            c = (claims or {}).get(k)
            if c is not None and any(c.get(n) != m[n] for n in c):
                raise Refusal(k, code="MEMBER_CLAIM_MISMATCH")                  # a caller's replacement scope/timeframe/vintage/availability is refused
            out.append(m)
        return out

    def seal(self, instrument: str, query_asof: int, fence: int, member_keys: list, mixed_policy_id=None, claims=None):
        res = {}
        def decide(st):
            if not _int(query_asof) or not _int(fence) or query_asof > fence: raise Refusal("query_asof after fence", code="ASOF_AFTER_FENCE")
            mem = self._members_from_store(st, instrument, member_keys, claims)
            for m in mem:
                if self._blocked(st, m["key"]): raise Refusal(m["key"], code="MEMBER_BLOCKED")
            inc = [m for m in mem if m["available_asof"] < fence]                # half-open: equality excluded
            tfs = {}
            for m in inc: tfs.setdefault(m["timeframe"], set()).add(m["vintage"])
            mixed = len({v for vs in tfs.values() for v in vs}) > 1 or any(len(v) > 1 for v in tfs.values())
            kind = "SEALED"
            if mixed:
                if not self.simulation: res["r"] = ("MIXED_DECLARED_POLICY_UNBOUND_HELD", None); return None, None
                p = st["policies"].get(mixed_policy_id)
                if p is None or p.get("revoked") or query_asof >= p["expires_at"]: res["r"] = ("MIXED_VINTAGE_REFUSED", None); return None, None
                kind = "SIMULATION_MIXED_VIEW"                                    # NOT a single causal snapshot
            body = {"kind": kind, "instrument": instrument, "query_asof": query_asof, "fence": fence, "members": sorted(inc, key=lambda x: x["key"]), "mixed_policy": mixed_policy_id if mixed else None}
            h = domain_hash("TRK/SNAPSHOT_CANDIDATE", canonical_bytes(body)); res["r"] = (kind, h)
            return None, (None if h in st["snaps"] else ("SNAPSHOT_SEALED", dict(body, hash=h)))
        self._commit(decide); return res["r"]

    def verify_snapshot(self, h: str, instrument, query_asof, fence, member_keys, mixed_policy_id=None) -> bool:
        st = self._replay(); s = st["snaps"].get(h)
        if s is None: return False
        try:
            mem = self._members_from_store(st, instrument, member_keys, None)
        except Refusal: return False
        inc = sorted([m for m in mem if m["available_asof"] < fence], key=lambda x: x["key"])
        body = {"kind": s["kind"], "instrument": instrument, "query_asof": query_asof, "fence": fence, "members": inc, "mixed_policy": mixed_policy_id if s["kind"] != "SEALED" else None}
        return domain_hash("TRK/SNAPSHOT_CANDIDATE", canonical_bytes(body)) == h

    # ---- B05 semantic epoch / dependent invalidation ----------------------------------------------
    def declare_dependency(self, dependent: str, upstream: str):
        if dependent == upstream: raise Refusal(dependent, code="SELF_DEPENDENCY")
        def decide(st):
            if dependent in st["anc"]: raise Refusal(dependent, code="ANCESTRY_ALREADY_DECLARED_COMPLETE")           # an edge added after a completeness assertion would contradict it
            if self._reaches(st, upstream, dependent): raise Refusal(dependent, code="DEPENDENCY_CYCLE")
            return None, ("DEPENDENCY", {"dependent": dependent, "upstream": upstream})
        self._commit(decide)

    def declare_ancestry_complete(self, subject: str, source_ref: str):
        """SUPPLIED, UNADMITTED assertion that the dependency edges recorded for `subject` (possibly none) are its complete ancestry. A declaration with no edges is a PROVEN-EMPTY claim only as far as the supplying source is
        trusted: nothing here can verify completeness (no source-defined proof adapter exists). Absent declaration is UNKNOWN, never empty. Later edges for the subject are refused."""
        if not (isinstance(subject, str) and subject and isinstance(source_ref, str) and source_ref): raise Refusal("ancestry declaration", code="ANCESTRY_DECLARATION_INVALID")
        self._commit(lambda st: (None, None) if subject in st["anc"] and st["anc"][subject]["edges"] == sorted(st["ups"].get(subject, [])) else (None, ("ANCESTRY_COMPLETE", {"subject": subject, "edges": sorted(st["ups"].get(subject, [])), "source_ref": source_ref, "admission": "CALLER_ASSERTED_UNADMITTED"})))
    @staticmethod
    def _ancestry_blocks(st, subject):
        """Required ancestry: the subject AND every transitive upstream must carry a completeness declaration. An undeclared node is UNKNOWN ancestry => blocks. A subject unrelated to the unknown one is unaffected."""
        out = []; seen, stack = set(), [subject]
        while stack:
            c = stack.pop()
            if c in seen: continue
            seen.add(c)
            if c not in st["anc"]: out.append("REQUIRED_ANCESTRY_UNKNOWN:" + c)
            else: stack += st["ups"].get(c, [])
        return out
    @staticmethod
    def _reaches(st, start, target):                      # does `start` already depend (transitively) on `target`?
        seen, stack = set(), [start]
        while stack:
            c = stack.pop()
            if c == target: return True
            if c in seen: continue
            seen.add(c); stack += st["ups"].get(c, [])
        return False

    def advance_epoch(self, key: str, epoch: int):
        def decide(st):
            if not _int(epoch) or epoch <= st["epoch"].get(key, 0): raise Refusal(key, code="EPOCH_NOT_ADVANCING")
            return None, ("EPOCH", {"key": key, "epoch": epoch})
        self._commit(decide)

    def _basis(self, st, subject):
        """The current epoch basis of a subject: its own epoch and every recorded ancestor's. A witness is valid only for the basis it was recorded under."""
        return [[k, st["epoch"].get(k, 0)] for k in sorted({subject, *self._closure(st, subject)})]

    def reresolve(self, key: str, version: str, now: int):
        """Clears an invalidation only with a FRESH witness (recorded after the LATEST invalidation AND under the current epoch basis) and only when every recorded upstream is itself valid. The witness
        is caller-asserted evidence, so a QUALIFIED core holds this (verifier binding unbound). D25 clearance policy is source-owned and unresolved: nothing is restored automatically.
        R24: the witness must be POSITIVE for the requested version at `now` (L1 PASS and, when required, L2 PASS; not FAIL/UNAVAILABLE/future/stale/wrong-version). This clears ONLY the epoch
        invalidation marker (an epoch acknowledgement): it neither lifts a quarantine nor makes the subject eligible - eligible_asof still evaluates every condition itself."""
        if not self.simulation: raise Refusal("fresh permitted witness/materialization binding unbound", code="VERIFIER_BINDING_UNBOUND_HELD")
        def decide(st):
            if key not in st["inval"]: raise Refusal(key, code="NOT_INVALIDATED")
            if any(u in st["inval"] or self._blocked(st, u) for u in st["ups"].get(key, [])): raise Refusal(key, code="UPSTREAM_STILL_INVALID")
            h = st["health"].get(key)
            if h is None or h["seq"] <= st["inval"][key][1] or h["basis"] != self._basis(st, key): raise Refusal(key, code="NO_FRESH_WITNESS")
            if self._health(st, key, version, now) != "HEALTHY": raise Refusal(key, code="WITNESS_NOT_POSITIVE")      # FAIL/UNAVAILABLE/future/stale/wrong-version never clears
            return None, ("RERESOLVED", {"key": key, "version": version})
        self._commit(decide)

    # ---- quarantine: multi-reason, retry suppression, reopen != reactivation ------------------------
    def quarantine(self, subject: str, reason: str):
        self._commit(lambda st: (None, ("Q_REASON", {"subject": subject, "reason": reason})))
    REASON_CONTEXT_DOMAIN_METADATA_MISSING = "CONTEXT_DOMAIN_METADATA_MISSING"
    def fail_closed_missing_context_metadata(self, subject: str, *, subject_kind: str = "TRACKER", mv=None, fence: int = None) -> "FailClosedResult":
        """Existing-authority SAFETY action for an already defective subject whose Context-domain metadata is missing (DecisionContextV4 FAIL-CLOSED SAFETY RULE, source clause cited by ID/range only).
        Available in BOTH modes: a generic qualification hold never suppresses a risk-reducing action. What this DOES, in one atomic journal record: opens the Core quarantine reason and raises the
        source-named review `CONTEXT_DOMAIN_RESOLUTION_FAILURE` (derived from `fail_closed_transition`, not retyped). Restoration stays prohibited until governed context exists.
        What this does NOT do (exact integration blocker, R24): it does not transition the OWNING lifecycle authority. The existing ChainStatusAuthority is keyed by materialization version (mv), the Core
        by subject string, and no source-bound subject->mv mapping or status-kind choice (DEGRADED_NOT_CURRENT vs HALTED, the latter terminal) is supplied, so none is invented. When a bound chain and an
        mv are supplied the result REPORTS whether the chain still reads CURRENT; it is never reported as applied."""
        if subject_kind not in SUBJECT_DOMAIN: raise Refusal(subject_kind, code="UNKNOWN_SUBJECT_KIND")
        decision = fail_closed_transition(subject_kind, True, False)               # the source rule: apply=True, review raised, restoration prohibited
        self._commit(lambda st: (None, ("Q_REASON_WITH_REVIEW", {"subject": subject, "reason": self.REASON_CONTEXT_DOMAIN_METADATA_MISSING, "review": decision["review"]})))
        chain = "NO_CHAIN_BOUND_OR_MV_NOT_SUPPLIED"
        if self._chain is not None and mv is not None and fence is not None:
            f = self._chain.status_at(mv, fence); chain = "CHAIN_STILL_CURRENT" if (f is not None and f.status == "CURRENT") else ("CHAIN_NOT_CURRENT" if f is not None else "CHAIN_NO_VISIBLE_STATUS")
        return FailClosedResult(subject, True, decision["review"], decision["restoration_allowed"], "NOT_APPLIED_SUBJECT_TO_MV_AND_STATUS_KIND_MAPPING_UNBOUND", chain)

    def reviews(self, subject: str) -> list: return list(self._replay()["reviews"].get(subject, []))
    def clear_reason(self, subject: str, reason: str, certifier: str, creator: str):
        if not self.simulation: raise Refusal("source approval/evidence binding unbound", code="SOURCE_APPROVAL_BINDING_UNBOUND_HELD")
        if not certifier or certifier == creator: raise Refusal("creator!=certifier", code="CREATOR_IS_CERTIFIER")
        if reason == self.REASON_CONTEXT_DOMAIN_METADATA_MISSING: raise Refusal(reason, code="RESTORATION_PROHIBITED_UNTIL_GOVERNED_CONTEXT")   # no governed context exists to bind (D2/Context registry)
        def decide(st):
            if reason not in st["q"].get(subject, {"reasons": set()})["reasons"]: raise Refusal(reason, code="REASON_NOT_OPEN")
            return None, ("Q_CLEAR", {"subject": subject, "reason": reason})
        self._commit(decide)

    def retry_allowed(self, subject: str) -> bool:
        q = self._replay()["q"].get(subject); return q is None or (not q["reasons"] and q["status"] == "ACTIVE")
    def reopen(self, subject: str):
        def decide(st):
            if subject not in st["q"]: raise Refusal(subject, code="NOT_QUARANTINED")
            return None, ("Q_REOPEN", {"subject": subject})                   # reopen alone never reactivates
        self._commit(decide)

    def _closure(self, st, subject):
        seen, stack = set(), list(st["ups"].get(subject, []))
        while stack:
            c = stack.pop()
            if c in seen: continue
            seen.add(c); stack += st["ups"].get(c, [])
        return sorted(seen)

    def blast_radius(self, subject: str) -> dict:
        """Health blast radius of `subject` over the DECLARED dependency edges (reverse closure): every subject that depends on it transitively and is therefore blocked while it is (UPSTREAM_BLOCKED). Unrelated subjects are
        never listed. It reads only the journal's declared edges: an undeclared dependency is invisible here (a declared-edge fact, not a completeness proof of the dependency graph)."""
        st = self._replay(); dependents, stack = set(), [subject]
        while stack:
            cur = stack.pop()
            for d, ups in st["ups"].items():
                if cur in ups and d not in dependents: dependents.add(d); stack.append(d)
        return {"subject": subject, "dependents": sorted(dependents), "basis": "DECLARED_EDGES_ONLY"}
    def _reconstructable(self, st, up, _seen=frozenset()) -> bool:
        """Genuine reconstruction only: a persisted raw observation whose payload reproduces its digest, or a derived node whose ENTIRE recorded ancestry is itself so reconstructable. A Health record or an
        identity is never reconstruction evidence (R23). Current source/code/environment/contract proof is unbound, hence the qualified hold in `reactivate`."""
        if up in _seen or self._blocked(st, up): return False
        o = st["obs"].get(up)
        if o is not None: return up not in st["amb"] and self._payload_reconstructs(o)
        ups = st["ups"].get(up, [])
        return bool(ups) and all(self._reconstructable(st, u, _seen | {up}) for u in ups)

    def reactivate(self, subject: str):
        """The closure is the RECORDED dependency closure (the caller supplies no list). Dependency identity recorded != dependency reconstructable: every ancestor must reproduce from persisted
        material. Current source/code/environment/contract/raw reconstruction PROOF has no bound source, so a QUALIFIED core holds reactivation."""
        if not self.simulation: raise Refusal("reconstruction proof binding unbound", code="RECONSTRUCTION_PROOF_BINDING_UNBOUND_HELD")
        def decide(st):
            q = st["q"].get(subject)
            if q is None or q["reasons"]: raise Refusal(subject, code="REASONS_STILL_OPEN")
            bad = [u for u in self._closure(st, subject) if not self._reconstructable(st, u)]
            if bad: raise Refusal(",".join(bad), code="NOT_RECONSTRUCTABLE")
            return None, ("Q_REACTIVATE", {"subject": subject})
        self._commit(decide)

    def _blocked(self, st, key) -> list:
        out = []; q = st["q"].get(key)
        if q and (q["reasons"] or q["status"] != "ACTIVE"): out.append("QUARANTINED")
        if key in st["inval"]: out.append("EPOCH_INVALIDATED")
        if key in st["amb"]: out.append("OBSERVATION_AMBIGUOUS")
        for u in self._closure(st, key):                                     # reverse-dependency propagation: a blocked ancestor blocks the dependent
            uq = st["q"].get(u)
            if (uq and (uq["reasons"] or uq["status"] != "ACTIVE")) or u in st["inval"] or u in st["amb"]:
                out.append("UPSTREAM_BLOCKED"); break
        return out
    def blocked(self, key: str) -> list: return self._blocked(self._replay(), key)

    # ---- B14 verification / Recording Health (caller-asserted evidence until a verifier is bound) ------
    def record_verification(self, subject: str, version: str, l2_requirement: str, l2_status: str, l1: str, at: int, max_age: int, verifier_id: str, result_digest: str, definition_ref: str = None, evidence_class: str = "CALLER_ASSERTED", result=None):
        if evidence_class not in EVIDENCE_CLASSES: raise Refusal(str(evidence_class), code="HEALTH_EVIDENCE_CLASS_UNKNOWN")
        if evidence_class == COMPOSED_RECOMPUTATION:       # the composed label is earned by a typed verifier result bound to THIS subject/digest/levels, never asserted by label alone
            from ..tracker.verification.verification_result import SCOPE_MATERIALIZATION, COMPOSED_VERIFIER_ID, split_levels, result_is_self_consistent, issued_by_verifier_run
            if result is None: raise Refusal("composed evidence needs the verifier result", code="HEALTH_COMPOSED_RESULT_MISSING")
            if not result_is_self_consistent(result): raise Refusal("result not self-consistent", code="HEALTH_COMPOSED_RESULT_FORGED")
            if (result.scope != SCOPE_MATERIALIZATION or verifier_id != COMPOSED_VERIFIER_ID or result_digest != result.result_hash
                    or dict(result.subject).get("expect_scope_key") != subject or l2_requirement != "REQUIRED" or (l1, l2_status) != split_levels(result)
                    or str(dict(result.subject).get("expect_scope_key")).rsplit("/", 1)[-1] != version):      # the verified VERSION (last scope-key segment), not only the scope-key string
                raise Refusal("composed evidence not bound to result", code="HEALTH_COMPOSED_RESULT_UNBOUND")
            if not issued_by_verifier_run(result): raise Refusal("a structurally valid result is not a verifier run", code="HEALTH_COMPOSED_RESULT_NOT_FROM_VERIFIER_RUN")   # asserted PASS-shaped objects (incl. FAIL-shaped) stay CALLER_ASSERTED; checked after binding so mismatches keep their exact code
        elif result is not None: raise Refusal("result only for composed evidence", code="HEALTH_RESULT_WITHOUT_COMPOSED_CLASS")
        if l2_requirement not in REQ or l2_status not in L2_ST or l1 not in L1_ST: raise Refusal("vocabulary", code="HEALTH_VOCABULARY_UNKNOWN")
        if not _int(at) or at < 0 or not _int(max_age) or max_age <= 0: raise Refusal("interval", code="HEALTH_INTERVAL_INVALID")
        if not all(isinstance(x, str) and x for x in (subject, version, verifier_id, result_digest)): raise Refusal("binding", code="HEALTH_BINDING_INCOMPLETE")
        if l2_requirement == "NOT_APPLICABLE_BY_GOVERNED_DEFINITION" and not definition_ref: raise Refusal("definition proof", code="NOT_APPLICABLE_NEEDS_DEFINITION_PROOF")
        self._commit(lambda st: (None, ("HEALTH", {"subject": subject, "version": version, "req": l2_requirement, "l2": l2_status, "l1": l1, "at": at, "max_age": max_age,
                                                    "verifier_id": verifier_id, "result_digest": result_digest, "definition_ref": definition_ref or "", "evidence_class": evidence_class,
                                                    "basis": self._basis(st, subject)})))

    def reverify(self, subject: str, version: str, verifier, now: int, l2_requirement: str, max_age: int, definition_ref: str = None):
        """Re-verification trigger path: RUNS the supplied verifier (callable(subject, version) -> (l1, l2, result_digest)) and records its result. Binding this to the real L2 recomputation
        (stateful_verifier / independent_traversal over a materialization) is NOT wired: the qualified pipeline holds before materialization."""
        l1, l2, dg = verifier(subject, version)
        self.record_verification(subject, version, l2_requirement, l2, l1, now, max_age, getattr(verifier, "__name__", "verifier"), dg, definition_ref)

    def record_reverify_pass(self, pass_id: str, now: int, max_items: int, items: list):
        """Durable record of ONE bounded re-verification pass: every item (VERIFIED / UNBOUND / REFUSED / KEY_MISMATCH / SKIPPED_BOUND_EXCEEDED) with its detail, so work that was NOT done stays visible after restart and is never
        mistaken for health (health is only the verifier's recorded result). Idempotent for identical content; the same pass id with different content is refused. Candidate mechanics: not a daemon, no cadence/burst/resource policy is defined."""
        if not (isinstance(pass_id, str) and pass_id and _int(now) and _int(max_items) and max_items >= 1 and isinstance(items, list)): raise Refusal("pass", code="REVERIFY_PASS_INVALID")
        body = {"pass_id": pass_id, "at": now, "max_items": max_items, "items": [list(i) for i in items]}
        def d(st):
            old = st["passes"].get(pass_id)
            if old is not None:
                if {k: old[k] for k in body} == _s(body): return None, None
                raise Refusal(pass_id, code="REVERIFY_PASS_ID_REUSED")
            return None, ("REVERIFY_PASS", body)
        self._commit(d)
    def reverify_pass(self, pass_id: str):
        p = self._replay()["passes"].get(pass_id); return None if p is None else dict(p)
    def request_reverification(self, subject: str, trigger: str):
        if trigger not in ("STALE", "ABSENT", "EPOCH_ADVANCED", "QUARANTINE_CLEARED", "SCHEDULED"): raise Refusal(trigger, code="UNKNOWN_REVERIFY_TRIGGER")
        self._commit(lambda st: (None, ("REVERIFY_REQUESTED", {"key": subject, "trigger": trigger})))

    def due_for_reverification(self, subjects, now: int, versions: dict = None) -> list:
        """versions: optional {subject: expected_version}. Health recorded for a DIFFERENT version never satisfies the expected one (it is ABSENT for that version) and never suppresses needed work."""
        st = self._replay(); due = []
        for s in subjects:
            h = st["health"].get(s)
            if h is None or (versions is not None and s in versions and h["version"] != versions[s]): due.append((s, "ABSENT"))
            elif h["at"] > now or now - h["at"] > h["max_age"]: due.append((s, "STALE"))
            elif st["reverify"].get(s, 0) >= h["seq"]: due.append((s, "EPOCH_ADVANCED"))
        return due

    def _health(self, st, subject, version, now) -> str:
        h = st["health"].get(subject)
        if h is None or h["version"] != version: return "UNKNOWN"
        if h["at"] > now or now - h["at"] > h["max_age"]: return "UNKNOWN"                # future or stale evidence never certifies
        if h["basis"] != self._basis(st, subject): return "UNKNOWN"                      # recorded under a different epoch basis
        if st["reverify"].get(subject, 0) >= h["seq"]: return "UNKNOWN"                   # a later epoch/reverification request supersedes this evidence
        if h["l1"] == "FAIL" or h["l2"] == "FAIL": return "NOT_HEALTHY"
        if h["req"] == "REQUIRED": return "HEALTHY" if h["l2"] == "PASS" else "UNKNOWN"   # UNAVAILABLE L2 never falls back to L1
        return "HEALTHY"
    def recording_health(self, subject: str, version: str, now: int) -> "HealthReading":
        """Typed reading. The calculation is over CALLER-ASSERTED evidence, so it is never presented as qualified Recording Health: a qualified core reports state HELD (the local calculation stays visible as
        `local_state`); a simulation core reports the calculation labelled SIMULATION_CALLER_ASSERTED. NOT_APPLICABLE is not an admitted definition proof; reverify() is an injected callable."""
        local = self._health(self._replay(), subject, version, now)
        h = self._replay()["health"].get(subject); composed = h is not None and h.get("evidence_class") == COMPOSED_RECOMPUTATION
        return HealthReading(local if self.simulation else HELD, ("SIMULATION_COMPOSED_RECOMPUTATION" if composed else "SIMULATION_CALLER_ASSERTED") if self.simulation else "QUALIFIED_HELD", local, False)

    # ---- as-of eligibility: bound to the ONE existing chain-status authority; qualified use is HELD -----
    def eligible_asof(self, subject: str, version: str, asof_seq: int, now: int, *, mv=None, fence=None) -> dict:
        st = self._replay(asof_seq); reasons = []
        if self._blocked(st, subject): reasons += self._blocked(st, subject)
        if self._health(st, subject, version, now) != "HEALTHY": reasons.append("RECORDING_HEALTH_NOT_HEALTHY")
        reasons += self._proof_blocks(st, subject, version, now)
        if self._chain is not None and mv is not None and fence is not None:
            f = self._chain.status_at(mv, fence)
            if f is None or f.status != "CURRENT": reasons.append("CHAIN_STATUS_NOT_CURRENT")
        if self.simulation:
            return {"state": SIM_NOT_ELIGIBLE if reasons else SIM_ELIGIBLE, "eligible": False, "reasons": reasons, "mode": "SIMULATION_EVIDENCE_ONLY"}
        missing = list(QUALIFIED_PREREQS_UNBOUND) + ([] if self._chain is not None else ["BASELINE_LIFECYCLE_AUTHORITY_UNBOUND"])
        return {"state": HELD, "eligible": False, "reasons": reasons, "undetermined_inputs": missing, "mode": "QUALIFIED_HELD"}

    def resolve_snapshot(self, query_asof: int, streams: dict):
        """Cross-timeframe snapshot resolution over the bound timeframe registry (UNBOUND registry => refusal: no calendar default). Journals the per-timeframe result; it selects/binds nothing else."""
        from . import time_family as TF
        if self._timeframes is None: raise Refusal("registry", code="TIMEFRAME_REGISTRY_UNBOUND")
        r = TF.resolve_snapshot(self._timeframes, query_asof, streams)
        self._commit(lambda st: (None, ("SNAPSHOT_RESOLVED", {"query_asof": query_asof, "state": r.state, "entries": [[e.timeframe, e.selection.state, e.selection.parent_id, e.vintage, e.watermark, e.state, list(e.reasons)] for e in r.entries]})))
        return r
    def resolve_sealed_snapshot(self, instrument: str, query_asof: int, fence: int, member_keys: list, parents_by_tf: dict, watermarks_by_tf: dict, mixed_policy_id=None) -> dict:
        """ONE bounded callpath: seal (store-backed members, half-open fence, mixed-vintage default-deny) -> per-timeframe selection ONLY among SEALED members -> per-timeframe vintage read from the sealed records -> resolve over the bound
        timeframe registry. `parents_by_tf` = {timeframe: [(member_key, complete_bool)]}: the caller names candidate parents and their completeness (segmentation proof is `time_family.parent_complete`, supplied) but AVAILABILITY and VINTAGE come
        from the sealed observation records, never from the caller; a parent excluded by the fence or absent from the seal cannot be selected. `watermarks_by_tf` are SUPPLIED per-timeframe currentness watermarks (no store source exists; unadmitted).
        A non-SEALED kind (mixed view / held policy) is returned UNRESOLVED_HELD with no selection. The result journals the sealed hash it bound. Candidate mechanics: no calendar, freshness policy or threshold is invented."""
        from . import time_family as TF
        if self._timeframes is None: raise Refusal("registry", code="TIMEFRAME_REGISTRY_UNBOUND")
        if not isinstance(parents_by_tf, dict) or not parents_by_tf or not isinstance(watermarks_by_tf, dict): raise Refusal("streams", code="SNAPSHOT_STREAMS_INVALID")
        kind, h = self.seal(instrument, query_asof, fence, member_keys, mixed_policy_id)
        if kind != "SEALED" or h is None: return {"state": "UNRESOLVED_HELD", "reason": kind, "base_seal_hash": h, "resolved_manifest_hash": None, "resolution": None}
        st = self._replay(); members = {m["key"]: m for m in st["snaps"][h]["members"]}
        if not self.verify_snapshot(h, instrument, query_asof, fence, member_keys): raise IntegrityFailure("sealed snapshot does not re-derive")
        streams = {}
        for tf, cands in sorted(parents_by_tf.items()):
            self._timeframes.require(tf)
            vint = sorted({m["vintage"] for m in members.values() if m["timeframe"] == tf})
            plist = []
            for key, complete in cands:
                m = members.get(key)
                if m is None: raise Refusal(key, code="PARENT_NOT_IN_SEALED_SNAPSHOT")                 # excluded by the half-open fence, unknown, or not a member
                if m["timeframe"] != tf: raise Refusal(key, code="PARENT_TIMEFRAME_MISMATCH")
                plist.append((key, m["available_asof"], complete))
            streams[tf] = TF.StreamView(tuple(plist), vint[0] if vint else None, watermarks_by_tf.get(tf))       # a SEALED snapshot is single-vintage (mixed => held above), so >1 is unreachable; none => VINTAGE_NOT_RESOLVED
        r = TF.resolve_snapshot(self._timeframes, query_asof, streams)
        ents = [{"timeframe": e.timeframe, "selection_state": e.selection.state, "parent_id": e.selection.parent_id, "parent_available_asof": e.selection.available_asof, "candidates": sorted(list(v) for v in streams[e.timeframe].parents),
                 "vintage": e.vintage, "watermark": e.watermark, "state": e.state, "reasons": list(e.reasons)} for e in r.entries]
        body = {"label": "CANDIDATE_RESOLVED_SNAPSHOT_COMPOSITION_NOT_THE_REGISTRY_TRACKER_SNAPSHOT_MANIFEST", "base_seal_hash": h, "instrument": instrument, "query_asof": query_asof, "fence": fence, "mixed_policy": mixed_policy_id,
                "registry_basis": [list(x) for x in self._timeframes.basis()], "state": r.state, "entries": ents, "supplied_unadmitted": ["watermarks", "parent_completeness", "segmentation"]}
        mh = domain_hash("TRK/RESOLVED_SNAPSHOT_CANDIDATE", canonical_bytes(body))
        self._commit(lambda st2: (None, None) if mh in st2["resolved"] else (None, ("SNAPSHOT_RESOLVED_MANIFEST", dict(body, resolved_manifest_hash=mh))))
        self._commit(lambda st2: (None, ("SNAPSHOT_RESOLVED", {"query_asof": query_asof, "base_seal_hash": h, "resolved_manifest_hash": mh, "state": r.state, "entries": [[e.timeframe, e.selection.state, e.selection.parent_id, e.vintage, e.watermark, e.state, list(e.reasons)] for e in r.entries]})))
        return {"state": r.state, "reason": "", "base_seal_hash": h, "resolved_manifest_hash": mh, "resolution": r}
    def resolved_manifest(self, mh: str):
        """Detached copy of a journaled resolved-snapshot CANDIDATE composition (internal label/hash; NOT the Registry TRACKER_SNAPSHOT_MANIFEST: no normative byte layout or admission is inferred)."""
        import copy
        b = self._replay()["resolved"].get(mh); return None if b is None else copy.deepcopy(b)

    @staticmethod
    def _proof_blocks(st, subject, version, now, require_authority=False, require_transform=False):
        """Reasons from journaled evidence-truth / transform verdicts that bind EXACTLY (subject, version). Freshness is checked at USE time. Absence of a verdict blocks only when the caller declares the proof REQUIRED
        (no battery/proof is invented as universally required)."""
        out = []; a = [b for b in st["authev"].values() if b["subject"] == subject and b["version"] == version]; x = [b for b in st["xform"].values() if b["subject"] == subject and b["version"] == version]
        for b in a:
            if b["status"] != "VALID": out.append("AUTHORITY_TRANSITION_EVIDENCE_NOT_VALID")
            elif b["valid_until"] is None or now > b["valid_until"] or now < b["at"]: out.append("AUTHORITY_TRANSITION_EVIDENCE_STALE_AT_USE")
        for b in x:
            if b["status"] != "VALID": out.append("TRANSFORM_NOT_CAUSAL_OR_UNPROVEN")
        if require_authority and not any(b["status"] == "VALID" for b in a): out.append("AUTHORITY_TRANSITION_EVIDENCE_REQUIRED_UNPROVEN")
        if require_transform and not any(b["status"] == "VALID" for b in x): out.append("TRANSFORM_PROOF_REQUIRED_UNPROVEN")
        return sorted(set(out))
    def judge_transition_evidence(self, claim, index: dict, now: int):
        """Candidate evidence-truth predicate (tracker.evidence_truth) with its verdict journaled WITH the full claim binding (subject, version/hash, scope, battery, vintage, dependencies, evidence refs, freshness end); the
        caller-supplied index is NOT an admitted authority. Records the verdict; never advances authority. A malformed claim is journaled nowhere (refused)."""
        from ..tracker.evidence_truth import judge_transition_evidence, valid_until, TransitionClaim
        v = judge_transition_evidence(claim, index, now)
        if not isinstance(claim, TransitionClaim) or v.reasons == ("CLAIM_MALFORMED",): raise Refusal("claim", code="TRANSITION_CLAIM_MALFORMED")
        self._commit(lambda st: (None, ("AUTH_EVIDENCE", {"subject": claim.subject, "version": claim.version_or_hash, "instrument": claim.instrument, "timeframe": claim.timeframe, "battery": claim.battery, "vintage": claim.vintage,
                                                         "dependencies": list(claim.dependencies), "refs": list(claim.evidence_refs), "status": v.status, "reasons": list(v.reasons), "at": now,
                                                         "valid_until": valid_until(claim, index) if v.status == "VALID" else None})))
        return v
    def judge_transform(self, subject: str, spec, feature_version: str):
        from ..tracker.evidence_truth import judge_transform
        if not (isinstance(subject, str) and subject and isinstance(feature_version, str) and feature_version): raise Refusal("binding", code="TRANSFORM_BINDING_INCOMPLETE")
        v = judge_transform(spec)
        self._commit(lambda st: (None, ("TRANSFORM_VERDICT", {"subject": subject, "version": feature_version, "kind": str(getattr(spec, "kind", "")), "transform_version": str(getattr(spec, "version", "")),
                                                              "lineage_ref": str(getattr(spec, "lineage_ref", "")), "status": v.status, "reasons": list(v.reasons)})))
        return v

    # ---- subject <-> dependency association (explicit INPUT; no kernel-string to frozen-ID mapping is invented) ----
    @staticmethod
    def _bhex(b): return [b.feature_id.hex(), b.feature_version, b.instrument_id.hex(), b.timeframe_id.hex()]
    def associate_subject(self, subject: str, binding, source_ref: str):
        """Records that Health subject `subject` is asserted to speak for the dependency `binding`. The assertion is CALLER-SUPPLIED and UNADMITTED (its owner/appointment is an input, not defined here); Core only refuses to issue a
        bound Health snapshot for an association it was never given."""
        if not (isinstance(subject, str) and subject and isinstance(source_ref, str) and source_ref) or not hasattr(binding, "feature_id"): raise Refusal("association", code="SUBJECT_ASSOCIATION_INVALID")
        if not isinstance(binding.feature_id, bytes) or not isinstance(binding.instrument_id, bytes) or not isinstance(binding.timeframe_id, bytes) or not isinstance(binding.feature_version, str): raise Refusal("binding types", code="SUBJECT_ASSOCIATION_INVALID")
        h = self._bhex(binding); self._commit(lambda st: (None, None) if h in st["assoc"].get(subject, []) else (None, ("SUBJECT_ASSOC", {"subject": subject, "binding": h, "source_ref": source_ref, "admission": "CALLER_ASSERTED_UNADMITTED"})))
    @staticmethod
    def _snapshot_id(subject, version, bhex, ref, resolved_at, acceptable, evidence_class, now, held, ra=False, rt=False, rn=False):
        return domain_hash("TRK/HEALTH_SNAPSHOT", canonical_bytes({"s": subject, "v": version, "b": bhex, "ref": repr(ref), "r": resolved_at, "a": acceptable, "c": evidence_class, "n": now, "h": held, "ra": ra, "rt": rt, "rn": rn}))
    def confirm_snapshot(self, snap) -> bool:
        """True only if `snap` is a Core-typed snapshot whose id re-derives from its own fields AND is present in this Core's journal as issued (survives restart). A replaced/forged field changes the id."""
        if type(snap) is not CoreHealthSnapshot or snap.binding is None: return False
        if self._snapshot_id(snap.subject, snap.version, self._bhex(snap.binding), snap.resolution_ref, snap.resolved_at, snap.acceptable, snap.evidence_class, snap.evaluated_at, snap.held_reason, snap.require_authority_evidence, snap.require_transform_proof, snap.require_ancestry) != snap.snapshot_id: return False
        return snap.snapshot_id in self._replay()["snapiss"]
    def _current_ok(self, st, subject, version, now, ra, rt, rn=False) -> bool:
        return self.simulation and not self._blocked(st, subject) and self._health(st, subject, version, now) == "HEALTHY" and not self._proof_blocks(st, subject, version, now, ra, rt) and not (rn and self._ancestry_blocks(st, subject))
    def snapshot_current_at_use(self, snap, use_at: int) -> bool:
        """Journal issuance proves only that THIS Core issued the snapshot; it is not current permission. At USE (a NEW ordinary binding) the issued snapshot must still be confirmable AND the same Health/blocks/epoch/
        evidence-truth/transform predicates, re-read from the CURRENT journal at `use_at`, must still accept the same (subject, version, binding). Quarantine, epoch invalidation, ambiguity, a later re-verification request,
        expired evidence and an invalidated proof all fail here. Already-finalized bindings are immutable and are NOT re-judged by this (no retroactive rewrite); no historical Health mode or threshold is invented
        (freshness uses the Health evidence's own max_age against `use_at`)."""
        if not self.confirm_snapshot(snap) or not _int(use_at) or use_at < snap.evaluated_at: return False
        st = self._replay()
        return self._current_ok(st, snap.subject, snap.version, use_at, snap.require_authority_evidence, snap.require_transform_proof, snap.require_ancestry)

    # ---- composition output: the health the downstream Gateway actually consumes -------------------
    def gateway_health(self, subject: str, version: str, now: int, ref, resolved_at: int, *, asof_seq: int = None, binding=None, require_authority_evidence: bool = False, require_transform_proof: bool = False, require_ancestry: bool = False):
        """binding: gateway.contracts.HealthBinding naming the dependency this reading speaks for. Without it the Gateway DENIES (HEALTH_BINDING_UNBOUND); its version must equal the queried Health version. A binding for which
        no subject association was ever supplied (`associate_subject`) is HELD (acceptable False, held_reason). The snapshot composes Recording Health, quarantine/epoch blocks AND journaled evidence-truth/transform verdicts
        for exactly (subject, version), checked at use time; the require_* flags make an absent proof held (the caller declares what is required; nothing is invented). The issued snapshot is journaled and confirmable."""
        from ..gateway.contracts import HealthSnapshot
        from dataclasses import dataclass
        if asof_seq is not None: raise Refusal("historical Health consistency mode has no source-correct rule here", code="HISTORICAL_HEALTH_MODE_UNRESOLVED")
        st = self._replay()
        ok = self._current_ok(st, subject, version, now, require_authority_evidence, require_transform_proof, require_ancestry)
        if binding is not None and getattr(binding, "feature_version", None) != version: raise Refusal("binding version != Health version", code="HEALTH_BINDING_VERSION_MISMATCH")
        held = ""
        if binding is not None and self._bhex(binding) not in st["assoc"].get(subject, []): ok = False; held = "SUBJECT_ASSOCIATION_UNBOUND"
        ec = "SIMULATION" if self.simulation else "QUALIFIED_HELD"
        sid = self._snapshot_id(subject, version, self._bhex(binding) if binding is not None else None, ref, resolved_at, ok, ec, now, held, require_authority_evidence, require_transform_proof, require_ancestry)
        if binding is not None: self._commit(lambda st2: (None, None) if sid in st2["snapiss"] else (None, ("SNAPSHOT_ISSUED", {"snapshot_id": sid, "subject": subject, "version": version, "at": now})))
        return CoreHealthSnapshot(ref, resolved_at, ok, ec, binding=binding, subject=subject, version=version, evaluated_at=now, held_reason=held, snapshot_id=sid, require_authority_evidence=require_authority_evidence, require_transform_proof=require_transform_proof, require_ancestry=require_ancestry)

    # Construction orders are NOT owned by Core: the single order/claim authority is tracker_component.ClaimService (see stage_a/composer/order_authority.py).

    # ---- reviewer / write-plane boundary ------------------------------------------------------------
    FINDING_FIELDS = ("finding_id", "task_origin", "summary", "author")
    def accept_finding(self, finding: dict):
        if not isinstance(finding, dict) or set(finding) != set(self.FINDING_FIELDS) or any(not isinstance(finding[k], str) or not finding[k] for k in self.FINDING_FIELDS):
            raise Refusal("finding carries non-finding fields or lacks task origin", code="REVIEW_INPUT_NOT_FINDING_ONLY")
        def d(st):
            for f in st["findings"]:
                if f["finding_id"] == finding["finding_id"]:
                    if {k: v for k, v in f.items() if k != "plane"} == finding: return None, None                                                  # identical re-submission: idempotent, nothing appended
                    raise Refusal(finding["finding_id"], code="FINDING_ID_REUSED")                      # same id, different content/task_origin: never two findings under one id
            return None, ("FINDING", dict(finding))
        self._commit(d)            # recorded only; mutates no state, authorizes nothing. LEGACY minimal carrier: no bound task/framing/denylist - use accept_review_finding for the §15 carrier

    # B22 (frozen Tracker DOCX section 15 reviewer boundary): Tracker-side carrier + guards. No SALIX AI is built or invoked; the carrier is recorded, never acted on.
    REVIEW_TASK_FIELDS = ("task_origin", "framing_hash", "context_hash", "forbidden_inputs", "permitted_evidence_refs")
    REVIEW_CARRIER_FIELDS = ("finding_id", "reviewer_role", "reviewer_version", "implementation", "topology", "context_hash", "task_origin", "framing_hash",
                             "evidence_refs", "affected_scope", "proposed_investigation", "forbidden_inputs", "author", "model_version")
    _LISTS = ("evidence_refs", "forbidden_inputs")
    @staticmethod
    def _strs(v): return isinstance(v, list) and all(isinstance(x, str) and x for x in v)
    def bind_review_task(self, task: dict):
        """Binds a review task (origin, framing hash, context hash, forbidden-input denylist) BEFORE any finding may cite it. The framing/denylist are supplied by the task owner, never by the reviewer."""
        if not isinstance(task, dict) or set(task) != set(self.REVIEW_TASK_FIELDS) or not all(isinstance(task[k], str) and task[k] for k in ("task_origin", "framing_hash", "context_hash")) or not self._strs(task["forbidden_inputs"]) or not self._strs(task["permitted_evidence_refs"]) or not task["permitted_evidence_refs"]:
            raise Refusal("review task shape", code="REVIEW_TASK_INVALID")
        def d(st):
            old = st["tasks"].get(task["task_origin"])
            if old is not None:
                if {k: old[k] for k in self.REVIEW_TASK_FIELDS} == task: return None, None
                raise Refusal(task["task_origin"], code="REVIEW_TASK_REBOUND")                          # a task's framing is never silently replaced
            return None, ("REVIEW_TASK", dict(task))
        self._commit(d)
    def accept_review_finding(self, c: dict):
        if not isinstance(c, dict) or set(c) != set(self.REVIEW_CARRIER_FIELDS): raise Refusal("carrier fields", code="REVIEW_CARRIER_FIELDS_INVALID")
        if any(not isinstance(c[k], str) or not c[k] for k in self.REVIEW_CARRIER_FIELDS if k not in self._LISTS and k != "model_version") or not all(self._strs(c[k]) for k in self._LISTS) or not c["evidence_refs"]:
            raise Refusal("carrier values", code="REVIEW_CARRIER_VALUES_INVALID")
        mv = c["model_version"]                    # s15: 'model/version where applicable'. Applicability is NOT asserted by the reviewer: only a HUMAN topology may omit it; every other topology must name it (the topology vocabulary beyond HUMAN is not source-defined).
        if c["topology"] == "HUMAN":
            if mv is not None: raise Refusal("human with model", code="REVIEW_MODEL_VERSION_NOT_APPLICABLE_TO_HUMAN")
        elif not (isinstance(mv, str) and mv): raise Refusal("model_version", code="REVIEW_MODEL_VERSION_REQUIRED")
        def d(st):
            t = st["tasks"].get(c["task_origin"])
            if t is None: raise Refusal(c["task_origin"], code="REVIEW_TASK_NOT_BOUND")
            if c["framing_hash"] != t["framing_hash"] or c["context_hash"] != t["context_hash"]: raise Refusal("framing/context", code="REVIEW_FRAMING_MISMATCH")
            if sorted(c["forbidden_inputs"]) != sorted(t["forbidden_inputs"]): raise Refusal("forbidden inputs", code="REVIEW_FORBIDDEN_INPUTS_MISMATCH")
            used = set(c["evidence_refs"]) & set(t["forbidden_inputs"])
            if used: raise Refusal(",".join(sorted(used)), code="REVIEW_FORBIDDEN_INPUT_USED")
            if not set(c["evidence_refs"]) <= set(t["permitted_evidence_refs"]): raise Refusal(",".join(sorted(set(c["evidence_refs"]) - set(t["permitted_evidence_refs"]))), code="REVIEW_EVIDENCE_OUTSIDE_PERMITTED_CONTEXT")   # s15: only PERMITTED governed evidence, bound by the task owner
            for f in st["findings"]:
                if f["finding_id"] == c["finding_id"]:
                    if {k: v for k, v in f.items() if k != "plane"} == c: return None, None
                    raise Refusal(c["finding_id"], code="FINDING_ID_REUSED")
            return None, ("FINDING", dict(c))
        self._commit(d)

from dataclasses import dataclass as _dc
from ..gateway.contracts import HealthSnapshot as _HS
@_dc(frozen=True)
class CoreHealthSnapshot(_HS):
    """A Health snapshot from Core that carries its evidence class. `acceptable` can be True ONLY for SIMULATION evidence; a qualified Core always reports QUALIFIED_HELD (acceptable=False)."""
    evidence_class: str = "SIMULATION"
    binding: object = None
    subject: str = ""
    version: str = ""
    evaluated_at: int = 0
    held_reason: str = ""
    snapshot_id: str = ""
    require_authority_evidence: bool = False
    require_transform_proof: bool = False
    require_ancestry: bool = False


@dataclass(frozen=True)
class FailClosedResult:
    subject: str
    core_quarantined: bool
    review: str                  # source-named review raised (CONTEXT_DOMAIN_RESOLUTION_FAILURE)
    restoration_allowed: bool    # always False
    owning_lifecycle_transition: str   # exact integration blocker; never "APPLIED" here
    chain_reading: str           # what the bound existing chain reads, if supplied


@dataclass(frozen=True)
class HealthReading:
    state: str            # HEALTHY / NOT_HEALTHY / UNKNOWN for a simulation core; HELD for a qualified core
    evidence_class: str
    local_state: str      # the caller-asserted calculation, always visible, never qualified
    qualified: bool       # always False: no admitted verifier/definition proof/appointment exists
