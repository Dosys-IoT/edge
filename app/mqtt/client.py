import logging
import ssl
import json

import paho.mqtt.client as mqtt

from app.config import Settings
from app.mqtt.topics import SUBSCRIPTIONS


logger = logging.getLogger(__name__)


class MqttClientManager:
    def __init__(self, settings: Settings, message_handler):
        self.settings = settings
        self.message_handler = message_handler
        self.connected = False
        self.last_reason = "not_connected"

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=settings.mqtt_client_id)
        self.client.username_pw_set(settings.mqtt_username, settings.mqtt_password)

        if settings.mqtt_tls:
            self.client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS_CLIENT)
            self.client.tls_insecure_set(False)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def start(self) -> None:
        if (
            not self.settings.mqtt_username
            or not self.settings.mqtt_password
            or self.settings.mqtt_username.startswith("<REPLACE_WITH_")
            or self.settings.mqtt_password.startswith("<REPLACE_WITH_")
        ):
            self.connected = False
            self.last_reason = "missing_or_placeholder_mqtt_credentials"
            logger.error("MQTT credentials missing or placeholders detected. Set MQTT_USERNAME and MQTT_PASSWORD.")
            return
        logger.info("Connecting to MQTT host=%s port=%s tls=%s clientId=%s",
                    self.settings.mqtt_host, self.settings.mqtt_port, self.settings.mqtt_tls, self.settings.mqtt_client_id)
        self.client.connect(self.settings.mqtt_host, self.settings.mqtt_port, keepalive=60)
        self.client.loop_start()

    def stop(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()

    def status(self) -> dict[str, object]:
        return {
            "connected": self.connected,
            "clientId": self.settings.mqtt_client_id,
            "reason": self.last_reason,
        }

    def publish_json(self, topic: str, payload: dict, qos: int = 1) -> None:
        if not self.connected:
            raise RuntimeError("MQTT is not connected")

        result = self.client.publish(topic, json.dumps(payload), qos=qos)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f"MQTT publish failed rc={result.rc}")

    def _on_connect(self, client, userdata, flags, reason_code, properties):  # pylint: disable=unused-argument
        self.connected = reason_code == 0
        self.last_reason = str(reason_code)
        logger.info("MQTT connected reason_code=%s", reason_code)
        if self.connected:
            for topic, qos in SUBSCRIPTIONS:
                client.subscribe(topic, qos=qos)
                logger.info("Subscribed to topic=%s qos=%s", topic, qos)

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):  # pylint: disable=unused-argument
        self.connected = False
        self.last_reason = str(reason_code)
        logger.warning("MQTT disconnected reason_code=%s", reason_code)

    def _on_message(self, client, userdata, msg):  # pylint: disable=unused-argument
        self.message_handler.handle_message(client, msg.topic, msg.payload)
