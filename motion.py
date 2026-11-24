"""Deterministic relative motion from a sequence of tracked positions."""

from fractions import Fraction
from numbers import Rational, Real


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


def _signal_floor(signal, retention):
    """Allow a subnormal-sized tail relative to each injected signal."""
    tail = signal * retention
    if not tail:
        return 1074
    return max(1074, 1074 + tail.denominator.bit_length()
               - abs(tail.numerator).bit_length())


def _round_output(value, max_shift):
    """Round to 53 significant binary bits, without float exponent limits.

    Bound recursive filter precision, not the input range. Integer arithmetic
    implements round-to-nearest, ties-to-even, even for tiny/huge rationals.
    The quantum floor starts at binary64's smallest subnormal. Extend it
    below the injected signal and its first retained tail, not merely for a
    decaying history: an
    unbounded exponent alone would still grow denominators during long idles.
    """
    if not value:
        return Fraction(0)
    numerator, denominator = abs(value.numerator), value.denominator
    exponent = numerator.bit_length() - denominator.bit_length()
    if exponent >= 0:
        if numerator < denominator << exponent:
            exponent -= 1
    elif numerator << -exponent < denominator:
        exponent -= 1
    shift = min(52 - exponent, max_shift)
    if shift >= 0:
        numerator <<= shift
    else:
        denominator <<= -shift
    significand, remainder = divmod(numerator, denominator)
    if 2 * remainder > denominator or (
            2 * remainder == denominator and significand % 2):
        significand += 1
    if value < 0:
        significand = -significand
    if shift >= 0:
        return Fraction(significand, 1 << shift)
    return Fraction(significand << -shift)


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
        self._retention = 1 - self._smoothing
        self._max_jump_squared = max_jump * max_jump
        self._paused = False
        self.reset()

    def reset(self):
        """Forget position and filter history without changing pause status."""
        self._position = None
        self._output = _ZERO
        self._output_shifts = (1074, 1074)

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
            self._output_shifts = (1074, 1074)
        else:
            sx, sy = self._sensitivity * dx, self._sensitivity * dy
            a = self._smoothing
            ox, oy = self._output
            if a == 1:
                # No recursive history: exact arithmetic cannot accumulate bits.
                self._output = (sx, sy)
            else:
                ix, iy = a * sx, a * sy
                qx, qy = self._output_shifts
                qx = max(qx, _signal_floor(ix, self._retention))
                qy = max(qy, _signal_floor(iy, self._retention))
                self._output_shifts = (qx, qy)
                self._output = (
                    _round_output(ix + self._retention * ox, qx),
                    _round_output(iy + self._retention * oy, qy),
                )
        return self._output
