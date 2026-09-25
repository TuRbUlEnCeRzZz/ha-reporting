from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import calendar
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
            "duration_seconds": max(
                0.0,
                self.end.timestamp() - self.start.timestamp(),
            ),
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

        if end.timestamp() <= start.timestamp():
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

        if end.timestamp() <= start.timestamp():
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
            local = dt.replace(tzinfo=self.tz)
            if datetime.fromtimestamp(local.timestamp(), self.tz).replace(tzinfo=None) != dt:
                raise ValueError("Heure locale inexistante lors du passage à l'heure d'été")
            return local
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

    def comparison_targets(
        self,
        base: ResolvedPeriod,
        comparison_spec: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        spec = comparison_spec or {}
        previous_periods = self._bounded_count(spec.get("previous_periods", 0))
        previous_years = self._bounded_count(spec.get("previous_years", 0))

        output = []
        for offset in range(1, previous_periods + 1):
            output.append(
                self._comparison_target(base, "previous_period", offset)
            )
        for offset in range(1, previous_years + 1):
            output.append(
                self._comparison_target(base, "previous_year", offset)
            )
        return output

    @staticmethod
    def _bounded_count(raw: Any) -> int:
        try:
            value = int(raw or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError("Le nombre de périodes de comparaison doit être un entier") from exc
        if value < 0 or value > 5:
            raise ValueError("Les comparaisons N-x sont limitées à 5 périodes par type")
        return value

    def _comparison_target(
        self,
        base: ResolvedPeriod,
        kind: str,
        offset: int,
    ) -> dict[str, Any]:
        if kind == "previous_period":
            if base.period_type == "custom":
                duration_seconds = max(
                    0.0,
                    base.end.timestamp() - base.start.timestamp(),
                )
                start = datetime.fromtimestamp(
                    base.start.timestamp() - duration_seconds * offset,
                    self.tz,
                )
                end = datetime.fromtimestamp(
                    base.end.timestamp() - duration_seconds * offset,
                    self.tz,
                )
            else:
                start = self._shift_preserving_position(
                    base.start, base.period_type, -offset
                )
                end = self._shift_preserving_position(
                    base.end, base.period_type, -offset
                )
            label = (
                f"N-{offset} période"
                if offset == 1
                else f"N-{offset} périodes"
            )
            target_id = f"period_{offset}"
        elif kind == "previous_year":
            start = self._add_years_preserve_day(base.start, -offset)
            end = self._add_years_preserve_day(base.end, -offset)
            label = f"N-{offset} an" if offset == 1 else f"N-{offset} ans"
            target_id = f"year_{offset}"
        else:
            raise ValueError(f"Type de comparaison inconnu: {kind}")

        resolved = ResolvedPeriod(
            period_type=base.period_type,
            mode="comparison",
            timezone=self.timezone_name,
            start=start,
            end=end,
            label=(
                f"{label} · {start:%d.%m.%Y %H:%M} → "
                f"{end:%d.%m.%Y %H:%M}"
            ),
        )
        return {
            "id": target_id,
            "kind": kind,
            "offset": offset,
            "label": label,
            "resolved_period": resolved,
        }

    def _shift_preserving_position(
        self,
        dt: datetime,
        period_type: str,
        amount: int,
    ) -> datetime:
        if period_type == "day":
            return dt + timedelta(days=amount)
        if period_type == "week":
            return dt + timedelta(weeks=amount)
        if period_type == "month":
            return self._add_months_preserve_day(dt, amount)
        if period_type == "quarter":
            return self._add_months_preserve_day(dt, amount * 3)
        if period_type == "semester":
            return self._add_months_preserve_day(dt, amount * 6)
        if period_type == "year":
            return self._add_years_preserve_day(dt, amount)
        raise ValueError(period_type)

    @staticmethod
    def _add_months_preserve_day(dt: datetime, months: int) -> datetime:
        total = dt.year * 12 + (dt.month - 1) + months
        year, month_index = divmod(total, 12)
        month = month_index + 1
        day = min(dt.day, calendar.monthrange(year, month)[1])
        return dt.replace(year=year, month=month, day=day)

    @staticmethod
    def _add_years_preserve_day(dt: datetime, years: int) -> datetime:
        year = dt.year + years
        day = min(dt.day, calendar.monthrange(year, dt.month)[1])
        return dt.replace(year=year, day=day)

    @staticmethod
    def _label(period_type: str, mode: str, start: datetime, end: datetime) -> str:
        current_labels = {
            "day": "Jour en cours",
            "week": "Semaine en cours",
            "month": "Mois en cours",
            "quarter": "Trimestre en cours",
            "semester": "Semestre en cours",
            "year": "Année en cours",
        }
        previous_labels = {
            "day": "Jour précédent",
            "week": "Semaine précédente",
            "month": "Mois précédent",
            "quarter": "Trimestre précédent",
            "semester": "Semestre précédent",
            "year": "Année précédente",
        }
        label = current_labels[period_type] if mode == "current" else previous_labels[period_type]
        return f"{label} · {start:%d.%m.%Y %H:%M} → {end:%d.%m.%Y %H:%M}"
