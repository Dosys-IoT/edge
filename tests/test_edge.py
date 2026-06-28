import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from flask import Flask

from app.interfaces.http_routes import create_http_blueprint
from app.mqtt.handlers import MqttMessageHandler
from app.mqtt.topics import config_response_topic
from app.schemas.payloads import ConfigRequestPayload
from app.services.command_service import CommandService
from app.services.sync_service import SyncService


class FakeResponse:
    def __init__(self, status_code=200, text="ok", payload=None):
        self.status_code = status_code
        self.text = text
        self._payload = payload or {}

    def json(self):
        return self._payload


class FakeRestClient:
    def __init__(self, response=None):
        self.response = response or FakeResponse()
        self.calls = []

    def post_internal_event(self, endpoint_path, payload, device_key=None):
        self.calls.append(("POST", endpoint_path, payload, device_key))
        return self.response

    def get_runtime_config(self, device_id, device_key=None):
        self.calls.append(("GET", device_id, device_key))
        return FakeResponse(payload={"deviceId": device_id, "configVersion": 1, "serverTime": "2026-06-27T12:00:00Z"})


class FakeEvent:
    def __init__(self, device_id, topic, payload_json):
        self.id = 1
        self.device_id = device_id
        self.topic = topic
        self.payload_json = payload_json
        self.status = "RECEIVED"

    def save(self):
        return None


class FakeMqttClient:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload, qos=1):
        self.published.append((topic, json.loads(payload), qos))
        return SimpleNamespace(rc=0)


class FakeMqttManager:
    def __init__(self):
        self.connected = True
        self.published = []

    def publish_json(self, topic, payload, qos=1):
        self.published.append((topic, payload, qos))

    def status(self):
        return {"connected": True, "clientId": "dosys-edge-api", "reason": "0"}


def build_test_app(sync_service, config_service, mqtt_manager, command_service):
    app = Flask(__name__)
    app.register_blueprint(create_http_blueprint(sync_service, config_service, mqtt_manager, command_service))
    return app


