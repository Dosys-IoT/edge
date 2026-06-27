from app.mqtt.client import MqttClientManager
from app.mqtt.topics import commands_topic


class CommandService:
    def __init__(self, mqtt_manager: MqttClientManager):
        self.mqtt_manager = mqtt_manager

    def publish_audio_test(self, device_id: str, command_id: str) -> dict[str, object]:
        payload = {
            "commandId": command_id,
            "command": "AUDIO_TEST",
            "track": 1,
        }
        self.mqtt_manager.publish_json(commands_topic(device_id), payload)
        return payload

    def publish_led_test(self, device_id: str, command_id: str) -> dict[str, object]:
        payload = {
            "commandId": command_id,
            "command": "LED_TEST",
        }
        self.mqtt_manager.publish_json(commands_topic(device_id), payload)
        return payload

    def publish_status_request(self, device_id: str, command_id: str) -> dict[str, object]:
        payload = {
            "commandId": command_id,
            "command": "STATUS_REQUEST",
        }
        self.mqtt_manager.publish_json(commands_topic(device_id), payload)
        return payload

    def publish_config_sync(self, device_id: str, command_id: str) -> dict[str, object]:
        payload = {
            "commandId": command_id,
            "command": "CONFIG_SYNC",
        }
        self.mqtt_manager.publish_json(commands_topic(device_id), payload)
        return payload
