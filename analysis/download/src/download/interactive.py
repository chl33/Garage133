import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from download.config_utils import get_root_dir, save_config
from download.download import VALID_STATES, download_data, parse_time

# Mapping for shortcut entry
STATE_MAP = {"o": "open", "c": "closed_car", "e": "closed_empty"}
SHORTCUT_HINT = "[o]pen, [c]ar, [e]mpty"


def get_state_input(prompt, default_key):
    """Helper to get state using shortcuts."""
    default_state = STATE_MAP[default_key]
    while True:
        prompt_full = f"{prompt} {SHORTCUT_HINT} [{default_state}] (or 'q' to abort): "
        res = input(prompt_full).strip().lower()
        if res == "q":
            return "q"
        if not res:
            return default_state
        if res in STATE_MAP:
            return STATE_MAP[res]
        if res in VALID_STATES:
            return res
        print(f"Invalid input. Please use {SHORTCUT_HINT} or full name.")


def get_input(prompt, default=None):
    """Helper for terminal inputs with defaults."""
    prompt_suffix = " (or 'q' to abort)"
    if default:
        res = input(f"{prompt} [{default}]{prompt_suffix}: ").strip()
        if res.lower() == "q":
            return "q"
        return res if res else default
    res = input(f"{prompt}{prompt_suffix}: ").strip()
    return res


def get_valid_start_time(date_str, timezone):
    """Prompts until a valid start time is provided."""
    while True:
        start_hour = get_input("Start Hour (HH:MM or HH:MM:SS)", "10:00")
        if start_hour == "q":
            return "q", "q"
        full_str = f"{date_str} {start_hour}"
        start_utc = parse_time(full_str, timezone)
        if start_utc:
            return start_hour, start_utc
        msg = f"Error: Could not parse time '{start_hour}'. Please use HH:MM format."
        print(msg)


