# AI Smart Farming Assistant

A beginner-friendly, field-deployable "AI" Smart Farming Assistant built for Smart India Hackathon (SIH). It helps farmers detect crop diseases, pests, nutrient deficiencies, and irrigation needs early, while building resilience against droughts, floods, and heat waves.

Includes a **Wokwi ESP32 virtual IoT prototype** that pushes live sensor data
to the Flask backend over the internet. See **[WOKWI_SETUP.md](WOKWI_SETUP.md)**
for the full IoT integration guide.

---

## How To Run The Project

### Step 1: Install Python (already done if you have Python 3)

Check Python version:
```
python --version
```

### Step 2: Install dependencies

Open a terminal/Command Prompt inside the `smart_farming_assistant` folder and run:

```
pip install -r requirements.txt
```

This installs:
- **Flask** - the web framework
- **Werkzeug** - used for password hashing and file name security
- **Pillow** - used to open and verify uploaded images

### Step 3: Run the app

```
python app.py
```

You will see:
```
* Running on http://127.0.0.1:5000
```

Open your browser and go to: **http://127.0.0.1:5000**

### Step 4: Login

Use the demo credentials:

| Email | Password |
|-------|----------|
| demo@farm.com | demo123 |

Or create a new account using the **Register** page. The `database.db` file is created automatically the first time you run the app.

---

## Project Structure

```
smart_farming_assistant/
│
├── app.py                      # Main Flask application (all routes + database setup)
├── database.db                 # SQLite database (created automatically)
├── requirements.txt            # Python packages needed
│
├── models/
│   └── model_interface.py      # All AI/prototype decision logic (irrigation, risk, pest/nutrient, disease interface)
│
├── templates/                  # HTML pages using Jinja2
│   ├── base.html               # Shared layout (sidebar + navbar)
│   ├── login.html              # Login page
│   ├── register.html           # Registration page
│   ├── dashboard.html          # Main dashboard
│   ├── farm.html               # Farm/Crop setup
│   ├── irrigation.html         # Smart irrigation + Live Farm Simulation
│   ├── disease.html            # Crop disease detection (image upload)
│   ├── pest_nutrient.html      # Pest & nutrient diagnosis
│   ├── risk_monitor.html       # Drought/flood/heat risk assessment
│   ├── recommendations.html    # Smart recommendations
│   └── history.html            # All past records
│
└── static/
    ├── css/
    │   └── style.css           # All styling (agriculture theme)
    ├── js/
    │   └── script.js           # Simulation + live Wokwi sensor polling + UI interactivity
    └── uploads/                # Uploaded crop images are stored here

    └── wokwi/
        ├── smart_farming_esp32.ino   # Wokwi ESP32 Arduino sketch (virtual sensors -> Flask API)
        └── diagram.json              # Wokwi circuit wiring (ESP32 + DHT22 + 2 potentiometers)
```

### Wokwi / IoT files

| File | What it is |
|------|-----------|
| `POST /api/sensor-data` (in app.py) | Endpoint the ESP32 pushes readings to; validates → SQLite → decision logic → returns JSON analysis |
| `GET /api/latest-sensor-data` (in app.py) | Returns the newest Wokwi reading + 🟢/🔴 connection status for the dashboard |
| `/iot-simulation` (in app.py + template) | Virtual Farm / IoT Simulation page |
| `wokwi/smart_farming_esp32.ino` | ESP32 sketch: reads simulated sensors, POSTs JSON every 10s |
| `WOKWI_SETUP.md` | Full guide: wiring, deployment, testing order, troubleshooting |

---

## How The App Works (Architecture)

### Concept flow (behind the scenes)

```
Sensor/Input Data
      ↓
Data Processing
      ↓
AI / Decision Logic (models/model_interface.py)
      ↓
Crop Health Analysis
      ↓
Risk Detection
      ↓
Recommendation Engine
      ↓
Farmer Dashboard
```

### Frontend ↔ Backend ↔ Database connection

```
Browser (HTML + CSS + JS)
       │  sends form / fetch() calls
       ▼
Flask routes (app.py)
       │  reads/writes
       ▼
SQLite database (database.db)
```

- **Frontend**: The HTML pages in `templates/` are rendered by Flask using Jinja2 templates. JavaScript in `static/js/script.js` powers the **Live Farm Simulation** by calling Flask JSON APIs (`/api/analyze-farm`, `/api/generate-sensor-data`).
- **Backend**: `app.py` handles all routes. Each page has its own route function. Form data is validated and stored in SQLite.
- **Database**: SQLite stores users, farms, sensor readings, disease detections, alerts, recommendations, and pest diagnoses. All data is real (saved to disk), not fake frontend data.

---

## How The AI Prototype Works

**Important:** This is a *demonstration prototype*. It uses simple, explainable **rule-based logic** (if-else conditions) instead of a trained ML model. The code is structured so real models can be plugged in later.

All logic lives in `models/model_interface.py`:

| Function | What it does |
|----------|--------------|
| `predict_disease(image_path)` | Simulates image-based disease detection. Returns disease name, confidence %, symptoms, action, prevention. A comment in the code shows exactly where a trained CNN model would go. |
| `calculate_irrigation(moisture, temp, humidity, rainfall)` | Decides if irrigation is Required / Recommended / Not Required based on moisture + temperature thresholds. |
| `calculate_risks(...)` | Returns LOW/MODERATE/HIGH risk for drought, flood, heat stress, excess rainfall, low moisture. |
| `diagnose_pest_nutrient(...)` | Matches keywords in symptoms to flag possible N/P/K deficiency or pest/fungal issues. |
| `generate_recommendations(...)` | Combines everything into simple farmer-friendly actions. |
| `analyze_farm(...)` | One-shot analysis used by the Live Farm Simulation. |

