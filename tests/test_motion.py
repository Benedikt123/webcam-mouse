import math
import unittest

from motion import MotionTracker


class MotionTrackerTests(unittest.TestCase):
    def test_first_position_sets_baseline_then_returns_delta(self):
        tracker = MotionTracker()
        self.assertEqual(tracker.update((10, 20)), (0, 0))
        self.assertEqual(tracker.update((13, 18)), (3.0, -2.0))

    def test_sensitivity_is_applied_before_exponential_smoothing(self):
        tracker = MotionTracker(sensitivity=2, smoothing=0.5)
        tracker.update((0, 0))
        self.assertEqual(tracker.update((4, 2)), (4.0, 2.0))
        self.assertEqual(tracker.update((5, 4)), (3.0, 3.0))

    def test_configuration_requires_finite_real_non_boolean_values_in_range(self):
        for kwargs in (
            {"sensitivity": 0}, {"sensitivity": -1}, {"sensitivity": True},
            {"sensitivity": math.inf}, {"sensitivity": math.nan},
            {"smoothing": 0}, {"smoothing": -0.5}, {"smoothing": 1.1},
            {"smoothing": False}, {"max_jump": 0}, {"max_jump": -1},
            {"max_jump": math.inf}, {"max_jump": "10"},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                MotionTracker(**kwargs)

    def test_position_must_be_none_or_two_finite_real_non_boolean_coordinates(self):
        tracker = MotionTracker()
        invalid_positions = (
            1, "1,2", (), (1,), (1, 2, 3), [1, 2, 3], (True, 2),
            (1, False), (math.inf, 0), (0, math.nan), ("1", 2),
        )
        for position in invalid_positions:
            with self.subTest(position=position), self.assertRaises(ValueError):
                tracker.update(position)

    def test_invalid_position_does_not_change_baseline_or_smoothed_output(self):
        tracker = MotionTracker(smoothing=0.5)
        tracker.update((0, 0))
        self.assertEqual(tracker.update((4, 0)), (2.0, 0.0))
        with self.assertRaises(ValueError):
            tracker.update((math.nan, 0))
        self.assertEqual(tracker.update((6, 0)), (2.0, 0.0))

    def test_jump_threshold_uses_raw_euclidean_distance_and_allows_equality(self):
        tracker = MotionTracker(sensitivity=10, max_jump=5)
        tracker.update((0, 0))
        self.assertEqual(tracker.update((3, 4)), (30.0, 40.0))
        self.assertEqual(tracker.update((9, 4)), (0, 0))
        self.assertEqual(tracker.update((10, 4)), (10.0, 0.0))

    def test_tracking_loss_clears_baseline_and_output(self):
        tracker = MotionTracker(smoothing=0.5)
        tracker.update((0, 0))
        self.assertEqual(tracker.update((4, 0)), (2.0, 0.0))
        self.assertEqual(tracker.update(None), (0, 0))
        self.assertEqual(tracker.update((1000, 1000)), (0, 0))
        self.assertEqual(tracker.update((1002, 1000)), (1.0, 0.0))

    def test_pause_ignores_valid_positions_until_resume_reacquires_baseline(self):
        tracker = MotionTracker()
        tracker.update((0, 0))
        tracker.pause()
        tracker.pause()
        self.assertEqual(tracker.update((5, 0)), (0, 0))
        self.assertEqual(tracker.update((10, 0)), (0, 0))
        with self.assertRaises(ValueError):
            tracker.update((True, 0))
        tracker.resume()
        tracker.resume()
        self.assertEqual(tracker.update((50, 50)), (0, 0))
        self.assertEqual(tracker.update((51, 49)), (1.0, -1.0))

    def test_reset_clears_motion_but_preserves_paused_status(self):
        tracker = MotionTracker()
        tracker.update((0, 0))
        self.assertEqual(tracker.update((5, 0)), (5.0, 0.0))
        tracker.reset()
        self.assertEqual(tracker.update((20, 20)), (0, 0))
        self.assertEqual(tracker.update((21, 20)), (1.0, 0.0))
        tracker.pause()
        tracker.reset()
        self.assertEqual(tracker.update((0, 0)), (0, 0))
        tracker.resume()
        self.assertEqual(tracker.update((30, 30)), (0, 0))


if __name__ == "__main__":
    unittest.main()
