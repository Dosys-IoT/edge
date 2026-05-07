from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class EnvironmentPayload(BaseModel):
    temperature: float
    humidity: float
    recordedAt: datetime


class IntakePayload(BaseModel):
    scheduleId: str
    containerNumber: int = Field(ge=1, le=5)
    scheduledAt: datetime
    confirmedAt: datetime
    status: Literal["TAKEN", "MISSED", "SKIPPED"]


class StockPayload(BaseModel):
    containerNumber: int = Field(ge=1, le=5)
    remainingPills: int = Field(ge=0)
    recordedAt: datetime


class HeartbeatPayload(BaseModel):
    recordedAt: datetime
    rtcTime: datetime
    wifiConnected: bool
    deviceStatus: Literal["ONLINE", "OFFLINE", "ERROR"]


class ConfigRequestPayload(BaseModel):
    requestId: str
    requestedAt: datetime
