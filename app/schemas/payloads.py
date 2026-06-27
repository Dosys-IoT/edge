from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class EnvironmentPayload(BaseModel):
    deviceId: str | None = None
    eventId: str | None = None
    temperature: float
    humidity: float
    recordedAt: datetime
    firmwareVersion: str | None = None


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


class StockPayload(BaseModel):
    deviceId: str | None = None
    eventId: str | None = None
    containerNumber: int = Field(ge=1, le=5)
    remainingPills: int = Field(ge=0)
    reportedAt: datetime | None = None
    recordedAt: datetime | None = None
    reason: str | None = None


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


class ConfigRequestPayload(BaseModel):
    requestId: str
    deviceId: str | None = None
    firmwareVersion: str | None = None
    hardwareVersion: str | None = None
    rtcTime: datetime | None = None
    reason: str | None = None
    requestedAt: datetime | None = None
