CURRENT_LIFECYCLES = {"CURRENT"}

NON_CURRENT_LIFECYCLES = {
    "DEPRECATED",
    "SUPERSEDED",
    "RETIRED",
    "REJECTED_INVALID",
    "QUARANTINED",
}

KNOWN_LIFECYCLES = CURRENT_LIFECYCLES | NON_CURRENT_LIFECYCLES


def lifecycle_currentness(state: str) -> bool:
    normalized = str(state).upper()
    if normalized in CURRENT_LIFECYCLES:
        return True
    if normalized in NON_CURRENT_LIFECYCLES:
        return False
    raise ValueError(f"UNKNOWN_LIFECYCLE_STATE:{state}")
