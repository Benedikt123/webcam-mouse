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

Inputs use Python's `numbers.Real` interface, excluding booleans and nonfinite values. Rational inputs are preserved exactly on ingestion; other real inputs are taken at their Python `float` value, as before. Raw displacements and the squared jump comparison use exact `fractions.Fraction` arithmetic, so a large integer coordinate can still resolve a one-unit step. The returned tuple can contain `Fraction` values, not necessarily floats.

With smoothing below one, the filter evaluates the blend of the exact input term and the stored previous output. It keeps the resulting fraction when its denominator fits the precision budget; otherwise, it truncates toward zero on a binary grid and uses that result both for output and for feedback. The budget accounts for gain, smoothing, and the highest displacement-denominator bit length since the filter history was cleared, plus 48 guard bits. The budget does not increase with the number of updates for fixed-size inputs. The truncation contributes less than `2**-48` absolute error per axis relative to the exact recurrence, including accumulated error from prior updates (see `REVIEW.md`). Smoothing equal to one remains exact. A very small decay tail can truncate to zero; very large or precise inputs still cost more, and no real-time latency guarantee is made.

This is a synchronous, standard-library motion core. It does not capture video, read a clock, click, or move an OS pointer.

## Verification

Commands (from this directory, CPython 3.14.9):

```sh
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python benchmark_stream.py
```

The local suite exited 0 after the continuous-stream repair:

```text
Ran 16 tests in 0.357s

OK
```

The 6,000-update replay took 0.409494 s after repair (12.527899 s before). See `REVIEW.md` for the failing regression on inherited code, complete timing results, and limitations. The controller's independent suite was not inspected or executed.
