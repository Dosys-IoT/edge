from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Literal

from pydantic import BaseModel, Field, field_validator


LIMA_TZ = ZoneInfo("America/Lima")


def _fallback_local_datetime() -> datetime:
    return datetime.now(LIMA_TZ).replace(tzinfo=None, microsecond=0)


def _coerce_local_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(LIMA_TZ).replace(tzinfo=None)
        return value.replace(microsecond=0)
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return _fallback_local_datetime()
        normalized = candidate.replace("Z", "+00:00") if candidate.endswith("Z") else candidate
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return _fallback_local_datetime()
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(LIMA_TZ).replace(tzinfo=None)
        return parsed.replace(microsecond=0)
    return _fallback_local_datetime()


class EnvironmentPayload(BaseModel):
    deviceId: str | None = None
    eventId: str | None = None
    temperature: float
    humidity: float
    recordedAt: datetime
    firmwareVersion: str | None = None

    @field_validator("recordedAt", mode="before")
    @classmethod
    def normalize_recorded_at(cls, value):
        return _coerce_local_datetime(value)


class IntakePayload(BaseModel):
    deviceId: str | None = None
    eventId: str | None = None
    scheduleId: str
    containerNumber: int = Field(ge=1, le=5)
    scheduledAt: datetime
    confirmedAt: datetime | None = None
    status: Literal["TAKEN", "MISSED", "SNOOZED", "SKIPPED"]
    source: Literal["PHYSICAL_BUTTON"] | None = None
    buttonPin: int | None = None

    @field_validator("scheduledAt", "confirmedAt", mode="before")
    @classmethod
    def normalize_intake_datetimes(cls, value):
        return _coerce_local_datetime(value)


class StockPayload(BaseModel):
    deviceId: str | None = None
    eventId: str | None = None
    containerNumber: int = Field(ge=1, le=5)
    remainingPills: int = Field(ge=0)
    reportedAt: datetime | None = None
    recordedAt: datetime | None = None
    reason: str | None = None

    @field_validator("reportedAt", "recordedAt", mode="before")
    @classmethod
    def normalize_stock_datetimes(cls, value):
        return _coerce_local_datetime(value)


class HeartbeatPayload(BaseModel):
    deviceId: str | None = None
    eventId: str | None = None
    rtcTime: datetime | None = None
    recordedAt: datetime | None = None
    wifiConnected: bool
    mqttConnected: bool | None = None
    rtcOk: bool | None = None
    sht3xOk: bool | None = None
    dfPlayerOk: bool | None = None
    sdCardOk: bool | None = None
    switchOk: bool | None = None
    buttonPin: int | None = None
    freeHeap: int | None = None
    rssi: int | None = None
    deviceStatus: Literal["ONLINE", "OFFLINE", "ERROR"]
    firmwareVersion: str | None = None

    @field_validator("rtcTime", "recordedAt", mode="before")
    @classmethod
    def normalize_heartbeat_datetimes(cls, value):
        return _coerce_local_datetime(value)


class ConfigRequestPayload(BaseModel):
    requestId: str
    deviceId: str | None = None
    firmwareVersion: str | None = None
    hardwareVersion: str | None = None
    rtcTime: datetime | None = None
    reason: str | None = None
    requestedAt: datetime | None = None

    @field_validator("rtcTime", "requestedAt", mode="before")
    @classmethod
    def normalize_config_datetimes(cls, value):
        return _coerce_local_datetime(value)
