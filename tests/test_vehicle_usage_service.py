import pytest
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.utils.vehicle_services import VehicleUsageResponse, VehicleUsageService


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


@pytest.fixture
def start_ts():
    return datetime(2026, 1, 1, 8, 0, 0)


@pytest.fixture
def last_ts():
    return datetime(2026, 1, 8, 12, 0, 0)


def make_ping(ts, odometer_km, device_id="device-123"):
    return {"device_id": device_id, "ts": ts, "odometer_km": odometer_km}


class TestIterValidMovements:

    def test_should_yield_valid_movement(self, service, start_ts):
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
        pings = [
            make_ping(start_ts, 100.0),
            make_ping(start_ts + timedelta(hours=2), 140.0),
        ]

        movements = list(service._iter_valid_movements(pings))

        assert len(movements) == 1
        movement = movements[0]
        assert movement.distance_km == pytest.approx(40.0)
        assert movement.speed_kmph == pytest.approx(20.0)
        assert movement.timestamp == start_ts + timedelta(hours=2)

    def test_should_ignore_odometer_reset(self, service, start_ts):
        """
        Arrange:
            100 -> 120 -> 10 -> 20

        Assert:
            - First movement counted.
            - Reset ignored.
            - Movement after reset counted.
        """
        pings = [
            make_ping(start_ts, 100.0),
            make_ping(start_ts + timedelta(hours=1), 120.0),
            make_ping(start_ts + timedelta(hours=2), 10.0),
            make_ping(start_ts + timedelta(hours=3), 20.0),
        ]

        movements = list(service._iter_valid_movements(pings))

        assert len(movements) == 2
        assert movements[0].distance_km == pytest.approx(20.0)
        assert movements[0].speed_kmph == pytest.approx(20.0)
        assert movements[1].distance_km == pytest.approx(10.0)
        assert movements[1].speed_kmph == pytest.approx(10.0)

    def test_should_ignore_missing_odometer(self, service, start_ts):
        """
        Arrange:
            100 -> None -> 105

        Assert:
            Missing odometer readings are skipped and valid subsequent movement is counted.
        """
        pings = [
            make_ping(start_ts, 100.0),
            make_ping(start_ts + timedelta(hours=1), None),
            make_ping(start_ts + timedelta(hours=2), 105.0),
        ]

        movements = list(service._iter_valid_movements(pings))

        assert len(movements) == 1
        assert movements[0].distance_km == pytest.approx(5.0)
        assert movements[0].speed_kmph == pytest.approx(2.5)

    def test_should_ignore_impossible_speed(self, service, start_ts):
        """
        Arrange:
            Create two pings that imply an impossible speed.

        Assert:
            No movement should be yielded.
        """
        pings = [
            make_ping(start_ts, 100.0),
            make_ping(start_ts + timedelta(minutes=1), 200.0),
        ]

        movements = list(service._iter_valid_movements(pings))

        assert movements == []

    def test_should_ignore_duplicate_timestamp(self, service, start_ts):
        """
        Arrange:
            Two pings with identical timestamps.

        Assert:
            Movement should be ignored.
        """
        pings = [
            make_ping(start_ts, 100.0),
            make_ping(start_ts, 120.0),
        ]

        movements = list(service._iter_valid_movements(pings))

        assert movements == []

    def test_should_sort_pings_before_processing(self, service, start_ts):
        """
        Arrange:
            Supply pings out of chronological order.

        Assert:
            Correct movement sequence is produced.
        """
        pings = [
            make_ping(start_ts + timedelta(hours=2), 150.0),
            make_ping(start_ts, 100.0),
            make_ping(start_ts + timedelta(hours=1), 120.0),
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

    def test_should_compute_total_distance(self, service, start_ts):
        """
        Arrange:
            Several valid movements.

        Assert:
            Total equals sum of all yielded movements.
        """
        pings = [
            make_ping(start_ts, 100.0),
            make_ping(start_ts + timedelta(hours=1), 120.0),
            make_ping(start_ts + timedelta(hours=2), 150.0),
        ]

        total_distance = service._compute_total_distance(pings)

        assert total_distance == pytest.approx(50.0)


class TestComputeActiveDays:

    def test_should_count_unique_active_days(self, service, start_ts):
        """
        Arrange:
            Multiple movements on the same day.

        Assert:
            Day counted only once.
        """
        pings = [
            make_ping(start_ts, 100.0),
            make_ping(start_ts + timedelta(hours=1), 120.0),
            make_ping(start_ts + timedelta(hours=2), 140.0),
        ]

        active_days, status = service._compute_active_days(pings)

        assert active_days == 1
        assert status == "active"

    def test_should_mark_vehicle_active(self, service, last_ts):
        """
        Arrange:
            Movement occurs within the last 7 days.

        Assert:
            Status == active.
        """
        pings = [
            make_ping(last_ts - timedelta(days=1), 100.0),
            make_ping(last_ts, 120.0),
        ]

        active_days, status = service._compute_active_days(pings)

        assert active_days == 1
        assert status == "active"

    def test_should_mark_vehicle_inactive(self, service, last_ts):
        """
        Arrange:
            No movement in the last 7 days.

        Assert:
            Status == inactive.
        """
        pings = [
            make_ping(last_ts - timedelta(days=9, hours=2), 100.0),
            make_ping(last_ts - timedelta(days=9), 120.0),  # last movement
            make_ping(last_ts, 120.0),                       # unchanged for 8 days
            make_ping(last_ts + timedelta(minutes=10), 120.0),                       # unchanged for 8 days
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

    def test_should_return_usage_for_valid_vehicle(self, service, start_ts):
        """
        Arrange:
            Vehicle exists with valid pings.

        Assert:
            Response model contains expected values.
        """
        pings = [
            make_ping(start_ts, 100.0),
            make_ping(start_ts + timedelta(hours=1), 120.0),
            make_ping(start_ts + timedelta(hours=2), 150.0),
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


class TestVehicleUsageAPI:

    def test_should_return_200_and_vehicle_usage_for_valid_vehicle(self, monkeypatch):
        """
        Arrange:
            - Mock the VehicleUsageService.
            - Configure it to return a valid VehicleUsageResponse
              for a known device_id.

        Act:
            - Send a GET request to:
              /vehicles/{device_id}/usage

        Assert:
            - Response status code is 200.
            - Response body contains:
                - total_distance_km
                - active_days
                - status
            - Response values match the mocked service output.
            - VehicleUsageService.compute_vehicle_usage()
              is called exactly once with the requested device_id.
        """
        expected_response = VehicleUsageResponse(
            total_distance_km=42.5,
            active_days=3,
            status="active",
        )
        calls = []

        def fake_compute_vehicle_usage(device_id: str):
            calls.append(device_id)
            return expected_response

        monkeypatch.setattr("app.api_routes.vehicles.vehicles.compute_vehicle_usage", fake_compute_vehicle_usage)

        with TestClient(app) as client:
            response = client.get("/vehicles/device-123/usage")

        assert response.status_code == 200
        assert response.json() == {
            "total_distance_km": 42.5,
            "active_days": 3,
            "status": "active",
        }
        assert calls == ["device-123"]