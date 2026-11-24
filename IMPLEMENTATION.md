# MotionTracker

Use one tracker per position stream. Pass samples in order; `update` returns relative motion, not absolute cursor coordinates.

```python
from motion import MotionTracker

tracker = MotionTracker(sensitivity=1.5, smoothing=0.25, max_jump=100)
assert tracker.update((0, 0)) == (0, 0)     # establish baseline
assert tracker.update((4, -8)) == (1.5, -3)
assert tracker.update(None) == (0, 0)       # tracking lost
assert tracker.update((900, 800)) == (0, 0) # reacquire without motion
```

## Design

The tracker remembers the previous position, previous output, and a pause flag. Both coordinates are validated and copied before any state change, including while paused. Mutating a caller's list therefore cannot move the baseline.

A squared Euclidean distance test on the raw delta avoids a square root. A displacement strictly beyond the limit becomes the new baseline with zero output. Otherwise, each axis is scaled by sensitivity and blended with its own previous output. Tracking loss and `reset()` forget both histories; `pause()` and `resume()` also clear them and set the pause flag. Paused samples never establish a baseline.

## Numeric behavior and limitations

Inputs use Python's `numbers.Real` interface, excluding booleans and nonfinite values. Rational inputs are preserved exactly; other real inputs are taken at their Python `float` value. Internal arithmetic uses `fractions.Fraction`, so a large integer coordinate can still resolve a one-unit step. The returned tuple can contain `Fraction` values, not necessarily floats. With smoothing below one, exact output denominators can grow over a long uninterrupted stream, increasing arithmetic cost. No real-time latency guarantee is made.

This is a synchronous, standard-library motion core. It does not capture video, read a clock, click, or move an OS pointer.

## Verification

Command (from this directory, Python 3.14.9):

```sh
python -m unittest discover -s tests -v
```

Tests were written and run before `motion.py` existed. The first run exited 1 with `ModuleNotFoundError: No module named 'motion'` and `FAILED (errors=1)`. After implementation, every listed test reported `ok`; the run exited 0:

```text
Ran 11 tests in 0.005s

OK
```

Only the local suite was run; the controller's independent suite was not inspected or executed.
