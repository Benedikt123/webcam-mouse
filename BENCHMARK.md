# Webcam Mouse — model benchmark, round 1

## Purpose
Implement the deterministic motion core of a future webcam mouse. No webcam, GUI, network, OS mouse control or third-party dependency is required. All model branches start at the same specification commit. Python 3.11+ standard library only.

## Deliverables
- `motion.py`, exporting `MotionTracker`.
- `tests/test_motion.py`, runnable with `python -m unittest discover -s tests -v`.
- `IMPLEMENTATION.md`: usage, design, limitations, exact test command/results.
- Do not edit this specification or README. Do not add dependencies. No Git commits, pushes, branch switches, external network or inspection of other worktrees/solutions. The benchmark controller handles Git.
- Use test-driven development: demonstrate at least one expected failing test before implementation, then passing tests. Complete the task, do not only propose a plan.

## Exact public API and semantics
`MotionTracker(sensitivity=1.0, smoothing=1.0, max_jump=100.0)`
- All configuration values must be finite real numbers, excluding bool. sensitivity > 0, 0 < smoothing <= 1, max_jump > 0. Invalid values raise ValueError.
- `update(position)` returns `(dx, dy)` as a pair of numbers. position is None or a tuple/list of exactly two finite real numbers (bool excluded). Malformed position raises ValueError **without changing any state**.
- First valid position establishes a baseline and returns (0, 0).
- Subsequent raw delta = current position minus previous valid position. Apply sensitivity, then exponential smoothing of output: `out = smoothing * scaled_delta + (1-smoothing) * previous_output`, independently per axis. Initial previous output is (0,0).
- If Euclidean raw displacement is **greater than** max_jump, treat it as a discontinuity: rebase to current position, clear previous output, return (0,0). Equality is allowed. Compare before sensitivity and smoothing.
- `update(None)` represents tracking loss. Clear baseline and previous output and return (0,0). Reacquisition establishes a fresh baseline, never a jump.
- `pause()` clears baseline/output and enters paused mode. Valid updates while paused return (0,0) and establish no baseline. Malformed input still raises ValueError. `resume()` clears baseline/output and leaves paused mode. Both operations are idempotent.
- `reset()` clears baseline/output but preserves paused status.
- No rounding, integer coercion, clamping, time dependence, clicks or actual cursor movement.
- Configuration is fixed at construction; no public runtime configuration interface required.

## Acceptance and evaluation
The controller runs an independent standard-library unittest suite covering nominal movement, numeric/config validation, smoothing, threshold geometry, state preservation on invalid input, pause/resume/reset and tracking loss. Models must write their own tests without reading the independent suite. The controller records actual test outcomes, CLI usage telemetry where provided, wall time, tool activity and git diff. Scores are descriptive and not a statistically robust ranking.

## Equal run conditions
Models: selected from live account catalog; exact selection recorded in final report. Reasoning effort high; normal service tier; fresh one-shot worker sessions; no fallback configured for benchmark runs; max 35 tool turns and 480 seconds per run. Context: this spec and the identical prompt. Models share the same VM user: worktrees provide working-copy separation, not a security sandbox. No deployment or merges are authorized.
