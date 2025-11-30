import math

Coord = tuple[float, float]

def lerp(start: Coord, end: Coord, v: float) -> Coord:
    sx, sy = start
    ex, ey = end
    return (
        sx + (ex - sx) * v,
        sy + (ey - sy) * v,
    )

class Animator:
    def __init__(
            self,
            start: Coord,
            end: Coord,
            duration: float
        ) -> None:
            self._start = start
            self._end = end
            self._duration = max(duration, 1e-6)
            self._elapsed = 0.0
            self._v = 0

    def reset(self) -> None:
          self._elapsed = 0.0

    def _update_t(self, delta: float) -> float:
        self._elapsed += max(delta, 0.0)
        if self._elapsed >= self._duration:
            self._elapsed = self._duration
        return self._elapsed / self._duration

    @property
    def curr(self) -> Coord:
        return lerp(self._start, self._end, self._v)

    @property
    def is_finished(self) -> bool:
        return self._elapsed >= self._duration

class Linear(Animator):
    def update(self, delta: float) -> None:
        t = self._update_t(delta)
        self._v = t

class OutCubic(Animator):
    def update(self, delta: float) -> None:
        t = self._update_t(delta)
        self._v = 1.0 - (1.0 - t) ** 3

class InCubic(Animator):
    def update(self, delta: float) -> None:
        t = self._update_t(delta)
        self._v = t ** 3

class OutBack(Animator):
    def update(self, delta: float, s: float = 1.70158) -> None:
        t = self._update_t(delta)
        t_prime = t - 1.0
        self._v = t_prime * t_prime * ((s + 1.0) * t_prime + s) + 1.0

class InBack(Animator):
    def update(self, delta: float, s: float = 1.70158) -> None:
        t = self._update_t(delta)
        self._v = t * t * ((s + 1.0) * t - s)

class Elastic(Animator):
    def update(self, delta: float, period: float = 0.3) -> None:
        t = self._update_t(delta)

        if t == 0.0:
            self._v = 0.0
        elif t == 1.0:
            self._v = 1.0
        else:
            s = period / 4.0
            self._v = pow(2.0, -10.0 * t) * math.sin((t - s) * 2.0 * math.pi / period) + 1.0