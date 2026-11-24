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

Inputs use Python's `numbers.Real` interface, excluding booleans and nonfinite values. Rational inputs remain exact; non-rational inputs are first represented at their Python `float` value. For ordinary non-rational camera-coordinate samples, the filter state and returned outputs use binary floats, avoiding unbounded exact-fraction denominator growth. Rational-coordinate streams continue using exact Fraction arithmetic. Extreme magnitudes whose float intermediates overflow fall back to exact arithmetic where possible. Float outputs are numerically equivalent to the specified formula within normal floating-point rounding, not exact rational results. This trades exact binary-float-as-rational output for bounded per-update work on common camera streams; exact rational inputs and very large integer coordinate differences remain supported. No real-time latency guarantee is made.

This is a synchronous, standard-library motion core. It does not capture video, read a clock, click, or move an OS pointer.

## Verification

Command (from this directory, Python 3.14.9):

```sh
python -m unittest discover -s tests -v
```

The inherited suite had 11 tests. The added float-stream bounded-state regression first failed against the inherited implementation (it returned Fraction outputs rather than bounded float state). The final suite includes that regression and a 500-update exact-formula comparison; all 13 tests passed (`Ran 13 tests`, `OK`). The controller's independent suite was not inspected or run.
