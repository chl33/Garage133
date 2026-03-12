import argparse
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml
from influxdb_client import InfluxDBClient

from download.config_utils import get_root_dir, save_config

# Connection Settings
URL = "https://influxdb.go-robo.net"
ORG = "Bailey Road"
# Remove hardcoded token; load from environment variable
TOKEN = os.getenv("INFLUX_TOKEN")
BUCKET = "garage"

VALID_STATES = ["open", "closed_car", "closed_empty"]


def parse_time(time_str, tz="America/New_York"):
    """Parses a time string and returns a UTC ISO-8601 string."""
    if not time_str:
        return None
    try:
        ts = pd.to_datetime(time_str)
        if ts.tzinfo is None:
            ts = ts.tz_localize(tz)
        return ts.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception as e:
        print(f"Warning: Could not parse time '{time_str}': {e}")
        return None


def update_manifest(manifest_path, entry):
    """Appends or creates a manifest.yaml file with the new data entry."""
    manifest_path = Path(manifest_path)
    manifest = {"episodes": []}

    if manifest_path.exists():
        try:
            with manifest_path.open("r") as f:
                content = yaml.safe_load(f)
                if content and isinstance(content, dict):
                    manifest = content
        except Exception as e:
            now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = manifest_path.with_suffix(f".yaml.bak.{now_str}")
            print(f"Error reading manifest {manifest_path}: {e}")
            print(f"Backing up corrupted manifest to {backup_path}")
            shutil.copy2(manifest_path, backup_path)

    if "episodes" not in manifest:
        manifest["episodes"] = []

    # Check for duplicates based on the filename
    manifest["episodes"] = [
        e for e in manifest["episodes"] if e.get("file") != entry.get("file")
    ]
    manifest["episodes"].append(entry)

    with manifest_path.open("w") as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=False)
    print(f"Updated manifest: {manifest_path}")


def download_data(
    start_time, end_time, output_file, manifest_path=None, labels=None, root_dir=None
):
    """Downloads data from InfluxDB v2 for a specific entity and time range."""
    if not TOKEN:
        print("Error: INFLUX_TOKEN environment variable is not set.")
        sys.exit(1)

    client = InfluxDBClient(url=URL, token=TOKEN, org=ORG)
    query_api = client.query_api()

    # Resolve root_dir and output paths
    root_path = Path(root_dir).resolve() if root_dir else Path.cwd()
    root_path.mkdir(parents=True, exist_ok=True)

    output_path = root_path / output_file
    if manifest_path:
        manifest_path = root_path / manifest_path

    # Flux query
    flux_query = f"""
    from(bucket: "{BUCKET}")
      |> range(start: {start_time}, stop: {end_time})
      |> filter(fn: (r) => r["_measurement"] == "garage")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
    """

    print("Querying InfluxDB (v2)...")
    print(f"Range (UTC): {start_time} to {end_time}")

    try:
        df = query_api.query_data_frame(org=ORG, query=flux_query)

        if isinstance(df, list):
            df = pd.concat(df)

        if df.empty:
            print("No data found for the specified criteria.")
            return

        # Clean up
        cols_to_keep = ["_time", "left", "right"]
        df = df[df.columns.intersection(cols_to_keep)]
        df.rename(columns={"_time": "time"}, inplace=True)
        df["time"] = pd.to_datetime(df["time"])
        df.sort_values("time", inplace=True)

        # Save to CSV
        df.to_csv(output_path, index=False)
        print(f"Successfully downloaded {len(df)} records to {output_path}")

        # Update manifest
        if manifest_path and labels:
            entry = {
                "file": output_path.name,
                "start": start_time,
                "end": end_time,
                "left": labels.get("left", {}),
                "right": labels.get("right", {})
            }
            update_manifest(manifest_path, entry)

    except Exception as e:
        print(f"Error querying InfluxDB: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    desc = "Download sonar data and label it for HMM training."
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument(
        "--start",
        type=str,
        required=True,
        help="Start time (e.g., '2026-02-27 10:00:00')",
    )
    parser.add_argument("--end", type=str, required=True, help="End time")
    parser.add_argument(
        "--timezone",
        type=str,
        default="America/New_York",
        help="Local timezone for inputs (default: America/New_York)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="sonar_data.csv",
        help="Output CSV file name (relative to root-dir)",
    )
    parser.add_argument(
        "--manifest",
        type=str,
        default="manifest.yaml",
        help="Path to manifest file (relative to root-dir)",
    )
    parser.add_argument("--root-dir", type=str, help="Output root directory")
    parser.add_argument(
        "--set-root-dir",
        type=str,
        help="Set the persistent default root directory and exit",
    )

    # Labels
    parser.add_argument(
        "--left-state", type=str, choices=VALID_STATES, help="Initial state for left"
    )
    parser.add_argument(
        "--right-state", type=str, choices=VALID_STATES, help="Initial state for right"
    )
    parser.add_argument("--left-trans-time", type=str, help="Transition time for left")
    parser.add_argument(
        "--left-trans-to",
        type=str,
        choices=VALID_STATES,
        help="State to transition to for left",
    )
    parser.add_argument(
        "--right-trans-time", type=str, help="Transition time for right"
    )
    parser.add_argument(
        "--right-trans-to",
        type=str,
        choices=VALID_STATES,
        help="State to transition to for right",
    )

    args = parser.parse_args()

    # Global Config
    if args.set_root_dir:
        save_config({"root_dir": str(Path(args.set_root_dir).resolve())})
        sys.exit(0)

    root_dir = get_root_dir(args.root_dir)
    print(f"Using root directory: {root_dir}")

    # 1. Overwrite Protection
    output_full_path = root_dir / args.output
    if output_full_path.exists():
        print(f"Error: Output file '{output_full_path}' already exists.")
        sys.exit(1)

    # 2. Parse times
    start_utc = parse_time(args.start, args.timezone)
    end_utc = parse_time(args.end, args.timezone)
    left_trans_utc = parse_time(args.left_trans_time, args.timezone)
    right_trans_utc = parse_time(args.right_trans_time, args.timezone)

    # 3. Validation
    if start_utc >= end_utc:
        print(f"Error: Start time ({start_utc}) must be before end time ({end_utc}).")
        sys.exit(1)

    if left_trans_utc and not (start_utc <= left_trans_utc <= end_utc):
        print(f"Error: Left transition time ({left_trans_utc}) is outside range.")
        sys.exit(1)

    if right_trans_utc and not (start_utc <= right_trans_utc <= end_utc):
        print(f"Error: Right transition time ({right_trans_utc}) is outside range.")
        sys.exit(1)

    # Build labels
    labels = {
        "left": {"initial_state": args.left_state, "transitions": []},
        "right": {"initial_state": args.right_state, "transitions": []},
    }

    if left_trans_utc and args.left_trans_to:
        labels["left"]["transitions"].append(
            {"time": left_trans_utc, "to": args.left_trans_to}
        )

    if right_trans_utc and args.right_trans_to:
        labels["right"]["transitions"].append(
            {"time": right_trans_utc, "to": args.right_trans_to}
        )

    download_data(
        start_utc, end_utc, args.output, args.manifest, labels, root_dir=root_dir
    )
