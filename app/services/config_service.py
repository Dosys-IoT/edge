import json
from datetime import datetime, timezone
from typing import Any

from app.persistence import repositories
from app.rest.rest_client import RestClient


class ConfigService:
    def __init__(self, rest_client: RestClient):
        self.rest_client = rest_client

    def fetch_runtime_config(self, device_id: str) -> dict[str, Any]:
        response = self.rest_client.get_runtime_config(device_id)
        if not (200 <= response.status_code < 300):
            raise RuntimeError(f"Runtime config request failed ({response.status_code}): {response.text[:500]}")

        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("Runtime config response is not a JSON object")

        return payload

    def cache_runtime_config(self, device_id: str, payload: dict[str, Any]) -> None:
        version = int(payload.get("configVersion", 0))
        repositories.cache_runtime_config(device_id=device_id, config_version=version, payload=payload)

    def build_config_response(self, device_id: str, request_id: str, runtime_config: dict[str, Any]) -> dict[str, Any]:
        response = dict(runtime_config)
        response["requestId"] = request_id
        response.setdefault("deviceId", device_id)
        response.setdefault("configVersion", 1)
        response.setdefault("serverTime", datetime.now(timezone.utc).isoformat())
        return response

    def get_cached_config(self, device_id: str) -> dict[str, Any] | None:
        cached = repositories.get_latest_cached_runtime_config(device_id)
        if not cached:
            return None

        return {
            "deviceId": cached.device_id,
            "available": True,
            "config": json.loads(cached.payload_json),
            "cachedAt": cached.cached_at.isoformat(),
        }
