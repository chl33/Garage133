#include <ArduinoFake.h>
#include <unity.h>

#include "hmm.h"

// A dummy logger to fulfill HMM's requirement
class DummyLogger : public og3::Logger {
 public:
  void log(const char* msg) override {}
  void logf(const char* fmt, ...) override {}
};

static DummyLogger s_logger;

const char* basic_model_json = R"({
  "boundaries": [50.0, 150.0],
  "pi": [0.33, 0.33, 0.34],
  "A": [
    [0.9, 0.05, 0.05],
    [0.05, 0.9, 0.05],
    [0.05, 0.05, 0.9]
  ],
  "B": [
    [0.8, 0.1, 0.1],
    [0.1, 0.8, 0.1],
    [0.1, 0.1, 0.8]
  ]
})";

void test_load_from_json(void) {
  HMM hmm(&s_logger);
  JsonDocument doc;
  deserializeJson(doc, basic_model_json);

  TEST_ASSERT_TRUE(hmm.loadFromJson(doc));
  TEST_ASSERT_TRUE(hmm.isLoaded());

  auto probs = hmm.probabilities();
  TEST_ASSERT_EQUAL(3, probs.size());
  TEST_ASSERT_FLOAT_WITHIN(0.001, 0.33, probs[0]);
  TEST_ASSERT_FLOAT_WITHIN(0.001, 0.33, probs[1]);
  TEST_ASSERT_FLOAT_WITHIN(0.001, 0.34, probs[2]);

  // Initially, max state is 2 because pi[2] is slightly higher
  TEST_ASSERT_EQUAL(2, hmm.currentState());
}

void test_update_probabilities(void) {
  HMM hmm(&s_logger);
  JsonDocument doc;
  deserializeJson(doc, basic_model_json);
  hmm.loadFromJson(doc);

  // Distance 0.3m -> 30cm -> bucket 0 (< 50.0)
  // High probability for state 0 (emission 0.8)
  int state = hmm.update(0.3f);
  TEST_ASSERT_EQUAL(0, state);

  auto probs = hmm.probabilities();
  TEST_ASSERT_TRUE(probs[0] > probs[1]);
  TEST_ASSERT_TRUE(probs[0] > probs[2]);

  // Update again with distance 1.0m -> 100cm -> bucket 1 (< 150.0)
  // State 1 should become the most likely
  state = hmm.update(1.0f);
  // It might take a couple updates to shift depending on the transition matrix
  state = hmm.update(1.0f);
  TEST_ASSERT_EQUAL(1, state);

  // Distance 2.0m -> 200cm -> bucket 2 (>= 150.0)
  state = hmm.update(2.0f);
  state = hmm.update(2.0f);
  TEST_ASSERT_EQUAL(2, state);
}

void test_force_state(void) {
  HMM hmm(&s_logger);
  JsonDocument doc;
  deserializeJson(doc, basic_model_json);
  hmm.loadFromJson(doc);

  hmm.setState(1);
  TEST_ASSERT_EQUAL(1, hmm.currentState());

  auto probs = hmm.probabilities();
  TEST_ASSERT_FLOAT_WITHIN(0.001, 0.0, probs[0]);
  TEST_ASSERT_FLOAT_WITHIN(0.001, 1.0, probs[1]);
  TEST_ASSERT_FLOAT_WITHIN(0.001, 0.0, probs[2]);

  // A subsequent update consistent with state 1 should keep it there
  TEST_ASSERT_EQUAL(1, hmm.update(1.0f));
}

void test_zero_sum_fallback(void) {
  HMM hmm(&s_logger);

  // Create a model where reaching bucket 2 from state 0 is impossible
  const char* strict_json = R"({
    "boundaries": [100.0],
    "pi": [1.0, 0.0],
    "A": [
      [1.0, 0.0],
      [0.0, 1.0]
    ],
    "B": [
      [1.0, 0.0],
      [0.0, 1.0]
    ]
  })";

  JsonDocument doc;
  deserializeJson(doc, strict_json);
  hmm.loadFromJson(doc);

  // Initially in state 0
  TEST_ASSERT_EQUAL(0, hmm.currentState());

  // Provide observation for bucket 1 (> 100.0)
  // Since B[0][1] == 0, sum of next_probs will be 0.
  // The code should handle this gracefully and not divide by zero.
  int state = hmm.update(2.0f);

  // Check that probs are still valid numbers, not NaN
  auto probs = hmm.probabilities();
  TEST_ASSERT_FALSE(isnan(probs[0]));
}

int main(int argc, char** argv) {
  UNITY_BEGIN();
  RUN_TEST(test_load_from_json);
  RUN_TEST(test_update_probabilities);
  RUN_TEST(test_force_state);
  RUN_TEST(test_zero_sum_fallback);
  return UNITY_END();
}
