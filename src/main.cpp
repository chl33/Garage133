// Copyright (c) 2025 Chris Lee and contibuters.
// Licensed under the MIT license. See LICENSE file in the project root for details.

#include <Arduino.h>
#include <LittleFS.h>
#include <WiFiClientSecure.h>
#include <og3/blink_led.h>
#include <og3/constants.h>
#include <og3/ha_app.h>
#include <og3/ha_dependencies.h>
#include <og3/html_table.h>
#include <og3/mapped_analog_sensor.h>
#include <og3/motion_detector.h>
#include <og3/oled_wifi_info.h>
#include <og3/pir.h>
#include <og3/relay.h>
#include <og3/shtc3.h>
#include <og3/sonar.h>
#include <og3/units.h>
#include <og3/variable.h>

#include <algorithm>
#include <cstring>

#define VERSION "0.8.0"

namespace og3 {

static const char kManufacturer[] = "Chris Lee";
static const char kModel[] = "Garage133";
static const char kSoftware[] = "Garage133 v" VERSION;

#if defined(LOG_UDP) && defined(LOG_UDP_ADDRESS)
constexpr App::LogType kLogType = App::LogType::kUdp;
#else
// constexpr App::LogType kLogType = App::LogType::kNone;  // kSerial
constexpr App::LogType kLogType = App::LogType::kSerial;
#endif

HAApp s_app(HAApp::Options(kManufacturer, kModel,
                           WifiApp::Options()
                               .withSoftwareName(kSoftware)
                               .withDefaultDeviceName("rooml33")
#if defined(LOG_UDP) && defined(LOG_UDP_ADDRESS)
                               .withUdpLogHost(IPAddress(LOG_UDP_ADDRESS))

#endif
                               .withOta(OtaManager::Options(OTA_PASSWORD))
                               .withApp(App::Options().withLogType(kLogType))));

// Hardware config
constexpr uint8_t kPirPin = 25;
constexpr int8_t kLSonarTrigger = 16;
constexpr int8_t kRSonarTrigger = 5;
constexpr int8_t kLSonarEcho = 17;
constexpr int8_t kRSonarEcho = 18;
constexpr uint8_t kRelayLeftPin = 15;
constexpr uint8_t kRelayRightPin = 2;
constexpr uint8_t kLightPin = 33;

constexpr int kRelayOnMsec = 10000;
constexpr int kMqttUpdateMsec = kMsecInMin;

// Names
static const char kTemperature[] = "temperature";
static const char kHumidity[] = "humidity";
static const char kRelay[] = "relay";
static const char kSonar[] = "sonar";
static const char kMotion[] = "motion";
static const char kLight[] = "light";
static const char kPirModule[] = "PIR";

VariableGroup s_cvg("garage_cfg");
VariableGroup s_vg("garage");
VariableGroup s_lvg("left", VariableGroup::VarNameType::kWithGroup);
VariableGroup s_rvg("right", VariableGroup::VarNameType::kWithGroup);

Shtc3 s_shtc3(kTemperature, kHumidity, &s_app.module_system(), "temperature", s_vg);

Relay s_left_relay(kRelay, &s_app.tasks(), kRelayLeftPin, "Left button", true, s_lvg,
                   Relay::OnLevel::kHigh);
Relay s_right_relay(kRelay, &s_app.tasks(), kRelayRightPin, "Right button", true, s_rvg,
                    Relay::OnLevel::kHigh);

Sonar s_left_sonar(kSonar, kLSonarTrigger, kLSonarEcho, &s_app.module_system(), s_lvg);
Sonar s_right_sonar(kSonar, kRSonarTrigger, kRSonarEcho, &s_app.module_system(), s_rvg);
Pir s_pir(kPirModule, kMotion, &s_app.module_system(), &s_app.tasks(), kPirPin, kMotion, s_vg, true,
          true);
MappedAnalogSensor s_light_sensor(
    MappedAnalogSensor::Options{
        .name = kLight,
        .pin = kLightPin,
        .units = units::kPercentage,
        .description = "light %",
        .raw_var_flags = 0,
        .mapped_var_flags = 0,
        .config_flags = VariableBase::kConfig | VariableBase::Flags::kSettable,
        .default_in_min = 4095,  // kAdcMax
        .default_in_max = 600,
        .default_out_min = 0.0f,
        .default_out_max = 100.0f,
        .config_decimals = 0,
        .decimals = 1,
        .valid_in_min = 0,
        .valid_in_max = 4095,
    },
    &s_app.module_system(), s_cvg, s_vg);

// Global variable for html, so asyncwebserver can send data in the background (single client)
String s_html;

// Delay between updates of the OLED.
constexpr unsigned kOledSwitchMsec = 5000;
OledDisplayRing s_oled(&s_app.module_system(), kSoftware, kOledSwitchMsec, Oled::kTenPt);

// Have oled display IP address or AP status.
og3::OledWifiInfo wifi_infof(&s_app.tasks());

WebButton s_button_wifi_config = s_app.createWifiConfigButton();
WebButton s_button_mqtt_config = s_app.createMqttConfigButton();
WebButton s_button_app_status = s_app.createAppStatusButton();
WebButton s_button_restart = s_app.createRestartButton();

og3::WebButton s_button_left_relay(&s_app.web_server(), "Left button", "/relay/left",
                                   [](AsyncWebServerRequest* request) {
                                     s_left_relay.turnOn(kRelayOnMsec);  // turn on for 1000msec
                                     request->redirect("/");
                                   });
og3::WebButton s_button_right_relay(&s_app.web_server(), "Right button", "/relay/right",
                                    [](AsyncWebServerRequest* request) {
                                      s_right_relay.turnOn(kRelayOnMsec);  // turn on for 1000msec
                                      request->redirect("/");
                                    });

class Classifier : public Module {
 public:
  Classifier(HAApp* app, const char* door, Relay* relay, MappedAnalogSensor* light,
             VariableGroup& vg)
      : Module(door, &app->module_system()),
        m_relay(relay),
        m_light(light),
        m_car("car", false, "car", vg),
        m_door("door", false, "door", vg) {
    setDependencies(&m_dependencies);
    add_init_fn([this]() {
      auto* ha_discovery = m_dependencies.ha_discovery();
      if (m_dependencies.mqtt_manager() && ha_discovery) {
        ha_discovery->addDiscoveryCallback([this](HADiscovery* had, JsonDocument* json) {
          HADiscovery::Entry entry(m_door, ha::device_type::kCover,
                                   ha::device_class::binary_sensor::kGarage);
          String command = String(m_door.name()) + "/set";
          entry.command = command.c_str();
          entry.command_callback = [this](const char* topic, const char* payload, size_t len) {
            const bool on =
                (0 == strncmp(payload, "ON", len)) || (0 == strncmp(payload, "on", len)) ||
                (0 == strncmp(payload, "1", len)) || (0 == strncmp(payload, "OPEN", len)) ||
                (0 == strncmp(payload, "CLOSE", len));
            if (on) {
              m_relay->turnOn(kRelayOnMsec);
            }
          };
          return had->addEntry(json, entry);
        });
        ha_discovery->addDiscoveryCallback([this](HADiscovery* had, JsonDocument* json) {
          HADiscovery::Entry entry(m_car, ha::device_type::kBinarySensor,
                                   ha::device_class::binary_sensor::kPresence);
          entry.icon = "mdi:car";
          return had->addEntry(json, entry);
        });
        if (m_light) {
          m_dependencies.ha_discovery()->addDiscoveryCallback([this](HADiscovery* had,
                                                                     JsonDocument* json) {
            return had->addMeas(json, m_light->mapped_value(), ha::device_type::kSensor, nullptr);
          });
        }
      }
    });
  }

