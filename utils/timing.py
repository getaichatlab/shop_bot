"""Monotonic-clock helpers.

`time.monotonic()` counts from an arbitrary point — on Linux it is the time
since the machine booted. On a freshly booted server (a CI runner, a container,
a VPS that just came up) it starts near zero.

That makes `0.0` a **wrong** default for "this has never happened":

    last = seen.get(key, 0.0)
    if time.monotonic() - last < COOLDOWN:   # 40.0 - 0.0 < 300 -> True (!)
        return                               # suppressed, though it never ran

The first minutes of uptime would silently behave as if everything had just
happened. `NEVER` is older than any monotonic reading on any machine, so the
comparison is correct from the first second.
"""
from __future__ import annotations

# Subtracting -inf yields +inf, which is greater than any cooldown.
NEVER: float = float("-inf")

__all__ = ["NEVER"]
