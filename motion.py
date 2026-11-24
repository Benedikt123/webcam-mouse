"""Deterministic motion filtering for 2D position samples."""

import math
import numbers


class MotionTracker:
    """Convert successive positions to sensitivity-scaled, smoothed deltas."""

    def __init__(self, sensitivity=1.0, smoothing=1.0, max_jump=100.0):
        self._sensitivity = self._finite_real(sensitivity, "sensitivity")
        self._smoothing = self._finite_real(smoothing, "smoothing")
        self._max_jump = self._finite_real(max_jump, "max_jump")
        if self._sensitivity <= 0:
            raise ValueError("sensitivity must be greater than zero")
        if not 0 < self._smoothing <= 1:
            raise ValueError("smoothing must be in (0, 1]")
        if self._max_jump <= 0:
            raise ValueError("max_jump must be greater than zero")
        self._baseline = None
        self._output = (0.0, 0.0)
        self._paused = False

    @staticmethod
    def _finite_real(value, name):
        if isinstance(value, bool) or not isinstance(value, numbers.Real):
            raise ValueError(f"{name} must be a finite real number")
        try:
            finite = math.isfinite(value)
        except OverflowError:
            finite = isinstance(value, numbers.Integral)
        if not finite:
            raise ValueError(f"{name} must be a finite real number")
        return value

    @classmethod
    def _validated_position(cls, position):
        if not isinstance(position, (tuple, list)) or len(position) != 2:
            raise ValueError("position must be None or a tuple/list of two finite real numbers")
        return (cls._finite_real(position[0], "x coordinate"),
                cls._finite_real(position[1], "y coordinate"))

    def update(self, position):
        """Process a position sample and return its filtered (dx, dy)."""
        if position is None:
            self._baseline = None
            self._output = (0.0, 0.0)
            return (0, 0)

        current = self._validated_position(position)
        if self._paused:
            return (0, 0)
        if self._baseline is None:
            self._baseline = current
            return (0, 0)

        raw_dx = current[0] - self._baseline[0]
        raw_dy = current[1] - self._baseline[1]
        self._baseline = current
        try:
            is_jump = math.hypot(raw_dx, raw_dy) > self._max_jump
        except OverflowError:
            is_jump = True
        if is_jump:
            self._output = (0.0, 0.0)
            return (0, 0)

        alpha = self._smoothing
        self._output = (
            alpha * (raw_dx * self._sensitivity) + (1 - alpha) * self._output[0],
            alpha * (raw_dy * self._sensitivity) + (1 - alpha) * self._output[1],
        )
        return self._output

    def pause(self):
        """Clear tracking and ignore valid updates until resumed."""
        self._baseline = None
        self._output = (0.0, 0.0)
        self._paused = True

    def resume(self):
        """Clear tracking and leave paused mode."""
        self._baseline = None
        self._output = (0.0, 0.0)
        self._paused = False

    def reset(self):
        """Clear baseline and output without changing paused status."""
        self._baseline = None
        self._output = (0.0, 0.0)
