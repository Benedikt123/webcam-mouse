"""Deterministic relative pointer motion from a stream of positions."""

from fractions import Fraction
from math import hypot, isfinite
from numbers import Rational, Real

__all__ = ["MotionTracker"]

_ZERO = (0, 0)


def _is_finite_real(value):
    # Rational numbers are finite, even when they are too large for a float.
    return (isinstance(value, Real) and not isinstance(value, bool)
            and (isinstance(value, Rational) or isfinite(value)))


def _as_fraction(value):
    if isinstance(value, (Rational, float)):
        return Fraction(value)
    return Fraction(float(value))


def _difference(current, previous):
    # Avoid losing a small delta by converting a large integer (or a precise
    # fraction) to float before subtraction. Ordinary float deltas stay floats.
    if isinstance(current, Rational) != isinstance(previous, Rational):
        rational = current if isinstance(current, Rational) else previous
        try:
            representable = float(rational) == rational
        except OverflowError:
            representable = False
        if not representable:
            return _as_fraction(current) - _as_fraction(previous)
    delta = current - previous
    if isinstance(delta, float) and not isfinite(delta):
        return _as_fraction(current) - _as_fraction(previous)
    return delta


def _is_jump(dx, dy, limit):
    # If an axis reaches the limit, a nonzero perpendicular component puts
    # the displacement over it, even when hypot would round back to the limit.
    ax, ay = abs(dx), abs(dy)
    if ax >= limit:
        return ax > limit or ay != 0
    if ay >= limit:
        return ay > limit or ax != 0

    # With rational deltas, the squared comparison avoids rounding at the
    # boundary. For ordinary float inputs, use the stable floating-point norm.
    if not (isinstance(dx, Rational) and isinstance(dy, Rational)):
        try:
            if all(float(value) == value for value in (dx, dy, limit)):
                return hypot(dx, dy) > limit
        except OverflowError:
            pass
    x, y, radius = map(_as_fraction, (dx, dy, limit))
    return x * x + y * y > radius * radius


class MotionTracker:
    """Convert successive 2D positions to scaled, smoothed displacements."""

    def __init__(self, sensitivity=1.0, smoothing=1.0, max_jump=100.0):
        for name, value in (("sensitivity", sensitivity), ("smoothing", smoothing),
                            ("max_jump", max_jump)):
            if not _is_finite_real(value) or value <= 0:
                raise ValueError(f"{name} must be a positive finite real number")
        if smoothing > 1:
            raise ValueError("smoothing must be at most 1")
        self._sensitivity = sensitivity
        self._smoothing = smoothing
        self._max_jump = max_jump
        self._paused = False
        self.reset()

    def update(self, position):
        """Return (dx, dy); None signals loss of tracking."""
        if position is None:
            self.reset()
            return _ZERO
        if not isinstance(position, (tuple, list)) or len(position) != 2:
            raise ValueError("position must be None or a two-element tuple or list")
        x, y = position
        if not (_is_finite_real(x) and _is_finite_real(y)):
            raise ValueError("position coordinates must be finite real numbers")
        if self._paused:
            return _ZERO

        previous = self._position
        self._position = (x, y)
        if previous is None:
            return _ZERO
        dx, dy = _difference(x, previous[0]), _difference(y, previous[1])
        if _is_jump(dx, dy, self._max_jump):
            self._output = _ZERO
        else:
            self._output = (self._smooth(dx, self._output[0]),
                            self._smooth(dy, self._output[1]))
        return self._output

    def _smooth(self, delta, previous):
        sensitivity, smoothing = self._sensitivity, self._smoothing
        try:
            scaled = delta if sensitivity == 1 else sensitivity * delta
            output = (scaled if smoothing == 1
                      else smoothing * scaled + (1 - smoothing) * previous)
            if not isinstance(output, float) or isfinite(output):
                return output
        except OverflowError:
            pass
        # A finite input can overflow even when the final output would fit
        # in a float. Recompute without float intermediates in that case.
        gain, weight, raw, last = map(_as_fraction, (sensitivity, smoothing, delta, previous))
        return weight * (gain * raw) + (1 - weight) * last

    def pause(self) -> None:
        """Clear motion history and ignore valid samples until resumed."""
        self._paused = True
        self.reset()

    def resume(self) -> None:
        """Enable motion with no baseline or previous output."""
        self._paused = False
        self.reset()

    def reset(self) -> None:
        """Clear motion history without changing the pause state."""
        self._position = None
        self._output = _ZERO
