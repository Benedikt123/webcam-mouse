import math
import unittest
from fractions import Fraction

from motion import MotionTracker


class MotionTests(unittest.TestCase):
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

    def test_continuous_float_smoothing_does_not_grow_output_precision(self):
        gain, alpha = 1.3, 0.3
        tracker = MotionTracker(sensitivity=gain, smoothing=alpha)
        previous = (320.0, 240.0)
        actual = tracker.update(previous)
        self.assertEqual(actual, (0, 0))
        expected = (0.0, 0.0)
        max_error = 0.0
        for i in range(1, 4097):
            point = (320.0 + 0.37 * (31 - abs(i % 62 - 31)),
                     240.0 - 0.61 * (23 - abs(i % 46 - 23)))
            expected = tuple(alpha * (gain * (new - old)) + (1 - alpha) * out
                             for new, old, out in zip(point, previous, expected))
            actual = tracker.update(point)
            max_error = max(max_error, *(abs(float(a) - e) for a, e in zip(actual, expected)))
            previous = point
        self.assertLessEqual(max_error, 1e-9)
        # Both final values are of camera scale. Test representation growth,
        # not elapsed time (which is machine/load dependent).
        largest = max(part.bit_length() for axis in actual for part in axis.as_integer_ratio())
        self.assertLessEqual(largest, 256, 'smoothing accumulated unbounded precision')

    def test_jump_uses_exact_distance_even_when_float_rounds_to_limit(self):
        tracker = MotionTracker(max_jump=5.0)
        tracker.update((0.0, 0.0))
        outside = (math.nextafter(3.0, math.inf), 4.0)
        self.assertEqual(tracker.update(outside), (0, 0))
        self.assertEqual(tracker.update((outside[0], 5.0)), (0, 1))

    def test_extreme_finite_scaled_outputs_are_not_lost(self):
        for gain in (Fraction(1, 10**400), 10**400):
            with self.subTest(gain=gain):
                tracker = MotionTracker(sensitivity=gain, smoothing=Fraction(1, 2))
                tracker.update((0, 0))
                self.assertEqual(tracker.update((2, -2)), (gain, -gain))
                self.assertEqual(tracker.update((2, -2)), (Fraction(gain, 2), -Fraction(gain, 2)))

    def test_nonbinary_fraction_is_not_narrowed_out_of_range(self):
        base = 10**400
        gain = Fraction(base, 3)
        tracker = MotionTracker(sensitivity=gain, smoothing=Fraction(1, 3), max_jump=1)
        tracker.update((base, -base))
        self.assertEqual(tracker.update((base + 1, -base)), (Fraction(base, 9), 0))

    def test_tiny_delta_survives_initial_decay_then_settles_at_rest(self):
        alpha = Fraction(1, 3)
        tiny = Fraction(1, 10**400)
        tracker = MotionTracker(smoothing=alpha)
        tracker.update((0, 0))
        self.assertEqual(tracker.update((tiny, -tiny)), (tiny * alpha, -tiny * alpha))
        out = tracker.update((tiny, -tiny))
        self.assertEqual(out, (tiny * 2 / 9, -tiny * 2 / 9))
        for _ in range(512):
            out = tracker.update((tiny, -tiny))
        self.assertEqual(out, (0, 0))
