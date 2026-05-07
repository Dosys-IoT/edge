import json
import os
from dataclasses import dataclass
from typing import Dict

from dotenv import load_dotenv


load_dotenv()


def _to_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    mqtt_host: str
    mqtt_port: int
    mqtt_username: str
    mqtt_password: str
    mqtt_tls: bool
    mqtt_client_id: str
    rest_api_base_url: str
    edge_service_key: str
    device_keys: Dict[str, str]
    edge_sqlite_path: str
    edge_http_port: int


class ConfigError(Exception):
    pass


def load_settings() -> Settings:
    mqtt_host = os.getenv("MQTT_HOST", "").strip()
    mqtt_username = os.getenv("MQTT_USERNAME", "").strip()
    mqtt_password = os.getenv("MQTT_PASSWORD", "").strip()
    rest_api_base_url = os.getenv("REST_API_BASE_URL", "").strip().rstrip("/")
    mqtt_client_id = os.getenv("MQTT_CLIENT_ID", "dosys-edge-api").strip()
    sqlite_path = os.getenv("EDGE_SQLITE_PATH", "./edge.db").strip()
    edge_service_key = os.getenv("EDGE_SERVICE_KEY", "").strip()

    if not mqtt_host:
        raise ConfigError("MQTT_HOST is required")
    if not rest_api_base_url:
        raise ConfigError("REST_API_BASE_URL is required")
    if not edge_service_key:
        raise ConfigError("EDGE_SERVICE_KEY is required")

    try:
        mqtt_port = int(os.getenv("MQTT_PORT", "8883"))
    except ValueError as exc:
        raise ConfigError("MQTT_PORT must be an integer") from exc

    edge_http_port_raw = os.getenv("EDGE_HTTP_PORT", "").strip()
    if not edge_http_port_raw:
        edge_http_port_raw = os.getenv("PORT", "8000").strip()
    try:
        edge_http_port = int(edge_http_port_raw)
    except ValueError as exc:
        raise ConfigError("EDGE_HTTP_PORT/PORT must be an integer") from exc

    raw_device_keys = os.getenv("DEVICE_KEYS_JSON", "{}").strip()
    try:
        parsed_keys = json.loads(raw_device_keys)
    except json.JSONDecodeError as exc:
        raise ConfigError("DEVICE_KEYS_JSON must be valid JSON") from exc

    if not isinstance(parsed_keys, dict):
        raise ConfigError("DEVICE_KEYS_JSON must be a JSON object")

    normalized_keys: Dict[str, str] = {}
    for device_id, key_value in parsed_keys.items():
        if not isinstance(device_id, str) or not isinstance(key_value, str):
            raise ConfigError("DEVICE_KEYS_JSON keys and values must be strings")
        normalized_keys[device_id.strip()] = key_value.strip()

    return Settings(
        mqtt_host=mqtt_host,
        mqtt_port=mqtt_port,
        mqtt_username=mqtt_username,
        mqtt_password=mqtt_password,
        mqtt_tls=_to_bool(os.getenv("MQTT_TLS"), default=True),
        mqtt_client_id=mqtt_client_id,
        rest_api_base_url=rest_api_base_url,
        edge_service_key=edge_service_key,
        device_keys=normalized_keys,
        edge_sqlite_path=sqlite_path,
        edge_http_port=edge_http_port,
    )
