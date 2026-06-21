# Copyright (c) 2026 Chris Lee and contributors.
# Licensed under the MIT license. See LICENSE file in the project root for details.

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml


class HMMEngine:
    """Python implementation of the ESP32 HMM logic (Forward Algorithm)."""

    def __init__(self, model_path):
        with open(model_path) as f:
            self.model = json.load(f)
        self.boundaries = self.model["boundaries"]
        self.A = np.array(self.model["A"])
        self.B = np.array(self.model["B"])
        self.pi = np.array(self.model["pi"])
        self.num_states = len(self.pi)
        self.state_names = self.model.get("states", ["open", "closed_car", "closed_empty"])

        self.is_dual_sonar = "B2" in self.model
        if self.is_dual_sonar:
            self.boundaries2 = self.model.get("boundaries2", self.boundaries)
            self.B2 = np.array(self.model["B2"])

        self.reset()

    def reset(self):
        self.probs = self.pi.copy()

    def get_bucket(self, dist_m, boundaries):
        dist_cm = dist_m * 100.0
        for i, b in enumerate(boundaries):
            if dist_cm < b:
                return i
        return len(boundaries)  # Error/Long bucket

    def update(self, dist1_m, dist2_m=None):
        bucket1 = self.get_bucket(dist1_m, self.boundaries)

        next_probs = np.zeros(self.num_states)
        for j in range(self.num_states):
            transition_prob = np.sum(self.probs * self.A[:, j])
            emission = self.B[j, bucket1]
            if self.is_dual_sonar and dist2_m is not None and not pd.isna(dist2_m):
                bucket2 = self.get_bucket(dist2_m, self.boundaries2)
                emission *= self.B2[j, bucket2]
            next_probs[j] = transition_prob * emission

        s = np.sum(next_probs)
        if s > 0:
            self.probs = next_probs / s
        return np.argmax(self.probs), self.probs.copy()


def get_ground_truth(df, side_info, state_names):
    states = []
    current_state = side_info["initial_state"]
    state_to_idx = {s: i for i, s in enumerate(state_names)}
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
        states.append(state_to_idx[current_state])
    return np.array(states)


def get_metrics(truth, preds, num_states):
    correct = np.sum(truth == preds)
    total = len(truth)
    cm = np.zeros((num_states, num_states), dtype=int)
    for t, p in zip(truth, preds, strict=False):
        cm[t, p] += 1
    return correct, total, cm


def print_cm(side_name, correct, total, cm, state_names):
    accuracy = (correct / total) * 100 if total > 0 else 0
    print(f"\n--- {side_name.upper()} GLOBAL METRICS ---")
    print(f"Accuracy: {accuracy:.2f}% ({correct}/{total} samples)")
    print("\nConfusion Matrix (Rows=Truth, Cols=Pred):")
    header = " " * 14 + " ".join([f"{s:>14}" for s in state_names])
    print(header)
    for i, row in enumerate(cm):
        row_str = f"{state_names[i]:>12} | " + " ".join([f"{count:>14}" for count in row])
        print(row_str)


