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
TS_FORMATS = config["data"]["ts_formats"]
