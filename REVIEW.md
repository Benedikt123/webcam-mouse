# Continuous-stream review

## Findings

- **High — smoothing cost grew with stream length.** The inherited `motion.py:72–75` fed the full exact `Fraction` result back into every update. With `smoothing=0.3`, the exact binary value has an odd numerator over `2**54`, and `1 - smoothing` has the same denominator. The denominator bit length grew by 54 per update at the measured checkpoints, even though the samples stayed in a small region. This growth increased the size of the retained output as well as the cost of the arithmetic; clearing history only on jumps or loss was not a solution for continuous tracking.
- **Compatibility constraint — do not replace exact geometry or validation with float arithmetic.** The inherited validation (`motion.py:10–19`) accepts integers and fractions outside the binary64 range. Exact subtraction also preserves unit motion around `10**400`. A rounded distance can hide a jump: `(nextafter(3.0, +inf), 4.0)` is strictly outside a radius of `5.0`, even though the norm rounds to `5.0` in binary64. The repaired code still validates both coordinates before mutating state (`motion.py:69–83`) and compares exact squared distances (`motion.py:85–89`).

## Repair

`motion.py:23–30` caps the denominator of the output used for feedback. It keeps small rationals exact and truncates an oversized denominator toward zero on a binary grid. The precision budget uses the gain and smoothing denominators, the largest accepted within-threshold displacement denominator seen since the history was cleared, and 48 guard bits (`motion.py:47–59`, `motion.py:94–105`). For fixed-size inputs, the budget does not grow with update count. The exact gain-only path (`smoothing=1`) has no feedback to cap. Invalid samples still leave all state untouched; a jump clears filter history and rebases; loss, pause, resume and reset retain their specified behavior.

The grid introduces less than one quantum (`2^-b`, for `b` fractional bits) of error per update and axis. Previous error is multiplied by `1 - smoothing`, so the accumulated error relative to the inherited exact filter is bounded by `2^-b_min / smoothing`, where `b_min = 48 + bit_length(gain.denominator) + bit_length(smoothing.denominator)`. For reduced smoothing `p/q`, `1 / smoothing <= q < 2**bit_length(q)`, so the bound is strictly below `2^-48` output units (about `3.55e-15`). This is a bound against the exact rational recurrence, not against a separate binary64 implementation. Truncation toward zero adds a small bias but avoids rounding a stationary decay tail back up to a persistent nonzero value.

## Evidence

`benchmark_stream.py` replays one deterministic two-axis triangular path, about x=320–331.47 and y=225.97–240, with fractional per-axis steps of approximately 0.37 and 0.61. It uses `sensitivity=1.3`, `smoothing=0.3`, and `max_jump=100.0`. One baseline sample is followed by 6,000 consecutive timed updates, without sleeps, jumps, tracking loss or resets. `perf_counter()` times only the update loops, excluding point creation, baseline setup, checkpoint inspection and printing. The size metric is the largest bit length of any numerator or denominator in the two returned axes, not a measurement of process memory.

Before: `python benchmark_stream.py`. After: `PYTHONDONTWRITEBYTECODE=1 python benchmark_stream.py`. Both runs used CPython 3.14.9 on x86_64, one timed replay per version.

| Updates | Before interval (s) | After interval (s) | Before cumulative (s) | After cumulative (s) | Before bits | After bits |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1,000 | 0.401082 | 0.068467 | 0.401082 | 0.068467 | 54,096 | 203 |
| 3,000 | 2.820465 | 0.136502 | 3.221547 | 0.204969 | 162,096 | 202 |
| 6,000 | 9.306353 | 0.204525 | 12.527899 | 0.409494 | 324,096 | 200 |

The complete timed replay was **30.59× faster**. The last 3,000 updates averaged 3.102117 ms/update before and 0.068175 ms/update after; these are block averages, not tail-latency measurements.

- **Red:** `python -m unittest discover -s tests -v` against the unchanged `motion.py` exited 1: `Ran 15 tests in 6.344s`, `FAILED (failures=1)`. `test_continuous_float_smoothing_does_not_grow_output_precision` (`tests/test_motion.py:106`) first verified per-axis agreement within `1e-9` against an independent float recurrence over 4,096 consecutive updates, then failed the representation bound: `221280 not less than or equal to 256 : smoothing accumulated unbounded precision`. It does not fail based on elapsed time.
- **Green:** `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v` exited 0: `Ran 16 tests in 0.357s`, `OK`. All 11 inherited tests passed. The five added tests cover continuous smoothing, a near-boundary jump, sub-float and above-float gain, nonbinary rational configuration with huge coordinates, and an extremely small finite delta whose initial decay remains nonzero and whose stationary tail eventually settles.

## Limitations and remaining risks

- Smoothing no longer promises exact rational output indefinitely; a sufficiently small tail can truncate to zero. Input validation and exact displacement/jump comparison are unchanged, and the returned values can still be `Fraction`s. No result is narrowed to binary64 inside the filter.
- Very large magnitudes or high-precision rationals still cost more than ordinary coordinates. An unusually fine accepted displacement can raise the precision budget until the next history clear. There is no fixed resource bound for arbitrarily large inputs, only a bound independent of stream length for fixed-size inputs. A per-update error bound also does not bound the error of an external integrator over an unlimited run.
- Measurements are a single synthetic, uninterrupted replay on one interpreter and host. They do not measure end-to-end latency, production jitter, or webcam/pointer integration. No device or controller acceptance suite was accessed.