### Wokwi IoT integration

The Wokwi virtual ESP32 sends readings over the internet using HTTP POST.
The full setup, wiring, deployment steps, and a 9-step testing order are in
**[WOKWI_SETUP.md](WOKWI_SETUP.md)**. The short version:

```
Wokwi ESP32 → HTTP POST /api/sensor-data → Flask validates → SQLite
     → irrigation + risk logic → recommendation → Dashboard live section
```

- `POST /api/sensor-data` — receives, validates, stores, analyzes, responds.
- `GET /api/latest-sensor-data` — dashboard polls this every 5 seconds.
- 🟢 Connected (reading within 30s) / 🔴 Offline otherwise. No fake data.

### Disease Detection model interface

`predict_disease()` in `models/model_interface.py` is the *only* place real AI would be added later:

```python
# FUTURE SCOPE:
# model = load_my_trained_model("models/tomato_leaf_cnn.h5")
# preprocessed = preprocess_image(image_path)
# prediction = model.predict(preprocessed)
```

No unrealistic accuracy claims are made — the prototype is clearly labelled as a demo system.

---

## Live Farm Simulation (SIH Demo Feature)

On the **Smart Irrigation** page, the team can:

1. Click **"Generate Sensor Data"** to fill random realistic values.
2. Manually edit values (e.g. Soil Moisture 25%, Temperature 36°C, Humidity 45%).
3. Click **"Analyze Farm"** → the app instantly shows irrigation status, drought/heat/flood risks, crop stress level, and farmer actions.
4. Change values (e.g. Soil Moisture 75%, Temperature 29°C, Humidity 70%) and click **"Analyze Farm"** again → recommendations change to match the new conditions.

This proves the system *analyzes* data and makes decisions rather than just displaying numbers.

---

## SIH Demo Flow (What To Click, In Order)

Follow this during your presentation to tell a complete story:

1. **Open** `http://127.0.0.1:5000` → shows Login page.
2. **Login** with `demo@farm.com` / `demo123`.
3. **Dashboard**: Point out the cards — Soil Moisture, Temperature, Humidity, Irrigation status, Crop Health, Risk Level.
4. **Farm Setup**: Show the crop info form (already saved: e.g. Rice, Vegetative stage, Loamy soil). Edit and Save to show it updates.
5. **Smart Irrigation** → set Soil Moisture = **25**, Temp = **36**, Humidity = **45**, Rainfall = **0** → click **Analyze Farm**:
   - Show "Urgently Required" irrigation, HIGH drought risk, HIGH heat stress, severe crop stress.
   - Then change to Soil Moisture = **75**, Temp = **29**, Humidity = **70** → click **Analyze Farm**:
   - Show "Not Required" irrigation, LOW risk, normal stress. **This contrast is the "wow" moment.**
6. **Generate Sensor Data**: Click to show the simulated IoT concept.
7. **Crop Health**: Upload a leaf image → show predicted condition, confidence, symptoms, action, prevention.
8. **Pest & Nutrient**: Enter symptoms like "lower leaves turning yellow with brown edges" → shows Possible Nitrogen + Potassium Deficiency.
9. **Risk Monitor**: Set rainfall = 60, moisture = 90 → shows HIGH flood/waterlogging risk.
10. **Recommendations**: Click **Generate Recommendations** → shows immediate actions and general advice combining all modules.
11. **History**: Show all the stored records (readings, detections, alerts, recommendations) with date & time.

---

## Sample Farm Data

The demo user already has:

- **Crop**: Rice (Basmati)
- **Farm area**: 2 acres
- **Soil type**: Loamy
- **Growth stage**: Vegetative
- **Sowing date**: (current date)
- **Location**: Nashik, Maharashtra

---

## Security (Student Level)

- Passwords are hashed with `werkzeug.security` (never stored in plain text).
- Flask sessions keep the user logged in between pages.
- Image filenames are cleaned with `secure_filename()` before saving.
- Uploaded file types are checked and limited to 5MB.

---

## Error Handling

All routes validate input and show friendly flash messages instead of Python errors:
- Empty forms → "Please fill in all required fields."
- Invalid sensor values (e.g. moisture 150%) → "Please enter valid sensor values."
- Wrong login → "Invalid email or password."
- No image uploaded → "Please upload an image."
- Wrong file type → "Invalid file type. Please upload PNG, JPG, JPEG, or GIF."
- Missing farm info → app still works, shows a notice to set up the farm first.

---

## Prototype vs Future Scope

**Current version (working now):**
- Login/registration
- Farm setup
- Smart irrigation decision logic
- Live farm simulation
- Prototype disease detection workflow
- Pest/nutrient rule-based diagnosis
- Risk monitoring
- Smart recommendations
- Full history storage

**Future scope (NOT implemented — roadmap only):**
- Real ML disease detection (CNN on PlantVillage dataset)
- Real IoT sensor hardware / edge deployment (TFLite on-device)
- Live weather API integration
- Regional-language voice assistant
- SMS / WhatsApp alerts
- More crop varieties and datasets
- Mobile application
- Multi-language UI

---

## Team Notes For The Jury

- Emphasize the **4 core points**:
  1. **Early Detection** – disease, pest, deficiency
  2. **Smart Irrigation** – saves water
  3. **Risk Awareness** – drought/flood/heat
  4. **Actionable Recommendations** – simple farmer language
- Emphasize the **Live Farm Simulation** – it proves the system makes decisions, not just displays data.
- Be honest: "Currently a rule-based prototype; structured so a trained CNN model plugs in at `models/model_interface.py`."