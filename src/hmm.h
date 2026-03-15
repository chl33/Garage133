// Copyright (c) 2026 Chris Lee and contributors.
// Licensed under the MIT license. See LICENSE file in the project root for details.

#ifndef HMM_H
#define HMM_H

#include <Arduino.h>
#include <ArduinoJson.h>
#ifndef NATIVE
#include <LittleFS.h>
#include <og3/logger.h>
#else
namespace og3 {
class Logger {
 public:
  virtual void log(const char* msg) = 0;
  virtual void logf(const char* fmt, ...) = 0;
};
}  // namespace og3
#endif

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

  HMM(og3::Logger* logger) : m_logger(logger) {}

#ifndef NATIVE
  bool load(const char* path) {
    File file = LittleFS.open(path, "r");
    if (!file) {
      log()->logf("HMM: Failed to open %s.", path);
      return false;
    }

    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, file);
    file.close();

    if (error) {
      log()->logf("HMM: JSON parse failed: %s.", error.c_str());
      return false;
    }

    if (!loadFromJson(doc)) {
      return false;
    }
    log()->logf("HMM: Loaded model from %s (%d states).", path, m_model.num_states);
    return true;
  }
#endif

  bool loadFromJson(const JsonDocument& doc) {
    m_model.boundaries.clear();
    for (float b : doc["boundaries"].as<JsonArrayConst>()) {
      m_model.boundaries.push_back(b);
    }
    m_model.num_buckets = m_model.boundaries.size() + 1;

    m_model.pi.clear();
    for (float p : doc["pi"].as<JsonArrayConst>()) {
      m_model.pi.push_back(p);
    }
    m_model.num_states = m_model.pi.size();

    m_model.A.assign(m_model.num_states, std::vector<float>(m_model.num_states));
    JsonArrayConst A_json = doc["A"];
    for (int i = 0; i < m_model.num_states; i++) {
      for (int j = 0; j < m_model.num_states; j++) {
        m_model.A[i][j] = A_json[i][j];
      }
    }

    m_model.B.assign(m_model.num_states, std::vector<float>(m_model.num_buckets));
    JsonArrayConst B_json = doc["B"];
    for (int i = 0; i < m_model.num_states; i++) {
      for (int j = 0; j < m_model.num_buckets; j++) {
        m_model.B[i][j] = B_json[i][j];
      }
    }

    m_model.loaded = true;
    reset();
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
    const auto bucket = [this, distance_m]() -> unsigned {
      const float dist_cm = distance_m * 100.0f;
      for (size_t i = 0; i < m_model.boundaries.size(); i++) {
        if (dist_cm < m_model.boundaries[i]) {
          return i;
        }
      }
      // Default to last bucket (Error/Long)
      return m_model.num_buckets - 1;
    }();

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

    return currentState();
  }

  void setState(int state) {
    if (!m_model.loaded || state < 0 || state >= m_model.num_states) return;
    for (int i = 0; i < m_model.num_states; i++) {
      m_probs[i] = (i == state) ? 1.0f : 0.0f;
    }
  }

  int currentState() const {
    if (!m_model.loaded || m_probs.empty()) return -1;
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

 protected:
  og3::Logger* log() { return m_logger; }

 private:
  og3::Logger* m_logger;
  Model m_model;
  std::vector<float> m_probs;
};

#endif  // HMM_H
