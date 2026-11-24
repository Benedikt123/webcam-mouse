# Independent review — continuous webcam-style motion stream

## Findings

- High severity — `motion.py:15-16, 74-75` (inherited): float samples were converted to exact `Fraction` values, and every smoothed output remained an exact fraction. With non-binary smoothing such as 0.3, repeated updates grew denominators continuously. This is unsuitable for a long-running input loop: per-update work and retained numeric-state size grow with stream duration even though the camera coordinates remain ordinary and bounded. The inherited code had no practical amortized-work bound for such streams.

## Regression and evidence

Added `test_float_camera_stream_keeps_bounded_numeric_state` in `tests/test_motion.py`. Against the inherited implementation, the test failed as expected: output was a `Fraction` instead of float state. This establishes the problematic numeric path before the repair.

Measured the same workload before and after, using Python 3.14.9 on this host: one `MotionTracker(smoothing=0.3)`, baseline `(0.0, 0.0)`, then 10,000 successive bounded float samples `(i * 0.01, (i % 17) * 0.01)`. Timing is elapsed wall-clock for only the update loop, using `time.perf_counter()`; there was no webcam or device access.

- Before: 10,000 updates in 32.984771 s (3,298.477 microseconds/update); outputs remained `Fraction`; denominator length reached 540,060 bits on each axis.
- After: 10,000 updates in 0.149425 s (14.942 microseconds/update); outputs remained `float`, with no growing rational denominator.
- On these single runs, after was approximately 220.8x faster. This is an indicative local measurement, not a controlled statistical benchmark; machine load, runtime and workload affect timings.

## Repair

For non-rational coordinate samples, `motion.py:65-105` now keeps positions and smoothing outputs in float arithmetic. Rational-coordinate samples retain exact Fraction arithmetic, including the inherited large-integer coordinate behavior. Float-overflow edge paths fall back to exact arithmetic. No public API, validation rules, tracking-loss/pause/reset semantics, raw jump comparison or sensitivity/smoothing formula were intentionally changed. `IMPLEMENTATION.md` now records the numeric design and precision tradeoff.

## Verification

- Regression test reproduced before fix: 1 failure, specifically the expected Fraction-output assertion.
- `python -m unittest discover -s tests -v` after repair: 13 tests passed, 0 failures.
- Repeated the 10,000-update workload after repair; measurement above.
- `git diff --check`: passed.

## Limitations and remaining risks

- Float camera streams now have ordinary IEEE-754 rounding rather than exact rational output. For normal camera-range floats this is within the required 1e-9 equivalence tolerance; callers depending on exact `Fraction` outputs for float inputs observe this intended numeric representation change.
- Mixed rational/float streams switch arithmetic representation at sample boundaries; exact Fraction semantics for all mixed-type cases are not promised. Rational-only streams remain exact.
- The fallback for extreme magnitudes is best-effort and may incur expensive exact arithmetic; it is not a hard latency bound for every accepted finite real value.
- Only the local 12-test suite and synthetic coordinate stream were run. The controller suite was not read or run; no physical webcam, real-time scheduling, device/controller integration, broad production load or statistical benchmark was validated.
