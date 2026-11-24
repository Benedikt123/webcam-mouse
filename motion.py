"""Deterministic relative motion from a sequence of tracked positions."""

from fractions import Fraction
from numbers import Rational, Real
import math


_ZERO = (0, 0)


def _finite_real(value, name):
    """Keep rational values exact, without narrowing large integers to float."""
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f'{name} must be a finite real number')
    if isinstance(value, Rational):
        return Fraction(value)
    try:
        return Fraction.from_float(float(value))
    except (ValueError, OverflowError) as exc:  # NaN or infinity
        raise ValueError(f'{name} must be a finite real number') from exc


class MotionTracker:
    """Convert absolute position samples into relative (dx, dy) outputs."""

    def __init__(self, sensitivity=1.0, smoothing=1.0, max_jump=100.0):
        self._sensitivity = _finite_real(sensitivity, 'sensitivity')
        self._smoothing = _finite_real(smoothing, 'smoothing')
        max_jump = _finite_real(max_jump, 'max_jump')
        if self._sensitivity <= 0:
            raise ValueError('sensitivity must be positive')
        if not 0 < self._smoothing <= 1:
            raise ValueError('smoothing must be in (0, 1]')
        if max_jump <= 0:
            raise ValueError('max_jump must be positive')
        self._max_jump_squared = max_jump * max_jump
        self._paused = False
        self.reset()

    def reset(self):
        """Forget position and filter history without changing pause status."""
        self._position = None
        self._output = _ZERO

    def pause(self):
        self.reset()
        self._paused = True

    def resume(self):
        self.reset()
        self._paused = False

    def update(self, position):
        """Consume one sample (None for loss); reject malformed samples atomically."""
        if position is None:
            self.reset()
            return _ZERO
        if not isinstance(position, (tuple, list)) or len(position) != 2:
            raise ValueError('position must be None or a two-coordinate tuple/list')
        x = _finite_real(position[0], 'x')
        y = _finite_real(position[1], 'y')
        if self._paused:
            return _ZERO

        # Camera coordinates are normally floats. Keep their filter state in
        # binary floating point instead of growing exact fractions forever.
        if (not isinstance(position[0], Rational)
                and not isinstance(position[1], Rational)
                and (self._position is None
                     or all(isinstance(value, float) for value in self._position))):
            try:
                fx, fy = float(x), float(y)
                sensitivity = float(self._sensitivity)
                smoothing = float(self._smoothing)
                max_jump_squared = float(self._max_jump_squared)
                if not math.isfinite(max_jump_squared):
                    raise OverflowError
            except OverflowError:
                pass
            else:
                previous = self._position
                if previous is not None:
                    previous = (float(previous[0]), float(previous[1]))
                self._position = (fx, fy)
                if previous is None:
                    return _ZERO
                dx, dy = fx - previous[0], fy - previous[1]
                if math.hypot(dx, dy) > math.sqrt(max_jump_squared):
                    self._output = _ZERO
                else:
                    ox, oy = self._output
                    output = (smoothing * sensitivity * dx + (1 - smoothing) * ox,
                              smoothing * sensitivity * dy + (1 - smoothing) * oy)
                    if math.isfinite(output[0]) and math.isfinite(output[1]):
                        self._output = output
                    else:
                        # Retain exact behavior for extreme finite values whose
                        # intermediate floating-point arithmetic overflows.
                        self._position = (x, y)
                        previous = None if previous is None else tuple(Fraction(v) for v in previous)
                        self._output = tuple(Fraction(v) for v in self._output)
                        if previous is None:
                            return _ZERO
                        return self._exact_update(x, y, previous)
                return self._output

        previous = self._position
        if previous is not None:
            previous = tuple(Fraction(v) for v in previous)
        self._position = (x, y)
        if previous is None:
            return _ZERO
        return self._exact_update(x, y, previous)

    def _exact_update(self, x, y, previous):
        dx, dy = x - previous[0], y - previous[1]
        if dx * dx + dy * dy > self._max_jump_squared:
            self._output = _ZERO
        else:
            sx, sy = self._sensitivity * dx, self._sensitivity * dy
            a = self._smoothing
            ox, oy = self._output
            self._output = (a * sx + (1 - a) * ox, a * sy + (1 - a) * oy)
        return self._output
