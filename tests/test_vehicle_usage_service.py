import pytest
from datetime import datetime, timedelta

from app.utils.vehicle_services import VehicleUsageService


class DummyCSVRepository:
    def __init__(self):
        self.vehicles_map = {}

    def load_ping_data(self):
        return []


@pytest.fixture
def service(monkeypatch):
    """
    Create a VehicleUsageService instance with a dummy CSV repository.

    This avoids depending on the real CSV files for unit tests.
    """
    monkeypatch.setattr("app.utils.vehicle_services.CSVRepository", DummyCSVRepository)
    return VehicleUsageService()


class TestIterValidMovements:

    def test_should_yield_valid_movement(self, service):
        """
        Arrange:
            Create two valid pings with increasing odometer.

        Act:
            Call _iter_valid_movements()

        Assert:
            - Exactly one movement is yielded.
            - Distance is correct.
            - Speed is correct.
        """
        start_ts = datetime(2026, 1, 1, 8, 0, 0)
        pings = [
            {"device_id": "device-123", "ts": start_ts, "odometer_km": 100.0},
            {"device_id": "device-123", "ts": start_ts + timedelta(hours=2), "odometer_km": 140.0},
        ]

        movements = list(service._iter_valid_movements(pings))

        assert len(movements) == 1
        movement = movements[0]
        assert movement.distance_km == pytest.approx(40.0)
        assert movement.speed_kmph == pytest.approx(20.0)
        assert movement.timestamp == start_ts + timedelta(hours=2)

    def test_should_ignore_odometer_reset(self, service):
        """
        Arrange:
            100 -> 120 -> 10 -> 20

        Assert:
            - First movement counted.
            - Reset ignored.
            - Movement after reset counted.
        """
        start_ts = datetime(2026, 1, 1, 8, 0, 0)
        pings = [
            {"device_id": "device-123", "ts": start_ts, "odometer_km": 100.0},
            {"device_id": "device-123", "ts": start_ts + timedelta(hours=1), "odometer_km": 120.0},
            {"device_id": "device-123", "ts": start_ts + timedelta(hours=2), "odometer_km": 10.0},
            {"device_id": "device-123", "ts": start_ts + timedelta(hours=3), "odometer_km": 20.0},
        ]

        movements = list(service._iter_valid_movements(pings))

        assert len(movements) == 2
        assert movements[0].distance_km == pytest.approx(20.0)
        assert movements[0].speed_kmph == pytest.approx(20.0)
        assert movements[1].distance_km == pytest.approx(10.0)
        assert movements[1].speed_kmph == pytest.approx(10.0)

    def test_should_ignore_missing_odometer(self, service):
        """
        Arrange:
            100 -> None -> 105

        Assert:
            Missing odometer readings are skipped and valid subsequent movement is counted.
        """
        start_ts = datetime(2026, 1, 1, 8, 0, 0)
        pings = [
            {"device_id": "device-123", "ts": start_ts, "odometer_km": 100.0},
            {"device_id": "device-123", "ts": start_ts + timedelta(hours=1), "odometer_km": None},
            {"device_id": "device-123", "ts": start_ts + timedelta(hours=2), "odometer_km": 105.0},
        ]

        movements = list(service._iter_valid_movements(pings))

        assert len(movements) == 1
        assert movements[0].distance_km == pytest.approx(5.0)
        assert movements[0].speed_kmph == pytest.approx(2.5)

    def test_should_ignore_impossible_speed(self, service):
        """
        Arrange:
            Create two pings that imply an impossible speed.

        Assert:
            No movement should be yielded.
        """
        start_ts = datetime(2026, 1, 1, 8, 0, 0)
        pings = [
            {"device_id": "device-123", "ts": start_ts, "odometer_km": 100.0},
            {"device_id": "device-123", "ts": start_ts + timedelta(minutes=1), "odometer_km": 200.0},
        ]

        movements = list(service._iter_valid_movements(pings))

        assert movements == []

    def test_should_ignore_duplicate_timestamp(self, service):
        """
        Arrange:
            Two pings with identical timestamps.

        Assert:
            Movement should be ignored.
        """
        start_ts = datetime(2026, 1, 1, 8, 0, 0)
        pings = [
            {"device_id": "device-123", "ts": start_ts, "odometer_km": 100.0},
            {"device_id": "device-123", "ts": start_ts, "odometer_km": 120.0},
        ]

        movements = list(service._iter_valid_movements(pings))

        assert movements == []

    def test_should_sort_pings_before_processing(self, service):
        """
        Arrange:
            Supply pings out of chronological order.

        Assert:
            Correct movement sequence is produced.
        """
        start_ts = datetime(2026, 1, 1, 8, 0, 0)
        pings = [
            {"device_id": "device-123", "ts": start_ts + timedelta(hours=2), "odometer_km": 150.0},
            {"device_id": "device-123", "ts": start_ts, "odometer_km": 100.0},
            {"device_id": "device-123", "ts": start_ts + timedelta(hours=1), "odometer_km": 120.0},
        ]

        movements = list(service._iter_valid_movements(pings))

        assert len(movements) == 2
        assert movements[0].distance_km == pytest.approx(20.0)
        assert movements[0].speed_kmph == pytest.approx(20.0)
        assert movements[0].timestamp == start_ts + timedelta(hours=1)
        assert movements[1].distance_km == pytest.approx(30.0)
        assert movements[1].speed_kmph == pytest.approx(30.0)
        assert movements[1].timestamp == start_ts + timedelta(hours=2)


