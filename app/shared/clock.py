from datetime import date, datetime, timedelta, timezone


class Clock:
    """Fuente de tiempo inyectable. Los servicios nunca llaman a datetime.now() directamente."""

    def now(self) -> datetime:
        raise NotImplementedError

    def today(self) -> date:
        return self.now().date()


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class FixedClock(Clock):
    """Reloj controlable para pruebas: se fija en un instante y se adelanta a voluntad."""

    def __init__(self, start: datetime):
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, **kwargs) -> None:
        self._now = self._now + timedelta(**kwargs)
