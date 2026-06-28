# Dosys Edge API

Bridge HTTP/MQTT between the physical ESP32 and the Spring Boot REST API.

## Architecture

ESP32 -> HiveMQ Cloud MQTT -> Edge Service -> REST API -> Supabase PostgreSQL

HiveMQ is configured only in Edge and ESP32, not in REST.

## Environment

```env
MQTT_HOST=d58a7ac7288e4ba5955e6bd6baea64dd.s1.eu.hivemq.cloud
MQTT_PORT=8883
MQTT_USERNAME=replace-with-real-hivemq-username
MQTT_PASSWORD=replace-with-real-hivemq-password
MQTT_TLS=true
MQTT_CLIENT_ID=dosys-edge-api

REST_API_BASE_URL=https://dosys-backend-149855215912.us-central1.run.app
EDGE_SERVICE_KEY=replace-with-edge-service-key

DEVICE_KEYS_JSON={}

EDGE_SQLITE_PATH=./edge.db
EDGE_HTTP_PORT=8000
```

`EDGE_SERVICE_KEY` must match the value in the REST API environment.

## Run

```powershell
cd "C:\Users\VR\Desktop\Dosys Code TF\edge"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m app.main
```

## HTTP Endpoints

- `GET /edge/v1/health`
- `GET /edge/v1/mqtt/status`
- `POST /edge/v1/sync/retry`
- `GET /edge/v1/devices/{deviceId}/cached-config`
- `GET /edge/v1/diagnostics/rest/runtime-config/{deviceId}`
- `GET /edge/v1/diagnostics/events/recent`
- `POST /edge/v1/devices/{deviceId}/commands/audio-test`
- `POST /edge/v1/devices/{deviceId}/commands/led-test`
- `POST /edge/v1/devices/{deviceId}/commands/status-request`
- `POST /edge/v1/devices/{deviceId}/commands/config-sync`

These endpoints include CORS for local frontend development from `http://localhost:3000`
and `http://127.0.0.1:3000`.

`GET /edge/v1/devices/{deviceId}/cached-config` returns `200` with:

```json
{ "deviceId": "1", "available": false, "config": null }
```

when nothing is cached yet.

## MQTT Topics

Subscriptions:
- `dosys/devices/+/environment`
- `dosys/devices/+/heartbeat`
- `dosys/devices/+/intake`
- `dosys/devices/+/stock`
- `dosys/devices/+/config/request`

Publications:
- `dosys/devices/{deviceId}/config/response`
- `dosys/devices/{deviceId}/commands`

## PowerShell Examples

Runtime config:
```powershell
Invoke-RestMethod -Method Get `
  -Uri "http://localhost:8000/edge/v1/devices/1/cached-config"

Invoke-RestMethod -Method Get `
  -Uri "http://localhost:8000/edge/v1/diagnostics/rest/runtime-config/1"
```

Environment payload:
```powershell
@{
  eventId = "env-1"
  deviceId = "1"
  temperature = 27.8
  humidity = 60.2
  recordedAt = "2026-06-27T12:00:00"
  firmwareVersion = "1.0.0"
} | ConvertTo-Json
```

Heartbeat payload:
```powershell
@{
  eventId = "hb-1"
  deviceId = "1"
  rtcTime = "2026-06-27T12:00:00"
  wifiConnected = $true
  mqttConnected = $true
  rtcOk = $true
  sht3xOk = $true
  dfPlayerOk = $true
  sdCardOk = $true
  switchOk = $true
  buttonPin = 15
  freeHeap = 180000
  rssi = -55
  deviceStatus = "ONLINE"
  firmwareVersion = "1.0.0"
} | ConvertTo-Json
```

Intake payload:
```powershell
@{
  eventId = "intake-1"
  deviceId = "1"
  scheduleId = "1"
  containerNumber = 1
  scheduledAt = "2026-06-27T08:00:00"
  confirmedAt = "2026-06-27T08:02:15"
  status = "TAKEN"
  source = "PHYSICAL_BUTTON"
  buttonPin = 15
} | ConvertTo-Json
```

Stock payload:
```powershell
@{
  eventId = "stock-1"
  deviceId = "1"
  containerNumber = 1
  remainingPills = 19
  reportedAt = "2026-06-27T08:02:20"
  reason = "INTAKE_CONFIRMED"
} | ConvertTo-Json
```

Config request payload:
```powershell
@{
  requestId = "req-1"
  deviceId = "1"
  firmwareVersion = "1.0.0"
  hardwareVersion = "esp32-dosys-v1"
  rtcTime = "2026-06-27T12:00:00"
  reason = "BOOT"
} | ConvertTo-Json
```

MQTT status:
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/edge/v1/mqtt/status"
```

Diagnostics:
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/edge/v1/diagnostics/events/recent"
```

Commands:
```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/edge/v1/devices/1/commands/audio-test"
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/edge/v1/devices/1/commands/led-test"
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/edge/v1/devices/1/commands/status-request"
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/edge/v1/devices/1/commands/config-sync"
```

## Topics Mapping

Inbound:
- `dosys/devices/+/environment`
- `dosys/devices/+/heartbeat`
- `dosys/devices/+/intake`
- `dosys/devices/+/stock`
- `dosys/devices/+/config/request`

Outbound:
- `dosys/devices/{deviceId}/config/response`
- `dosys/devices/{deviceId}/commands`

## Render Deploy

This repo includes `render.yaml`.

1. Create a new Web Service in Render from this repo/folder.
2. Confirm:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python -m app.main`
3. Configure variables:
   - `MQTT_HOST`
   - `MQTT_PORT=8883`
   - `MQTT_USERNAME`
   - `MQTT_PASSWORD`
   - `MQTT_TLS=true`
   - `MQTT_CLIENT_ID=dosys-edge-api`
   - `REST_API_BASE_URL`
   - `EDGE_SERVICE_KEY`
   - `DEVICE_KEYS_JSON={}`
   - `EDGE_SQLITE_PATH=./edge.db`
4. Render injects `PORT`; the service already supports it.

## Security

- Do not commit real secrets.
- Keep `MQTT_PASSWORD` and `EDGE_SERVICE_KEY` only in local or deploy environment variables.
