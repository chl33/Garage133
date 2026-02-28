# Garage133 Training Module

This module trains a Hidden Markov Model (HMM) to classify garage states (Open, Closed+Car, Closed+Empty) based on sonar distance readings. It generates side-specific models (`hmm_left.json` and `hmm_right.json`) that can be uploaded directly to the ESP32.

## Setup

Ensure you have Poetry installed, then run:

```bash
poetry install
```

## Training the Model

To train side-specific models using a labeled manifest:

```bash
poetry run python src/training/train_hmm.py --manifest manifest.yaml --output-dir .
```

### Advanced Training Options
*   **Granular Bucketing**: Instead of manual boundaries, you can generate evenly spaced buckets to capture a more detailed "fingerprint" of the garage states.
    ```bash
    poetry run python src/training/train_hmm.py --num-buckets 10 --max-dist 400
    ```
    *   `--num-buckets`: Number of distance ranges to use (e.g., 10).
    *   `--max-dist`: The maximum expected distance in cm (e.g., 400). Readings beyond this will fall into an "Error/Reflection" bucket.
*   **Manual Boundaries**: 
    ```bash
    poetry run python src/training/train_hmm.py --boundaries 70 190 350
    ```

## Testing and Validation

### Individual Episode Test
To visualize the performance on a specific episode:
```bash
poetry run python src/training/test_hmm.py --model-dir . --manifest manifest.yaml --episode 0 --probs
```
*   `--probs`: Show internal state probabilities (confidence) over time.

### Global Performance Characterization
To characterize how well your model performs across **every episode** in your manifest at once:
```bash
poetry run python src/training/test_hmm.py --model-dir . --manifest manifest.yaml --all
```

**What this provides:**
*   **Global Accuracy**: A single percentage representing performance across all your collected data.
*   **Global Confusion Matrix**: An aggregated matrix that highlights systematic errors (e.g., if the model frequently confuses "Car" and "Empty" across multiple days).

### Understanding the Metrics
*   **Accuracy**: The percentage of sonar samples correctly classified.
*   **Confusion Matrix**: Rows represent the actual state (Ground Truth), and columns represent what the HMM predicted.
    *   *Diagonal entries* (top-left to bottom-right) represent correct classifications.
    *   *Off-diagonal entries* show exactly which states are being confused.

## Data Organization

The trainer expects a `manifest.yaml` file that points to CSV files containing sonar data. Use the `interactive.py` tool in the `download` module to generate and label these episodes.