def run_test(model_dir, manifest_path, episode_idx=None, show_probs=False, test_all=False):
    manifest_path = Path(manifest_path)
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)

    episodes = manifest.get("episodes", [])

    # Dynamic shapes based on loaded models
    left_model_path = Path(model_dir) / "hmm_left.json"
    right_model_path = Path(model_dir) / "hmm_right.json"

    left_num_states = 3
    left_state_names = ["open", "closed_car", "closed_empty"]
    if left_model_path.exists():
        with open(left_model_path) as f:
            left_m = json.load(f)
            left_state_names = left_m.get("states", left_state_names)
            left_num_states = len(left_state_names)

    right_num_states = 3
    right_state_names = ["open", "closed_car", "closed_empty"]
    if right_model_path.exists():
        with open(right_model_path) as f:
            right_m = json.load(f)
            right_state_names = right_m.get("states", right_state_names)
            right_num_states = len(right_state_names)

    results = {
        "left": {
            "correct": 0,
            "total": 0,
            "cm": np.zeros((left_num_states, left_num_states), dtype=int),
            "states": left_state_names,
        },
        "right": {
            "correct": 0,
            "total": 0,
            "cm": np.zeros((right_num_states, right_num_states), dtype=int),
            "states": right_state_names,
        },
    }

    test_indices = range(len(episodes)) if test_all else [episode_idx]

    for idx in test_indices:
        episode = episodes[idx]
        file_path = manifest_path.parent / episode["file"]
        if not test_all:
            print(f"Testing Episode: {episode['file']}")

        df = pd.read_csv(file_path)
        df["time"] = pd.to_datetime(df["time"], format="ISO8601")
        df.sort_values("time", inplace=True)

        for side in ["left", "right"]:
            if side not in episode:
                continue
            model_path = Path(model_dir) / f"hmm_{side}.json"
            if not model_path.exists():
                continue

            engine = HMMEngine(model_path)
            truth = get_ground_truth(df, episode[side], engine.state_names)

            engine.reset()
            preds = []
            confidences = []
            col_sonar2 = f"{side}_2"
            has_sonar2 = col_sonar2 in df.columns
            for idx_row, dist in enumerate(df[side]):
                dist2 = df[col_sonar2].iloc[idx_row] if has_sonar2 else None
                p, probs = engine.update(dist, dist2)
                preds.append(p)
                confidences.append(probs)

            preds = np.array(preds)
            c, t, cm = get_metrics(truth, preds, engine.num_states)
            results[side]["correct"] += c
            results[side]["total"] += t
            results[side]["cm"] += cm

    # Print Global Results
    for side in ["left", "right"]:
        if results[side]["total"] > 0:
            print_cm(
                side,
                results[side]["correct"],
                results[side]["total"],
                results[side]["cm"],
                results[side]["states"],
            )

    if not test_all:
        # Re-run single episode with full plotting
        test_single_with_plot(model_dir, manifest_path, episode_idx, show_probs)


def test_single_with_plot(model_dir, manifest_path, episode_idx, show_probs):
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)
    episode = manifest["episodes"][episode_idx]
    file_path = manifest_path.parent / episode["file"]
    df = pd.read_csv(file_path)
    df["time"] = pd.to_datetime(df["time"], format="ISO8601")
    df.sort_values("time", inplace=True)

    num_plots = 2 + (2 if show_probs else 0)
    _fig, axes = plt.subplots(num_plots, 1, figsize=(12, 4 * num_plots), sharex=True)

    for i, side in enumerate(["left", "right"]):
        if side not in episode:
            continue
        model_path = Path(model_dir) / f"hmm_{side}.json"
        engine = HMMEngine(model_path)
        truth = get_ground_truth(df, episode[side], engine.state_names)
        engine.reset()
        preds, confs = [], []
        col_sonar2 = f"{side}_2"
        has_sonar2 = col_sonar2 in df.columns
        for idx_row, dist in enumerate(df[side]):
            dist2 = df[col_sonar2].iloc[idx_row] if has_sonar2 else None
            p, pr = engine.update(dist, dist2)
            preds.append(p)
            confs.append(pr)
        preds, confs = np.array(preds), np.array(confs)

        ax_sonar = axes[i]
        ax_state = ax_sonar.twinx()
        ax_sonar.plot(df["time"], df[side], color="gray", alpha=0.4, label="Sonar 1")
        if has_sonar2:
            ax_sonar.plot(
                df["time"],
                df[col_sonar2],
                color="blue",
                alpha=0.3,
                label="Sonar 2",
            )
        ax_sonar.legend(loc="upper left")
        ax_state.step(df["time"], truth, color="blue", where="post", linewidth=2)
        ax_state.step(df["time"], preds, color="red", linestyle="--", where="post")
        ax_state.set_yticks(range(engine.num_states))
        ax_state.set_yticklabels(engine.state_names)
        ax_sonar.set_title(f"{side.capitalize()} Episode {episode_idx}")
        if show_probs:
            ax_prob = axes[i + 2]
            for s_idx, s_name in enumerate(engine.state_names):
                ax_prob.plot(df["time"], confs[:, s_idx], label=s_name)
            ax_prob.legend()

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test HMM performance.")
    parser.add_argument("--model-dir", type=str, default=".", help="Model dir")
    parser.add_argument("--manifest", type=str, default="manifest.yaml", help="Path")
    parser.add_argument("--episode", type=int, default=0, help="Episode index")
    parser.add_argument("--probs", action="store_true", help="Show probabilities")
    parser.add_argument("--all", action="store_true", help="Test all episodes")

    args = parser.parse_args()
    run_test(
        args.model_dir,
        args.manifest,
        args.episode,
        show_probs=args.probs,
        test_all=args.all,
    )
