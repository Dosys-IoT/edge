from uuid import uuid4

from flask import Blueprint, jsonify, request
from app.persistence import repositories


def create_http_blueprint(sync_service, config_service, mqtt_manager, command_service):
    bp = Blueprint("edge_api", __name__)

    @bp.get("/edge/v1/health")
    def health():
        return jsonify({"status": "UP"}), 200

    @bp.get("/edge/v1/mqtt/status")
    def mqtt_status():
        return jsonify(mqtt_manager.status()), 200

    @bp.post("/edge/v1/sync/retry")
    def retry_sync():
        result = sync_service.retry_failed_events(limit=100)
        return jsonify(result), 200

    @bp.get("/edge/v1/devices/<device_id>/cached-config")
    def get_cached_config(device_id: str):
        cached = config_service.get_cached_config(device_id)
        if cached is None:
            return jsonify({"message": "No cached config found"}), 404
        return jsonify(cached), 200

    @bp.get("/edge/v1/diagnostics/rest/runtime-config/<device_id>")
    def diagnostics_runtime_config(device_id: str):
        try:
            response = config_service.rest_client.get_runtime_config(device_id)
            try:
                body = response.json() if response.text else None
            except Exception:  # pylint: disable=broad-except
                body = response.text
            return jsonify({"statusCode": response.status_code, "body": body}), 200
        except Exception as exc:  # pylint: disable=broad-except
            return jsonify({"statusCode": 500, "error": str(exc)}), 500

    @bp.get("/edge/v1/diagnostics/events/recent")
    def diagnostics_recent_events():
        recent_events = [
            {
                "id": event.id,
                "deviceId": event.device_id,
                "topic": event.topic,
                "status": event.status,
                "receivedAt": event.received_at.isoformat(),
                "payloadJson": event.payload_json,
            }
            for event in repositories.get_recent_received_events(10)
        ]
        recent_attempts = [
            {
                "id": attempt.id,
                "eventId": attempt.event_id,
                "targetEndpoint": attempt.target_endpoint,
                "status": attempt.status,
                "responseCode": attempt.response_code,
                "errorMessage": attempt.error_message,
                "attemptedAt": attempt.attempted_at.isoformat(),
            }
            for attempt in repositories.get_recent_sync_attempts(10)
        ]
        return jsonify({"recentReceivedMqttEvents": recent_events, "recentSyncAttempts": recent_attempts}), 200

    @bp.post("/edge/v1/devices/<device_id>/commands/audio-test")
    def audio_test_command(device_id: str):
        command_id = (request.get_json(silent=True) or {}).get("commandId") or str(uuid4())
        try:
            payload = command_service.publish_audio_test(device_id, command_id)
            return jsonify({"topic": f"dosys/devices/{device_id}/commands", "payload": payload}), 200
        except RuntimeError as exc:
            return jsonify({"status": "MQTT_UNAVAILABLE", "message": str(exc)}), 503

    @bp.post("/edge/v1/devices/<device_id>/commands/led-test")
    def led_test_command(device_id: str):
        command_id = (request.get_json(silent=True) or {}).get("commandId") or str(uuid4())
        try:
            payload = command_service.publish_led_test(device_id, command_id)
            return jsonify({"topic": f"dosys/devices/{device_id}/commands", "payload": payload}), 200
        except RuntimeError as exc:
            return jsonify({"status": "MQTT_UNAVAILABLE", "message": str(exc)}), 503

    @bp.post("/edge/v1/devices/<device_id>/commands/status-request")
    def status_request_command(device_id: str):
        command_id = (request.get_json(silent=True) or {}).get("commandId") or str(uuid4())
        try:
            payload = command_service.publish_status_request(device_id, command_id)
            return jsonify({"topic": f"dosys/devices/{device_id}/commands", "payload": payload}), 200
        except RuntimeError as exc:
            return jsonify({"status": "MQTT_UNAVAILABLE", "message": str(exc)}), 503

    @bp.post("/edge/v1/devices/<device_id>/commands/config-sync")
    def config_sync_command(device_id: str):
        command_id = (request.get_json(silent=True) or {}).get("commandId") or str(uuid4())
        try:
            payload = command_service.publish_config_sync(device_id, command_id)
            return jsonify({"topic": f"dosys/devices/{device_id}/commands", "payload": payload}), 200
        except RuntimeError as exc:
            return jsonify({"status": "MQTT_UNAVAILABLE", "message": str(exc)}), 503

    return bp
