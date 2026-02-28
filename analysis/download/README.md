# InfluxDB Data Downloader

This tool downloads sonar sensor data (or any other entity) from InfluxDB for a specified time range and saves it to a CSV file, suitable for analysis and model training (e.g., HMMs).

## Setup

1.  Navigate to this directory:
    ```bash
    cd analysis/download
    ```
2.  Install dependencies using Poetry:
    ```bash
    poetry install
    ```

## Usage

Run the script via `poetry run`:

```bash
poetry run python src/download/download.py \
    --start "2026-02-01T00:00:00Z" \
    --end "2026-02-25T23:59:59Z" \
    --entity "garage_measured_distance" \
    --output "sonar_training_data.csv"
```

### Parameters:
*   `--start`: ISO8601 start timestamp (UTC).
*   `--end`: ISO8601 end timestamp (UTC).
*   `--entity`: The `entity_id` tag in InfluxDB (default: `garage_measured_distance`).
*   `--output`: Filename for the resulting CSV (default: `sonar_data.csv`).

## Configuration
The script uses the following defaults (found in `download.py`):
*   **Host:** `influxdb.go-robo.net`
*   **Database:** `Home Assistant`
*   **Token:** Can be set via the `INFLUX_TOKEN` environment variable.
