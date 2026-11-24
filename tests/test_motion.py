import math
import unittest
from fractions import Fraction

from motion import MotionTracker


class MotionTests(unittest.TestCase):
    def test_continuous_smoothing_has_compact_feedback(self):
        tracker = MotionTracker(sensitivity=1.25, smoothing=0.3)
        previous = (320.0, 240.0)
        output = tracker.update(previous)
        expected = (0.0, 0.0)
        for i in range(1, 3001):
            point = (320.0 + (i % 23) * 0.125, 240.0 - (i % 17) * 0.25)
            expected = tuple(0.3 * (1.25 * (p - q)) + 0.7 * e
                             for p, q, e in zip(point, previous, expected))
            output = tracker.update(point)
            for got, want in zip(output, expected):
                self.assertAlmostEqual(float(got), want, delta=1e-9)
            previous = point

        # Deterministic size check, not a latency threshold tied to this host.
        # Even binary64 subnormals need at most 1075 denominator bits.
        for value in output:
            n, d = value.as_integer_ratio()
            self.assertLessEqual(max(n.bit_length(), d.bit_length()), 2048)

    def test_baseline_and_relative_motion(self):
        tracker = MotionTracker()
        point = [10.0, -2.0]
        self.assertEqual(tracker.update(point), (0, 0))
        point[:] = [11.25, -4.5]
        self.assertEqual(tracker.update(point), (1.25, -2.5))
        self.assertEqual(tracker.update((10, -4.5)), (-1.25, 0))

    def test_sensitivity_and_smoothing(self):
        tracker = MotionTracker(sensitivity=1.5, smoothing=0.25)
        tracker.update((0, 0))
        self.assertEqual(tracker.update((4, -8)), (1.5, -3))
        self.assertEqual(tracker.update((0, 0)), (-0.375, 0.75))
        self.assertEqual(tracker.update((0, 0)), (-0.28125, 0.5625))

    def test_invalid_configuration(self):
        for name in ('sensitivity', 'smoothing', 'max_jump'):
            invalid = [True, False, '1', None, 1+0j, math.nan, math.inf,
                       -math.inf, -1, 0]
            if name == 'smoothing':
                invalid.append(math.nextafter(1.0, math.inf))
            for value in invalid:
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    MotionTracker(**{name: value})

    def test_fractional_real_inputs(self):
        tracker = MotionTracker(Fraction(1, 2), Fraction(1, 4), Fraction(3, 2))
        tracker.update((Fraction(1, 2), 0))
        self.assertEqual(tracker.update([2, 0]), (Fraction(3, 16), 0))

    def test_raw_threshold_equality_jump_and_rebase(self):
        tracker = MotionTracker(sensitivity=4, smoothing=0.5, max_jump=5)
        tracker.update((0, 0))
        self.assertEqual(tracker.update((3, -4)), (6, -8))  # length exactly 5
        self.assertEqual(tracker.update((7, -8)), (0, 0))   # length exceeds 5
        self.assertEqual(tracker.update((6, -7)), (-2, 2))  # from jump endpoint

    def test_small_gain_cannot_hide_jump(self):
        tracker = MotionTracker(sensitivity=0.01, max_jump=1)
        tracker.update((0, 0))
        self.assertEqual(tracker.update((math.nextafter(1.0, math.inf), 0)), (0, 0))

    def test_invalid_input_preserves_baseline_and_output(self):
        for bad in [0, '12', {0: 1, 1: 2}, (), [0], (1, 2, 3), (True, 1),
                    (0, False), [0, math.nan], [math.inf, 0], [0, -math.inf],
                    [0, '1'], [None, 0], [0, 1+0j]]:
            with self.subTest(position=bad):
                tracker = MotionTracker(smoothing=0.5)
                tracker.update((0, 0))
                tracker.update((4, -8))
                with self.assertRaises(ValueError):
                    tracker.update(bad)
                self.assertEqual(tracker.update((6, -6)), (2, -1))

    def test_loss_and_reacquisition(self):
        tracker = MotionTracker(smoothing=0.5)
        tracker.update((0, 0))
        tracker.update((4, 6))
        self.assertEqual(tracker.update(None), (0, 0))
        self.assertEqual(tracker.update(None), (0, 0))
        self.assertEqual(tracker.update((900, 800)), (0, 0))
        self.assertEqual(tracker.update((902, 798)), (1, -1))

    def test_pause_validation_reset_and_resume(self):
        tracker = MotionTracker(smoothing=0.5)
        tracker.update((0, 0))
        tracker.update((8, 2))
        tracker.pause()
        tracker.pause()
        self.assertEqual(tracker.update((9, 2)), (0, 0))
        with self.assertRaises(ValueError):
            tracker.update((3, False))
        tracker.reset()
        self.assertEqual(tracker.update(None), (0, 0))
        self.assertEqual(tracker.update((10, 10)), (0, 0))
        self.assertEqual(tracker.update((11, 11)), (0, 0))
        tracker.resume()
        tracker.resume()
        self.assertEqual(tracker.update((12, 12)), (0, 0))
        self.assertEqual(tracker.update((14, 10)), (1, -1))

    def test_reset_or_resume_clears_active_history(self):
        for action in ('reset', 'resume'):
            with self.subTest(action=action):
                tracker = MotionTracker(smoothing=0.5)
                tracker.update((0, 0))
                tracker.update((6, -4))
                getattr(tracker, action)()
                self.assertEqual(tracker.update((7, -2)), (0, 0))
                self.assertEqual(tracker.update((9, 0)), (1, 1))

    def test_large_integer_coordinates_keep_small_motion(self):
        base = 10**400
        tracker = MotionTracker(max_jump=base)
        tracker.update((base, -base))
        self.assertEqual(tracker.update((base+1, 1-base)), (1, 1))

    def test_extreme_gains_and_scaled_motion(self):
        # Neither the small gain nor the large accepted movement fits a float.
        big = 10**400
        tracker = MotionTracker(sensitivity=big, smoothing=Fraction(1, big),
                                max_jump=big + 1)
        tracker.update((0, 0))
        self.assertEqual(tracker.update((big, Fraction(1, big))),
                         (big, Fraction(1, big)))
        x, y = tracker.update((big, Fraction(1, big)))
        self.assertEqual(x, big - 1)
        expected = Fraction(big - 1, big**2)
        self.assertLess(abs(y - expected), expected / 10**18)

    def test_jump_just_outside_circle_at_float_resolution(self):
        tracker = MotionTracker(smoothing=0.3, max_jump=1)
        tracker.update((0, 0))
        # sqrt(1 + epsilon**2) would round to 1.0 in binary64.
        epsilon = 2.0**-52
        self.assertEqual(tracker.update((1, epsilon)), (0, 0))
        self.assertEqual(tracker.update((2, epsilon)), (0.3, 0))
