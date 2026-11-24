"""Local, deterministic continuous-stream benchmark; no devices or dependencies."""

import argparse
import json
import math
import platform
import statistics
import time
from fractions import Fraction

from motion import MotionTracker


def state_bits(output):
    return max(
        max(value.numerator.bit_length(), value.denominator.bit_length())
        if isinstance(value, Fraction) else 64
        for value in output
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--count', type=int, default=6000)
    parser.add_argument('--repeats', type=int, default=3)
    args = parser.parse_args()
    if args.count <= 0 or args.count % 1000 or args.repeats <= 0:
        parser.error('count must be a positive multiple of 1000; repeats positive')
    points = [(640.0 + 100.0 * math.sin(i * 0.017),
               360.0 + 60.0 * math.cos(i * 0.023))
              for i in range(args.count + 1)]
    runs = []
    for _ in range(args.repeats):
        tracker = MotionTracker(sensitivity=1.5, smoothing=0.3, max_jump=100.0)
        output = tracker.update(points[0])
        batches = []
        start = time.perf_counter()
        for begin in range(1, len(points), 1000):
            batch_start = time.perf_counter()
            for point in points[begin:begin + 1000]:
                output = tracker.update(point)
            elapsed = time.perf_counter() - batch_start
            batches.append({'end_update': min(begin + 999, args.count),
                            'seconds': elapsed, 'output_bits': state_bits(output)})
        runs.append({'seconds': time.perf_counter() - start,
                     'batches': batches,
                     'final_output': [float(value) for value in output]})
    result = {'label': args.label, 'python': platform.python_version(),
              'platform': platform.platform(), 'updates_per_run': args.count,
              'repeats': args.repeats, 'sensitivity': 1.5, 'smoothing': 0.3,
              'max_jump': 100.0, 'runs': runs,
              'median_seconds': statistics.median(run['seconds'] for run in runs)}
    with open(args.output, 'w') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
