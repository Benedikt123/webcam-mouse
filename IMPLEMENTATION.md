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

Inputs use Python's `numbers.Real` interface, excluding booleans and nonfinite values. Rational inputs are preserved exactly; other real inputs are taken at their Python `float` value. The baseline, jump comparison and scaled deltas use `fractions.Fraction`, so even a large integer coordinate can resolve a one-unit step. The returned tuple can contain `Fraction` values, not necessarily floats.

Only the feedback blend has limited precision. On each axis, the denominator bit budget is 64 guard bits plus the bit lengths of the smoothing denominator and the largest scaled-delta denominator since the last history clear. If the blend exceeds that budget, it is stored and returned rounded to the nearest multiple of `2**-budget` (ties to even). For fixed input sizes this prevents the history from getting larger simply because more frames arrived. Unsmoothed deltas remain exact. Smoothed output has bounded absolute, not relative, error; near zero a small residual may persist or disappear. Very large inputs or exceptionally precise fractions can still be expensive. No real-time latency guarantee is made. See `REVIEW.md` for the error bound and measurements.

This is a synchronous, standard-library motion core. It does not capture video, read a clock, click, or move an OS pointer.

## Verification

Command (from this directory, Python 3.14.9):

```sh
python -m unittest discover -s tests -v
```

The inherited suite passed before review (11 tests). With the new continuous-stream regression and the inherited implementation, one of 12 tests failed as expected. After repair and the additional numeric edge cases, the command exited 0:

```text
Ran 14 tests in 0.204s

OK
```

Only the local suite was run; the controller's independent suite was not inspected or executed.
