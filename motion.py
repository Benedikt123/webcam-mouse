"""Deterministic relative motion from a sequence of tracked positions."""

from fractions import Fraction
from numbers import Rational, Real


_ZERO = (0, 0)
_GUARD_BITS = 48


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


def _bound_precision(value, fractional_bits):
    """Keep small rationals exact; truncate oversized denominators to a binary grid."""
    if value.denominator.bit_length() <= fractional_bits + 1:
        return value
    scale = 1 << fractional_bits
    # Toward zero rather than nearest, so an idle axis cannot stick at a
    # nonzero value due to quantization opposing the filter's decay.
    return Fraction(int(value * scale), scale)


class MotionTracker:
    """Convert absolute position samples into relative (dx, dy) outputs."""

    def __init__(self, sensitivity=1.0, smoothing=1.0, max_jump=100.0):
        sensitivity = _finite_real(sensitivity, 'sensitivity')
        smoothing = _finite_real(smoothing, 'smoothing')
        max_jump = _finite_real(max_jump, 'max_jump')
        if sensitivity <= 0:
            raise ValueError('sensitivity must be positive')
        if not 0 < smoothing <= 1:
            raise ValueError('smoothing must be in (0, 1]')
        if max_jump <= 0:
            raise ValueError('max_jump must be positive')
        self._max_jump_squared = max_jump * max_jump
        self._drive = sensitivity * smoothing
        self._decay = 1 - smoothing
        # Account for very small gain/alpha without narrowing either to float.
        self._base_bits = (_GUARD_BITS + sensitivity.denominator.bit_length()
                           + smoothing.denominator.bit_length())
        self._paused = False
        self.reset()

    def reset(self):
        """Forget position and filter history without changing pause status."""
        self._position = None
        self._output = _ZERO
        self._delta_bits = 0

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

        previous = self._position
        self._position = (x, y)
        if previous is None:
            return _ZERO
        dx, dy = x - previous[0], y - previous[1]
        if dx * dx + dy * dy > self._max_jump_squared:
            self._output = _ZERO
            self._delta_bits = 0
            return _ZERO
        if not self._decay:
            # No feedback means there is no accumulated denominator to cap.
            return self._drive * dx, self._drive * dy

        # Size the grid by input precision, not by how long the filter has run.
        # Retain the largest delta precision in the current filter history so a
        # stationary sample doesn't immediately erase a legitimate tiny output.
        self._delta_bits = max(self._delta_bits, dx.denominator.bit_length(),
                               dy.denominator.bit_length())
        bits = self._base_bits + self._delta_bits
        ox, oy = self._output
        self._output = (
            _bound_precision(self._drive * dx + self._decay * ox, bits),
            _bound_precision(self._drive * dy + self._decay * oy, bits),
        )
        return self._output
