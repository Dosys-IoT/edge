from datetime import datetime

from peewee import (
    AutoField,
    CharField,
    DateTimeField,
    ForeignKeyField,
    IntegerField,
    Model,
    TextField,
)

from app.persistence.database import db


class BaseModel(Model):
    class Meta:
        database = db


class ReceivedMqttEvent(BaseModel):
    id = AutoField()
    device_id = CharField(max_length=64, index=True)
    topic = CharField(max_length=255)
    payload_json = TextField()
    received_at = DateTimeField(default=datetime.utcnow)
    status = CharField(max_length=16, default="RECEIVED", index=True)

    class Meta:
        table_name = "received_mqtt_events"


class SyncAttempt(BaseModel):
    id = AutoField()
    event = ForeignKeyField(ReceivedMqttEvent, backref="sync_attempts", on_delete="CASCADE")
    target_endpoint = CharField(max_length=255)
    status = CharField(max_length=16)
    response_code = IntegerField(null=True)
    error_message = TextField(null=True)
    attempted_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = "sync_attempts"


class CachedRuntimeConfig(BaseModel):
    id = AutoField()
    device_id = CharField(max_length=64, index=True)
    config_version = IntegerField(default=0)
    payload_json = TextField()
    cached_at = DateTimeField(default=datetime.utcnow)

    class Meta:
        table_name = "cached_runtime_configs"
