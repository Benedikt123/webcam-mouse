"""Deterministic relative motion from a sequence of tracked positions."""

from fractions import Fraction
from numbers import Rational, Real


_ZERO = (0, 0)
# Extra fractional bits beyond the resolution of the scaled input and gain.
_GUARD_BITS = 64


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
        self._retention = 1 - self._smoothing
        self._base_bits = _GUARD_BITS + self._smoothing.denominator.bit_length()
        self._paused = False
        self.reset()

    def _clear_output(self):
        self._output = _ZERO
        self._x_bits = self._y_bits = self._base_bits

    def reset(self):
        """Forget position and filter history without changing pause status."""
        self._position = None
        self._clear_output()

    def pause(self):
        self.reset()
        self._paused = True

    def resume(self):
        self.reset()
        self._paused = False

    def _blend(self, scaled, previous, bits):
        # Size history by peak input precision on this axis, not frame count.
        bits = max(bits, self._base_bits + scaled.denominator.bit_length())
        value = self._smoothing * scaled + self._retention * previous
        if value.denominator.bit_length() > bits:
            # Round only filter history, never coordinates or threshold geometry.
            unit = 1 << bits
            value = Fraction(round(value * unit), unit)
        return value, bits

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

        previous = self._position
        self._position = (x, y)
        if previous is None:
            return _ZERO
        dx, dy = x - previous[0], y - previous[1]
        if dx * dx + dy * dy > self._max_jump_squared:
            self._clear_output()
        else:
            sx, sy = self._sensitivity * dx, self._sensitivity * dy
            ox, oy = self._output
            ox, self._x_bits = self._blend(sx, ox, self._x_bits)
            oy, self._y_bits = self._blend(sy, oy, self._y_bits)
            self._output = ox, oy
        return self._output