class EdgeContractTests(unittest.TestCase):
    def setUp(self):
        self.rest_client = FakeRestClient()
        self.sync_service = SyncService(rest_client=self.rest_client, device_keys={})
        self.config_service = SimpleNamespace(
            fetch_runtime_config=lambda device_id: {
                "deviceId": device_id,
                "configVersion": 1,
                "serverTime": "2026-06-27T12:00:00Z",
                "timezone": "America/Lima",
                "containers": [],
                "schedules": [],
                "environmentThresholds": {},
            },
            cache_runtime_config=lambda device_id, payload: None,
            build_config_response=lambda device_id, request_id, runtime_config: {
                **runtime_config,
                "requestId": request_id,
                "deviceId": device_id,
            },
            get_cached_config=lambda device_id: None,
        )

    def test_parseTopicExtractsDeviceIdAndEventType(self):
        device_id, event_type = self.sync_service.parse_topic("dosys/devices/1/environment")
        self.assertEqual(device_id, "1")
        self.assertEqual(event_type, "environment")

    def test_rejectMismatchedDeviceId(self):
        with self.assertRaises(ValueError):
            self.sync_service.save_and_sync_event(
                "dosys/devices/1/environment",
                {
                    "deviceId": "2",
                    "eventId": "env-1",
                    "temperature": 27.8,
                    "humidity": 60.2,
                    "recordedAt": "2026-06-27T12:00:00",
                    "firmwareVersion": "1.0.0",
                },
            )

    def test_forwardEnvironmentToRest(self):
        with patch("app.persistence.repositories.create_received_event", return_value=FakeEvent("1", "dosys/devices/1/environment", "{}")), \
             patch("app.persistence.repositories.mark_event_status", side_effect=lambda event, status: setattr(event, "status", status)), \
             patch("app.persistence.repositories.create_sync_attempt", return_value=SimpleNamespace(id=1)):
            self.sync_service.save_and_sync_event(
                "dosys/devices/1/environment",
                {
                    "deviceId": "1",
                    "eventId": "env-1",
                    "temperature": 27.8,
                    "humidity": 60.2,
                    "recordedAt": "2026-06-27T12:00:00",
                    "firmwareVersion": "1.0.0",
                },
            )

        method, endpoint, payload, device_key = self.rest_client.calls[0]
        self.assertEqual(method, "POST")
        self.assertEqual(endpoint, "/api/v1/device/internal/1/environment-readings")
        self.assertEqual(payload["deviceId"], "1")
        self.assertEqual(payload["eventId"], "env-1")
        self.assertIsNone(device_key)

    def test_forwardHeartbeatToRest(self):
        with patch("app.persistence.repositories.create_received_event", return_value=FakeEvent("1", "dosys/devices/1/heartbeat", "{}")), \
             patch("app.persistence.repositories.mark_event_status", side_effect=lambda event, status: setattr(event, "status", status)), \
             patch("app.persistence.repositories.create_sync_attempt", return_value=SimpleNamespace(id=1)):
            self.sync_service.save_and_sync_event(
                "dosys/devices/1/heartbeat",
                {
                    "deviceId": "1",
                    "eventId": "hb-1",
                    "rtcTime": "2026-06-27T12:00:00",
                    "wifiConnected": True,
                    "mqttConnected": True,
                    "rtcOk": True,
                    "sht3xOk": True,
                    "dfPlayerOk": True,
                    "sdCardOk": True,
                    "switchOk": True,
                    "buttonPin": 15,
                    "freeHeap": 180000,
                    "rssi": -55,
                    "deviceStatus": "ONLINE",
                    "firmwareVersion": "1.0.0",
                },
            )

        _, endpoint, payload, _ = self.rest_client.calls[0]
        self.assertEqual(endpoint, "/api/v1/device/internal/1/heartbeats")
        self.assertEqual(payload["buttonPin"], 15)
        self.assertEqual(payload["deviceStatus"], "ONLINE")

    def test_forwardIntakeWithButtonPin15ToRest(self):
        with patch("app.persistence.repositories.create_received_event", return_value=FakeEvent("1", "dosys/devices/1/intake", "{}")), \
             patch("app.persistence.repositories.mark_event_status", side_effect=lambda event, status: setattr(event, "status", status)), \
             patch("app.persistence.repositories.create_sync_attempt", return_value=SimpleNamespace(id=1)):
            self.sync_service.save_and_sync_event(
                "dosys/devices/1/intake",
                {
                    "deviceId": "1",
                    "eventId": "intake-1",
                    "scheduleId": "1",
                    "containerNumber": 1,
                    "scheduledAt": "2026-06-27T08:00:00",
                    "confirmedAt": "2026-06-27T08:02:15",
                    "status": "TAKEN",
                    "source": "PHYSICAL_BUTTON",
                    "buttonPin": 15,
                },
            )

        _, endpoint, payload, _ = self.rest_client.calls[0]
        self.assertEqual(endpoint, "/api/v1/device/internal/1/intake-events")
        self.assertEqual(payload["buttonPin"], 15)
        self.assertEqual(payload["source"], "PHYSICAL_BUTTON")

    def test_configRequestPublishesConfigResponse(self):
        handler = MqttMessageHandler(sync_service=SimpleNamespace(
            parse_topic=lambda topic: ("1", "config_request"),
            validate_config_request=lambda payload: ConfigRequestPayload.model_validate(payload),
        ), config_service=self.config_service)
        mqtt_client = FakeMqttClient()

        handler.handle_message(
            mqtt_client,
            "dosys/devices/1/config/request",
            json.dumps({
                "requestId": "req-1",
                "deviceId": "1",
                "firmwareVersion": "1.0.0",
                "hardwareVersion": "esp32-dosys-v1",
                "rtcTime": "2026-06-27T12:00:00",
                "reason": "BOOT",
            }).encode("utf-8"),
        )

        self.assertEqual(mqtt_client.published[0][0], config_response_topic("1"))
        self.assertEqual(mqtt_client.published[0][1]["requestId"], "req-1")
        self.assertEqual(mqtt_client.published[0][1]["deviceId"], "1")

    def test_audioTestCommandPublishesMqttCommand(self):
        mqtt_manager = FakeMqttManager()
        command_service = CommandService(mqtt_manager=mqtt_manager)
        app = build_test_app(self.sync_service, self.config_service, mqtt_manager, command_service)
        client = app.test_client()

        response = client.post("/edge/v1/devices/1/commands/audio-test")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mqtt_manager.published[0][0], "dosys/devices/1/commands")
        self.assertEqual(mqtt_manager.published[0][1]["command"], "AUDIO_TEST")
        self.assertEqual(mqtt_manager.published[0][1]["track"], 1)

    def test_ledTestCommandPublishesMqttCommand(self):
        mqtt_manager = FakeMqttManager()
        command_service = CommandService(mqtt_manager=mqtt_manager)
        app = build_test_app(self.sync_service, self.config_service, mqtt_manager, command_service)
        client = app.test_client()

        response = client.post("/edge/v1/devices/1/commands/led-test")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(mqtt_manager.published[0][0], "dosys/devices/1/commands")
        self.assertEqual(mqtt_manager.published[0][1]["command"], "LED_TEST")

    def test_corsHeadersPresentForHealth(self):
        mqtt_manager = FakeMqttManager()
        command_service = CommandService(mqtt_manager=mqtt_manager)
        app = build_test_app(self.sync_service, self.config_service, mqtt_manager, command_service)
        client = app.test_client()

        response = client.get("/edge/v1/health", headers={"Origin": "http://localhost:3000"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "http://localhost:3000")

    def test_corsHeadersPresentForMqttStatus(self):
        mqtt_manager = FakeMqttManager()
        command_service = CommandService(mqtt_manager=mqtt_manager)
        app = build_test_app(self.sync_service, self.config_service, mqtt_manager, command_service)
        client = app.test_client()

        response = client.options(
            "/edge/v1/mqtt/status",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "http://localhost:3000")

    def test_cachedConfigReturns200WhenMissing(self):
        mqtt_manager = FakeMqttManager()
        command_service = CommandService(mqtt_manager=mqtt_manager)
        app = build_test_app(self.sync_service, self.config_service, mqtt_manager, command_service)
        client = app.test_client()

        response = client.get("/edge/v1/devices/1/cached-config")

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["deviceId"], "1")
        self.assertFalse(body["available"])
        self.assertIsNone(body["config"])


if __name__ == "__main__":
    unittest.main()
