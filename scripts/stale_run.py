import re

VARIABLE = "FLOOD_STALE_RUN_MINUTES"
DEFAULT_LIMIT_MINUTES = 120


def limit_minutes(env):
    """The age in minutes above which a run is stale. 0 turns the guard off."""
    raw = env.get(VARIABLE, str(DEFAULT_LIMIT_MINUTES)).strip()
    if not re.fullmatch(r"[0-9]+", raw):
        raise ValueError(f"{VARIABLE} must be a whole number of minutes, 0 or more, got {raw!r}")
    return int(raw)


def age_minutes(slot, now):
    return (now - slot).total_seconds() / 60


def is_stale(slot, now, limit):
    return limit > 0 and age_minutes(slot, now) > limit


def message(slot, now, limit):
    return (
        f"Run slot {slot.strftime('%Y-%m-%dT%H:%M:%SZ')} is {age_minutes(slot, now):.0f} minutes old, "
        f"over the limit of {limit} minutes ({VARIABLE}). Skipping so an old run does no work."
    )
