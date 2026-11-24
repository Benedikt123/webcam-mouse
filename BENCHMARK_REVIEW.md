# Round 2 — review and repair an inherited motion core

This is a separate maintenance task, not a retroactive change to round 1.

You inherit one identical implementation, tests and documentation. The controller selected this fixture from round 1; no model is told its author. Review it as code intended for a continuously running webcam input pipeline.

## Task
1. Read BENCHMARK.md and inspect motion.py, tests and IMPLEMENTATION.md.
2. Find and reproduce an important practical defect or unsuitable design choice for prolonged ordinary camera-coordinate streams. Measure at least several thousand successive updates with non-binary smoothing (e.g. 0.3); report the workload and timing. Do not just run the existing short suite.
3. Add a regression test demonstrating the issue before your fix. Repair it without adding dependencies or changing the public API, validation rules, tracking-loss/pause/reset behavior or jump semantics. For ordinary camera-range floats, numerical equivalence within 1e-9 is sufficient; exact rational output is not required. Do not silently drop previously accepted finite real inputs; document numeric tradeoffs honestly.
4. Run the existing tests plus your new tests, and repeat your workload after repair.
5. Write REVIEW.md: findings with code locations, severity, evidence, changes, before/after measurements, limitations and remaining risks. Update IMPLEMENTATION.md if the implementation's numeric design changes.

## Boundaries
Work only in your directory. No sibling solutions, network, Git commits/pushes, branch switches, real input-device access, dependency installs or edits to either benchmark specification / README. Do not read the controller's acceptance suite. The controller will run its own tests. Do not claim a physical webcam test or broad production validation.

Same model effort and limits as round 1: high reasoning, max 35 tool turns, 480 second run budget. New fresh session per candidate, all starting at the exact same inherited-code commit. Deliver fixes, not merely review advice.
