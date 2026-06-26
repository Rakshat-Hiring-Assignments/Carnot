from app.utils.csv_repository import CSVRepository
from app.config import MAX_REASONABLE_SPEED_KMPH, MIN_ACTIVE_DAYS


class Vehicles:

    def __init__(self):
        self.csv_repository = CSVRepository()
        self.pings_data = self.csv_repository.load_ping_data()
    
    def compute_vehicle_usage(self, device_id:str):
        """
        Computes the vehicle usage for a given device_id.
        
        Args:
            device_id (str): The device ID of the vehicle
        """
        usage_data = {}
        if not self.csv_repository.vehicles_map.get(device_id):
            return usage_data  # Return empty if vehicle not found

        vehicles_pings = [ping for ping in self.pings_data if ping['device_id'] == device_id]
        vehicles_pings.sort(key=lambda ping: ping['ts'])
        if not vehicles_pings:
            usage_data['status'] = 'no_data'
            usage_data["total_distance_km"] = -1
            usage_data["active_days"] = -1
            return usage_data
        usage_data["total_distance_km"] =  self.compute_total_distance(vehicles_pings)
        usage_data["active_days"], usage_data['status'] = self.compute_active_days(vehicles_pings)
        return usage_data

    def compute_total_distance(self, pings):
        """
        Computes the total distance traveled based on ping data.
        
        Args:
            pings (list): List of ping records for a vehicle
            
        Returns:
            float: Total distance traveled in kilometers
        """
        total_distance = 0.0
        last_odometer = None
        last_ping_ts = None
        for ping in pings:
            odometer = ping.get('odometer_km', None)
            if not odometer or odometer < 0:
                continue
            if last_odometer is not None and last_ping_ts is not None:
                distance = odometer - last_odometer
                if distance < 0:
                    print(f"Warning: Odometer reading decreased for device {ping['device_id']} at {ping['ts']}," 
                          f"indicating device reset/replaced. Ignoring this reading.")
                    continue
                time_diff_hours = (ping['ts'] - last_ping_ts).total_seconds() / 3600
                if time_diff_hours <= 0:
                    print(f"Warning: Non-positive time difference for device {ping['device_id']} at {ping['ts']}. "
                          f"Time difference: {time_diff_hours:.2f} hours. Ignoring this reading.")
                    continue
                speed = distance / time_diff_hours
                if speed > MAX_REASONABLE_SPEED_KMPH:
                    print(f"Warning: Unreasonable speed detected for device {ping['device_id']} at {ping['ts']}. "
                          f"Speed: {speed:.2f} km/h. Ignoring this reading.")
                    continue
                total_distance += distance
            last_odometer = odometer
            last_ping_ts = ping['ts']
        return total_distance

    def compute_active_days(self, pings):
        """
        Computes the number of active days based on ping data.
        
        Args:
            pings (list): List of ping records for a vehicle
            
        Returns:
            int: Number of unique active days
            str: Status ('active' or 'inactive')
        """
        active_days = set()
        active_days_count = 0
        curr_date = None
        first_odometer = None
        last_odometer = None
        curr_date_movement = False
        day_movement_list = []

        for ping in pings:
            if not ping.get('odometer_km'):
                continue  # Skip if odometer_km is None or 0

            last_odometer = ping.get('odometer_km')
            if not first_odometer:
                first_odometer = ping.get('odometer_km')
            
            if curr_date:
                if ping['ts'].date() == curr_date:
                    curr_date_movement = True if last_odometer > first_odometer else curr_date_movement
                    continue  # Skip if the date is the same as the previous ping
                else:
                    day_movement_list.append(curr_date_movement)
                    if curr_date_movement:
                        active_days.add(curr_date)
                        active_days_count += 1
                    curr_date_movement = False
                    first_odometer = None  # Reset for the new date
            curr_date = ping['ts'].date()
        
        if (len(day_movement_list) < MIN_ACTIVE_DAYS or 
                False in day_movement_list[-MIN_ACTIVE_DAYS:]):
            status = 'inactive'
        else:
            status = 'active'
        return active_days_count, status
