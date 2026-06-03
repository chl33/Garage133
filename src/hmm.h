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

class Matrix {
 public:
  Matrix() : m_rows(0), m_cols(0) {}
  Matrix(int rows, int cols) : m_rows(rows), m_cols(cols), m_data(rows * cols, 0.0f) {}

  void resize(int rows, int cols) {
    m_rows = rows;
    m_cols = cols;
    m_data.assign(rows * cols, 0.0f);
  }

  float& operator()(int r, int c) { return m_data[r * m_cols + c]; }
  const float& operator()(int r, int c) const { return m_data[r * m_cols + c]; }

  int rows() const { return m_rows; }
  int cols() const { return m_cols; }

 private:
  int m_rows, m_cols;
  std::vector<float> m_data;
};

class HMM {
 public:
  struct Model {
    int num_states = 0;
    int num_buckets = 0;
    std::vector<float> boundaries;   // sonar distance bucket boundary distances
    std::vector<float> boundaries2;  // sonar 2 distance bucket boundary distances
    int num_buckets2 = 0;
    std::vector<float> pi;           // Initial probabilities
    Matrix A;                        // Transition matrix [from][to]
    Matrix B;                        // Emission matrix [state][bucket]
    Matrix B2;                       // Emission matrix for sonar 2 [state][bucket]
    bool is_dual_sonar = false;
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

    m_model.boundaries2.clear();
    if (doc["boundaries2"].is<JsonArrayConst>()) {
      for (float b : doc["boundaries2"].as<JsonArrayConst>()) {
        m_model.boundaries2.push_back(b);
      }
    } else {
      m_model.boundaries2 = m_model.boundaries;
    }
    m_model.num_buckets2 = m_model.boundaries2.size() + 1;

    m_model.pi.clear();
    for (float p : doc["pi"].as<JsonArrayConst>()) {
      m_model.pi.push_back(p);
    }
    m_model.num_states = m_model.pi.size();

    m_model.A.resize(m_model.num_states, m_model.num_states);
    JsonArrayConst A_json = doc["A"];
    for (int i = 0; i < m_model.num_states; i++) {
      for (int j = 0; j < m_model.num_states; j++) {
        m_model.A(i, j) = A_json[i][j];
      }
    }

    m_model.B.resize(m_model.num_states, m_model.num_buckets);
    JsonArrayConst B_json = doc["B"];
    for (int i = 0; i < m_model.num_states; i++) {
      for (int j = 0; j < m_model.num_buckets; j++) {
        m_model.B(i, j) = B_json[i][j];
      }
    }

    m_model.is_dual_sonar = false;
    if (doc["B2"].is<JsonArrayConst>()) {
      m_model.B2.resize(m_model.num_states, m_model.num_buckets2);
      JsonArrayConst B2_json = doc["B2"];
      for (int i = 0; i < m_model.num_states; i++) {
        for (int j = 0; j < m_model.num_buckets2; j++) {
          m_model.B2(i, j) = B2_json[i][j];
        }
      }
      m_model.is_dual_sonar = true;
    }

    m_model.loaded = true;
    reset();
    return true;
  }

  void reset() {
    if (!m_model.loaded) return;
    m_probs = m_model.pi;
  }

  // Update probabilities based on a single sonar reading (meters) for backward compatibility
  int update(float distance_m) { return update(distance_m, -1.0f); }

  // Update probabilities based on two sonar readings (meters)
  int update(float distance1_m, float distance2_m) {
    if (!m_model.loaded) return -1;

    // 1. Map distance 1 (m) to bucket index
    const auto bucket1 = [this, distance1_m]() -> unsigned {
      if (distance1_m < 0) return m_model.num_buckets - 1;
      const float dist_cm = distance1_m * 100.0f;
      for (size_t i = 0; i < m_model.boundaries.size(); i++) {
        if (dist_cm < m_model.boundaries[i]) {
          return i;
        }
      }
      return m_model.num_buckets - 1;
    }();

    // 2. Map distance 2 (m) to bucket index
    const auto bucket2 = [this, distance2_m]() -> unsigned {
      if (distance2_m < 0) return m_model.num_buckets2 - 1;
      const float dist_cm = distance2_m * 100.0f;
      for (size_t i = 0; i < m_model.boundaries2.size(); i++) {
        if (dist_cm < m_model.boundaries2[i]) {
          return i;
        }
      }
      return m_model.num_buckets2 - 1;
    }();

    // 3. Forward Step: P(next_state | observation)
    // next_probs[j] = sum_i( prob[i] * A[i][j] ) * B1[j][bucket1] * B2[j][bucket2]
    std::vector<float> next_probs(m_model.num_states, 0.0f);

    for (int i = 0; i < m_model.num_states; i++) {
      const float p = m_probs[i];
      for (int j = 0; j < m_model.num_states; j++) {
        next_probs[j] += p * m_model.A(i, j);
      }
    }

    float sum = 0.0f;
    for (int j = 0; j < m_model.num_states; j++) {
      float emission = m_model.B(j, bucket1);
      if (m_model.is_dual_sonar) {
        emission *= m_model.B2(j, bucket2);
      }
      next_probs[j] *= emission;
      sum += next_probs[j];
    }

    // 4. Normalize to prevent underflow
    if (sum > 0) {
      for (int j = 0; j < m_model.num_states; j++) {
        next_probs[j] /= sum;
      }
      m_probs = next_probs;
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
  bool isDualSonar() const { return m_model.is_dual_sonar; }
  int numStates() const { return m_model.num_states; }

 protected:
  og3::Logger* log() { return m_logger; }

 private:
  og3::Logger* m_logger;
  Model m_model;
  std::vector<float> m_probs;
};

#endif  // HMM_H
