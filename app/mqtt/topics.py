ENVIRONMENT = "dosys/devices/+/environment"
INTAKE = "dosys/devices/+/intake"
STOCK = "dosys/devices/+/stock"
HEARTBEAT = "dosys/devices/+/heartbeat"
CONFIG_REQUEST = "dosys/devices/+/config/request"

SUBSCRIPTIONS = [
    (ENVIRONMENT, 1),
    (INTAKE, 1),
    (STOCK, 1),
    (HEARTBEAT, 1),
    (CONFIG_REQUEST, 1),
]


def config_response_topic(device_id: str) -> str:
    return f"dosys/devices/{device_id}/config/response"
