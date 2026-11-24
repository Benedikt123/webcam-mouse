# Motion core implementation

## Usage

Python 3.11+; standard library only. Run from this directory so `motion.py` is importable.

```python
from motion import MotionTracker

tracker = MotionTracker(sensitivity=2, smoothing=0.5, max_jump=10)
assert tracker.update((0, 0)) == (0, 0)       # establish baseline
assert tracker.update((2, -4)) == (2, -4)    # scale, then smooth

tracker.pause()                              # clear baseline and output
assert tracker.update((50, 50)) == (0, 0)    # ignored while paused
tracker.resume()                             # next position is a fresh baseline
assert tracker.update((100, 100)) == (0, 0)
assert tracker.update(None) == (0, 0)        # tracking loss clears history
tracker.reset()                             # clear history; preserve paused status
```

`update` accepts only `None` or a tuple/list containing exactly two finite `numbers.Real` values, excluding booleans. Configuration uses the same numeric validation: sensitivity and max_jump must be positive; smoothing must be greater than zero and at most one. Invalid inputs raise `ValueError`. Integers, floats and `fractions.Fraction` are supported. `Decimal`, complex numbers, numeric strings, generators and other container types are rejected. Lists are copied into a tuple so later caller mutation cannot alter the stored baseline.

## Design

Each instance stores fixed private configuration, a paused flag, a previous position (or no baseline), and a previous output pair. There are no global mutable tracker variables, clocks or external effects.

Update order:

1. Handle `None` by clearing motion history without altering paused status.
2. Validate an entire position before any state change, including while paused.
3. Ignore valid positions while paused, establishing no baseline.
4. Establish a baseline on the first valid active update, returning `(0, 0)`.
5. Compute raw displacement from the previous valid position.
6. Compare its Euclidean magnitude to max_jump before scaling or smoothing. A strictly greater displacement rebases to the current position, clears previous output, and returns `(0, 0)`; equality is accepted.
7. Per axis, compute `smoothing * (raw_delta * sensitivity) + (1 - smoothing) * previous_output`. Store the current position and resulting output only after computing both axes.

Ordinary floating-point geometry uses `math.hypot` rather than squaring floats, avoiding overflow/underflow in the distance calculation. Rational-only threshold comparisons use exact squared distances, including arbitrary-size integers and exact fractional equality. Mixed numeric geometry falls back to exact `Fraction` comparison when float conversion would overflow. Axis checks recognize displacement overflow from subtraction of opposite-sign large finite floats as a discontinuity.

`pause()` and `resume()` always clear baseline/output and set paused status. Repeating either operation is idempotent. Even `resume()` on an already active instance clears history as specified. `reset()` clears baseline/output without changing paused status. Tracking loss uses that same reset operation. No public runtime configuration mutators are provided.

## Tests and recorded results

Exact command, run from this directory:

```text
python -m unittest discover -s tests -v
```

TDD red phase: before creating `motion.py`, a first-position test explicitly asserted that the module existed, then would exercise baseline establishment and movement. The actual run exited with status 1:

```text
AssertionError: unexpectedly None : motion.py must provide the motion core
Ran 1 test in 0.002s
FAILED (failures=1)
```

The main regression suite was written before implementation. After implementation, it exited with status 0:

```text
Ran 36 tests in 0.009s
OK
```

Three additional numeric boundary tests were then added. The final run exited with status 0:

```text
Ran 39 tests in 0.009s
OK
```

Runtime verified with `python --version`: `Python 3.14.9`.

Coverage includes signed/fractional movement; positional/keyword construction; sensitivity; exponential output smoothing and independent axes; mutable input isolation; invalid types, booleans, nonfinite values and configuration bounds; state preservation after invalid updates; Euclidean threshold equality and discontinuities before scaling/smoothing; ordinary, tiny, huge and mixed numeric threshold geometry; tracking loss and reacquisition; pause/resume/reset, repeated calls, invalid paused updates, paused-state preservation; and independent instances. Invalid-input tests use subtests for individual cases; the reported 39 is the unittest test-method count.

## Limitations and scope

- This is only a deterministic motion core: no webcam, GUI, network, OS mouse control, clicks, timing, rounding, integer coercion or output clamping.
- Floating-point calculations retain Python's ordinary representation error. Input validation guarantees finite inputs, not finite intermediate scaled/smoothed outputs. Extreme magnitudes can overflow float arithmetic (including `OverflowError` for sufficiently large mixed integer/float operations); arbitrary-precision output arithmetic is not promised. Exact rational inputs/configuration can avoid float arithmetic.
- A tracker is mutable and not synchronized for concurrent updates. Give each independent stream its own tracker, or synchronize access externally.
- Executed on Python 3.14.9 only; Python 3.11 compatibility follows the language/library features used but was not exercised on a separate interpreter.
- The independent controller suite was not inspected or run. The results above are for the delivered local tests only.

Only the requested deliverable files were written. BENCHMARK.md and README.md were not edited. No dependencies, network access, sibling worktree inspection, Git commits, pushes or branch changes were used.
