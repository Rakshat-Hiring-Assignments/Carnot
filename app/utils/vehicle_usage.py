from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.config import PINGS_CSV_PATH, VEHICLES_CSV_PATH

DATE_FORMATS = [
    "%d/%m/%Y %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%d-%b-%Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
]
MAX_PLAUSIBLE_ODOMETER_INCREASE_KM = 10000.0
MAX_PLAUSIBLE_ODOMETER_KM = 1_000_000.0


class VehicleNotFoundError(KeyError):
    pass


@dataclass
class PingRecord:
    device_id: str
    ts: datetime
    odometer_km: float | None


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _parse_odometer(value: str | None) -> float | None:
    if value is None:
        return None
    raw = value.strip()
    if raw == "":
        return None
    try:
        odometer = float(raw)
    except ValueError:
        return None
    if odometer < 0 or odometer > MAX_PLAUSIBLE_ODOMETER_KM:
        return None
    return odometer


def _load_csv_rows(file_path: Path) -> list[dict[str, str]]:
    with file_path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _load_vehicle_master() -> dict[str, dict[str, str]]:
    rows = _load_csv_rows(VEHICLES_CSV_PATH)
    return {
        row["device_id"].strip(): {
            key: value.strip() for key, value in row.items() if value is not None
        }
        for row in rows
        if row.get("device_id")
    }


def _load_ping_records() -> tuple[list[PingRecord], list[str]]:
    records: list[PingRecord] = []
    warnings: list[str] = []
    invalid_timestamp_count = 0
    invalid_odometer_count = 0
    ignored_empty_device_count = 0

    for row in _load_csv_rows(PINGS_CSV_PATH):
        device_id = (row.get("device_id") or "").strip()
        if not device_id:
            ignored_empty_device_count += 1
            continue

        ts = _parse_timestamp(row.get("ts"))
        if ts is None:
            invalid_timestamp_count += 1
            continue

        odometer_km = _parse_odometer(row.get("odometer_km"))
        if odometer_km is None and row.get("odometer_km", "").strip() != "":
            invalid_odometer_count += 1

        records.append(PingRecord(device_id=device_id, ts=ts, odometer_km=odometer_km))

    if invalid_timestamp_count:
        warnings.append(
            f"Ignored {invalid_timestamp_count} ping rows with invalid or unsupported timestamps."
        )
    if invalid_odometer_count:
        warnings.append(
            f"Ignored {invalid_odometer_count} odometer readings because they were missing, negative, or out of range."
        )
    if ignored_empty_device_count:
        warnings.append(f"Ignored {ignored_empty_device_count} ping rows with missing device_id.")

    return records, warnings


def _build_active_window_end(records: list[PingRecord]) -> datetime | None:
    if not records:
        return None
    return max(record.ts for record in records)


def compute_vehicle_usage(device_id: str) -> dict[str, Any]:
    vehicle_master = _load_vehicle_master()
    if device_id not in vehicle_master:
        raise VehicleNotFoundError(device_id)

    ping_records, warnings = _load_ping_records()
    vehicle_records = [record for record in ping_records if record.device_id == device_id]
    if not vehicle_records:
        return {
            "device_id": device_id,
            "total_distance_km": 0.0,
            "active_days": 0,
            "status": "no_data",
            "notes": warnings + ["No ping records found for this vehicle."],
        }

    valid_odometer_records = [record for record in vehicle_records if record.odometer_km is not None]
    if not valid_odometer_records:
        return {
            "device_id": device_id,
            "total_distance_km": 0.0,
            "active_days": 0,
            "status": "no_data",
            "notes": warnings + ["Found ping records for this vehicle, but no valid odometer readings."],
        }

    vehicle_records.sort(key=lambda record: record.ts)
    dataset_end = _build_active_window_end(ping_records)
    active_window_start = (
        dataset_end.date() - timedelta(days=6)
    ) if dataset_end else None

    total_distance = 0.0
    active_dates: set[datetime.date] = set()
    prev_odometer: float | None = None
    reset_count = 0
    outlier_count = 0

    for record in vehicle_records:
        if record.odometer_km is None:
            prev_odometer = None
            continue

        if prev_odometer is None:
            prev_odometer = record.odometer_km
            continue

        diff = record.odometer_km - prev_odometer
        if diff <= 0:
            reset_count += 1
            prev_odometer = record.odometer_km
            continue

        if diff > MAX_PLAUSIBLE_ODOMETER_INCREASE_KM:
            outlier_count += 1
            prev_odometer = record.odometer_km
            continue

        total_distance += diff
        active_dates.add(record.ts.date())
        prev_odometer = record.odometer_km

    if reset_count:
        warnings.append(
            f"Detected {reset_count} odometer resets or rollbacks; those intervals were ignored."
        )
    if outlier_count:
        warnings.append(
            f"Ignored {outlier_count} implausible odometer jumps larger than {MAX_PLAUSIBLE_ODOMETER_INCREASE_KM:.0f} km."
        )

    status = "inactive"
    if not active_dates:
        status = "inactive"
    elif active_window_start is not None and any(
        day >= active_window_start for day in active_dates
    ):
        status = "active"

    if total_distance == 0 and not active_dates:
        status = "inactive" if vehicle_records else "no_data"

    response = {
        "device_id": device_id,
        "total_distance_km": round(total_distance, 1),
        "active_days": len(active_dates),
        "status": status,
        "notes": warnings,
    }
    return response
