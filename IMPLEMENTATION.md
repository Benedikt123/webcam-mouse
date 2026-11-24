# MotionTracker

## Usage

```pycon
>>> from motion import MotionTracker
>>> tracker = MotionTracker(sensitivity=2.0, smoothing=0.5, max_jump=10.0)
>>> tracker.update((10, 10))  # Establish a baseline.
(0, 0)
>>> tracker.update((13, 8))   # Raw motion (3, -2), scaled and smoothed.
(3.0, -2.0)
>>> tracker.update((13, 8))   # No raw motion; the previous output decays.
(1.5, -1.0)
>>> tracker.update(None)     # Tracking loss clears motion history.
(0, 0)
>>> tracker.update((50, 50)) # Reacquisition starts a new baseline.
(0, 0)

```

Call `pause()` to discard motion history and ignore valid samples. `resume()`
reenables movement with no baseline. `reset()` discards history without
changing whether the tracker is paused. Invalid configuration or positions
raise `ValueError`; invalid positions leave state untouched, even when paused.

## Design

The tracker keeps a pause flag, the previous position, and the previous output.
It validates both coordinates before changing state and stores each accepted
position as a tuple, independent of the caller's list. The jump check uses raw
Euclidean displacement before sensitivity or smoothing. A jump strictly beyond
the threshold clears the output and uses the new position as the baseline.
Otherwise each axis applies gain to the raw delta, then blends it with the
previous output using the configured smoothing weight.

Numeric validation uses `numbers.Real` (excluding `bool`). Rational deltas use
an exact squared-distance comparison; ordinary floating-point deltas use
`math.hypot`. Rational arithmetic also handles mixed-coordinate cancellation
and floating-point overflow when native arithmetic cannot preserve the motion.

## Limitations

- This is a sample-driven motion core, not a webcam, GUI, or OS cursor driver.
  Smoothing is per sample rather than per elapsed time. There are no dependencies
  outside the standard library.
- Ordinary floating-point arithmetic can round or underflow, and a floating-point
  distance very close to the threshold can round to it. Use integers or
  `fractions.Fraction` for exact rational distance comparisons. Outputs are
  numeric pairs, not guaranteed to be floats. `decimal.Decimal` is not a
  `numbers.Real`.
- The local runs used Python 3.14.9. Python 3.11 and the controller's independent
  suite were not run here.

## Test results

- Before implementation, `python -m unittest discover -s tests -v` exited 1:
  discovery reported `FAILED (errors=1)` because `motion` did not yet exist.
- Before fixing the threshold rounding regression,
  `python -m unittest discover -s tests -v -k axis_at_limit` ran one test in
  0.001s and exited 1 with `FAILED (failures=1)`: it emitted `(1.0, 1e-12)`
  instead of rejecting that displacement as `(0, 0)`.
- After the fix, `python -m unittest discover -s tests -v` exited 0:
  `Ran 17 tests in 0.006s`, `OK`.
- `python -B -m doctest -v IMPLEMENTATION.md` exited 0: `7 tests in 1 item`,
  `7 passed`.
