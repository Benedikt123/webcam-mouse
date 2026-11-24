"""Regression tests using only the Python standard library."""

from decimal import Decimal
from fractions import Fraction
import unittest

from motion import MotionTracker


class MotionTrackerTests(unittest.TestCase):
    def assertPairAlmostEqual(self, actual, expected):
        self.assertIsInstance(actual, tuple)
        self.assertEqual(len(actual), 2)
        for observed, wanted in zip(actual, expected):
            self.assertAlmostEqual(observed, wanted)

    def test_first_position_establishes_baseline(self):
        tracker = MotionTracker()
        self.assertEqual(tracker.update((10, 20)), (0, 0))
        self.assertEqual(tracker.update((13, 18)), (3, -2))

    def test_default_signed_movement(self):
        tracker = MotionTracker()
        for position, expected in [((0, 0), (0, 0)), ((3, -4), (3, -4)),
                                   ((-2, 6), (-5, 10)), ((-2, 6), (0, 0))]:
            self.assertEqual(tracker.update(position), expected)

    def test_positional_constructor_arguments(self):
        tracker = MotionTracker(2, 0.5, 10)
        tracker.update((0, 0))
        self.assertEqual(tracker.update((2, -4)), (2, -4))

    def test_fractional_motion_is_not_rounded(self):
        tracker = MotionTracker(sensitivity=0.5)
        tracker.update((0.25, -0.5))
        self.assertEqual(tracker.update((0.75, -0.25)), (0.25, 0.125))

    def test_sensitivity_does_not_clamp_output(self):
        tracker = MotionTracker(sensitivity=100)
        tracker.update((0, 0))
        self.assertEqual(tracker.update((3, 4)), (300, 400))

    def test_exponential_smoothing_uses_previous_output(self):
        tracker = MotionTracker(sensitivity=2, smoothing=0.25)
        for position, expected in [((0, 0), (0, 0)), ((8, -4), (4, -2)),
                                   ((12, 0), (5, 0.5)), ((12, 0), (3.75, 0.375))]:
            self.assertPairAlmostEqual(tracker.update(position), expected)

    def test_smoothing_one_has_no_history(self):
        tracker = MotionTracker(smoothing=1)
        tracker.update((0, 0))
        self.assertEqual(tracker.update((8, -4)), (8, -4))
        self.assertEqual(tracker.update((8, -4)), (0, 0))

    def test_axes_are_smoothed_independently(self):
        tracker = MotionTracker(smoothing=0.5)
        tracker.update((0, 0))
        self.assertEqual(tracker.update((4, 0)), (2, 0))
        self.assertEqual(tracker.update((4, 6)), (1, 3))

    def test_lists_are_accepted_and_baseline_is_copied(self):
        position = [1, 2]
        tracker = MotionTracker()
        tracker.update(position)
        position[:] = [99, 99]
        self.assertEqual(tracker.update([3, 5]), (2, 3))

    def test_fractions_are_real_numbers(self):
        tracker = MotionTracker(sensitivity=Fraction(3, 2), smoothing=Fraction(1, 2),
                                max_jump=Fraction(10))
        tracker.update((Fraction(1, 4), Fraction(1, 2)))
        self.assertEqual(tracker.update((Fraction(3, 4), Fraction(1))),
                         (Fraction(3, 8), Fraction(3, 8)))

    def test_invalid_configuration_types(self):
        for name in ('sensitivity', 'smoothing', 'max_jump'):
            for value in (None, True, False, '1', 1 + 0j, [], {}, object(), Decimal('1')):
                with self.subTest(name=name, value=value):
                    with self.assertRaises(ValueError):
                        MotionTracker(**{name: value})

    def test_nonfinite_configuration(self):
        for name in ('sensitivity', 'smoothing', 'max_jump'):
            for value in (float('nan'), float('inf'), -float('inf')):
                with self.subTest(name=name, value=value):
                    with self.assertRaises(ValueError):
                        MotionTracker(**{name: value})

    def test_nonpositive_configuration(self):
        for name in ('sensitivity', 'smoothing', 'max_jump'):
            for value in (0, -0.0, -1, -0.25):
                with self.subTest(name=name, value=value):
                    with self.assertRaises(ValueError):
                        MotionTracker(**{name: value})

    def test_smoothing_upper_bound(self):
        for value in (1.000001, 2, Fraction(3, 2)):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    MotionTracker(smoothing=value)
        MotionTracker(smoothing=1)
        MotionTracker(smoothing=1e-300)

    def test_large_finite_integers_are_not_rejected(self):
        huge = 10 ** 400
        MotionTracker(sensitivity=huge)
        tracker = MotionTracker(max_jump=huge)
        tracker.update((huge, huge))
        self.assertEqual(tracker.update((huge + 1, huge - 1)), (1, -1))

    @staticmethod
    def invalid_positions():
        return [(), (1,), (1, 2, 3), [], [1], [1, 2, 3], '12', b'12',
                {0: 1, 1: 2}, {1, 2}, iter((1, 2)), 5, object(),
                (True, 0), (0, False), ('1', 0), (0, None), (1j, 0),
                (Decimal('1'), 0), (float('nan'), 0), (0, float('nan')),
                (float('inf'), 0), (0, -float('inf')), ([1], 2)]

    def test_invalid_positions_raise_value_error(self):
        for position in self.invalid_positions():
            with self.subTest(position=position):
                with self.assertRaises(ValueError):
                    MotionTracker().update(position)

    def test_invalid_positions_preserve_baseline_and_output(self):
        for position in self.invalid_positions():
            with self.subTest(position=position):
                tracker = MotionTracker(smoothing=0.5)
                tracker.update((0, 0))
                self.assertEqual(tracker.update((4, 8)), (2, 4))
                with self.assertRaises(ValueError):
                    tracker.update(position)
                self.assertEqual(tracker.update((6, 10)), (2, 3))

    def test_invalid_input_does_not_establish_baseline(self):
        tracker = MotionTracker()
        with self.assertRaises(ValueError):
            tracker.update((5, float('nan')))
        self.assertEqual(tracker.update((10, 20)), (0, 0))

    def test_threshold_equality_is_allowed(self):
        tracker = MotionTracker(max_jump=5)
        tracker.update((0, 0))
        self.assertEqual(tracker.update((3, 4)), (3, 4))
        self.assertEqual(tracker.update((0, 0)), (-3, -4))

    def test_axis_threshold_and_just_over_threshold(self):
        tracker = MotionTracker(max_jump=5)
        tracker.update((0, 0))
        self.assertEqual(tracker.update((5, 0)), (5, 0))
        self.assertEqual(tracker.update((10.000001, 0)), (0, 0))
        self.assertPairAlmostEqual(tracker.update((11.000001, 0)), (1, 0))

    def test_threshold_is_euclidean_not_per_axis(self):
        tracker = MotionTracker(max_jump=5)
        tracker.update((0, 0))
        self.assertEqual(tracker.update((4, 4)), (0, 0))
        self.assertEqual(tracker.update((5, 4)), (1, 0))

    def test_threshold_precedes_sensitivity_and_smoothing(self):
        tracker = MotionTracker(sensitivity=100, smoothing=0.5, max_jump=5)
        tracker.update((0, 0))
        self.assertEqual(tracker.update((3, 4)), (150, 200))
        self.assertEqual(tracker.update((9, 4)), (0, 0))
        self.assertEqual(tracker.update((10, 4)), (50, 0))
        tracker = MotionTracker(sensitivity=0.01, smoothing=0.01, max_jump=5)
        tracker.update((0, 0))
        self.assertEqual(tracker.update((6, 0)), (0, 0))

    def test_jump_rebases_and_clears_previous_output(self):
        tracker = MotionTracker(smoothing=0.5, max_jump=10)
        tracker.update((0, 0))
        self.assertEqual(tracker.update((4, 6)), (2, 3))
        self.assertEqual(tracker.update((100, 100)), (0, 0))
        self.assertEqual(tracker.update((102, 104)), (1, 2))

    def test_large_float_threshold_geometry_does_not_square_overflow(self):
        tracker = MotionTracker(max_jump=1e308)
        tracker.update((0, 0))
        self.assertEqual(tracker.update((8e307, 8e307)), (0, 0))
        self.assertEqual(tracker.update((8e307, 8e307)), (0, 0))

    def test_tiny_float_threshold_geometry_does_not_square_underflow(self):
        tracker = MotionTracker(max_jump=1e-300)
        tracker.update((0, 0))
        self.assertEqual(tracker.update((8e-301, 8e-301)), (0, 0))

    def test_huge_integer_threshold_geometry(self):
        huge = 10 ** 400
        tracker = MotionTracker(max_jump=5 * huge)
        tracker.update((0, 0))
        self.assertEqual(tracker.update((4 * huge, 4 * huge)), (0, 0))
        self.assertEqual(tracker.update((4 * huge + 1, 4 * huge)), (1, 0))

    def test_fraction_threshold_equality_is_exact(self):
        tracker = MotionTracker(sensitivity=1, smoothing=1, max_jump=Fraction(1, 10))
        tracker.update((0, 0))
        self.assertEqual(tracker.update((Fraction(3, 50), Fraction(2, 25))),
                         (Fraction(3, 50), Fraction(2, 25)))
        self.assertEqual(tracker.update((Fraction(7, 50), Fraction(4, 25))), (0, 0))

    def test_mixed_huge_integer_and_float_threshold_geometry(self):
        huge = 10 ** 400
        tracker = MotionTracker(max_jump=huge)
        tracker.update((0, 0))
        self.assertEqual(tracker.update((huge, 1.0)), (0, 0))
        self.assertEqual(tracker.update((huge + 1, 1.0)), (1, 0))

    def test_finite_positions_whose_subtraction_overflows_are_a_jump(self):
        tracker = MotionTracker(max_jump=1e308)
        tracker.update((-1e308, 0))
        self.assertEqual(tracker.update((1e308, 0)), (0, 0))
        self.assertEqual(tracker.update((1e308, 1)), (0, 1))

    def test_tracking_loss_clears_baseline_and_output(self):
        tracker = MotionTracker(smoothing=0.5)
        tracker.update((0, 0))
        tracker.update((4, 6))
        self.assertEqual(tracker.update(None), (0, 0))
        self.assertEqual(tracker.update(None), (0, 0))
        self.assertEqual(tracker.update((1000, -1000)), (0, 0))
        self.assertEqual(tracker.update((1002, -996)), (1, 2))

    def test_loss_before_first_position(self):
        tracker = MotionTracker()
        self.assertEqual(tracker.update(None), (0, 0))
        self.assertEqual(tracker.update((1000, 2000)), (0, 0))

    def test_pause_ignores_positions_and_resume_rebaselines(self):
        tracker = MotionTracker(smoothing=0.5)
        tracker.update((0, 0))
        tracker.update((8, 4))
        tracker.pause()
        self.assertEqual(tracker.update((10, 20)), (0, 0))
        self.assertEqual(tracker.update((30, 40)), (0, 0))
        tracker.resume()
        self.assertEqual(tracker.update((1000, 1000)), (0, 0))
        self.assertEqual(tracker.update((1002, 1004)), (1, 2))

    def test_pause_and_resume_are_idempotent(self):
        tracker = MotionTracker()
        tracker.pause()
        tracker.pause()
        self.assertEqual(tracker.update((1, 2)), (0, 0))
        tracker.resume()
        tracker.resume()
        self.assertEqual(tracker.update((3, 4)), (0, 0))
        self.assertEqual(tracker.update((4, 6)), (1, 2))

    def test_resume_even_when_active_clears_motion_history(self):
        tracker = MotionTracker(smoothing=0.5)
        tracker.update((0, 0))
        tracker.update((4, 6))
        tracker.resume()
        self.assertEqual(tracker.update((50, 50)), (0, 0))
        self.assertEqual(tracker.update((52, 54)), (1, 2))

    def test_invalid_input_while_paused_still_raises(self):
        tracker = MotionTracker()
        tracker.pause()
        for position in self.invalid_positions():
            with self.subTest(position=position):
                with self.assertRaises(ValueError):
                    tracker.update(position)
        self.assertEqual(tracker.update((0, 0)), (0, 0))
        self.assertEqual(tracker.update((1, 2)), (0, 0))
        tracker.resume()
        self.assertEqual(tracker.update((10, 20)), (0, 0))
        self.assertEqual(tracker.update((11, 22)), (1, 2))

    def test_tracking_loss_preserves_paused_status(self):
        tracker = MotionTracker()
        tracker.pause()
        self.assertEqual(tracker.update(None), (0, 0))
        self.assertEqual(tracker.update((1, 1)), (0, 0))
        self.assertEqual(tracker.update((2, 2)), (0, 0))

    def test_reset_active_clears_baseline_and_output(self):
        tracker = MotionTracker(smoothing=0.5)
        tracker.update((0, 0))
        tracker.update((4, 6))
        tracker.reset()
        tracker.reset()
        self.assertEqual(tracker.update((1000, 1000)), (0, 0))
        self.assertEqual(tracker.update((1002, 1004)), (1, 2))

    def test_reset_preserves_paused_status(self):
        tracker = MotionTracker()
        tracker.pause()
        tracker.reset()
        self.assertEqual(tracker.update((1, 1)), (0, 0))
        self.assertEqual(tracker.update((2, 3)), (0, 0))
        tracker.resume()
        self.assertEqual(tracker.update((5, 6)), (0, 0))
        self.assertEqual(tracker.update((6, 8)), (1, 2))

    def test_instances_have_independent_state(self):
        first, second = MotionTracker(), MotionTracker()
        first.update((0, 0))
        second.update((50, 50))
        first.pause()
        self.assertEqual(second.update((51, 52)), (1, 2))
        self.assertEqual(first.update((1, 2)), (0, 0))


if __name__ == '__main__':
    unittest.main()
