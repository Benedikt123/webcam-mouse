# MotionTracker implementation

## Usage

`motion.py` exports `MotionTracker`. Create a tracker with optional sensitivity, smoothing, and maximum raw displacement:

```python
from motion import MotionTracker

tracker = MotionTracker(sensitivity=1.5, smoothing=0.4, max_jump=80.0)
print(tracker.update((120.0, 65.0)))  # (0, 0): establishes baseline
print(tracker.update((123.0, 64.0)))  # filtered (dx, dy)
tracker.pause()                       # ignore valid positions
tracker.resume()                      # next valid position starts a new baseline
tracker.update(None)                  # signal tracking loss
```

Inputs are `None` or a tuple/list with two finite real coordinates. Configuration and positions reject booleans and invalid numeric values with `ValueError`. `reset()` clears tracking/output state while retaining paused status.

## Design

The class stores only its fixed validated configuration, the previous valid baseline, the preceding filtered output, and paused status. For each valid sample it computes raw displacement, checks Euclidean distance against `max_jump`, scales each axis by sensitivity, then applies the configured exponential smoothing independently per axis. A discontinuity rebases and clears the filter. Loss, pause, resume, and reset clear motion state as specified. Invalid positions are fully validated before any state mutation.

## Limitations

This is a deterministic motion core only: it has no camera acquisition, image processing, timing, GUI, operating-system cursor control, click behavior, or external dependencies. It does not round, clamp, or convert outputs to integer cursor coordinates. It assumes samples are supplied in sequence by the caller.

## Tests

Command: `python -m unittest discover -s tests -v`

Result: **Ran 9 tests in 0.002s — OK** (9 passed, 0 failures, 0 errors). The suite covers movement, sensitivity/smoothing, configuration and input validation, preservation of state after invalid input, Euclidean jump threshold/equality, tracking loss, pause/resume, reset, and paused-state preservation.
