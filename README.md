# Carnot Technologies Backend Assignment

## Overview

This project computes vehicle usage statistics from raw telemetry data and exposes them through a REST API built with FastAPI.

For each vehicle, the application computes:

* **Total Distance Travelled (km)**
* **Number of Active Days**
* **Vehicle Status**

  * `active`
  * `inactive`
  * `no_data`

The application loads the CSV files during startup, performs the required processing in memory, and serves usage information through a single endpoint.

---

# Project Structure

```text
app/
├── api_routes/
│   └── vehicles.py
├── services/
│   └── vehicle_usage_service.py
├── utils/
│   ├── csv_repository.py
│   └── logging_config.py
|   └── vehicle_services.py
├── config.py
├── config.toml
└── main.py
LOGS/
tests/
outputs/
README.md
requirements.txt
```

---

# API

## Get Vehicle Usage

```
GET /vehicles/{device_id}/usage
```

Example response:

```json
{
    "total_distance_km": 152.4,
    "active_days": 5,
    "status": "active"
}
```

---

# How to Run

## Prerequisites

- `Python 3.12+`
- `uv`

## Clone the repository

```bash
git clone https://github.com/Rakshat-Hiring-Assignments/Carnot.git
cd Carnot
```

## Using `uv` (Recommended)

### Install dependencies

```bash
uv sync
```

### Start the server

```bash
uv run uvicorn app.main:app
```

---

# Running Without `uv`

## Install dependencies

```bash
pip install -r requirements.txt
```

## Start the server

```bash
python -m app.main
```
API documentation:

```
http://localhost:8000/docs
```

---

# Running Tests

```bash
pytest
```

---

# Design Decisions

## Separation of Concerns

The project separates responsibilities into three layers:

* **CSVRepository** – Loads and parses input CSV files.
* **VehicleUsageService** – Contains the business logic for computing vehicle usage.
* **API Layer** – Responsible only for HTTP request/response handling.

---

## Shared Movement Iterator

Distance, active days, and vehicle status all depend on determining whether two consecutive telemetry records represent valid movement.

Instead of duplicating validation logic in multiple methods, the application uses a single movement iterator that:

* sorts telemetry chronologically
* ignores missing odometer readings
* ignores invalid/repeated timestamps
* handles odometer resets
* filters implausible movements based on maximum reasonable speed, based on max speed of Mahindra 575 at 31 KMPH, with some buffer included

Each metric is then computed by aggregating over these validated movement events.

This keeps business rules centralized and avoids inconsistencies between different calculations.

---

# Data Quality Assumptions

The supplied dataset contains several real-world data quality issues.

The following assumptions were made while processing telemetry:

### Missing odometer values

Missing odometer readings are treated as unavailable data.

Intervals containing missing values are skipped instead of assuming a value of zero.

---

### Odometer resets

If the odometer decreases between consecutive readings, the interval is treated as a device reset or replacement as specified in the assignment.

The negative interval is ignored and processing continues from the new baseline.

---

### Implausible telemetry

Some records contain unrealistic odometer jumps resulting in impossible vehicle speeds.

These intervals are ignored to prevent corrupting total distance calculations.

---

### Unknown devices

Some telemetry records reference device IDs that are not present in the vehicle master.

The vehicle master (`vehicles.csv`) is treated as the source of truth.

Telemetry belonging to unknown devices is ignored.

---

### Vehicles without telemetry

Vehicles present in the vehicle master but without any telemetry are returned with:

* status: `no_data`
* total distance: `0 km`
* active days: `0`

---

# AI Usage

AI tools (ChatGPT and Cursor) were used to:

* review code structure
* discuss edge cases and data quality assumptions
* review implementation decisions
* improve documentation
* Autocomplete and intial project setup

All implementation decisions, debugging, and final validation were performed manually.

---

# Production Considerations

If this application were processing production telemetry:

* vehicle metrics would be precomputed rather than calculated on request
* telemetry ingestion would be separated from the API
* metrics would be stored in a database for efficient querying
* invalid telemetry would be logged and monitored for investigation
* processing would be parallelized for larger datasets
