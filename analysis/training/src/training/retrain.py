# Copyright (c) 2026 Chris Lee and contributors.
# Licensed under the MIT license. See LICENSE file in the project root for details.

import argparse
import shutil
import sys
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

from training.test_hmm import print_cm, run_test
from training.train_hmm import train_models


def get_unique_backup_dir(archive_dir: Path, custom_name: str | None = None) -> Path:
    """Finds a non-colliding backup directory path under archive_dir."""
    archive_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    base_name = custom_name or today
    candidate = archive_dir / base_name
    if not candidate.exists():
        return candidate

    # If it already exists, append timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    candidate = archive_dir / timestamp
    if not candidate.exists():
        return candidate

    # Suffix counter fallback
    counter = 1
    while (archive_dir / f"{timestamp}_{counter}").exists():
        counter += 1
    return archive_dir / f"{timestamp}_{counter}"


def backup_models(model_dir: Path, backup_dir: Path) -> list[str]:
    """Copies existing HMM model JSON files to backup_dir."""
    backed_up = []
    for side in ["left", "right"]:
        m_file = model_dir / f"hmm_{side}.json"
        if m_file.exists():
            backup_dir.mkdir(parents=True, exist_ok=True)
            dest = backup_dir / m_file.name
            shutil.copy2(m_file, dest)
            backed_up.append(m_file.name)
    return backed_up


def restore_models(model_dir: Path, backup_dir: Path) -> list[str]:
    """Restores HMM model JSON files from backup_dir to model_dir."""
    restored = []
    for side in ["left", "right"]:
        b_file = backup_dir / f"hmm_{side}.json"
        if b_file.exists():
            dest = model_dir / b_file.name
            shutil.copy2(b_file, dest)
            restored.append(b_file.name)
    return restored


def upload_model(host: str, side: str, model_path: Path) -> tuple[bool, str]:
    """Uploads a model JSON file to Garage133 device via HTTP POST /upload_<side>."""
    if not host.startswith("http://") and not host.startswith("https://"):
        url = f"http://{host}/upload_{side}"
    else:
        url = f"{host.rstrip('/')}/upload_{side}"

    boundary = f"----Garage133UploadBoundary{uuid.uuid4().hex}"
    with open(model_path, "rb") as f:
        file_bytes = f.read()

    body = (
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="model"; filename="{model_path.name}"\r\n'
            f"Content-Type: application/json\r\n\r\n"
        ).encode()
        + file_bytes
        + f"\r\n--{boundary}--\r\n".encode()
    )

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status in (200, 204):
                return True, f"HTTP {resp.status}"
            return False, f"Unexpected HTTP status {resp.status}"
    except Exception as e:
        return False, str(e)


def print_comparison_table(baseline_results: dict | None, updated_results: dict):
    """Prints a clear, side-by-side performance characterization comparison table."""
    print("\n" + "=" * 80)
    print("                     HMM MODEL PERFORMANCE COMPARISON")
    print("=" * 80)
    print(f"{'Side':<7} | {'Baseline Accuracy':<23} | {'Updated Accuracy':<23} | {'Delta':<18}")
    print("-" * 8 + "+" + "-" * 25 + "+" + "-" * 25 + "+" + "-" * 19)

    has_regression = False

    for side in ["left", "right"]:
        up = updated_results.get(side, {})
        up_tot = up.get("total", 0)
        up_cor = up.get("correct", 0)
        up_acc = (up_cor / up_tot * 100) if up_tot > 0 else 0.0

        if baseline_results and side in baseline_results and baseline_results[side]["total"] > 0:
            base = baseline_results[side]
            base_tot = base["total"]
            base_cor = base["correct"]
            base_acc = (base_cor / base_tot * 100) if base_tot > 0 else 0.0

            delta_acc = up_acc - base_acc
            delta_cor = up_cor - base_cor
            sign = "+" if delta_acc >= 0 else ""
            delta_str = f"{sign}{delta_acc:.2f}% ({sign}{delta_cor})"

            base_str = f"{base_acc:.2f}% ({base_cor}/{base_tot})"
            up_str = f"{up_acc:.2f}% ({up_cor}/{up_tot})"

            if delta_acc < 0:
                has_regression = True
        else:
            base_str = "N/A (No previous)"
            up_str = f"{up_acc:.2f}% ({up_cor}/{up_tot})"
            delta_str = "N/A (Initial)"

        print(f"{side.upper():<7} | {base_str:<23} | {up_str:<23} | {delta_str:<18}")

    print("=" * 80)

    if has_regression:
        print("[WARNING] Performance regression detected on updated model!")
    elif baseline_results:
        print("[OK] Performance maintained or improved across all sides.")
    else:
        print("[OK] Initial model characterization complete.")


