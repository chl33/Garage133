# Copyright (c) 2026 Chris Lee and contributors.
# Licensed under the MIT license. See LICENSE file in the project root for details.

import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

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


def build_transition_matrix(states):
    """
    Constructs a transition matrix based on physical priors:
    - Updates every 2 seconds.
    """
    num_states = len(states)
    A = np.zeros((num_states, num_states))
    if num_states == 3:
        # States: open, closed_car, closed_empty
        A[0, 0] = 0.9934  # Stay open
        A[0, 1] = 0.0033  # Close with car
        A[0, 2] = 0.0033  # Close empty

        A[1, 1] = 0.9999  # Stay closed (car)
        A[1, 0] = 0.0001  # Open door
        A[1, 2] = 0.0000

        A[2, 2] = 0.9999  # Stay closed (empty)
        A[2, 0] = 0.0001  # Open door
        A[2, 1] = 0.0000
    elif num_states == 4:
        # States: open_car, open_empty, closed_car, closed_empty
        # index mapping: 0: open_car, 1: open_empty, 2: closed_car, 3: closed_empty
        A[0, 0] = 0.9900  # Stay open_car
        A[0, 1] = 0.0050  # Car leaves (open_car -> open_empty)
        A[0, 2] = 0.0050  # Door closes (open_car -> closed_car)
        A[0, 3] = 0.0000  # Impossible transition

        A[1, 1] = 0.9900  # Stay open_empty
        A[1, 0] = 0.0050  # Car enters (open_empty -> open_car)
        A[1, 3] = 0.0050  # Door closes (open_empty -> closed_empty)
        A[1, 2] = 0.0000  # Impossible transition

        A[2, 2] = 0.9999  # Stay closed_car
        A[2, 0] = 0.0001  # Door opens (closed_car -> open_car)
        A[2, 1] = 0.0000
        A[2, 3] = 0.0000

        A[3, 3] = 0.9999  # Stay closed_empty
        A[3, 1] = 0.0001  # Door opens (closed_empty -> open_empty)
        A[3, 0] = 0.0000
        A[3, 2] = 0.0000
    return A


def train_side_emissions(side, manifest, manifest_path, boundaries, boundaries2=None, states=None):
    """Calculates emission probabilities for a side from labeled CSVs."""
    num_states = len(states)
    num_buckets = len(boundaries) + 1
    counts = np.zeros((num_states, num_buckets))

    num_buckets2 = len(boundaries2) + 1 if boundaries2 is not None else 0
    counts2 = np.zeros((num_states, num_buckets2)) if num_buckets2 > 0 else None

    state_to_idx = {s: i for i, s in enumerate(states)}
    manifest_dir = Path(manifest_path).parent

    has_sonar2 = False

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

        col_sonar2 = f"{side}_2"
        episode_has_sonar2 = col_sonar2 in df.columns and counts2 is not None

        for _, row in df.iterrows():
            if trans_idx < len(transitions):
                t_str = transitions[trans_idx]["time"]
                trans_time = pd.to_datetime(t_str, format="ISO8601")
                if row["time"] >= trans_time:
                    current_state = transitions[trans_idx]["to"]
                    trans_idx += 1

            if current_state not in state_to_idx:
                continue
            s_idx = state_to_idx[current_state]

            dist = row.get(side)
            if dist is not None and not pd.isna(dist):
                # Input is meters, bucket logic expects cm
                bucket = get_bucket(dist * 100.0, boundaries)
                counts[s_idx][bucket] += 1

            if episode_has_sonar2:
                dist2 = row.get(col_sonar2)
                if dist2 is not None and not pd.isna(dist2):
                    bucket2 = get_bucket(dist2 * 100.0, boundaries2)
                    counts2[s_idx][bucket2] += 1
                    has_sonar2 = True

    # Normalize to probabilities (with Laplace smoothing)
    denom = counts.sum(axis=1, keepdims=True) + 0.1 * num_buckets
    emissions = (counts + 0.1) / denom

    emissions2 = None
    if has_sonar2:
        denom2 = counts2.sum(axis=1, keepdims=True) + 0.1 * num_buckets2
        emissions2 = (counts2 + 0.1) / denom2

    return emissions, emissions2


def save_model(side, A, B, pi, boundaries, output_dir, B2=None, boundaries2=None, states=None):
    model = {
        "side": side,
        "states": states,
        "boundaries": boundaries,
        "pi": pi.tolist(),
        "A": A.tolist(),
        "B": B.tolist(),
    }
    if B2 is not None and boundaries2 is not None:
        model["boundaries2"] = boundaries2
        model["B2"] = B2.tolist()

    output_path = Path(output_dir) / f"hmm_{side}.json"
    with output_path.open("w") as f:
        json.dump(model, f, indent=2)
    print(f"Saved {side} model to {output_path}")


