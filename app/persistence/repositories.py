import json
from typing import Any, Optional

from app.persistence.models import CachedRuntimeConfig, ReceivedMqttEvent, SyncAttempt


def create_tables() -> None:
    ReceivedMqttEvent.create_table(safe=True)
    SyncAttempt.create_table(safe=True)
    CachedRuntimeConfig.create_table(safe=True)


def create_received_event(device_id: str, topic: str, payload: dict[str, Any]) -> ReceivedMqttEvent:
    return ReceivedMqttEvent.create(
        device_id=device_id,
        topic=topic,
        payload_json=json.dumps(payload),
        status="RECEIVED",
    )


def mark_event_status(event: ReceivedMqttEvent, status: str) -> None:
    event.status = status
    event.save()


def create_sync_attempt(
    event: ReceivedMqttEvent,
    target_endpoint: str,
    status: str,
    response_code: Optional[int],
    error_message: Optional[str],
) -> SyncAttempt:
    return SyncAttempt.create(
        event=event,
        target_endpoint=target_endpoint,
        status=status,
        response_code=response_code,
        error_message=error_message,
    )


def get_failed_events(limit: int = 100) -> list[ReceivedMqttEvent]:
    query = (
        ReceivedMqttEvent.select()
        .where(ReceivedMqttEvent.status == "FAILED")
        .order_by(ReceivedMqttEvent.received_at.asc())
        .limit(limit)
    )
    return list(query)


def cache_runtime_config(device_id: str, config_version: int, payload: dict[str, Any]) -> CachedRuntimeConfig:
    return CachedRuntimeConfig.create(
        device_id=device_id,
        config_version=config_version,
        payload_json=json.dumps(payload),
    )


def get_latest_cached_runtime_config(device_id: str) -> Optional[CachedRuntimeConfig]:
    query = (
        CachedRuntimeConfig.select()
        .where(CachedRuntimeConfig.device_id == device_id)
        .order_by(CachedRuntimeConfig.cached_at.desc())
    )
    return query.first()


def get_recent_received_events(limit: int = 10) -> list[ReceivedMqttEvent]:
    query = (
        ReceivedMqttEvent.select()
        .order_by(ReceivedMqttEvent.received_at.desc())
        .limit(limit)
    )
    return list(query)


def get_recent_sync_attempts(limit: int = 10) -> list[SyncAttempt]:
    query = (
        SyncAttempt.select()
        .order_by(SyncAttempt.attempted_at.desc())
        .limit(limit)
    )
    return list(query)
