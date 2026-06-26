import tomllib
from pathlib import Path

PROJECT_PATH = Path(__file__).resolve().parent.parent
CONFIG_PATH = Path(__file__).resolve().parent / "config.toml"

with CONFIG_PATH.open("rb") as handle:
    config = tomllib.load(handle)

APP_HOST = config["app"]["host"]
APP_PORT = config["app"]["port"]

PINGS_CSV_PATH = PROJECT_PATH / config["data"]["pings_csv"]
VEHICLES_CSV_PATH = PROJECT_PATH / config["data"]["vehicles"]

TS_FORMATS = config["processing"]["ts_formats"]
MAX_REASONABLE_SPEED_KMPH = config["processing"]["max_reasonable_speed_kmph"]
MIN_ACTIVE_DAYS = config["processing"]["min_active_days"]
