from app.utils.csv_repository import CSVRepository


class Vehicles:

    def __init__(self):
        self.csv_repository = CSVRepository()
        self.pings_data = self.csv_repository.load_ping_data()
    



if __name__ == "__main__":
    Vehicles()