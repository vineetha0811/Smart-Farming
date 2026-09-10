# Wokwi ESP32 Integration Setup Guide

This guide explains how the **Wokwi virtual ESP32** sends live sensor data to the Flask application.

```
Wokwi ESP32 (virtual sensors)
        ↓  HTTP POST (JSON)
Flask API  POST /api/sensor-data
        ↓  validation → SQLite → irrigation/risk logic → recommendation
Dashboard  (auto-updating LIVE FARM SENSOR DATA section)
```

---

## 1. New / Updated Files

| File | Purpose |
|------|---------|
| `app.py` | Added `POST /api/sensor-data`, `GET /api/latest-sensor-data`, `/iot-simulation` page, CORS headers, Render `PORT` support |
| `database.db` | `sensor_readings` table upgraded with `drought_risk`, `heat_risk`, `recommendation`, `source` columns; `user_id` now optional (Wokwi data has no login) |
| `wokwi/smart_farming_esp32.ino` | The Arduino/ESP32 sketch that runs inside Wokwi |
| `wokwi/diagram.json` | Wokwi circuit: ESP32 + DHT22 + 2 potentiometers |
| `templates/dashboard.html` | New **LIVE FARM SENSOR DATA** section |
| `templates/iot_simulation.html` | New **Virtual Farm / IoT Simulation** page |
| `static/js/script.js` | Polls `GET /api/latest-sensor-data` every 5 seconds |

---

## 2. Required Wokwi Components & Connections

Open the Wokwi project and add these parts (the `diagram.json` already wires them):

| Part | Used for | Wire connections |
|------|----------|------------------|
| ESP32 DevKit V1 | The microcontroller | — |
| DHT22 | Temperature + humidity | VCC→3V3, GND→GND, OUT→GPIO15 |
| Potentiometer 1 | Soil moisture (0–100%) | VCC→5V, GND→GND, W→GPIO36 |
| Potentiometer 2 | Rainfall (0–30mm) | VCC→5V, GND→GND, W→GPIO39 |

> For a live demo, turn the **soil moisture knob** during the presentation
> and watch the dashboard change within ~10 seconds.

---

## 3. API Endpoint Documentation

### POST /api/sensor-data
Called by the ESP32. No login required.

Request body (JSON):
```json
{
  "soil_moisture": 28,
  "temperature": 35,
  "humidity": 48,
  "rainfall": 2
}
```

What the server does:
1. Validates the values (moisture 0–100, temp -10–55, humidity 0–100, rainfall 0–100).
2. Inserts a new row into `sensor_readings` (source = `wokwi`).
3. Runs irrigation decision logic + drought/heat risk analysis.
4. Builds a farmer-friendly recommendation.
5. Returns JSON.

Response (success):
```json
{
  "success": true,
  "soil_moisture": 28,
  "temperature": 35,
  "humidity": 48,
  "rainfall": 2,
  "irrigation_status": "Recommended",
  "drought_risk": "MODERATE",
  "heat_risk": "LOW",
  "recommendation": "Irrigation is recommended in the near future... Drought risk is moderate..."
}
```

Response (invalid input):
```json
{ "success": false, "error": "Invalid sensor values" }
```
(status code 400)

### GET /api/latest-sensor-data
Returns the newest Wokwi reading + live connection status. Used by the dashboard.

```json
{
  "success": true,
  "has_data": true,
  "connected": true,
  "seconds_ago": 3,
  "last_updated": "2026-09-10 09:30:00",
  "soil_moisture": 28,
  "temperature": 35,
  "humidity": 48,
  "rainfall": 2,
  "irrigation_status": "Recommended",
  "drought_risk": "MODERATE",
  "heat_risk": "LOW",
  "recommendation": "..."
}
```

**Connection rule:** if the latest reading arrived within the last 30 seconds
→ `connected: true` (🟢). Otherwise → `connected: false` (🔴). If no reading has
ever arrived → `has_data: false`.

---

## 4. Render Deployment Requirements

