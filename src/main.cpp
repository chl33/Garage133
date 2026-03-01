// Copyright (c) 2026 Chris Lee and contributors.
// Licensed under the MIT license. See LICENSE file in the project root for details.

#include <Arduino.h>
#include <LittleFS.h>
#include <WiFiClientSecure.h>
#include <og3/blink_led.h>
#include <og3/ha_app.h>
#include <og3/html_table.h>
#include <og3/mapped_analog_sensor.h>
#include <og3/oled.h>
#include <og3/pir.h>
#include <og3/relay.h>
#include <og3/shtc3.h>
#include <og3/sonar.h>
#include <og3/wifi_watchdog.h>

#include <algorithm>
#include <cstring>

#include "hmm.h"

#define VERSION "0.9.6"

namespace og3 {

static const char kManufacturer[] = "Chris Lee";
static const char kModel[] = "Garage133";
static const char kSoftware[] = "Garage133 v" VERSION;

// --- Garage133 Hardware Configuration ---

// Relays (Door Control)
const int kRelayLeftPin = 15;
const int kRelayRightPin = 2;

// Sonar Sensors
const int kLeftTrigPin = 16;
const int kLeftEchoPin = 17;
const int kRightTrigPin = 5;
const int kRightEchoPin = 18;

// PIR & Light Sensors
const int kPirPin = 25;
const int kLightPin = 33;

// Application and configuration.
#if defined(LOG_UDP) && defined(LOG_UDP_ADDRESS)
WifiApp::Options s_app_options =
    WifiApp::Options()
    .withDefaultDeviceName("garage133")
    .withSoftwareName(kSoftware)
    .withApp(App::Options().withLogType(App::LogType::kUdp);
    .withUdpLogHost(IPAddress(LOG_UDP_ADDRESS));
#else
WifiApp::Options s_app_options =
    WifiApp::Options()
        .withDefaultDeviceName("garge133")
        .withSoftwareName(kSoftware)
        .withApp(App::Options().withLogType(App::LogType::kSerial));  // kNone
#endif

HAApp::Options s_ha_options(kManufacturer, kModel, s_app_options);
HAApp s_app(s_ha_options);

// Variable Groups for MQTT/Discovery
VariableGroup s_garage_vg("garage", nullptr, 10);
VariableGroup s_left_vg("left", nullptr, 2);
VariableGroup s_right_vg("right", nullptr, 2);

// Relay and sensors.
Relay s_left_relay("left_relay", &s_app.tasks(), kRelayLeftPin, "left relay", true, s_garage_vg);
Relay s_right_relay("right_relay", &s_app.tasks(), kRelayRightPin, "right relay", true, s_garage_vg);

MappedAnalogSensor::Options s_light_options = {
    .name = "light",
    .pin = static_cast<uint8_t>(kLightPin),
    .units = "percentage",
    .raw_description = "light raw",
    .description = "light %",
    .raw_var_flags = 0,
    .mapped_var_flags = 0,
    .config_flags = VariableBase::kConfig | VariableBase::Flags::kSettable,
    .default_in_min = 0,
    .default_in_max = 4095,
    .default_out_min = 100.0f,
    .default_out_max = 0.0f,
    .config_decimals = 1,
    .decimals = 1,
    .valid_in_min = 0,
    .valid_in_max = 4095,
};
VariableGroup s_light_cfg_vg("light_cfg");
MappedAnalogSensor s_light_sensor(s_light_options, &s_app.module_system(), s_light_cfg_vg, s_garage_vg);

Sonar s_left_sonar("left_sonar", kLeftTrigPin, kLeftEchoPin, &s_app.module_system(), s_garage_vg, &s_app.ha_discovery());
Sonar s_right_sonar("right_sonar", kRightTrigPin, kRightEchoPin, &s_app.module_system(), s_garage_vg, &s_app.ha_discovery());

Pir s_pir("pir", "motion", &s_app.module_system(), kPirPin, "motion", s_garage_vg, true, true);

// SHTC3 temperature and humidity sensor.
Shtc3 s_shtc3("temperature", "humidity", &s_app.module_system(), "climate", s_garage_vg);

// OLED display.
Oled s_oled("oled", &s_app.module_system(), kSoftware);

const long kMqttUpdateMsec = 60 * kMsecInSec;

class Classifier : public Module {
 public:
  Classifier(HAApp * app, const char* side, Relay* relay, MappedAnalogSensor* light,
             VariableGroup& vg)
      : Module(side, &app->module_system()),
        m_relay(relay),
        m_light(light),
        m_side(side),
        m_door_name(String(side) + "_door"),
        m_car("car", false, "car", vg),
        m_door("door", false, "door", vg) {
    setDependencies(&m_dependencies);
    add_init_fn([this]() {
      loadModel();
      auto* ha_discovery = m_dependencies.ha_discovery();

      ha_discovery->addDiscoveryCallback([this](HADiscovery* had, JsonDocument* json) {
        had->addBinarySensor(json, m_car, ha::device_class::binary_sensor::kConnectivity, nullptr,
                             m_side.c_str());
        had->addBinarySensor(json, m_door, ha::device_class::binary_sensor::kGarageDoor, nullptr,
                             m_side.c_str());

        // Add Cover discovery for the door control
        HADiscovery::Entry cover_entry(m_door, ha::device_type::kCover,
                                       ha::device_class::cover::kGarage);
        char cmd_topic[80];
        snprintf(cmd_topic, sizeof(cmd_topic), "%s/set", had->deviceId());
        cover_entry.command = cmd_topic;
        cover_entry.device_id = m_door_name.c_str();
        cover_entry.device_name = m_door_name.c_str();
        cover_entry.command_callback = [this](const char* topic, const char* payload, size_t len) {
          m_relay->turnOn(500);  // 500ms pulse to toggle door
        };
        had->addEntry(json, cover_entry);

        return true;
      });
    });
  }

  void setValue(float m) {
    if (m_hmm.isLoaded()) {
      int state = m_hmm.update(m);
      // States: 0: open, 1: closed_car, 2: closed_empty
      switch (state) {
        case 0:
          set_open(true);
          set_car(false);
          break;
        case 1:
          set_open(false);
          set_car(true);
          break;
        case 2:
          set_open(false);
          set_car(false);
          break;
      }
    } else {
      // Fallback to basic thresholds if model is not loaded
      if (m < 0.10) {
      } else if (m < 0.7) {
        set_open(true);      // 0.1 to 0.7
      } else if (m < 2.4) {  // 0.7 to 2.4
        set_open(false);
        set_car(true);
      } else if (m < 4) {  // 2.0 to 4.0
        set_open(false);
        set_car(false);
      }
    }
  }

  void loadModel() {
    char path[32];
    snprintf(path, sizeof(path), "/hmm_%s.json", m_side.c_str());
    m_hmm.load(path);
  }
  bool isModelLoaded() const { return m_hmm.isLoaded(); }

  bool updated() const { return m_updated; }
  void resetUpdated() { m_updated = false; }

 protected:
  void set_car(bool car) {
    if (car == m_car.value()) {
      return;
    }
    m_car = car;
    m_updated = true;
  }
  void set_open(bool open) {
    if (open == m_door.value()) {
      return;
    }
    m_door = open;
    m_updated = true;
  }

 private:
  HADependencies m_dependencies;
  Relay* m_relay;
  MappedAnalogSensor* m_light;
  String m_side;
  String m_door_name;
  BinarySensorVariable m_car;
  BinaryCoverSensorVariable m_door;
  HMM m_hmm;
  bool m_updated = false;
};

Classifier s_left_classifier(&s_app, "left", &s_left_relay, &s_light_sensor, s_left_vg);
Classifier s_right_classifier(&s_app, "right", &s_right_relay, nullptr, s_right_vg);

NetHandlerStatus handleUpload(NetRequest* request, const String& filename, size_t index, uint8_t* data,
                           size_t len, bool final) {
  static File file;
  String side = request->url().endsWith("_left") ? "left" : "right";
  String path = "/hmm_" + side + ".json";

  if (!index) {
    file = LittleFS.open(path, "w");
    if (!file) {
      s_app.log().log("Failed to open file for upload");
    }
  }
  if (file) {
    file.write(data, len);
  }
  if (final) {
    if (file) {
      file.close();
      s_app.log().log(side + " model upload complete. Reloading...");
      if (side == "left")
        s_left_classifier.loadModel();
      else
        s_right_classifier.loadModel();
    }
  }
  NET_REPLY(request, ESP_OK);
}

void update() {
  s_shtc3.read();
  s_light_sensor.read();
  s_right_sonar.setTemp(s_shtc3.temperature());
  s_left_sonar.setTemp(s_shtc3.temperature());
  s_left_sonar.read();
  s_right_sonar.read();

  char text[256];
  snprintf(text, sizeof(text), "L:%.2fm R:%.2fm | T:%.1fF L:%.0f%%", s_left_sonar.distance(),
           s_right_sonar.distance(), s_shtc3.temperaturef(), s_light_sensor.value());
  s_oled.display(text);

  s_app.log().log(text);

  s_pir.read();

  if (s_right_sonar.ok()) {
    s_right_classifier.setValue(s_right_sonar.distance());
  }
  if (s_left_sonar.ok()) {
    s_left_classifier.setValue(s_left_sonar.distance());
  }

  const long now_msec = millis();
  static unsigned long s_send_millis = 0;
  if (s_left_classifier.updated() || s_right_classifier.updated() ||
      (now_msec - s_send_millis) > kMqttUpdateMsec || s_send_millis == 0) {
    s_app.mqttSend(s_garage_vg);
    s_app.mqttSend(s_left_vg);
    s_app.mqttSend(s_right_vg);
    s_send_millis = now_msec;
    s_left_classifier.resetUpdated();
    s_right_classifier.resetUpdated();
  }
}

PeriodicTaskScheduler s_update_scheduler(4 * kMsecInSec, 2 * kMsecInSec, []() {
  update(); },
                                         &s_app.tasks());

og3::WebButton s_button_left_relay(&s_app.web_server_module().native_server(), "Toggle Left Door", "/relay/left",
                                   [](NetRequest* request) {
  s_left_relay.turnOn(500);
  og3::sendWrappedHTML(request, "relay", "", "Left door toggled.");
  NET_REPLY(request, ESP_OK);
                                   });
og3::WebButton s_button_right_relay(&s_app.web_server_module().native_server(), "Toggle Right Door",
                                    "/relay/right", [](NetRequest* request) {
  s_right_relay.turnOn(500);
  og3::sendWrappedHTML(request, "relay", "", "Right door toggled.");
  NET_REPLY(request, ESP_OK);
                                    });
og3::WebButton s_button_wifi_config = s_app.createWifiConfigButton();
og3::WebButton s_button_mqtt_config = s_app.createMqttConfigButton();
og3::WebButton s_button_app_status = s_app.createAppStatusButton();
og3::WebButton s_button_restart = s_app.createRestartButton();

NetHandlerStatus handleWebRoot(NetRequest* request) {
  s_shtc3.read();
  String html;
  html::writeTableInto(&html, s_garage_vg);
  html::writeTableInto(&html, s_left_vg);
  html::writeTableInto(&html, s_right_vg);
  html::writeTableInto(&html, s_app.wifi_manager().variables());
  html::writeTableInto(&html, s_app.mqtt_manager().variables());
  html += "<h3>HMM Models</h3>";
  html += "<p>Left Model: ";
  html += s_left_classifier.isModelLoaded() ? "Loaded" : "Not Loaded";
  html += " | Right Model: ";
  html += s_right_classifier.isModelLoaded() ? "Loaded" : "Not Loaded";
  html += "</p>";

  html += "<form method='POST' action='/upload_left' enctype='multipart/form-data'>";
  html += "Left: <input type='file' name='model'><input type='submit' value='Upload Left'>";
  html += "</form>";

  html += "<form method='POST' action='/upload_right' enctype='multipart/form-data'>";
  html += "Right: <input type='file' name='model'><input type='submit' value='Upload Right'>";
  html += "</form>";

  s_button_left_relay.add_button(&html);
  s_button_right_relay.add_button(&html);
  s_button_wifi_config.add_button(&html);
  s_button_mqtt_config.add_button(&html);
  s_button_app_status.add_button(&html);
  s_button_restart.add_button(&html);
  sendWrappedHTML(request, s_app.board_cname(), kSoftware, html.c_str());
  NET_REPLY(request, ESP_OK);
}

void onMotion() {
  s_app.mqttSend(s_garage_vg);
  if (s_pir.motion()) {
    s_app.log().log("Motion detected!");
    s_oled.display("Motion");
  }
}

void checkMotion() {
  bool changed = false;
  static bool wasMotion = false;
  s_pir.read();
  const bool motion = s_pir.motion();
  changed = changed || (wasMotion != motion);
  if (changed) {
    onMotion();
  }
  wasMotion = motion;
}

// Add a watchdog to reboot the device if it locks-up for some reason.
WifiWatchdog s_watchdog(&s_app, std::chrono::seconds(5), std::chrono::seconds(1));

}  // namespace og3

////////////////////////////////////////////////////////////////////////////////

void setup() {
  og3::s_oled.setup();
  og3::s_app.web_server_module().on("/", og3::handleWebRoot);
  og3::s_app.web_server_module().on("/config",
                                    [](og3::NetRequest* request) { NET_REPLY(request, ESP_OK); });

  auto upload_cb = [](og3::NetRequest* request, const String& filename, size_t index, uint8_t* data,
                      size_t len, bool final) {
    return og3::handleUpload(request, filename, index, data, len, final);
  };
  og3::s_app.web_server_module().on("/upload_left", HTTP_POST, og3::handleWebRoot, upload_cb);
  og3::s_app.web_server_module().on("/upload_right", HTTP_POST, og3::handleWebRoot, upload_cb);

  og3::s_app.setup();
}

void loop() {
  og3::s_app.loop();
  og3::checkMotion();
}
