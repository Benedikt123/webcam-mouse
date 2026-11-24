"""Time a deterministic uninterrupted float stream (no webcam required)."""

import platform
from time import perf_counter

from motion import MotionTracker


def main():
    points = [(320.0 + 0.37 * (31 - abs(i % 62 - 31)),
               240.0 - 0.61 * (23 - abs(i % 46 - 23))) for i in range(6001)]
    tracker = MotionTracker(sensitivity=1.3, smoothing=0.3, max_jump=100.0)
    output = tracker.update(points[0])
    print(f'{platform.python_implementation()} {platform.python_version()} {platform.machine()}',
          flush=True)
    print('updates  interval_s  cumulative_s  largest_ratio_integer_bits', flush=True)
    total = 0.0
    previous = 0
    for count in (1000, 3000, 6000):
        batch = points[previous + 1:count + 1]
        start = perf_counter()
        for point in batch:
            output = tracker.update(point)
        elapsed = perf_counter() - start
        total += elapsed
        width = max(part.bit_length() for axis in output for part in axis.as_integer_ratio())
        print(f'{count:7d}  {elapsed:10.6f}  {total:12.6f}  {width:26d}',
              flush=True)
        previous = count


if __name__ == '__main__':
    main()
