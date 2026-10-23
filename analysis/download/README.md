# InfluxDB Data Downloader

This tool downloads sonar sensor data from InfluxDB for a specified time range and saves it to a CSV file, suitable for analysis and HMM model training.

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

### Interactive Visual Trimming (Recommended)

Run the interactive trimmer with GUI support:

```bash
poetry run python -m download.interactive --date "2026-10-10"
```
Or use the wrapper script from `analysis/`:
```bash
./interactive.sh
```

**Selection Flow:**
1. Click **Start Trim** point.
2. Click **End Trim** point.
3. The plot window closes automatically once both points are selected.
4. Enter the static state for the left and right doors (e.g. `c` for closed_car, `e` for closed_empty, `o` for open, `oc` for open_car, `oe` for open_empty).
5. The trimmed CSV is downloaded and the manifest entry is saved with the chosen states.

### Direct Download via CLI

Run the script via `poetry run`:

```bash
poetry run python src/download/download.py \
    --start "2026-10-10 10:00:00" \
    --end "2026-10-10 10:15:00" \
    --left-state "closed_car" \
    --right-state "closed_car" \
    --output "sonar_training_data.csv"
```
Or using relative time in minutes:
```bash
./download.sh -s 30 -d 15 --left-state closed_car --right-state closed_car
```

### Parameters:
*   `--start`: Start time (e.g., '2026-10-10 10:00:00').
*   `--end`: End time (e.g., '2026-10-10 10:15:00').
*   `-s`, `--start-min`: Start time in minutes before now.
*   `-d`, `--duration-min`: Log duration in minutes.
*   `--left-state`: Garage state for the left side (`open`, `closed_car`, `closed_empty`, `open_car`, `open_empty`).
*   `--right-state`: Garage state for the right side.
*   `--output`: Filename for resulting CSV (default: auto-generated from date/time).
*   `--manifest`: Manifest YAML file to update (default: `manifest.yaml`).

## Configuration
*   **Host:** `influxdb.go-robo.net`
*   **Token:** Set via the `INFLUX_TOKEN` environment variable (loaded from `secrets.sh` if using helper scripts).
