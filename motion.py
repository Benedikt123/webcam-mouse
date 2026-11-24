"""Deterministic, dependency-free motion tracking; no device or OS access."""

from fractions import Fraction
from math import hypot, isfinite
from numbers import Rational, Real

__all__ = ['MotionTracker']


def _finite_real(value):
    """Accept real numbers, without converting arbitrary-size rationals to float."""
    return (
        isinstance(value, Real)
        and not isinstance(value, bool)
        and (isinstance(value, Rational) or isfinite(value))
    )


class MotionTracker:
    """Convert successive positions into scaled, exponentially smoothed deltas.

    Configuration is fixed at construction. None signals tracking loss. A raw
    displacement strictly greater than max_jump rebases without producing motion.
    pause(), resume(), and reset() discard all motion history.
    """

    def __init__(self, sensitivity=1.0, smoothing=1.0, max_jump=100.0):
        for name, value in (('sensitivity', sensitivity),
                            ('smoothing', smoothing), ('max_jump', max_jump)):
            if not _finite_real(value) or value <= 0:
                raise ValueError(f'{name} must be a positive finite real number')
        if smoothing > 1:
            raise ValueError('smoothing must be at most 1')
        self._sensitivity = sensitivity
        self._smoothing = smoothing
        self._max_jump = max_jump
        self._paused = False
        self.reset()

    def reset(self):
        """Clear baseline and output history, preserving paused status."""
        self._position = None
        self._output = (0, 0)

    def pause(self):
        """Enter paused mode and discard motion history, even if already paused."""
        self.reset()
        self._paused = True

    def resume(self):
        """Leave paused mode and discard motion history, even if already active."""
        self.reset()
        self._paused = False

    def _is_jump(self, dx, dy):
        # Axis checks also handle infinite deltas from finite-float subtraction.
        if abs(dx) > self._max_jump or abs(dy) > self._max_jump:
            return True
        if all(isinstance(value, Rational) for value in (dx, dy, self._max_jump)):
            # Exact rational comparison preserves equality and huge integers.
            return dx * dx + dy * dy > self._max_jump * self._max_jump
        try:
            # Unlike naive squaring, hypot avoids float overflow/underflow.
            return hypot(dx, dy) > self._max_jump
        except OverflowError:
            # Mixed float/rational inputs can contain integers too large for
            # hypot's float conversion. All values here are finite.
            x, y, limit = (Fraction(value) for value in (dx, dy, self._max_jump))
            return x * x + y * y > limit * limit

    def update(self, position):
        """Return (dx, dy); reject malformed input before changing any state."""
        if position is None:
            self.reset()
            return (0, 0)
        if (not isinstance(position, (tuple, list)) or len(position) != 2
                or not all(_finite_real(value) for value in position)):
            raise ValueError('position must be None or two finite real numbers in a tuple/list')
        current = (position[0], position[1])
        if self._paused:
            return (0, 0)
        if self._position is None:
            self._position = current
            return (0, 0)

        dx = current[0] - self._position[0]
        dy = current[1] - self._position[1]
        if self._is_jump(dx, dy):
            self._position = current
            self._output = (0, 0)
            return (0, 0)

        alpha = self._smoothing
        output = (
            alpha * (dx * self._sensitivity) + (1 - alpha) * self._output[0],
            alpha * (dy * self._sensitivity) + (1 - alpha) * self._output[1],
        )
        self._position = current
        self._output = output
        return output
