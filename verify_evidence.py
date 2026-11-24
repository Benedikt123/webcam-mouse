"""Summarize saved timings and compare every output to the inherited recurrence."""

import json
import math
import statistics
from fractions import Fraction

from motion import MotionTracker


def main():
    with open('benchmark_before.json') as stream:
        before = json.load(stream)
    with open('benchmark_after.json') as stream:
        after = json.load(stream)
    tracker = MotionTracker(sensitivity=1.5, smoothing=0.3)
    previous = (Fraction(640), Fraction(420))
    exact = (Fraction(0), Fraction(0))
    alpha = Fraction.from_float(0.3)
    tracker.update(previous)
    max_error = Fraction(0)
    max_bits = 0
    for i in range(1, 6001):
        point = tuple(Fraction.from_float(v) for v in
                      (640.0 + 100.0 * math.sin(i * 0.017),
                       360.0 + 60.0 * math.cos(i * 0.023)))
        exact = tuple(alpha * Fraction(3, 2) * (p - old) + (1 - alpha) * out
                      for p, old, out in zip(point, previous, exact))
        actual = tracker.update(point)
        max_error = max(max_error, *(abs(got - want)
                                     for got, want in zip(actual, exact)))
        max_bits = max(max_bits, *(max(v.numerator.bit_length(),
                                      v.denominator.bit_length()) for v in actual))
        previous = point
    assert max_error <= Fraction(1, 10**9)
    result = {
        'median_speedup': before['median_seconds'] / after['median_seconds'],
        'before_median_us_per_update': before['median_seconds'] / 6000 * 1e6,
        'after_median_us_per_update': after['median_seconds'] / 6000 * 1e6,
        'max_absolute_error_vs_exact_over_6000_updates': float(max_error),
        'max_after_output_bits_over_6000_updates': max_bits,
    }
    for label, data in (('before', before), ('after', after)):
        result[label + '_median_batch_seconds'] = [
            statistics.median(run['batches'][i]['seconds'] for run in data['runs'])
            for i in range(6)]
    with open('evidence_summary.json', 'w') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
