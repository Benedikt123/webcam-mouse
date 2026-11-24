# Independent inherited-code review and repair

## Finding: high severity for continuous operation

The inherited `motion.py:68-75` performed raw-delta checking and recursive smoothing entirely with `Fraction`. Exact geometry is useful, but exact recursive output is unsuitable for an uninterrupted webcam-coordinate stream. The binary float 0.3 becomes a rational with a power-of-two denominator; multiplying each previous output by its exact retention coefficient continually increases that denominator. Having only two output objects does not imply bounded memory or arithmetic cost.

This was reproduced, not inferred solely from inspection. The original 11 tests passed in 0.006 s (`baseline_tests.txt`), but a new 6,000-update regression failed before any repair:

    AssertionError: 324044 not less than or equal to 1075 : recursive exact fractions grow with stream length
    Ran 5 tests in 12.763s
    FAILED (failures=1)

The other four new tests then present passed. Full output is retained in `regression_before.txt`. The failing test checked every output against the floating recurrence within 1e-9 and then asserted bounded output representation size, avoiding a machine-specific timing assertion. Later additions cover stationary tails and rounding edges.

## Reproducible workload and measurements

`benchmark_motion.py` precomputes 6,001 points, establishes a baseline, then times 6,000 successive updates without resets, loss, pauses or jumps. Coordinates are:

    x(i) = 640.0 + 100.0 * sin(0.017*i)
    y(i) = 360.0 + 60.0 * cos(0.023*i)

Configuration: sensitivity=1.5, smoothing=0.3, max_jump=100.0. Points remain in ordinary camera range and adjacent steps are below the jump threshold. Three fresh trackers repeat the identical stream. Timing uses `perf_counter`, excludes point generation and baseline, and includes update loops, small batch slices and six state-size observations. This is aggregate throughput/batch evidence, not a per-frame latency distribution or RSS measurement.

Environment reported by the running interpreter: Python 3.14.9; Linux-7.0.0-42-generic-x86_64-with-glibc2.43.

Commands used, before and after the implementation change respectively:

    python benchmark_motion.py --label before --output benchmark_before.json
    python benchmark_motion.py --label after --output benchmark_after.json

Raw timing files retain full precision. Seconds per run:

| Run | Before | After |
| --- | ---: | ---: |
| 1 | 11.824149299878627 | 0.39538550889119506 |
| 2 | 11.763281341874972 | 0.39717395487241447 |
| 3 | 11.756914502941072 | 0.40092427912168205 |
| Median | 11.763281341874972 | 0.39717395487241447 |

Measured median speedup: 29.61745400866915x. Median aggregate cost per update: 1960.5468903124952 microseconds before, 66.19565914540242 microseconds after.

Median seconds for successive batches of 1,000 updates:

| End update | Before | After | Before output bits | After output bits |
| --- | ---: | ---: | ---: | ---: |
| 1000 | 0.37646300718188286 | 0.06630800710991025 | 54044 | 54 |
| 2000 | 1.0127801259513944 | 0.06533241411671042 | 108044 | 53 |
| 3000 | 1.6448815430048853 | 0.06584468996152282 | 162044 | 55 |
| 4000 | 2.2844011548440903 | 0.0663515729829669 | 216044 | 53 |
| 5000 | 2.9144405080005527 | 0.06689914199523628 | 270044 | 52 |
| 6000 | 3.5357174819801003 | 0.06631741905584931 | 324044 | 53 |

Bits means the largest numerator/denominator bit length across the two returned Fractions, not allocated bytes. Every repeat had the same sampled bit counts. A separate all-update comparison found a maximum of 64 output bits after repair.

`python verify_evidence.py` independently evaluates the inherited exact recurrence over all 6,000 points and compares every repaired output before converting the maximum error to float. Maximum absolute error: 5.9329110041187e-16, below 1e-9. Both versions' final outputs, converted to float, were (0.3803627748841387, 0.6008889201061232). Derived results are saved in `evidence_summary.json`.

## Changes and code locations

- `motion.py:_finite_real` (line 10) remains unchanged: accepted types, finite validation and exact rational conversion are preserved. Coordinates and squared jump comparisons remain exact.
- `motion.py:_signal_floor` (line 22) derives a per-axis quantum floor from the actual injected signal and retention. `MotionTracker.reset` (line 84) initializes that precision history; a discontinuity clears it along with the old output.
- `motion.py:_round_output` (line 31) rounds recursive output to at most 53 significant binary bits, ties-to-even, using integer arithmetic and a dyadic Fraction. It does not narrow huge or tiny inputs to a float.
- `MotionTracker.update` retains the original baseline, loss, validation, pause and jump control flow. Its smoothing branch now remembers each axis's quantum floor and rounds only the new output. Smoothing=1 keeps exact nonrecursive scaled deltas. Retention is cached at construction.
- `tests/test_continuous.py` adds eight tests: a 6,000-update moving stream, positive/negative rounding ties, 6,000-update idle tails at ordinary and tiny scales, an exact rational reference, extreme finite scales, extreme smoothing, huge-coordinate geometry and a just-over-threshold rational displacement.

An unrestricted exponent with only a bounded significand is insufficient: a long stationary tail would still grow its denominator as the output decays. The final implementation therefore retains an explicit quantum floor per axis rather than deriving it from the current rounded output. Intermediate implementations failed the added stationary/extreme-tail tests; those failures were repaired before the final passing run.

## Final verification

    python -m unittest discover -s tests -v
    Ran 19 tests in 1.053s
    OK

This includes all 11 unchanged inherited tests and eight new tests. The final run is saved in `tests_after.txt`. The benchmark and exact-reference comparison were then run sequentially after the tests. `git diff --check` exited 0. No specification, README, inherited test, public API or dependency was changed.

## Numeric tradeoffs and remaining risks

Exact recursive rational results are intentionally no longer promised when smoothing<1. Rounding happens once per axis after evaluating the recurrence exactly with the previous rounded output. Ordinary normal-sized outputs have binary64-like precision, but arbitrary exponents remain supported. Huge integers still resolve unit coordinate steps, and nonzero 10^-400-scale injected motion is tested without float underflow. Values previously accepted by validation are not newly rejected.

The denominator quantum initially permits 2^-1074 resolution. A nonzero injected signal extends this floor, if needed, to approximately 1,074 binary places below the scale of that signal's first retained tail. Floors persist until history is cleared. Consequently prolonged idle decay cannot by itself require ever finer storage. At the floor, a vanishing tail can round to zero or settle at a nonzero quantum, as subnormal floating arithmetic can; exact convergence and relative accuracy of arbitrarily decayed tails are not promised. Very small smoothing can also make rounding dominate tiny changes in an established output. No global 1e-9 guarantee is claimed for arbitrary huge magnitudes or every possible stream.

Storage and cost still depend on input magnitude, rational bit complexity and the smallest injected scale encountered, not just on sample count. Streams supplying increasingly extreme rationals can therefore increase resource use. Exact rational validation, deltas and jump geometry remain slower than a float-only implementation. The explicit floor logic is additional numeric code and deserves further fuzzing if used beyond this benchmark.

Measurements are local synthetic CPU timings, three repetitions on one shared host, without controlled CPU affinity, load isolation, allocation profiling or per-update tail-latency capture. No physical webcam, input device, GUI, network, sibling solution or controller acceptance suite was accessed. No broad production or hard-real-time validation is claimed. No commit, push or branch switch was performed. All artifacts remain in this directory.
