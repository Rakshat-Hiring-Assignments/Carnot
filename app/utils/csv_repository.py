import csv
import sys
from datetime import datetime
from app.config import PINGS_CSV_PATH, VEHICLES_CSV_PATH, TS_FORMATS, PROJECT_PATH


class CSVRepository:

    def __init__(self):
        """Initialize CSVRepository and load vehicle data into a map."""
        self.vehicles_map = self._load_vehicle_map()

    def _load_vehicle_map(self):
        """
        Loads vehicle data and returns a map with device_id as key.
        
        Returns:
            dict: Dictionary where key is device_id and value is vehicle metadata
        """
        vehicle_data = self.read_csv(str(VEHICLES_CSV_PATH))
        vehicles_map = {}
        for vehicle in vehicle_data:
            device_id = vehicle.get('device_id', '').strip()
            if device_id:
                vehicles_map[device_id] = vehicle
        return vehicles_map

    def read_csv(self, file_path):
        """
        Reads a CSV file and returns the data as a list of dictionaries.
        
        Args:
            file_path (str): Path to the CSV file to read
            
        Returns:
            list: List of dictionaries where each dictionary represents a row
        """
        data = []
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)
                data = list(csv_reader)
        except FileNotFoundError:
            print(f"Error: File not found at {file_path}")
            sys.exit(1)
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            sys.exit(1)
        return data

    def load_ping_data(self):
        """
        Loads ping data from the CSV file defined in config.
        
        Returns:
            list: List of dictionaries representing ping records
        """
        data = self.read_csv(str(PINGS_CSV_PATH))
        unprocessable_pings = []
        processed_pings = []
        
        for ping in data:
            device_id = ping['device_id'].strip()
            
            # Check if device_id exists in vehicle map
            if device_id not in self.vehicles_map:
                ping['error'] = 'device_id'
                unprocessable_pings.append(ping)
                continue
            
            # Normalize odometer_km: empty values become 0.0
            odometer_value = ping.get('odometer_km', '')
            if isinstance(odometer_value, str) and odometer_value.strip() == '':
                ping['odometer_km'] = 0.0
            else:
                try:
                    ping['odometer_km'] = float(str(odometer_value).strip())
                except (ValueError, AttributeError):
                    ping['error'] = 'odometer_km'
                    unprocessable_pings.append(ping)
                    continue
            
            # Try to parse timestamp using available formats
            ts_str = ping['ts'].strip()
            for fmt in TS_FORMATS:
                try:
                    ping['ts'] = datetime.strptime(ts_str, fmt)
                    processed_pings.append(ping)
                    break
                except ValueError:
                    continue
            else:
                ping['error'] = 'ts'
                unprocessable_pings.append(ping)
        
        if len(processed_pings) == 0:
            print("ERROR: No pings were successfully processed!")
            sys.exit(1)
        
        if unprocessable_pings:
            # Write unprocessable pings to CSV
            output_path = PROJECT_PATH / "unprocessable_pings.csv"
            try:
                with open(output_path, 'w', newline='', encoding='utf-8') as f:
                    fieldnames = unprocessable_pings[0].keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(unprocessable_pings)
            except Exception as e:
                print(f"Error writing unprocessable pings to CSV: {e}")
            print(f"UNPROCESSABLE PING ENTRIES ({len(unprocessable_pings)})")
        
        return processed_pings