class TestComputeTotalDistance:

    def test_should_compute_total_distance(self, service):
        """
        Arrange:
            Several valid movements.

        Assert:
            Total equals sum of all yielded movements.
        """
        start_ts = datetime(2026, 1, 1, 8, 0, 0)
        pings = [
            {"device_id": "device-123", "ts": start_ts, "odometer_km": 100.0},
            {"device_id": "device-123", "ts": start_ts + timedelta(hours=1), "odometer_km": 120.0},
            {"device_id": "device-123", "ts": start_ts + timedelta(hours=2), "odometer_km": 150.0},
        ]

        total_distance = service._compute_total_distance(pings)

        assert total_distance == pytest.approx(50.0)


class TestComputeActiveDays:

    def test_should_count_unique_active_days(self, service):
        """
        Arrange:
            Multiple movements on the same day.

        Assert:
            Day counted only once.
        """
        start_ts = datetime(2026, 1, 1, 8, 0, 0)
        pings = [
            {"device_id": "device-123", "ts": start_ts, "odometer_km": 100.0},
            {"device_id": "device-123", "ts": start_ts + timedelta(hours=1), "odometer_km": 120.0},
            {"device_id": "device-123", "ts": start_ts + timedelta(hours=2), "odometer_km": 140.0},
        ]

        active_days, status = service._compute_active_days(pings)

        assert active_days == 1
        assert status == "active"

    def test_should_mark_vehicle_active(self, service):
        """
        Arrange:
            Movement occurs within the last 7 days.

        Assert:
            Status == active.
        """
        last_ts = datetime(2026, 1, 8, 12, 0, 0)
        pings = [
            {"device_id": "device-123", "ts": last_ts - timedelta(days=1), "odometer_km": 100.0},
            {"device_id": "device-123", "ts": last_ts, "odometer_km": 120.0},
        ]

        active_days, status = service._compute_active_days(pings)

        assert active_days == 1
        assert status == "active"

    def test_should_mark_vehicle_inactive(self, service):
        """
        Arrange:
            No movement in the last 7 days.

        Assert:
            Status == inactive.
        """
        last_ts = datetime(2026, 1, 14, 12, 0, 0)
        pings = [
            {"device_id": "device-123", "ts": last_ts - timedelta(days=10), "odometer_km": 100.0},
            {"device_id": "device-123", "ts": last_ts - timedelta(days=9), "odometer_km": 120.0},
        ]

        active_days, status = service._compute_active_days(pings)

        assert active_days == 1
        assert status == "inactive"


class TestComputeVehicleUsage:

    def test_should_return_no_data_for_vehicle_without_pings(self, service):
        """
        Arrange:
            Vehicle exists but has no ping records.

        Assert:
            status == no_data
            total_distance == 0
            active_days == 0
        """
        service.csv_repository.vehicles_map = {"device-123": {"name": "Test Vehicle"}}
        service.pings_by_device = {}

        response = service.compute_vehicle_usage("device-123")

        assert response is not None
        assert response.status == "no_data"
        assert response.total_distance_km == pytest.approx(0.0)
        assert response.active_days == 0

    def test_should_return_usage_for_valid_vehicle(self, service):
        """
        Arrange:
            Vehicle exists with valid pings.

        Assert:
            Response model contains expected values.
        """
        start_ts = datetime(2026, 1, 1, 8, 0, 0)
        pings = [
            {"device_id": "device-123", "ts": start_ts, "odometer_km": 100.0},
            {"device_id": "device-123", "ts": start_ts + timedelta(hours=1), "odometer_km": 120.0},
            {"device_id": "device-123", "ts": start_ts + timedelta(hours=2), "odometer_km": 150.0},
        ]
        service.csv_repository.vehicles_map = {"device-123": {"name": "Test Vehicle"}}
        service.pings_by_device = {"device-123": pings}

        response = service.compute_vehicle_usage("device-123")

        assert response is not None
        assert response.total_distance_km == pytest.approx(50.0)
        assert response.active_days == 1
        assert response.status == "active"

    def test_should_handle_unknown_vehicle(self, service):
        """
        Arrange:
            Unknown device_id.

        Assert:
            Verify your chosen behaviour
            (None, exception, or HTTP 404 handled elsewhere).
        """
        service.csv_repository.vehicles_map = {}
        service.pings_by_device = {}

        response = service.compute_vehicle_usage("unknown-device")

        assert response is None