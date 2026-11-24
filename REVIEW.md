# Review: continuous motion filtering

**High severity for uninterrupted streams: update cost grew with session length, not motion complexity.** The inherited `motion.py:72–76` fed each exact `Fraction` blend back into the next. For `smoothing=0.3`, the actual binary float has a denominator of `2**54`; so does its exact complement. Multiplication introduces up to 54 more denominator bits per frame. Small coordinates and small *values* of the outputs do not keep their representations small. The inherited suite exercised short sequences and passed (11 tests in 0.005s).

## Reproduction and repair evidence

Run `python bench_stream.py` from this directory. On Python 3.14.9, one baseline followed by 6,000 updates on the **same tracker**, no losses or jumps. Sample `i` is `(320.0 + (i % 23)*0.125, 240.0 - (i % 17)*0.25)`; sensitivity 1.25, smoothing 0.3, max_jump 100.0. `perf_counter_ns` times just the loop over each prebuilt block, excluding setup, ratio inspection and printing. One local run per version, same script. Ratio sizes below are numerator/denominator bit lengths of the last x output of each block (also the x feedback state); they are not process memory measurements.

| Updates | Before (ms) | After (ms) | Before (bits) | After (bits) |
|---:|---:|---:|---:|---:|
| 1–1000 | 338.672 | 58.168 | 54003/54006 | 123/126 |
| 1001–2000 | 905.122 | 56.122 | 108003/108006 | 122/125 |
| 2001–3000 | 1469.503 | 56.685 | 162003/162006 | 123/126 |
| 3001–4000 | 2049.734 | 56.175 | 216003/216006 | 123/126 |
| 4001–5000 | 2621.666 | 58.661 | 270002/270006 | 117/121 |
| 5001–6000 | 3232.530 | 57.799 | 324003/324006 | 123/126 |
| **Total timed** | **10617.227** | **343.611** | | |

The inherited final block took 9.54 times as long as its first; after repair there was no comparable late-block slowdown. Total time improved by 30.9× in this run.

**Red before repair:** `python -m unittest discover -s tests -v` with the new `test_continuous_smoothing_has_compact_feedback` and unchanged `motion.py`: `Ran 12 tests in 2.982s`, `FAILED (failures=1)`, exit 1. All 3,000 pairs agreed with the independent float recurrence within `1e-9`; the size assertion failed with `AssertionError: 162006 not less than or equal to 2048`. The generous bit budget tests the underlying growth without asserting a machine-specific time limit.

**Green after repair:** same command, `Ran 14 tests in 0.204s`, `OK`, exit 0. This includes all 11 inherited tests, the red regression, and checks for gains and movements outside float range and a displacement barely outside the jump circle. While adding the extreme-input test its first draft incorrectly expected a diagonal displacement to pass a limit equal to its x component; the test limit was corrected, not the jump rule.

## Change and tradeoff

`MotionTracker._blend` now limits the denominator of stored feedback on each axis. It keeps the exact rational blend when small; otherwise it rounds once, to nearest (ties to even) on a fine binary grid. Grid precision depends on the gain and the largest **scaled input denominator** seen on that axis in the current run, never on the previous output's denominator. `_clear_output` clears both history and its precision budget on discontinuities and via `reset`, including pause, resume and tracking loss. The raw baseline, strict squared-distance comparison, gain application and validation are still exact for the same input representations as before. In particular, no float conversion was added for integers or fractions.

Why this precision suffices: let `a = p/q` be the positive smoothing factor. The grid spacing is `2**-bits`, with `bits >= 64 + q.bit_length()`. Thus each rounding error is at most `a * 2**-65` in absolute output units. Previous errors are multiplied by `1-a`, so their geometric sum is at most `2**-65` per axis relative to the exact recurrence on the accepted samples. This is an absolute error bound, not a promise of relative accuracy arbitrarily close to zero. Smoothing of 1 stays exact: without feedback, the scaled delta's denominator already fits.

## Remaining risks and scope

- Precision and cost are bounded **for bounded input sizes**, not for all possible finite reals. Exact rational validation, subtraction and geometry still cost more for very large operands. An unusually precise scaled delta can keep that axis's precision budget high until the next discontinuity or reset.
- The public result can still contain `Fraction`s, but long smoothed results need not equal the original fractions exactly. A very small decaying output can round to zero or settle at a small residual on the grid.
- The measurements cover a deterministic synthetic stream in one local interpreter, not scheduling jitter, worst-case latency, capture or integration. No physical webcam, controller suite or broad production validation was used.
