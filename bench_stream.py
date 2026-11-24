"""Time consecutive blocks of one synthetic stream; run with python bench_stream.py."""

from time import perf_counter_ns

from motion import MotionTracker


def main():
    # Repeatable subpixel jitter near frame center. No losses or jumps.
    points = [(320.0 + (i % 23) * 0.125, 240.0 - (i % 17) * 0.25)
              for i in range(6001)]
    tracker = MotionTracker(sensitivity=1.25, smoothing=0.3)
    result = tracker.update(points[0])
    total = 0
    for start in range(1, len(points), 1000):
        block = points[start:start + 1000]
        before = perf_counter_ns()
        for point in block:
            result = tracker.update(point)
        elapsed = perf_counter_ns() - before
        total += elapsed
        n, d = result[0].as_integer_ratio()
        print(f'{start}-{start+len(block)-1}: {elapsed / 1e6:.3f} ms; '
              f'x ratio bits {n.bit_length()}/{d.bit_length()}')
    print(f'total timed: {total / 1e6:.3f} ms')


if __name__ == '__main__':
    main()
