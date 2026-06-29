import atexit
import logging
import re

from flask import Flask
from flask_cors import CORS

from app.config import ConfigError, load_settings
from app.interfaces.http_routes import create_http_blueprint
from app.mqtt.client import MqttClientManager
from app.mqtt.handlers import MqttMessageHandler
from app.persistence.database import close_database, connect_database, init_database
from app.persistence.repositories import create_tables
from app.rest.rest_client import RestClient
from app.services.command_service import CommandService
from app.services.config_service import ConfigService
from app.services.sync_service import SyncService


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> tuple[Flask, object, object, object]:
    settings = load_settings()

    init_database(settings.edge_sqlite_path)
    connect_database()
    create_tables()

    rest_client = RestClient(base_url=settings.rest_api_base_url, edge_service_key=settings.edge_service_key)
    sync_service = SyncService(rest_client=rest_client, device_keys=settings.device_keys)
    config_service = ConfigService(rest_client=rest_client)

    message_handler = MqttMessageHandler(sync_service=sync_service, config_service=config_service)
    mqtt_manager = MqttClientManager(settings=settings, message_handler=message_handler)
    command_service = CommandService(mqtt_manager=mqtt_manager)

    app = Flask(__name__)
    CORS(
        app,
        resources={r"/edge/*": {"origins": [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://dosys-edge-149855215912.us-central1.run.app",
            "https://frontend-web-jet-seven.vercel.app",
            re.compile(r"^https://.*\.vercel\.app$"),
        ]}},
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
        methods=["GET", "POST", "OPTIONS"],
    )
    app.register_blueprint(create_http_blueprint(sync_service, config_service, mqtt_manager, command_service))

    return app, settings, mqtt_manager, rest_client


def main() -> None:
    try:
        app, settings, mqtt_manager, _rest_client = create_app()
    except ConfigError as exc:
        logger.error("Configuration error: %s", exc)
        raise SystemExit(1) from exc

    atexit.register(close_database)
    atexit.register(mqtt_manager.stop)

    logger.info("Loaded MQTT_HOST=%s MQTT_PORT=%s MQTT_TLS=%s MQTT_CLIENT_ID=%s",
                settings.mqtt_host, settings.mqtt_port, settings.mqtt_tls, settings.mqtt_client_id)
    logger.info("Loaded REST_API_BASE_URL=%s EDGE_SERVICE_KEY loaded=%s",
                settings.rest_api_base_url, bool(settings.edge_service_key))

    mqtt_manager.start()
    logger.info("Starting Edge API HTTP server on port %s", settings.edge_http_port)
    app.run(host="0.0.0.0", port=settings.edge_http_port, debug=False)


if __name__ == "__main__":
    main()
