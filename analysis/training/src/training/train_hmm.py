import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

# States: Door is open, closed with a car, or closed without a car.
STATES = ["open", "closed_car", "closed_empty"]
STATE_TO_IDX = {s: i for i, s in enumerate(STATES)}

# Default distance boundaries in cm for discrete buckets:
DEFAULT_BOUNDARIES = [70, 190, 350]


def get_bucket(val, boundaries):
    """Maps a raw distance value into a discrete bucket index."""
    if pd.isna(val) or val < 0:
        return len(boundaries)  # Last bucket for error
    for i, b in enumerate(boundaries):
        if val < b:
            return i
    return len(boundaries)  # Last bucket for long distances/errors


def build_transition_matrix():
    """
    Constructs a transition matrix based on physical priors:
    - Updates every 2 seconds.
    - 'Open' for ~5 mins (150 steps) -> P(stay) = 1 - (1/150) = 0.9933
    - 'Closed' for ~8 hours (14,400 steps) -> P(stay) = 1 - (1/14400) = 0.99993
    """
    A = np.zeros((len(STATES), len(STATES)))

    # From 'open' (index 0)
    A[0, 0] = 0.9934  # Stay open
    A[0, 1] = 0.0033  # Close with car
    A[0, 2] = 0.0033  # Close empty

    # From 'closed_car' (index 1)
    A[1, 1] = 0.9999  # Stay closed
    A[1, 0] = 0.0001  # Open door
    A[1, 2] = 0.0000  # Impossible without passing through 'open'

    # From 'closed_empty' (index 2)
    A[2, 2] = 0.9999  # Stay closed
    A[2, 0] = 0.0001  # Open door
    A[2, 1] = 0.0000  # Impossible without passing through 'open'

    return A


def train_side_emissions(side, manifest, manifest_path, boundaries):
    """Calculates emission probabilities for a side from labeled CSVs."""
    num_states = len(STATES)
    num_buckets = len(boundaries) + 1
    counts = np.zeros((num_states, num_buckets))

    manifest_dir = Path(manifest_path).parent

    for episode in manifest.get("episodes", []):
        file_name = episode.get("file")
        file_path = manifest_dir / file_name

        if not file_path.exists():
            continue

        # Load CSV
        df = pd.read_csv(file_path)
        df["time"] = pd.to_datetime(df["time"], format="ISO8601")
        df.sort_values("time", inplace=True)

        side_info = episode.get(side)
        if not side_info or not side_info.get("initial_state"):
            continue

        current_state = side_info["initial_state"]
        trans_list = side_info.get("transitions", [])
        transitions = sorted(trans_list, key=lambda x: x["time"])
        trans_idx = 0

        for _, row in df.iterrows():
            if trans_idx < len(transitions):
                t_str = transitions[trans_idx]["time"]
                trans_time = pd.to_datetime(t_str, format="ISO8601")
                if row["time"] >= trans_time:
                    current_state = transitions[trans_idx]["to"]
                    trans_idx += 1

            dist = row.get(side)
            if dist is not None:
                # Input is meters, bucket logic expects cm
                bucket = get_bucket(dist * 100.0, boundaries)
                counts[STATE_TO_IDX[current_state]][bucket] += 1

    # Normalize to probabilities (with Laplace smoothing)
    denom = counts.sum(axis=1, keepdims=True) + 0.1 * num_buckets
    emissions = (counts + 0.1) / denom
    return emissions


def save_model(side, A, B, pi, boundaries, output_dir):
    model = {
        "side": side,
        "states": STATES,
        "boundaries": boundaries,
        "pi": pi.tolist(),
        "A": A.tolist(),
        "B": B.tolist(),
    }
    output_path = Path(output_dir) / f"hmm_{side}.json"
    with output_path.open("w") as f:
        json.dump(model, f, indent=2)
    print(f"Saved {side} model to {output_path}")


def export_to_cpp(A, B, pi, boundaries, output_path):
    """Exports the HMM parameters to a C++ header file for ESP32."""
    output_path = Path(output_path)
    with output_path.open("w") as f:
        f.write("#ifndef HMM_CONFIG_H\n#define HMM_CONFIG_H\n\n")
        f.write(f"// Generated on {datetime.now().isoformat()}\n\n")
        f.write(f"const int HMM_NUM_STATES = {len(STATES)};\n")
        f.write(f"const int HMM_NUM_BUCKETS = {len(boundaries) + 1};\n\n")
        b_str = ", ".join(map(str, boundaries))
        f.write(f"const float HMM_BOUNDARIES[] = {{{b_str}}};\n\n")
        pi_str = ", ".join(map(str, pi))
        f.write(f"const float HMM_PI[] = {{{pi_str}}};\n\n")
        f.write("const float HMM_A[HMM_NUM_STATES][HMM_NUM_STATES] = {\n")
        for row in A:
            r_str = ", ".join(f"{x:.6f}f" for x in row)
            f.write(f"    {{{r_str}}},\n")
        f.write("};\n\n")
        f.write("const float HMM_B[HMM_NUM_STATES][HMM_NUM_BUCKETS] = {\n")
        for row in B:
            r_str = ", ".join(f"{x:.6f}f" for x in row)
            f.write(f"    {{{r_str}}},\n")
        f.write("};\n\n")
        f.write("#endif // HMM_CONFIG_H\n")
    print(f"Exported C++ header: {output_path}")


if __name__ == "__main__":
    desc = "Train separate HMMs for Garage133 sides."
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument(
        "--manifest", type=str, default="manifest.yaml", help="Path to manifest.yaml"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=".",
        help="Directory to save hmm_left.json and hmm_right.json",
    )
    parser.add_argument(
        "--cpp-header", type=str, help="Optional path to export C++ header"
    )
    parser.add_argument(
        "--boundaries", type=int, nargs="+", help="Manual distance boundaries (cm)"
    )
    parser.add_argument(
        "--num-buckets",
        type=int,
        help="Number of even buckets to create (replaces --boundaries)",
    )
    parser.add_argument(
        "--max-dist",
        type=int,
        default=400,
        help="Max distance for even bucketing (cm)",
    )

    args = parser.parse_args()

    # Determine boundaries
    if args.num_buckets:
        # Generate N-1 boundaries for N buckets
        linspace = np.linspace(0, args.max_dist, args.num_buckets, endpoint=False)
        boundaries = linspace.tolist()[1:]
        boundaries = [int(b) for b in boundaries]
        print(f"Generated {args.num_buckets} buckets with boundaries: {boundaries}")
    elif args.boundaries:
        boundaries = args.boundaries
    else:
        boundaries = DEFAULT_BOUNDARIES

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"Error: Manifest {manifest_path} not found.")
        exit(1)

    with manifest_path.open("r") as f:
        manifest = yaml.safe_load(f)

    # Common parameters
    A = build_transition_matrix()
    # Initial Probabilities: [open, closed_car, closed_empty]
    pi = np.array([0.1, 0.5, 0.4])

    # Ensure output directory exists
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Train and save Left
    print("Training left side...")
    B_left = train_side_emissions("left", manifest, manifest_path, boundaries)
    save_model("left", A, B_left, pi, boundaries, output_dir)

    # Train and save Right
    print("Training right side...")
    B_right = train_side_emissions("right", manifest, manifest_path, boundaries)
    save_model("right", A, B_right, pi, boundaries, output_dir)

    # Optional C++ header
    if args.cpp_header:
        export_to_cpp(A, B_left, pi, boundaries, args.cpp_header)