  void setValue(float m) {
    if (m < 0.10) {
    } else if (m < 0.7) {
      set_open(true);      // 0.1 to 0.7
    } else if (m < 2.4) {  // 0.7 to 2.4
      set_open(false);
      set_car(true);
    } else if (m < 4) {  // 2.0 to 4.0
      set_open(false);
      set_car(false);
    } else {
    }
  }

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
  BinarySensorVariable m_car;
  BinaryCoverSensorVariable m_door;
  bool m_updated = false;
};

Classifier s_left_classifier(&s_app, "left", &s_left_relay, &s_light_sensor, s_lvg);
Classifier s_right_classifier(&s_app, "right", &s_right_relay, nullptr, s_rvg);

void update() {
  s_shtc3.read();
  s_light_sensor.read();
  s_right_sonar.setTemp(s_shtc3.temperature());
  s_left_sonar.setTemp(s_shtc3.temperature());
  s_left_sonar.read();
  s_right_sonar.read();

  char text[256];
  snprintf(text, sizeof(text), "%.3f m %.0f usec | %.3f m %.0f usec | %.1f degf %.0f",
           s_left_sonar.distance(), s_left_sonar.ping_usec(), s_right_sonar.distance(),
           s_right_sonar.ping_usec(), s_shtc3.temperaturef(), s_light_sensor.value());
  og3::s_oled.display(text);

  s_app.log().debug(text);

  s_pir.read();
  s_light_sensor.read();

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
    s_app.mqttSend(s_vg);
    s_app.mqttSend(s_lvg);
    s_app.mqttSend(s_rvg);
    s_send_millis = now_msec;
    s_left_classifier.resetUpdated();
    s_right_classifier.resetUpdated();
  }
}

PeriodicTaskScheduler s_update_scheduler(
    4 * kMsecInSec, 2 * kMsecInSec, []() { update(); }, &s_app.tasks());

void handleWebRoot(AsyncWebServerRequest* request) {
  s_shtc3.read();
  s_html.clear();
  html::writeTableInto(&s_html, s_vg);
  html::writeTableInto(&s_html, s_lvg);
  html::writeTableInto(&s_html, s_rvg);
  // html::writeFormTableInto(&s_html, s_cvg);
  html::writeTableInto(&s_html, s_app.wifi_manager().variables());
  html::writeTableInto(&s_html, s_app.mqtt_manager().variables());
  s_button_left_relay.add_button(&s_html);
  s_button_right_relay.add_button(&s_html);
  s_button_wifi_config.add_button(&s_html);
  s_button_mqtt_config.add_button(&s_html);
  s_button_app_status.add_button(&s_html);
  s_button_restart.add_button(&s_html);
  sendWrappedHTML(request, s_app.board_cname(), kSoftware, s_html.c_str());
}

void onMotion() {
  s_app.mqttSend(s_vg);
  if (s_pir.motion()) {
    s_app.log().debug("Motion1!");
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

}  // namespace og3

////////////////////////////////////////////////////////////////////////////////

void setup() {
  og3::s_oled.addDisplayFn([]() { og3::s_oled.display(og3::s_app.board_cname()); });
  og3::s_app.web_server().on("/", og3::handleWebRoot);
  og3::s_app.web_server().on("/config", [](AsyncWebServerRequest* request) {});
  og3::s_app.setup();
}

void loop() {
  og3::s_app.loop();
  og3::checkMotion();
}
