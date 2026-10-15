# Garage133 Training Module

This module trains a Hidden Markov Model (HMM) to classify garage states (Open, Closed+Car, Closed+Empty) based on sonar distance readings. It generates side-specific models (`hmm_left.json` and `hmm_right.json`) that can be uploaded directly to the ESP32.

## Setup

Ensure you have Poetry installed, then run:

```bash
poetry install
```

## Retraining Workflow (Backup, Retrain, Characterize, Upload)

The primary tool for managing HMM updates is `retrain.py` (or the `retrain.sh` script from the `analysis/` root).

```bash
./retrain.sh
```

### What `retrain.sh` does:
1. **Evaluates Baseline**: Tests the currently active HMM models across all episodes in `sonar_data/manifest.yaml` to record baseline accuracy and confusion matrices.
2. **Backups Previous Models**: Copies the previous models to a timestamped folder under `training/Good/` (e.g. `training/Good/YYYY-MM-DD`).
3. **Retrains Updated Models**: Trains new HMM models using configurable bucketing parameters (default: 20 buckets).
4. **Characterizes Updated Models**: Tests the updated models across all manifest episodes.
5. **Compares Performance**: Displays a side-by-side comparison table showing accuracy differences and sample deltas, warning of any performance regressions.
6. **Keep or Revert**: Prompts whether to keep the new models or revert to the backup.
7. **Device Upload**: Prompts to upload the models directly to the Garage133 device over HTTP (`POST /upload_left` and `POST /upload_right`).

### Options:
*   `--num-buckets <N>`: Set number of distance buckets (default: 20).
*   `--keep`: Automatically keep updated models without prompting.
*   `--revert`: Automatically revert to backup models.
*   `--upload`: Upload to device.
*   `--host <ip_or_hostname>`: Garage133 device IP or hostname (e.g., `192.168.1.50` or `garage133.local`).
*   `--non-interactive`: Run unattended without interactive terminal prompts.

Example command to retrain and immediately upload to device:
```bash
./retrain.sh --host 192.168.1.50 --keep
```

---

## Standalone Tools

### Training Only
```bash
poetry run python src/training/train_hmm.py --manifest ../sonar_data/manifest.yaml --output-dir . --num-buckets 20
```

### Testing and Validation

#### Individual Episode Visualization:
```bash
poetry run python src/training/test_hmm.py --model-dir . --manifest ../sonar_data/manifest.yaml --episode 0 --probs
```

#### Global Performance Characterization:
```bash
poetry run python src/training/test_hmm.py --model-dir . --manifest ../sonar_data/manifest.yaml --all
```

**Metrics:**
*   **Accuracy**: The percentage of sonar samples correctly classified.
*   **Confusion Matrix**: Rows represent the actual steady state (Ground Truth), and columns represent what the HMM predicted.

### Model Visualization (SVG Generation)

Generate scalable vector diagrams showing the state transition topology and distance emission histograms:

```bash
# Generate SVGs for both hmm_left.json and hmm_right.json
./visualize_hmm.sh

# Or for a specific model JSON file:
poetry run python src/training/visualize_hmm.py hmm_left.json -o hmm_left.svg
```

The resulting SVGs illustrate:
1. **State Transition Topology**: Directed graph of states, transition probabilities $A_{ij}$, stay probabilities, and initial priors $\pi_i$.
2. **Emission Profiles**: Histograms of distance readings $P(\text{dist} \mid \text{state})$ for each state, comparing Sonar 1 and Sonar 2 distributions across distance buckets (0–400cm).

## Data Organization

The trainer expects a `manifest.yaml` file pointing to CSV files containing sonar data. Use `interactive.py` or `./interactive.sh` to download and label steady-state garage episodes without state transitions.
