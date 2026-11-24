"""Long-stream and numeric-edge coverage for the maintenance repair."""

import math
import unittest
from fractions import Fraction

from motion import MotionTracker


class ContinuousTests(unittest.TestCase):
    def test_output_rounds_halfway_values_to_even(self):
        for sign in (1, -1):
            for offset, expected in ((1, Fraction(1)),
                                     (3, 1 + Fraction(1, 2**51))):
                tracker = MotionTracker(smoothing=0.5)
                tracker.update((0, 0))
                point = sign * (2 + Fraction(offset, 2**52))
                self.assertEqual(tracker.update((point, 0)),
                                 (sign * expected, 0))

    def test_continuous_stream_has_bounded_filter_state(self):
        tracker = MotionTracker(sensitivity=1.5, smoothing=0.3)
        tracker.update((640.0, 420.0))
        expected = (0.0, 0.0)
        previous = (640.0, 420.0)
        largest_bits = 0
        for i in range(1, 6001):
            point = (640.0 + 100.0 * math.sin(i * 0.017),
                     360.0 + 60.0 * math.cos(i * 0.023))
            expected = tuple(0.3 * (p - old) * 1.5 + 0.7 * out
                             for p, old, out in zip(point, previous, expected))
            actual = tracker.update(point)
            for got, want in zip(actual, expected):
                self.assertLessEqual(abs(got - want), 1e-9)
                if isinstance(got, Fraction):
                    largest_bits = max(largest_bits, got.numerator.bit_length(),
                                       got.denominator.bit_length())
            previous = point
        # A structural regression rather than a machine-dependent timing limit.
        # Binary64-sized state needs at most 1075 bits even for subnormals.
        self.assertLessEqual(largest_bits, 1075,
                             'recursive exact fractions grow with stream length')

    def test_huge_and_tiny_finite_inputs_remain_accepted(self):
        for scale in (Fraction(10**400), Fraction(1, 10**400)):
            with self.subTest(scale='huge' if scale > 1 else 'tiny'):
                tracker = MotionTracker(sensitivity=scale, smoothing=0.3)
                tracker.update((0, 0))
                actual = tracker.update((1, -1))
                expected = Fraction.from_float(0.3) * scale
                for got, want in zip(actual, (expected, -expected)):
                    self.assertNotEqual(got, 0)
                    self.assertLessEqual(abs((got - want) / want), Fraction(1, 2**52))
                self.assertEqual(tracker.update(None), (0, 0))

    def test_long_stationary_tail_does_not_grow_denominators(self):
        for scale in (Fraction(1), Fraction(1, 10**400)):
            tracker = MotionTracker(sensitivity=scale, smoothing=0.3)
            tracker.update((0, 0))
            first = tracker.update((1, 0))[0]
            limit = max(1075, 1080 + first.denominator.bit_length()
                        - abs(first.numerator).bit_length())
            output = first
            for _ in range(6000):
                output = tracker.update((1, 0))[0]
                self.assertGreaterEqual(output, 0)
                self.assertLessEqual(output.denominator.bit_length(), limit)
            self.assertLess(output, abs(first) / 10**100)

    def test_nonbinary_filter_matches_exact_reference(self):
        tracker = MotionTracker(sensitivity=Fraction(7, 3),
                                smoothing=Fraction(3, 10))
        previous = (Fraction(0), Fraction(0))
        expected = previous
        tracker.update(previous)
        for i in range(1, 401):
            point = (Fraction(i % 47, 3), Fraction(i % 31, 7))
            expected = tuple(Fraction(3, 10) * Fraction(7, 3) * (p - old)
                             + Fraction(7, 10) * out
                             for p, old, out in zip(point, previous, expected))
            actual = tracker.update(point)
            for got, want in zip(actual, expected):
                self.assertLessEqual(abs(got - want), Fraction(1, 10**9))
            previous = point

    def test_extreme_smoothing_does_not_underflow_or_round_to_one(self):
        for alpha in (Fraction(1, 10**400), 1 - Fraction(1, 10**400)):
            tracker = MotionTracker(smoothing=alpha)
            tracker.update((0, 0))
            first = tracker.update((1, 0))[0]
            second = tracker.update((1, 0))[0]
            self.assertGreater(first, 0)
            self.assertGreater(second, 0)
            self.assertLessEqual(abs((second - alpha * (1 - alpha)) /
                                     (alpha * (1 - alpha))), Fraction(1, 2**51))

    def test_huge_coordinates_and_threshold_geometry_remain_exact(self):
        base = 10**400
        tracker = MotionTracker(sensitivity=base, smoothing=1, max_jump=5)
        tracker.update((base, -base))
        self.assertEqual(tracker.update((base + 3, 4 - base)), (3 * base, 4 * base))
        self.assertEqual(tracker.update((base + 7, 8 - base)), (0, 0))
        self.assertEqual(tracker.update((base + 8, 8 - base)), (base, 0))

    def test_exact_jump_boundary_not_rounded_by_filter(self):
        epsilon = Fraction(1, 10**400)
        tracker = MotionTracker(smoothing=0.3, max_jump=5)
        tracker.update((0, 0))
        self.assertNotEqual(tracker.update((3, 4)), (0, 0))
        self.assertEqual(tracker.update((6 + epsilon, 8)), (0, 0))
        self.assertEqual(tracker.update((7 + epsilon, 8)),
                         (Fraction.from_float(0.3), 0))


if __name__ == '__main__':
    unittest.main()
