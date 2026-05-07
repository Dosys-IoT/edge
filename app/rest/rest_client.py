from typing import Any

import requests


class RestClient:
    def __init__(self, base_url: str, edge_service_key: str, timeout_seconds: int = 10):
        self.base_url = base_url.rstrip("/")
        self.edge_service_key = edge_service_key
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()

    def post_internal_event(self, endpoint_path: str, payload: dict[str, Any], device_key: str | None = None) -> requests.Response:
        url = f"{self.base_url}{endpoint_path}"
        headers = {"X-Edge-Service-Key": self.edge_service_key, "Content-Type": "application/json"}
        if device_key:
            headers["X-Device-Key"] = device_key
        return self.session.post(url, json=payload, headers=headers, timeout=self.timeout_seconds)

    def get_runtime_config(self, device_id: str, device_key: str | None = None) -> requests.Response:
        endpoint_path = f"/api/v1/device/internal/{device_id}/runtime-config"
        url = f"{self.base_url}{endpoint_path}"
        headers = {"X-Edge-Service-Key": self.edge_service_key}
        if device_key:
            headers["X-Device-Key"] = device_key
        return self.session.get(url, headers=headers, timeout=self.timeout_seconds)
