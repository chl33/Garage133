# Garage133: HMM Classification Strategy

This document outlines the strategy for replacing distance-threshold-based logic with a Hidden Markov Model (HMM) for garage door and car presence classification.

## 1. State Definition
Each side of the garage is modeled independently with three hidden states:
1.  **`OPEN`**: The garage door is rolled up, typically resulting in very close sonar readings (< 60cm).
2.  **`CLOSED_CAR`**: The door is shut and a vehicle is present. Readings are in the middle range (e.g., 80cm – 180cm).
3.  **`CLOSED_EMPTY`**: The door is shut and no vehicle is present. Readings are far (e.g., > 200cm, bouncing off the floor).

## 2. Emission Model: Discrete Buckets
To ensure robustness against sensor noise and ease of implementation on the ESP32, we use **Discrete Emissions**:
*   Raw sonar readings (cm) are mapped into buckets (e.g., 0, 1, 2, 3).
*   **Bucket 0 (Near):** 0 – 70cm
*   **Bucket 1 (Mid):** 70 – 190cm
*   **Bucket 2 (Far):** 190 – 350cm
*   **Bucket 3 (Error/Long):** > 350cm

The HMM learns the probability of seeing each bucket while in each hidden state. For example, in state `OPEN`, the probability of Bucket 0 is very high (~0.95), while Bucket 2 is near zero.

## 3. Transition Model & Priors
Training data consists of short "episodes" (e.g., a car entering). This data is **not representative** of a full 24-hour cycle. To avoid a biased model:
*   **Learn Emissions from Data:** Use the episodes to calculate the mean/variance or bucket distributions for each state.
*   **Hard-code Transitions (Priors):** Manually define the transition matrix based on physical reality:
    *   `CLOSED_EMPTY` cannot transition to `CLOSED_CAR` without passing through `OPEN`.
    *   Stay-probabilities should be high (e.g., 0.999) to provide "hysteresis" and filter out transient sensor errors.

## 4. Data Organization: The Manifest
Training data is managed via a central `manifest.yaml`. This keeps raw CSVs immutable and allows for easy re-labeling.

### Manifest Structure
```yaml
episodes:
  - file: "raw/event_001.csv"
    left:
      initial_state: "closed_empty"
      transitions:
        - { time: "2026-02-27T10:00:05Z", to: "open" }
        - { time: "2026-02-27T10:01:00Z", to: "closed_car" }
    right:
      initial_state: "closed_car"
      transitions: []
```

## 5. Workflow
1.  **Collection:** Use `download.py` to fetch data from InfluxDB. Provide state labels during download to auto-populate the manifest.
2.  **Training:** A Python script reads the manifest, processes CSVs, and calculates HMM parameters (Transition Matrix $A$, Emission Matrix $B$, Initial Probabilities $\pi$).
3.  **Deployment:** Export parameters to a C++ header (`hmm_config.h`) for the ESP32.
4.  **Refinement:** If the ESP32 fails, download that specific time range, label it correctly in the manifest, and retrain.
