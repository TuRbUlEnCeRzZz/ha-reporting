from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo


PERIOD_TYPES = {"day", "week", "month", "quarter", "semester", "year", "custom"}
PERIOD_MODES = {"current", "previous"}


@dataclass(frozen=True)
class ResolvedPeriod:
    period_type: str
    mode: str
    timezone: str
    start: datetime
    end: datetime
    label: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "type": self.period_type,
            "mode": self.mode,
            "timezone": self.timezone,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "start_epoch": self.start.timestamp(),
            "end_epoch": self.end.timestamp(),
            "duration_seconds": max(0.0, (self.end - self.start).total_seconds()),
            "label": self.label,
            "semantics": "[start, end)",
        }


class PeriodEngine:
    """Resolve report shortcuts into explicit timezone-aware start/end bounds."""

    def __init__(self, timezone_name: str):
        self.timezone_name = timezone_name or "UTC"
        self.tz = ZoneInfo(self.timezone_name)

    def resolve(
        self,
        spec: dict[str, Any],
        now: datetime | None = None,
    ) -> ResolvedPeriod:
        period_type = str(spec.get("type") or "month")
        mode = str(spec.get("mode") or "current")

        if period_type not in PERIOD_TYPES:
            raise ValueError(f"Type de période non supporté: {period_type}")

        if period_type == "custom":
            return self._resolve_custom(spec)

        if mode not in PERIOD_MODES:
            raise ValueError(f"Mode de période non supporté: {mode}")

        ref = now or datetime.now(self.tz)
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=self.tz)
        else:
            ref = ref.astimezone(self.tz)

        current_start = self._floor(ref, period_type)

        if mode == "current":
            start = current_start
            end = ref
        else:
            start = self._shift(current_start, period_type, -1)
            end = current_start

        if end <= start:
            raise ValueError("La fin de période doit être postérieure au début")

        return ResolvedPeriod(
            period_type=period_type,
            mode=mode,
            timezone=self.timezone_name,
            start=start,
            end=end,
            label=self._label(period_type, mode, start, end),
        )

    def _resolve_custom(self, spec: dict[str, Any]) -> ResolvedPeriod:
        start = self._parse_local(spec.get("start"))
        end = self._parse_local(spec.get("end"))

        if end <= start:
            raise ValueError("La fin de période personnalisée doit être postérieure au début")

        return ResolvedPeriod(
            period_type="custom",
            mode="custom",
            timezone=self.timezone_name,
            start=start,
            end=end,
            label=f"{start:%d.%m.%Y %H:%M} → {end:%d.%m.%Y %H:%M}",
        )

    def _parse_local(self, raw: Any) -> datetime:
        value = str(raw or "").strip()
        if not value:
            raise ValueError("Début et fin sont requis pour une période personnalisée")

        try:
            dt = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"Date/heure invalide: {value}") from exc

        if dt.tzinfo is None:
            return dt.replace(tzinfo=self.tz)
        return dt.astimezone(self.tz)

    def _floor(self, dt: datetime, period_type: str) -> datetime:
        if period_type == "day":
            return dt.replace(hour=0, minute=0, second=0, microsecond=0)

        if period_type == "week":
            start = dt - timedelta(days=dt.weekday())
            return start.replace(hour=0, minute=0, second=0, microsecond=0)

        if period_type == "month":
            return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        if period_type == "quarter":
            month = ((dt.month - 1) // 3) * 3 + 1
            return dt.replace(month=month, day=1, hour=0, minute=0, second=0, microsecond=0)

        if period_type == "semester":
            month = 1 if dt.month <= 6 else 7
            return dt.replace(month=month, day=1, hour=0, minute=0, second=0, microsecond=0)

        if period_type == "year":
            return dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

        raise ValueError(period_type)

    def _shift(self, dt: datetime, period_type: str, amount: int) -> datetime:
        if period_type == "day":
            return dt + timedelta(days=amount)

        if period_type == "week":
            return dt + timedelta(weeks=amount)

        if period_type == "month":
            return self._add_months(dt, amount)

        if period_type == "quarter":
            return self._add_months(dt, amount * 3)

        if period_type == "semester":
            return self._add_months(dt, amount * 6)

        if period_type == "year":
            return dt.replace(year=dt.year + amount)

        raise ValueError(period_type)

    @staticmethod
    def _add_months(dt: datetime, months: int) -> datetime:
        total = dt.year * 12 + (dt.month - 1) + months
        year, month_index = divmod(total, 12)
        return dt.replace(year=year, month=month_index + 1, day=1)

    @staticmethod
    def _label(period_type: str, mode: str, start: datetime, end: datetime) -> str:
        names = {
            "day": "Jour",
            "week": "Semaine",
            "month": "Mois",
            "quarter": "Trimestre",
            "semester": "Semestre",
            "year": "Année",
        }
        mode_label = "en cours" if mode == "current" else "précédent(e)"
        return f"{names[period_type]} {mode_label} · {start:%d.%m.%Y %H:%M} → {end:%d.%m.%Y %H:%M}"
