from .canonical import canonical_json, sha256_hex, CanonicalError

SCHEMA_VERSION = "TSIR-1-DRAFT"
VERDICTS = ("ACCEPT_FOR_REGISTRY", "REUSE_EXISTING", "REJECT_FAIL_CLOSED", "REVIEW_REQUIRED", "QUARANTINE_REQUIRED")
DECISIONS = ("NEW_CANONICAL_FEATURE", "REUSE_EXISTING_CANONICAL_FEATURE", "NEW_VERSION_OR_RELATIONSHIP",
             "MATERIAL_ALTERNATIVE", "PURE_DUPLICATE_CANONICAL_SURVIVOR", "REJECTED_INVALID", "REVIEW_REQUIRED")
ANCESTRY = ("PASS", "FAIL", "UNKNOWN")

# Exactly the 23 entries of Composer 28, in declared order. Compound source entries are
# modelled as sub-objects with fixed sub-keys (open decision: confirm this split).
COMPOUND = {
    "BUILD_OUTPUT_PACKAGE": ("ID", "HASH"),
    "REQUEST": ("REQUEST_ID", "CREATION_REQUEST_ID"),
    "RESULTING_FEATURE": ("FEATURE_ID", "FEATURE_VERSION", "REGISTRY_ENTRY_REF"),
    "POLICY": ("ID", "VERSION", "HASH"),
}
NULLABLE = {"RESULTING_FEATURE", "CANONICAL_SURVIVOR", "FEATURE_VERSION_RELATIONSHIP_REF"}
REPORT_FIELDS = (
    "SAFE_INTAKE_REPORT_ID", "BUILD_OUTPUT_PACKAGE", "REQUEST", "INTAKE_VERDICT", "FAILED_DIMENSIONS",
    "FAILED_DIMENSION_REASON_CODES", "IDENTITY_DECISION", "RESULTING_FEATURE", "CANONICAL_SURVIVOR",
    "FEATURE_VERSION_RELATIONSHIP_REF", "DEPENDENCY_CLOSURE_REF", "ANCESTRY_COMPLETENESS",
    "CAUSAL_AVAILABILITY_VERDICT", "SOURCE_VINTAGE_PROVENANCE_VERDICT", "OUTCOME_INFORMATION_ACCESS_VERDICT",
    "LEARNED_OR_FITTED_ANCESTRY_VERDICT", "COMPLETION_SEMANTICS_VERDICT",
    "CURRENTNESS_HEALTH_ELIGIBILITY_INITIAL_STATE", "OMISSIONS_EXCLUSIONS_REASONS", "SAFE_INTAKE_TS",
    "TRACKER_VERIFIER_ID", "POLICY", "FINAL_REPORT_HASH",
)
assert len(REPORT_FIELDS) == 23
BODY_FIELDS = REPORT_FIELDS[:-1]
FIELD_LIST_HASH = sha256_hex(canonical_json(list(REPORT_FIELDS)))

class ReportError(ValueError):
    pass

def _nonempty_str(v, name):
    if not isinstance(v, str) or not v.strip():
        raise ReportError("%s must be a non-empty string" % name)

def _check_body(body: dict):
    keys = set(body)
    if keys != set(BODY_FIELDS):
        raise ReportError("field set mismatch: missing=%s extra=%s" % (sorted(set(BODY_FIELDS) - keys), sorted(keys - set(BODY_FIELDS))))
    for name, sub in COMPOUND.items():
        v = body[name]
        if v is None and name in NULLABLE:
            continue
        if not isinstance(v, dict) or set(v) != set(sub):
            raise ReportError("%s must have exactly sub-keys %s" % (name, sub))
        for sk in sub:
            if v[sk] is None and name in NULLABLE:
                continue
            _nonempty_str(v[sk], name + "." + sk)
    for name in ("SAFE_INTAKE_REPORT_ID", "DEPENDENCY_CLOSURE_REF", "CAUSAL_AVAILABILITY_VERDICT",
                 "SOURCE_VINTAGE_PROVENANCE_VERDICT", "OUTCOME_INFORMATION_ACCESS_VERDICT",
                 "LEARNED_OR_FITTED_ANCESTRY_VERDICT", "COMPLETION_SEMANTICS_VERDICT",
                 "CURRENTNESS_HEALTH_ELIGIBILITY_INITIAL_STATE", "SAFE_INTAKE_TS", "TRACKER_VERIFIER_ID"):
        _nonempty_str(body[name], name)
    for name in ("CANONICAL_SURVIVOR", "FEATURE_VERSION_RELATIONSHIP_REF"):
        if body[name] is not None:
            _nonempty_str(body[name], name)
    if body["INTAKE_VERDICT"] not in VERDICTS:
        raise ReportError("INTAKE_VERDICT invalid")
    if body["IDENTITY_DECISION"] not in DECISIONS:
        raise ReportError("IDENTITY_DECISION invalid")
    if body["ANCESTRY_COMPLETENESS"] not in ANCESTRY:
        raise ReportError("ANCESTRY_COMPLETENESS invalid")
    fd, rc = body["FAILED_DIMENSIONS"], body["FAILED_DIMENSION_REASON_CODES"]
    if not isinstance(fd, list) or not isinstance(rc, list) or len(fd) != len(rc):
        raise ReportError("failed dimensions and reason codes must be equal-length lists")
    if not all(isinstance(x, str) and x for x in fd + rc):
        raise ReportError("failed dimension/reason entries must be non-empty strings")
    if not isinstance(body["OMISSIONS_EXCLUSIONS_REASONS"], list):
        raise ReportError("OMISSIONS_EXCLUSIONS_REASONS must be a list (explicit, may be empty)")
    # Cross-field rules below are reviewer judgement, not quoted source (open decision).
    v = body["INTAKE_VERDICT"]
    if v == "ACCEPT_FOR_REGISTRY":
        if fd or body["ANCESTRY_COMPLETENESS"] != "PASS" or body["RESULTING_FEATURE"] is None:
            raise ReportError("ACCEPT_FOR_REGISTRY needs no failed dimensions, ancestry PASS and a resulting feature")
    if v in ("REJECT_FAIL_CLOSED", "QUARANTINE_REQUIRED") and not fd:
        raise ReportError("%s needs at least one failed dimension" % v)

def _hash_body(body: dict) -> str:
    return sha256_hex(canonical_json({"schema": SCHEMA_VERSION, "fields_hash": FIELD_LIST_HASH, "body": body}))

def build_report(body: dict) -> dict:
    _check_body(body)
    try:
        h = _hash_body(body)
    except CanonicalError as e:
        raise ReportError(str(e))
    out = dict(body)
    out["FINAL_REPORT_HASH"] = h
    return out

def verify_report(report: dict) -> None:
    if set(report) != set(REPORT_FIELDS):
        raise ReportError("report must contain exactly the 23 declared entries")
    body = {k: report[k] for k in BODY_FIELDS}
    _check_body(body)
    if report["FINAL_REPORT_HASH"] != _hash_body(body):
        raise ReportError("FINAL_REPORT_HASH mismatch")
