def should_hotstart(previous_slot_runs: int, enabled: bool = True) -> bool:
    """Whether a run may hotstart, given how many runs of the previous slot are success or running.

    With the rule off (`enabled` False), every run may hotstart, as before the rule existed.
    """
    return not enabled or previous_slot_runs > 0
