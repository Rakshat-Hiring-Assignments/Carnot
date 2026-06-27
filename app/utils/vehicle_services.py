from typing import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta

from pydantic import BaseModel  

from app.utils.csv_repository import CSVRepository
from app.config import MAX_REASONABLE_SPEED_KMPH, MIN_ACTIVE_DAYS
from app.utils.logging_config import configure_logging
 

logger = configure_logging()


@dataclass(frozen=True)
class Movement:
    timestamp: datetime
    distance_km: float
    speed_kmph: float

class VehicleUsageResponse(BaseModel):
    total_distance_km: float
    active_days: int
    status: str


class VehicleUsageService:

    def __init__(self):
        self.csv_repository = CSVRepository()
        self.pings_data = self.csv_repository.load_ping_data()
        self.pings_by_device = self._group_pings_by_device()


    def compute_vehicle_usage(self, device_id:str) -> VehicleUsageResponse | None:
        """
        Computes the vehicle usage for a given device_id.
        
        Args:
            device_id (str): The device ID of the vehicle
        """
        if not self.csv_repository.vehicles_map.get(device_id):
            return None  # Return None if vehicle not found

        vehicles_pings = self.pings_by_device.get(device_id, [])
        if vehicles_pings:
            return VehicleUsageResponse(
                total_distance_km=self._compute_total_distance(vehicles_pings),
                active_days=self._compute_active_days(vehicles_pings)[0],
                status=self._compute_active_days(vehicles_pings)[1]
            )
        else:
            return VehicleUsageResponse(total_distance_km=0.0, 
                                        active_days=0, 
                                        status='no_data')

    def _compute_total_distance(self, pings) -> float:
        """
        Computes the total distance traveled based on ping data.
        
        Args:
            pings (list): List of ping records for a vehicle
            
        Returns:
            float: Total distance traveled in kilometers
        """       
        total_distance = sum(movement.distance_km for movement in self._iter_valid_movements(pings))
        return total_distance

    def _compute_active_days(self, pings) -> tuple[int, str]:
        """
        Computes the number of active days based on ping data.
        active_days : days it actually moved
        Status active = moved in the last 7 days of the period.
        
        Args:
            pings (list): List of ping records for a vehicle
            
        Returns:
            int: Number of unique active days
            str: Status of active or inactive
        """
        active_days = {movement.timestamp.date() for movement in self._iter_valid_movements(pings)}
        last_ping_date = max(ping['ts'] for ping in pings).date()
        cutoff = last_ping_date - timedelta(days=MIN_ACTIVE_DAYS - 1)
        if any(day >= cutoff for day in active_days):
            return len(active_days), 'active'
        else:
            return len(active_days), 'inactive'

    def _iter_valid_movements(self, pings) -> Iterator[Movement]:
        """
        Iterates over valid movements based on ping data.
        
        Args:
            pings (list): List of ping records for a vehicle
            
        Yields:
            Movement: Valid movement data
        """
        last_odometer = None
        last_ping_ts = None
        for ping in sorted(pings, key=lambda p: p["ts"]):
            odometer = ping.get('odometer_km')
            if odometer is None or odometer < 0:
                continue
            if last_odometer is None  and last_ping_ts is None:
                last_odometer = odometer
                last_ping_ts = ping['ts']
                continue

            time_diff_hours = (ping['ts'] - last_ping_ts).total_seconds() / 3600
            if time_diff_hours <= 0:
                logger.warning(
                    "Non-positive time difference for device %s at %s. Time difference: %.2f hours. Ignoring this reading.",
                    ping["device_id"],
                    ping["ts"],
                    time_diff_hours,
                )
                continue

            distance = odometer - last_odometer
            if distance < 0:
                logger.warning(
                    "Odometer reading decreased for device %s at %s, indicating device reset/replaced. Ignoring this reading.",
                    ping["device_id"],
                    ping["ts"],
                )
                last_odometer = odometer
                last_ping_ts = ping['ts']
                continue

            speed = distance / time_diff_hours
            if speed > MAX_REASONABLE_SPEED_KMPH:
                logger.warning(
                    "Unreasonable speed detected for device %s at %s. Speed: %.2f km/h. Ignoring this reading.",
                    ping["device_id"],
                    ping["ts"],
                    speed,
                )
                continue

            yield Movement(timestamp=ping['ts'], distance_km=distance, speed_kmph=speed)
            last_odometer = odometer
            last_ping_ts = ping['ts']

    def _group_pings_by_device(self) -> dict[str, list[dict]]:
        """
        Groups pings by device_id for efficient access.
        
        Returns:
            dict: Dictionary with device_id as keys and list of pings as values
        """
        pings_by_device = {}
        for ping in self.pings_data:
            device_id = ping['device_id']
            if device_id not in pings_by_device:
                pings_by_device[device_id] = []
            pings_by_device[device_id].append(ping)
        return pings_by_device