def export_to_cpp(A, B, pi, boundaries, output_path, B2=None, boundaries2=None, states=None):
    """Exports the HMM parameters to a C++ header file for ESP32."""
    output_path = Path(output_path)
    with output_path.open("w") as f:
        f.write("#ifndef HMM_CONFIG_H\n#define HMM_CONFIG_H\n\n")
        f.write(f"// Generated on {datetime.now().isoformat()}\n\n")
        f.write(f"const int HMM_NUM_STATES = {len(states)};\n")
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

        if B2 is not None and boundaries2 is not None:
            f.write(f"const int HMM_NUM_BUCKETS2 = {len(boundaries2) + 1};\n\n")
            b2_str = ", ".join(map(str, boundaries2))
            f.write(f"const float HMM_BOUNDARIES2[] = {{{b2_str}}};\n\n")
            f.write("const float HMM_B2[HMM_NUM_STATES][HMM_NUM_BUCKETS2] = {\n")
            for row in B2:
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
    parser.add_argument("--cpp-header", type=str, help="Optional path to export C++ header")
    parser.add_argument(
        "--boundaries",
        type=int,
        nargs="+",
        help="Manual distance boundaries for sonar 1 (cm)",
    )
    parser.add_argument(
        "--num-buckets",
        type=int,
        help="Number of even buckets to create for sonar 1 (replaces --boundaries)",
    )
    parser.add_argument(
        "--max-dist",
        type=int,
        default=400,
        help="Max distance for even bucketing for sonar 1 (cm)",
    )
    parser.add_argument(
        "--boundaries2",
        type=int,
        nargs="+",
        help="Manual distance boundaries for sonar 2 (cm)",
    )
    parser.add_argument(
        "--num-buckets2",
        type=int,
        help="Number of even buckets to create for sonar 2 (replaces --boundaries2)",
    )
    parser.add_argument(
        "--max-dist2",
        type=int,
        default=400,
        help="Max distance for even bucketing for sonar 2 (cm)",
    )

    args = parser.parse_args()

    # Determine boundaries
    if args.num_buckets:
        linspace = np.linspace(0, args.max_dist, args.num_buckets, endpoint=False)
        boundaries = linspace.tolist()[1:]
        boundaries = [int(b) for b in boundaries]
        print(f"Generated {args.num_buckets} buckets for sonar 1 with boundaries: {boundaries}")
    elif args.boundaries:
        boundaries = args.boundaries
    else:
        boundaries = DEFAULT_BOUNDARIES

    # Determine boundaries2
    if args.num_buckets2:
        linspace2 = np.linspace(0, args.max_dist2, args.num_buckets2, endpoint=False)
        boundaries2 = linspace2.tolist()[1:]
        boundaries2 = [int(b) for b in boundaries2]
        print(f"Generated {args.num_buckets2} buckets for sonar 2 with boundaries: {boundaries2}")
    elif args.boundaries2:
        boundaries2 = args.boundaries2
    else:
        boundaries2 = boundaries

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"Error: Manifest {manifest_path} not found.")
        exit(1)

    with manifest_path.open("r") as f:
        manifest = yaml.safe_load(f)

    # Determine the state space from manifest entries
    has_four_states = False
    for episode in manifest.get("episodes", []):
        for side in ["left", "right"]:
            side_info = episode.get(side)
            if not side_info:
                continue
            states_found = [side_info.get("initial_state")] + [
                t.get("to") for t in side_info.get("transitions", [])
            ]
            if any(s in ["open_car", "open_empty"] for s in states_found if s):
                has_four_states = True
                break
        if has_four_states:
            break

    if has_four_states:
        states = ["open_car", "open_empty", "closed_car", "closed_empty"]
    else:
        states = ["open", "closed_car", "closed_empty"]

    print(f"Using HMM states: {states}")

    # Common parameters
    A = build_transition_matrix(states)
    pi = np.array([0.05, 0.05, 0.5, 0.4]) if len(states) == 4 else np.array([0.1, 0.5, 0.4])

    # Ensure output directory exists
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Train and save Left
    print("Training left side...")
    B_left, B_left2 = train_side_emissions(
        "left", manifest, manifest_path, boundaries, boundaries2, states
    )
    save_model("left", A, B_left, pi, boundaries, output_dir, B_left2, boundaries2, states)

    # Train and save Right
    print("Training right side...")
    B_right, B_right2 = train_side_emissions(
        "right", manifest, manifest_path, boundaries, boundaries2, states
    )
    save_model("right", A, B_right, pi, boundaries, output_dir, B_right2, boundaries2, states)

    # Optional C++ header
    if args.cpp_header:
        export_to_cpp(A, B_left, pi, boundaries, args.cpp_header, B_left2, boundaries2, states)
