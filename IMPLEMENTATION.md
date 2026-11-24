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

The tracker remembers the previous position, previous output, per-axis output precision floors, and a pause flag. Both coordinates are validated and copied before any state change, including while paused. Mutating a caller's list therefore cannot move the baseline.

A squared Euclidean distance test on the raw delta avoids a square root. A displacement strictly beyond the limit becomes the new baseline with zero output. Otherwise, each axis is scaled by sensitivity and blended with its own previous output. Tracking loss and `reset()` forget both histories; `pause()` and `resume()` also clear them and set the pause flag. Paused samples never establish a baseline.

## Numeric behavior and limitations

Inputs use Python's `numbers.Real` interface, excluding booleans and nonfinite values. Rational inputs are preserved exactly; other real inputs are taken at their Python `float` value. Validation, stored coordinates, raw deltas and squared jump geometry remain exact `fractions.Fraction` arithmetic, so huge integer coordinates can still resolve a one-unit step. Previously accepted finite inputs remain accepted; no float conversion is imposed on rational inputs. Returned numbers can be Fractions.

For smoothing below one, recursive outputs are rounded to at most 53 significant binary bits, nearest with ties to even. Exponents are not limited to the float range, preserving nonzero injected motion at extremely small scales and accepting extremely large scales. Smoothing=1 retains exact scaled deltas because there is no recursive growth.

To prevent denominator growth during a stationary decay as well as during movement, each axis retains a maximum denominator shift. It starts at 1074 (the smallest binary64 subnormal quantum). Nonzero injected motion may extend it to approximately 1074 bits below the scale of that signal's first retained tail. Rounding is limited by this floor, which resets with filter history, including jumps. At that resolution a decaying output can become zero or remain at a tiny nonzero quantum. Exact rational recursive results and arbitrary relative accuracy in vanishing tails are intentionally not promised. Resource cost can still grow with increasingly extreme input magnitudes or rational complexity. No hard-real-time or all-input absolute-error guarantee is made.

This is a synchronous, standard-library motion core. It does not capture video, read a clock, click, or move an OS pointer.

## Verification

Command (from this directory, Python 3.14.9):

```sh
python -m unittest discover -s tests -v
```

The inherited implementation passed 11 tests in 0.006s at review start. Before repair, a new 6000-update regression failed because its output representation reached 324044 bits instead of remaining bounded. The final run, including all inherited tests and eight added tests, exited 0:

```text
Ran 19 tests in 1.053s

OK
```

Only the local suite was run; the controller's independent suite was not inspected or executed.

See `REVIEW.md` for the failure transcript, numeric tradeoffs, code locations and measurement methodology. Three identical 6000-update workloads at smoothing=0.3 had median runtime 11.763281341874972s before repair and 0.39717395487241447s afterward (29.61745400866915x). An exact-reference comparison of every update measured maximum absolute error 5.9329110041187e-16. Reproduce the repaired timing with `python benchmark_motion.py --label after --output benchmark_after.json` and compare the retained before/after evidence with `python verify_evidence.py`. These are synthetic local CPU measurements, not a physical webcam test or production validation.
