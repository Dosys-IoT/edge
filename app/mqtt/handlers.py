import json
import logging
from typing import Any

from app.mqtt.topics import config_response_topic
from app.services.config_service import ConfigService
from app.services.sync_service import SyncService


logger = logging.getLogger(__name__)


class MqttMessageHandler:
    def __init__(self, sync_service: SyncService, config_service: ConfigService):
        self.sync_service = sync_service
        self.config_service = config_service

    def handle_message(self, mqtt_client, topic: str, payload_bytes: bytes) -> None:
        logger.info("MQTT message received topic=%s", topic)
        try:
            payload_raw = payload_bytes.decode("utf-8")
            payload = json.loads(payload_raw)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Invalid JSON payload on topic=%s error=%s", topic, exc)
            return

        try:
            device_id, event_type = self.sync_service.parse_topic(topic)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Topic/device validation failed topic=%s error=%s", topic, exc)
            return
        logger.info("Parsed event deviceId=%s eventType=%s payload=%s", device_id, event_type, payload)

        if event_type == "config_request":
            self._handle_config_request(mqtt_client, device_id, payload)
            return

        try:
            event = self.sync_service.save_and_sync_event(topic, payload)
            logger.info("Event processed id=%s topic=%s status=%s", event.id, topic, event.status)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to process event topic=%s error=%s", topic, exc)

    def _handle_config_request(self, mqtt_client, device_id: str, payload: dict[str, Any]) -> None:
        try:
            parsed = self.sync_service.validate_config_request(payload)
            if parsed.deviceId is not None and parsed.deviceId != device_id:
                raise ValueError(f"Payload deviceId={parsed.deviceId} does not match topic deviceId={device_id}")

            runtime_config = None
            try:
                runtime_config = self.config_service.fetch_runtime_config(device_id)
            except Exception as rest_exc:  # pylint: disable=broad-except
                logger.warning("Runtime config fetch failed deviceId=%s error=%s", device_id, rest_exc)
                cached = self.config_service.get_cached_config(device_id)
                if cached is not None:
                    runtime_config = cached["payloadJson"]
                    if isinstance(runtime_config, str):
                        runtime_config = json.loads(runtime_config)
                if runtime_config is None:
                    raise

            self.config_service.cache_runtime_config(device_id, runtime_config)
            response_payload = self.config_service.build_config_response(
                device_id=device_id,
                request_id=parsed.requestId,
                runtime_config=runtime_config,
            )
            publish_topic = config_response_topic(device_id)
            mqtt_client.publish(publish_topic, json.dumps(response_payload), qos=1)
            logger.info("Published runtime config deviceId=%s topic=%s", device_id, publish_topic)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed config request handling deviceId=%s error=%s", device_id, exc)
