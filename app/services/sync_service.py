import json
import logging
from dataclasses import dataclass
from typing import Any, Type

from pydantic import BaseModel, ValidationError

from app.persistence import repositories
from app.persistence.models import ReceivedMqttEvent
from app.rest.rest_client import RestClient
from app.schemas.payloads import (
    ConfigRequestPayload,
    EnvironmentPayload,
    HeartbeatPayload,
    IntakePayload,
    StockPayload,
)


@dataclass(frozen=True)
class EventRoute:
    schema: Type[BaseModel]
    endpoint_template: str


EVENT_ROUTES: dict[str, EventRoute] = {
    "environment": EventRoute(EnvironmentPayload, "/api/v1/device/internal/{device_id}/environment-readings"),
    "intake": EventRoute(IntakePayload, "/api/v1/device/internal/{device_id}/intake-events"),
    "stock": EventRoute(StockPayload, "/api/v1/device/internal/{device_id}/stock-events"),
    "heartbeat": EventRoute(HeartbeatPayload, "/api/v1/device/internal/{device_id}/heartbeats"),
}
logger = logging.getLogger(__name__)


class SyncService:
    def __init__(self, rest_client: RestClient, device_keys: dict[str, str]):
        self.rest_client = rest_client
        self.device_keys = device_keys

    def parse_topic(self, topic: str) -> tuple[str, str]:
        parts = topic.split("/")
        if len(parts) < 4 or parts[0] != "dosys" or parts[1] != "devices" or not parts[2]:
            raise ValueError(f"Unexpected topic format: {topic}")

        device_id = parts[2]
        if len(parts) >= 5 and parts[3] == "config" and parts[4] == "request":
            event_type = "config_request"
        elif parts[3] in {"environment", "intake", "stock", "heartbeat"}:
            event_type = parts[3]
        else:
            raise ValueError(f"Unsupported topic format: {topic}")
        return device_id, event_type

    def optional_device_key(self, device_id: str) -> str | None:
        return self.device_keys.get(device_id)

    def _send_to_rest(self, event: ReceivedMqttEvent, payload: dict[str, Any], event_type: str) -> None:
        route = EVENT_ROUTES[event_type]
        device_key = self.optional_device_key(event.device_id)
        endpoint = route.endpoint_template.format(device_id=event.device_id)

        try:
            response = self.rest_client.post_internal_event(endpoint, payload, device_key)
            logger.info("REST sync endpoint=%s status=%s response=%s", endpoint, response.status_code, response.text[:300])
            if 200 <= response.status_code < 300:
                repositories.mark_event_status(event, "SYNCED")
                repositories.create_sync_attempt(event, endpoint, "SUCCESS", response.status_code, None)
            else:
                repositories.mark_event_status(event, "FAILED")
                repositories.create_sync_attempt(
                    event,
                    endpoint,
                    "FAILED",
                    response.status_code,
                    response.text[:1000],
                )
        except Exception as exc:  # pylint: disable=broad-except
            repositories.mark_event_status(event, "FAILED")
            repositories.create_sync_attempt(event, endpoint, "FAILED", None, str(exc))

    def _normalize_timestamps(self, payload: dict[str, Any], event_type: str) -> dict[str, Any]:
        fields_by_type = {
            "environment": ["recordedAt"],
            "intake": ["scheduledAt", "confirmedAt"],
            "stock": ["recordedAt"],
            "heartbeat": ["recordedAt", "rtcTime"],
        }
        fields = fields_by_type.get(event_type, [])
        normalized = dict(payload)
        for field in fields:
            value = normalized.get(field)
            if isinstance(value, str) and value:
                # REST expects OffsetDateTime. If timezone is missing, force UTC.
                if "Z" not in value and "+" not in value[10:] and "-" not in value[10:]:
                    normalized[field] = value + "Z"
        return normalized

    def save_and_sync_event(self, topic: str, payload: dict[str, Any]) -> ReceivedMqttEvent:
        device_id, event_type = self.parse_topic(topic)
        if event_type not in EVENT_ROUTES:
            raise ValueError(f"Unsupported event type for sync: {event_type}")

        route = EVENT_ROUTES[event_type]

        try:
            validated_model = route.schema.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(f"Payload validation failed for event={event_type}: {exc}") from exc

        normalized_payload = json.loads(validated_model.model_dump_json())
        normalized_payload = self._normalize_timestamps(normalized_payload, event_type)
        event = repositories.create_received_event(device_id=device_id, topic=topic, payload=normalized_payload)
        self._send_to_rest(event, normalized_payload, event_type)
        return event

    def retry_failed_events(self, limit: int = 100) -> dict[str, int]:
        failed_events = repositories.get_failed_events(limit=limit)
        retried = 0
        synced = 0

        for event in failed_events:
            retried += 1
            try:
                _, event_type = self.parse_topic(event.topic)
                payload = json.loads(event.payload_json)
                payload = self._normalize_timestamps(payload, event_type)
                self._send_to_rest(event, payload, event_type)
                if event.status == "SYNCED":
                    synced += 1
            except Exception:
                continue

        return {"retried": retried, "synced": synced}

    def validate_config_request(self, payload: dict[str, Any]) -> ConfigRequestPayload:
        return ConfigRequestPayload.model_validate(payload)
