class Typewriter:
    def __init__(
            self,
            full_text: str,
            cps_scale: float = 1.0,
            base_cps: float = 18,
        ) -> None:
        self._full_text: str = full_text
        self._progress: float = 0.0

        self._base_cps = base_cps
        self.cps_scale = cps_scale

    @property
    def current_cps(self) -> float:
        return self._base_cps * self.cps_scale

    @property
    def visible_text(self) -> str:
        return self._full_text[:round(self._progress)]

    @property
    def is_finished(self) -> bool:
        return self._progress >= len(self._full_text)

    def update(self, delta: float) -> None:
        self._progress = min(len(self._full_text), self._progress + self.current_cps * delta)

    def skip(self) -> None:
        self._progress = len(self._full_text)

    def reset(self, full_text: str | None = None) -> None:
        self._progress = 0
        if full_text is not None:
            self._full_text = full_text
