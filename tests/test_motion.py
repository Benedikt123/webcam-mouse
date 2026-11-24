import math
import unittest
from fractions import Fraction

from motion import MotionTracker


class MotionTrackerTests(unittest.TestCase):
    def test_first_sample_and_relative_motion(self):
        tracker = MotionTracker()
        self.assertEqual(tracker.update((10, 20)), (0, 0))
        self.assertEqual(tracker.update([12, 17]), (2, -3))
        self.assertEqual(tracker.update((11.75, 17.5)), (-0.25, 0.5))
        self.assertEqual(tracker.update((11.75, 17.5)), (0, 0))

    def test_mutating_a_list_does_not_move_the_baseline(self):
        tracker = MotionTracker()
        position = [4, -6]
        self.assertEqual(tracker.update(position), (0, 0))
        position[:] = [6, -10]
        self.assertEqual(tracker.update(position), (2, -4))

    def test_sensitivity_then_output_smoothing(self):
        tracker = MotionTracker(sensitivity=2.0, smoothing=0.25)
        self.assertEqual(tracker.update((0, 0)), (0, 0))
        self.assertEqual(tracker.update((4, -2)), (2, -1))
        self.assertEqual(tracker.update((2, 4)), (0.5, 2.25))
        self.assertEqual(tracker.update((2, 4)), (0.375, 1.6875))

    def test_threshold_is_euclidean_strict_and_precedes_scaling(self):
        tracker = MotionTracker(sensitivity=2, smoothing=0.5, max_jump=5)
        self.assertEqual(tracker.update((0, 0)), (0, 0))
        self.assertEqual(tracker.update((3, 4)), (3, 4))
        self.assertEqual(tracker.update((7, 8)), (0, 0))
        self.assertEqual(tracker.update((8, 7)), (1, -1))

        tracker = MotionTracker(sensitivity=0.1, smoothing=0.5, max_jump=5)
        tracker.update((0, 0))
        self.assertEqual(tracker.update((6, 0)), (0, 0))

    def test_float_threshold_boundaries(self):
        tracker = MotionTracker(max_jump=0.5)
        tracker.update((0.0, 0.0))
        self.assertEqual(tracker.update((0.3, 0.4)), (0.3, 0.4))
        tracker.reset()
        tracker.update((0.0, 0.0))
        self.assertEqual(tracker.update((math.nextafter(0.5, math.inf), 0)), (0, 0))

    def test_axis_at_limit_and_nonzero_other_axis_is_a_jump(self):
        tracker = MotionTracker(max_jump=1.0)
        tracker.update((0.0, 0.0))
        self.assertEqual(tracker.update((1.0, 1e-12)), (0, 0))
        self.assertEqual(tracker.update((1.0, 0.0)), (0, -1e-12))

    def test_lost_tracking_clears_baseline_and_output(self):
        tracker = MotionTracker(smoothing=0.5)
        self.assertEqual(tracker.update(None), (0, 0))
        tracker.update((0, 0))
        self.assertEqual(tracker.update((4, 8)), (2, 4))
        self.assertEqual(tracker.update(None), (0, 0))
        self.assertEqual(tracker.update(None), (0, 0))
        self.assertEqual(tracker.update((5, 9)), (0, 0))
        self.assertEqual(tracker.update((6, 7)), (0.5, -1))

    def test_pause_resume_and_reset_preserve_the_right_state(self):
        tracker = MotionTracker(smoothing=0.5)
        tracker.update((0, 0))
        self.assertEqual(tracker.update((4, 4)), (2, 2))
        tracker.pause()
        tracker.pause()
        self.assertEqual(tracker.update([5, 5]), (0, 0))
        with self.assertRaises(ValueError):
            tracker.update((False, 0))
        self.assertEqual(tracker.update(None), (0, 0))
        tracker.reset()
        self.assertEqual(tracker.update((6, 6)), (0, 0))
        self.assertEqual(tracker.update((7, 7)), (0, 0))
        tracker.resume()
        self.assertEqual(tracker.update((8, 8)), (0, 0))
        self.assertEqual(tracker.update((9, 9)), (0.5, 0.5))
        tracker.resume()
        tracker.resume()
        self.assertEqual(tracker.update((10, 10)), (0, 0))
        self.assertEqual(tracker.update((11, 11)), (0.5, 0.5))
        tracker.reset()
        self.assertEqual(tracker.update((12, 12)), (0, 0))
        self.assertEqual(tracker.update((12, 10)), (0, -1))

    def test_invalid_config(self):
        for name in ("sensitivity", "smoothing", "max_jump"):
            for value in (0, -1, True, False, math.nan, math.inf, -math.inf,
                          "1", 1 + 0j, None, [], object()):
                with self.subTest(name=name, value=value):
                    with self.assertRaises(ValueError):
                        MotionTracker(**{name: value})
        for value in (1.01, Fraction(3, 2)):
            with self.subTest(smoothing=value):
                with self.assertRaises(ValueError):
                    MotionTracker(smoothing=value)

    def test_invalid_position_does_not_change_baseline_or_output(self):
        invalid = ((), [], (1,), [1, 2, 3], (False, 0), [0, True],
                   (math.nan, 0), [0, math.inf], (-math.inf, 0),
                   (0, 1 + 0j), (None, 0), ("1", 0), ([], 0), "12",
                   {0: 1, 1: 2}, range(2), iter((1, 2)), 1, object())
        for position in invalid:
            with self.subTest(position=position):
                tracker = MotionTracker(smoothing=0.5)
                tracker.update((0, 0))
                tracker.update((4, -4))
                with self.assertRaises(ValueError):
                    tracker.update(position)
                self.assertEqual(tracker.update((5, -6)), (1.5, -2))

    def test_invalid_first_sample_does_not_establish_baseline(self):
        tracker = MotionTracker()
        with self.assertRaises(ValueError):
            tracker.update((1, math.nan))
        self.assertEqual(tracker.update((2, 2)), (0, 0))
        self.assertEqual(tracker.update((3, 3)), (1, 1))

    def test_fractional_input_and_configuration(self):
        tracker = MotionTracker(sensitivity=Fraction(2, 3),
                                smoothing=Fraction(3, 4),
                                max_jump=Fraction(3, 2))
        tracker.update((0, 0))
        self.assertEqual(tracker.update((Fraction(1, 3), Fraction(-2, 3))),
                         (Fraction(1, 6), Fraction(-1, 3)))
        self.assertEqual(tracker.update((Fraction(1, 3), Fraction(-2, 3))),
                         (Fraction(1, 24), Fraction(-1, 12)))

    def test_large_integer_coordinates_preserve_small_delta(self):
        origin = 10 ** 400
        tracker = MotionTracker()
        self.assertEqual(tracker.update((origin, -origin)), (0, 0))
        self.assertEqual(tracker.update((origin + 1, -origin - 2)), (1, -2))
        self.assertEqual(tracker.update((0, 0)), (0, 0))
        self.assertEqual(tracker.update((1, 1)), (1, 1))

    def test_large_and_small_rational_thresholds(self):
        for unit in (10 ** 400, Fraction(1, 10 ** 400)):
            with self.subTest(unit=unit):
                tracker = MotionTracker(sensitivity=1, smoothing=1, max_jump=5 * unit)
                tracker.update((0, 0))
                self.assertEqual(tracker.update((3 * unit, 4 * unit)), (3 * unit, 4 * unit))
                self.assertEqual(tracker.update((7 * unit, 8 * unit)), (0, 0))

    def test_mixed_integer_and_float_coordinates_keep_small_delta(self):
        origin = 2 ** 60
        tracker = MotionTracker()
        tracker.update((float(origin), 0))
        self.assertEqual(tracker.update((origin + 1, 0)), (1, 0))

    def test_scaling_overflow_does_not_poison_smoothed_output(self):
        tracker = MotionTracker(sensitivity=1e308, smoothing=0.25)
        tracker.update((0, 0))
        self.assertEqual(tracker.update((4, 0)), (1e308, 0))
        self.assertEqual(tracker.update((4, 0)), (7.5e307, 0))

    def test_finite_float_coordinates_can_have_overflowing_raw_delta(self):
        tracker = MotionTracker(max_jump=1e308)
        tracker.update((-1e308, 0))
        self.assertEqual(tracker.update((1e308, 0)), (0, 0))
        self.assertEqual(tracker.update((1e308, 1)), (0, 1))


if __name__ == "__main__":
    unittest.main()