def interactive_session(date_str, timezone, root_dir):
    """Downloads a buffer of data and allows interactive labeling/trimming."""
    # 1. Setup the time range with a validation loop
    start_hour, start_utc = get_valid_start_time(date_str, timezone)
    if start_hour == "q":
        print("Aborting session.")
        return

    duration_input = get_input("Approx duration in minutes", "15")
    if duration_input == "q":
        print("Aborting session.")
        return
    try:
        duration_min = int(duration_input)
    except ValueError:
        print("Invalid duration, using default 15 minutes.")
        duration_min = 15

    start_dt = pd.to_datetime(start_utc)
    end_dt = start_dt + timedelta(minutes=duration_min)
    end_utc = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # 2. Download the 'raw' buffer (don't save to manifest yet)
    temp_csv = Path("temp_buffer.csv")
    print(f"\nDownloading data from {start_utc} to {end_utc}...")
    # Buffer is temporary, root_dir=None to keep it in current working dir
    download_data(start_utc, end_utc, str(temp_csv), root_dir=None)

    if not temp_csv.exists():
        print("No data found for this range.")
        return

    # Use read_csv and ensure 'time' is parsed and localized to UTC
    df = pd.read_csv(temp_csv)
    if df.empty:
        print("No data records found in this range.")
        temp_csv.unlink(missing_ok=True)
        return

    df["time"] = pd.to_datetime(df["time"], format="ISO8601")
    df.sort_values("time", inplace=True)
    temp_csv.unlink(missing_ok=True)

    # Calculate numeric time bounds for click validation
    time_nums = mdates.date2num(df["time"].dt.to_pydatetime())
    t_min = time_nums.min()
    t_max = time_nums.max()

    # 3. Plot and let the user interact
    print("\n--- Visual Labeling Mode ---")
    print("Selection Flow:")
    print("1. Start Trim | 2. End Trim | 3. Left Transition | 4. Right Transition")
    print("\nControls:")
    print("- CLICK: Select point (ignored if Zoom/Pan tool is active)")
    print("- CLICK OUTSIDE DATA: Skip a transition point")
    msg = "- TOOLBAR: Use Zoom/Pan investigate, then toggle them OFF to select"
    print(msg)
    print("- CLOSE WINDOW: Finish early with selected points")

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(df["time"], df["left"], label="Left Sonar", marker=".", markersize=2)
    ax.plot(df["time"], df["right"], label="Right Sonar", marker=".", markersize=2)
    ax.set_title(f"Garage Sonar: {date_str} (approx {start_hour})")
    ax.set_ylabel("Distance (m)")
    ax.legend()
    plt.grid(True, alpha=0.3)

    # Selection state
    clicks = []
    labels = ["Start Trim", "End Trim", "Left Transition", "Right Transition"]

    def on_click(event):
        if len(clicks) >= 4:
            return

        # Check if click is on the plot area
        if event.inaxes != ax:
            # If we already have trim points, allow clicking outside to skip transitions
            if len(clicks) >= 2:
                print(f"Skipped {labels[len(clicks)]} (clicked outside axes)")
                clicks.append(None)
                if len(clicks) == 4:
                    plt.close()
            return

        # CRITICAL: Ignore clicks if the Zoom or Pan tools are active
        if fig.canvas.toolbar.mode != "":
            return

        # Check if click is within the data's time range
        if event.xdata < t_min or event.xdata > t_max:
            if len(clicks) >= 2:
                print(f"Skipped {labels[len(clicks)]} (clicked outside data range)")
                clicks.append(None)
            else:
                msg = f"Ignored click outside data range for {labels[len(clicks)]}"
                print(msg)
                return
        else:
            dt = mdates.num2date(event.xdata).replace(tzinfo=None)
            ts = pd.Timestamp(dt).tz_localize("UTC")
            print(f"Selected {labels[len(clicks)]}: {ts.strftime('%H:%M:%S')}")
            clicks.append(ts)
            # Draw vertical line for feedback
            ax.axvline(x=event.xdata, color="r", linestyle="--", alpha=0.5)
            plt.draw()

        if len(clicks) == 4:
            plt.close()

    fig.canvas.mpl_connect("button_press_event", on_click)
    plt.show()  # Blocking call

    if len(clicks) < 2 or clicks[0] is None or clicks[1] is None:
        print("Need at least start and end trim points. Aborting.")
        return

    trim_start = clicks[0]
    trim_end = clicks[1]
    left_trans = clicks[2] if len(clicks) >= 3 else None
    right_trans = clicks[3] if len(clicks) >= 4 else None

    # 4. Final Metadata Gathering in Terminal
    print("\n--- Episode Metadata ---")
    default_name = (
        f"garage_{date_str.replace(' ', '_')}_{start_hour.replace(':', '')}.csv"
    )
    output_name = get_input("CSV Filename (e.g., event_001.csv)", default_name)
    if output_name == "q":
        print("Aborting session. Data not saved.")
        return

    left_initial = get_state_input("Left Initial State", "e")
    if left_initial == "q":
        print("Aborting session. Data not saved.")
        return

    left_to = None
    if left_trans is not None:
        left_to = get_state_input("Left Transition To", "o")
        if left_to == "q":
            print("Aborting session. Data not saved.")
            return

    right_initial = get_state_input("Right Initial State", "e")
    if right_initial == "q":
        print("Aborting session. Data not saved.")
        return

    right_to = None
    if right_trans is not None:
        right_to = get_state_input("Right Transition To", "o")
        if right_to == "q":
            print("Aborting session. Data not saved.")
            return

    # 5. Save the final trimmed data and update manifest
    episode_labels = {
        "left": {"initial_state": left_initial, "transitions": []},
        "right": {"initial_state": right_initial, "transitions": []},
    }

    if left_trans is not None and left_to is not None and left_to != left_initial:
        episode_labels["left"]["transitions"].append(
            {"time": left_trans.strftime("%Y-%m-%dT%H:%M:%SZ"), "to": left_to}
        )

    if right_trans is not None and right_to is not None and right_to != right_initial:
        episode_labels["right"]["transitions"].append(
            {"time": right_trans.strftime("%Y-%m-%dT%H:%M:%SZ"), "to": right_to}
        )

    final_start = trim_start.strftime("%Y-%m-%dT%H:%M:%SZ")
    final_end = trim_end.strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"\nSaving final trimmed data: {output_name}")
    download_data(
        final_start,
        final_end,
        output_name,
        "manifest.yaml",
        episode_labels,
        root_dir=root_dir,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactive Garage Data Downloader")
    parser.add_argument(
        "--date",
        type=str,
        help="Date (YYYY-MM-DD), defaults to today",
        default=datetime.now().strftime("%Y-%m-%d"),
    )
    parser.add_argument(
        "--timezone", type=str, default="America/New_York", help="Local timezone"
    )
    parser.add_argument("--root-dir", type=str, help="Output root directory")
    parser.add_argument(
        "--set-root-dir",
        type=str,
        help="Set the persistent default root directory and exit",
    )

    args = parser.parse_args()

    if args.set_root_dir:
        save_config({"root_dir": str(Path(args.set_root_dir).resolve())})
        sys.exit(0)

    root_dir = get_root_dir(args.root_dir)
    print(f"Using root directory: {root_dir}")

    while True:
        print(f"\n--- New Interactive Session (Date: {args.date}) ---")
        interactive_session(args.date, args.timezone, root_dir)

        cont = (
            input("Download another episode for this date? (y/n) [y]: ")
            .strip()
            .lower()
        )
        if cont == "n" or cont == "q":
            break
