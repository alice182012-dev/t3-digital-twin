"""Evidence for US-100. Runs the two closure rules of the reference code on the two cases of the closure reading.

Times are seconds from 08:00. Forecast steps are 15 minutes apart. The vehicle is a car with a 30 cm limit, and the
engine margin is 600 s. Read-only. Run from the repository root: python3 -I artifacts/docs/stories/evidence/us-100-closure-reading.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path("scripts/routing_reference").resolve()))

from arrival_only import ArrivalOnlyClosure  # noqa: E402
from sticky_reference import StickyClosure  # noqa: E402

STEPS = (0, 900, 1800, 2700)
LIMIT_CM = 30


def clock(seconds):
    return f"{8 + seconds // 3600:02d}:{seconds % 3600 // 60:02d}"


def show(title, depths, arrival_s, crossing_s):
    depth = lambda edge, step: depths[step]  # noqa: E731
    arrival_only = ArrivalOnlyClosure(STEPS, depth, LIMIT_CM)
    sticky = StickyClosure(STEPS, depth, LIMIT_CM, departure_s=0)
    leaves = arrival_s + crossing_s
    rises = [clock(STEPS[k]) for k, d in enumerate(depths) if d >= LIMIT_CM and arrival_s <= STEPS[k] <= leaves]
    print(title)
    print(f"  depths at {', '.join(clock(s) for s in STEPS)}: {', '.join(f'{d} cm' for d in depths)}")
    print(f"  the car enters at {clock(arrival_s)} and leaves at {clock(leaves)}")
    print(f"  limit reached while the car is on the road: {', '.join(rises) if rises else 'no'}")
    print(f"  arrival-only rule: {'closed' if arrival_only.is_closed(0, arrival_s) else 'OPEN'}")
    print(f"  sticky rule:       {'CLOSED' if sticky.is_closed(0, arrival_s) else 'open'}")


show("Case 1: the water rises while the car is on the road (2 km, 4 minutes)", (10, 40, 40, 40), 720, 240)
show("Case 2: the water recedes before the car arrives", (40, 20, 5, 5), 2700, 240)
