// Copyright (c) 2026 Chris Lee and contributors.
// Licensed under the MIT license. See LICENSE file in the project root for details.

#ifndef HMM_H
#define HMM_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include <LittleFS.h>

#include <vector>

class HMM {
 public:
  struct Model {
    int num_states = 0;
    int num_buckets = 0;
    std::vector<float> boundaries;
    std::vector<float> pi;              // Initial probabilities
    std::vector<std::vector<float>> A;  // Transition matrix [from][to]
    std::vector<std::vector<float>> B;  // Emission matrix [state][bucket]
    bool loaded = false;
  };

  HMM() {}

  bool load(const char* path) {
    File file = LittleFS.open(path, "r");
    if (!file) {
      Serial.printf("HMM: Failed to open %s\n", path);
      return false;
    }

    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, file);
    file.close();

    if (error) {
      Serial.printf("HMM: JSON parse failed: %s\n", error.c_str());
      return false;
    }

    m_model.boundaries.clear();
    for (float b : doc["boundaries"].as<JsonArray>()) {
      m_model.boundaries.push_back(b);
    }
    m_model.num_buckets = m_model.boundaries.size() + 1;

    m_model.pi.clear();
    for (float p : doc["pi"].as<JsonArray>()) {
      m_model.pi.push_back(p);
    }
    m_model.num_states = m_model.pi.size();

    m_model.A.assign(m_model.num_states, std::vector<float>(m_model.num_states));
    JsonArray A_json = doc["A"];
    for (int i = 0; i < m_model.num_states; i++) {
      for (int j = 0; j < m_model.num_states; j++) {
        m_model.A[i][j] = A_json[i][j];
      }
    }

    m_model.B.assign(m_model.num_states, std::vector<float>(m_model.num_buckets));
    JsonArray B_json = doc["B"];
    for (int i = 0; i < m_model.num_states; i++) {
      for (int j = 0; j < m_model.num_buckets; j++) {
        m_model.B[i][j] = B_json[i][j];
      }
    }

    m_model.loaded = true;
    reset();
    Serial.printf("HMM: Loaded model from %s (%d states)\n", path, m_model.num_states);
    return true;
  }

  void reset() {
    if (!m_model.loaded) return;
    m_probs = m_model.pi;
  }

  // Update probabilities based on a new sonar reading (meters)
  int update(float distance_m) {
    if (!m_model.loaded) return -1;

    // 1. Map distance (m) to bucket index
    float dist_cm = distance_m * 100.0f;
    int bucket = m_model.num_buckets - 1;  // Default to last bucket (Error/Long)
    for (size_t i = 0; i < m_model.boundaries.size(); i++) {
      if (dist_cm < m_model.boundaries[i]) {
        bucket = i;
        break;
      }
    }

    // 2. Forward Step: P(next_state | observation)
    // new_prob[j] = sum_i( prob[i] * A[i][j] ) * B[j][bucket]
    std::vector<float> next_probs(m_model.num_states, 0.0f);
    float sum = 0.0f;

    for (int j = 0; j < m_model.num_states; j++) {
      float transition_prob = 0.0f;
      for (int i = 0; i < m_model.num_states; i++) {
        transition_prob += m_probs[i] * m_model.A[i][j];
      }
      next_probs[j] = transition_prob * m_model.B[j][bucket];
      sum += next_probs[j];
    }

    // 3. Normalize to prevent underflow
    if (sum > 0) {
      for (int j = 0; j < m_model.num_states; j++) {
        next_probs[j] /= sum;
      }
      m_probs = next_probs;
    } else {
      // If sum is 0 (impossible observation), reset to pi or stay as is?
      // For now, we keep previous probs to handle transient garbage readings.
    }

    // 4. Return the most likely state
    int max_state = 0;
    for (int i = 1; i < m_model.num_states; i++) {
      if (m_probs[i] > m_probs[max_state]) {
        max_state = i;
      }
    }
    return max_state;
  }

  int currentState() const {
    int max_state = 0;
    for (size_t i = 1; i < m_probs.size(); i++) {
      if (m_probs[i] > m_probs[max_state]) {
        max_state = i;
      }
    }
    return max_state;
  }

  const std::vector<float>& probabilities() const { return m_probs; }
  bool isLoaded() const { return m_model.loaded; }

 private:
  Model m_model;
  std::vector<float> m_probs;
};

#endif  // HMM_H