1. Push the project to GitHub.
2. On [render.com](https://render.com) → **New → Web Service** → connect the repo.
3. Set:
   - **Name:** `smart-farm-assistant`
   - **Environment:** Python 3
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `python app.py`
4. Deploy.

The code already reads Render's `PORT` environment variable and binds to
`0.0.0.0`, so no extra configuration is required.

> Optional (better for production): add `gunicorn==23.0.0` to a
> `requirements-render.txt` and use start command `gunicorn app:app`.
> The built-in server is fine for a student demo.

---

## 5. Exact Steps: Connect Wokwi to the Deployed Render URL

1. Open the project in Wokwi (**Wokwi → New Project**, or load the files in
   the `wokwi/` folder).
2. Open `smart_farming_esp32.ino` and find this line near the top:
   ```cpp
   #define SERVER_URL "https://YOUR-RENDER-APP.onrender.com/api/sensor-data"
   ```
3. Replace `YOUR-RENDER-APP` with your real app name:
   ```cpp
   #define SERVER_URL "https://smart-farm-assistant.onrender.com/api/sensor-data"
   ```
4. Click **▶ Start the Simulation**.
5. Watch the **Serial Monitor** (9600 baud). It prints each reading, the HTTP
   POST, and the server's analysis response.
6. Open your deployed web app → **Dashboard** → the LIVE FARM SENSOR DATA
   section shows the Wokwi values and updates every 5 seconds.

---

## 6. Troubleshooting

| Problem | Likely cause | Fix |
|---------|--------------|-----|
| Serial monitor shows HTTP error -1 / -2 | ESP32 cannot reach the URL | Check `SERVER_URL` is the correct Render HTTPS URL; confirm the app is deployed and not paused (free tier sleeps) |
| `Could not begin http` | Bad URL / offline server | Re-check the URL; temporarily open the URL in a browser to confirm it is up |
| DHT22 reads NaN | DHT wiring / first read | Code auto-falls back to 30°C / 55%; check the DHT wire on GPIO15 |
| Dashboard shows 🔴 Offline | No reading in the last 30s | Make sure the Wokwi simulation is still running (it pauses after ~1 min of no interaction) |
| Endpoint returns 400 | Values out of range | Check a knob didn't send value >1000% — the second potentiometer maps to 0–30mm rainfall |
| Server won't start locally on 127.0.0.1:5000 | Port busy | Close other servers or change PORT in `app.py` |

### Local testing without Wokwi
While the server runs locally, push a fake reading with curl:

```
curl -X POST http://127.0.0.1:5000/api/sensor-data ^
  -H "Content-Type: application/json" ^
  -d "{\"soil_moisture\": 28, \"temperature\": 35, \"humidity\": 48, \"rainfall\": 2}"
```

> The Wokwi simulator cannot reach `localhost` on your PC. Use curl/Postman
> for local tests, and Wokwi only against the deployed Render URL.

---

## 7. Complete Data Flow (explain this to the judges)

1. **Wokwi ESP32** reads simulated soil moisture (potentiometer), temperature
   and humidity (DHT22), and rainfall (potentiometer).
2. The sketch builds a small **JSON** payload and **HTTP POSTs** it to
   `POST /api/sensor-data`.
3. **Flask** does not trust the input — it **validates** the readings.
4. A **new SQLite record** is stored for every push (full history is kept).
5. The **AI/decision logic** (`models/model_interface.py`) returns an
   irrigation decision and drought/heat risks, and a recommendation is written.
6. The browser dashboard **polls** `GET /api/latest-sensor-data` every 5 seconds
   and updates the LIVE FARM SENSOR DATA section — including a 🟢/🔴
   Wokwi connection status.

**Key point for judges:** Wokwi never touches the database directly. It only
sends HTTP POSTs; Flask is the only component that writes to SQLite.

---

## 8. Testing Order

Do these EXACTLY in this sequence:

- **TEST 1** — Run Flask locally: `python app.py`
- **TEST 2** — `POST /api/sensor-data` with the curl example above
- **TEST 3** — Open SQLite / History and confirm a `source='wokwi'` row was added
- **TEST 4** — Open the Dashboard → LIVE FARM SENSOR DATA shows the value
- **TEST 5** — Deploy to Render (section 4)
- **TEST 6** — Replace `YOUR-RENDER-APP` in `smart_farming_esp32.ino`
- **TEST 7** — Run the Wokwi simulation
- **TEST 8** — Check the Serial Monitor shows HTTP 200 + the JSON analysis
- **TEST 9** — Open the deployed web app and watch live values appear