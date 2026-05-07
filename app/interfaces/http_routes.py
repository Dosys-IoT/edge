from flask import Blueprint, jsonify
from app.persistence import repositories


def create_http_blueprint(sync_service, config_service, mqtt_manager):
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

    return bp