def retrain_and_characterize(
    manifest_path: str,
    model_dir: str = ".",
    archive_dir: str = "Good",
    backup_name: str | None = None,
    num_buckets: int = 20,
    max_dist: int = 400,
    boundaries: list[int] | None = None,
    num_buckets2: int | None = None,
    max_dist2: int = 400,
    boundaries2: list[int] | None = None,
    cpp_header: str | None = None,
    keep: bool = False,
    revert: bool = False,
    upload: bool = False,
    host: str | None = None,
    non_interactive: bool = False,
) -> bool:
    """Orchestrates backup, baseline characterization, retraining, evaluation, and upload."""
    model_path = Path(model_dir).resolve()
    manifest_file = Path(manifest_path).resolve()
    archive_path = (model_path / archive_dir).resolve()

    if not manifest_file.exists():
        print(f"Error: Manifest file '{manifest_file}' not found.")
        return False

    # Check for existing models
    has_left = (model_path / "hmm_left.json").exists()
    has_right = (model_path / "hmm_right.json").exists()
    has_existing = has_left or has_right

    baseline_results = None
    backup_path = None

    if has_existing:
        print(f"==> Step 1: Characterizing baseline models in '{model_path}'...")
        baseline_results = run_test(
            model_path,
            manifest_file,
            test_all=True,
            print_results=False,
        )

        backup_path = get_unique_backup_dir(archive_path, backup_name)
        backed_up = backup_models(model_path, backup_path)
        print(f"==> Step 2: Backed up {', '.join(backed_up)} to '{backup_path}'.")
    else:
        print(f"==> Step 1 & 2: No previous models found in '{model_path}'. Skipping backup.")

    # Step 3: Retrain models
    print(
        f"\n==> Step 3: Retraining HMM models (sonar 1: {num_buckets} buckets, max {max_dist}cm)..."
    )
    train_models(
        manifest_path=manifest_file,
        output_dir=model_path,
        boundaries=boundaries,
        num_buckets=num_buckets,
        max_dist=max_dist,
        boundaries2=boundaries2,
        num_buckets2=num_buckets2,
        max_dist2=max_dist2,
        cpp_header=cpp_header,
    )

    # Step 4: Characterize updated models
    print("\n==> Step 4: Characterizing updated models across all manifest episodes...")
    updated_results = run_test(
        model_path,
        manifest_file,
        test_all=True,
        print_results=False,
    )

    # Step 5: Display Comparison and Confusion Matrices
    print_comparison_table(baseline_results, updated_results)

    for side in ["left", "right"]:
        if updated_results[side]["total"] > 0:
            print_cm(
                f"UPDATED {side}",
                updated_results[side]["correct"],
                updated_results[side]["total"],
                updated_results[side]["cm"],
                updated_results[side]["states"],
            )

    # Step 6: Decide whether to keep or revert
    model_kept = True
    if backup_path and has_existing:
        if revert:
            print(f"\n==> Reverting to backup from '{backup_path}' (--revert specified)...")
            restore_models(model_path, backup_path)
            model_kept = False
        elif keep:
            print(f"\n==> Retaining updated models in '{model_path}' (--keep specified).")
            model_kept = True
        elif not non_interactive and sys.stdin.isatty():
            choice = input("\nKeep the updated models? [Y/n]: ").strip().lower()
            if choice.startswith("n"):
                print(f"==> Restoring previous models from '{backup_path}'...")
                restore_models(model_path, backup_path)
                print("[OK] Restored previous models.")
                model_kept = False
            else:
                print(
                    f"[OK] Updated models kept in '{model_path}'. Backup saved at '{backup_path}'."
                )
                model_kept = True
        else:
            print(f"==> Non-interactive mode: Updated models retained in '{model_path}'.")
            model_kept = True

    # Step 7: Upload to Garage133 device
    if model_kept:
        target_host = host
        if not target_host and (upload or (not non_interactive and sys.stdin.isatty())):
            if upload:
                target_host = input("\nEnter Garage133 device IP or hostname: ").strip()
            else:
                up_choice = (
                    input("\nUpload updated models to Garage133 device now? [y/N]: ")
                    .strip()
                    .lower()
                )
                if up_choice.startswith("y"):
                    target_host = input("Enter Garage133 device IP or hostname: ").strip()

        if target_host:
            print(f"\n==> Step 7: Uploading models to device at {target_host}...")
            for side in ["left", "right"]:
                m_file = model_path / f"hmm_{side}.json"
                if m_file.exists():
                    ok, msg = upload_model(target_host, side, m_file)
                    if ok:
                        print(f"  [OK] {side.capitalize()} model uploaded successfully ({msg}).")
                    else:
                        print(f"  [ERROR] {side.capitalize()} model upload failed: {msg}")
        else:
            print("\n==> To upload models to your Garage133 device:")
            print("  - Web UI: Open http://<garage133-ip>/ and upload JSON files on Models page")
            print("  - Retrain script: Run with --upload --host <garage133-ip> --keep")
            print("  - Curl: curl -F 'model=@hmm_left.json' http://<garage133-ip>/upload_left")
            print("          curl -F 'model=@hmm_right.json' http://<garage133-ip>/upload_right")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Backup, retrain, characterize, and manage HMM models for Garage133."
    )
    parser.add_argument(
        "--manifest",
        type=str,
        default="manifest.yaml",
        help="Path to manifest.yaml",
    )
    parser.add_argument(
        "--model-dir",
        type=str,
        default=".",
        help="Directory where models live (default: current directory)",
    )
    parser.add_argument(
        "--archive-dir",
        type=str,
        default="Good",
        help="Subdirectory under model-dir to store backups (default: Good)",
    )
    parser.add_argument(
        "--backup-name",
        type=str,
        help="Custom backup folder name (default: date/timestamp)",
    )
    parser.add_argument(
        "--num-buckets",
        type=int,
        default=20,
        help="Number of distance buckets for sonar 1 (default: 20)",
    )
    parser.add_argument(
        "--max-dist",
        type=int,
        default=400,
        help="Max distance in cm for sonar 1 (default: 400)",
    )
    parser.add_argument(
        "--boundaries",
        type=int,
        nargs="+",
        help="Custom boundaries for sonar 1",
    )
    parser.add_argument(
        "--num-buckets2",
        type=int,
        help="Number of distance buckets for sonar 2",
    )
    parser.add_argument(
        "--max-dist2",
        type=int,
        default=400,
        help="Max distance in cm for sonar 2",
    )
    parser.add_argument(
        "--boundaries2",
        type=int,
        nargs="+",
        help="Custom boundaries for sonar 2",
    )
    parser.add_argument(
        "--cpp-header",
        type=str,
        help="Optional path to export C++ header",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Automatically keep the updated models without prompting",
    )
    parser.add_argument(
        "--revert",
        action="store_true",
        help="Automatically revert to the backup models after evaluation",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Prompt to upload or upload to device",
    )
    parser.add_argument(
        "--host",
        type=str,
        help="Garage133 device hostname or IP for uploading models",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Do not prompt for interactive input",
    )

    args = parser.parse_args()

    success = retrain_and_characterize(
        manifest_path=args.manifest,
        model_dir=args.model_dir,
        archive_dir=args.archive_dir,
        backup_name=args.backup_name,
        num_buckets=args.num_buckets,
        max_dist=args.max_dist,
        boundaries=args.boundaries,
        num_buckets2=args.num_buckets2,
        max_dist2=args.max_dist2,
        boundaries2=args.boundaries2,
        cpp_header=args.cpp_header,
        keep=args.keep,
        revert=args.revert,
        upload=args.upload,
        host=args.host,
        non_interactive=args.non_interactive,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
