"""
AI Smart Farming Assistant - Main Application
===============================================
Flask backend with SQLite database, routes, and AI logic integration.

Run this file to start the application:
    python app.py

Then open http://127.0.0.1:5000 in your browser.
"""

import os
import sqlite3
import random
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, g, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from models.model_interface import (
    predict_disease, calculate_irrigation, calculate_risks,
    diagnose_pest_nutrient, generate_recommendations,
    generate_simulated_sensor_data, analyze_farm
)

# ============================================================
# APP CONFIGURATION
# ============================================================

app = Flask(__name__)
app.secret_key = "smart-farming-secret-key-2024"

# Upload settings
UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5MB max

# Database path
DATABASE = os.path.join(app.root_path, "database.db")


# ============================================================
# CORS SUPPORT (for the Wokwi / ESP32 push and browser JS)
# ============================================================
# The ESP32 HTTP request itself does not need CORS (it is not a browser).
# CORS headers are added so that any browser-based demo page can also call
# the API, and so the OPTIONS preflight request is handled correctly.

@app.after_request
def add_cors_headers(response):
    """Add simple CORS headers to every response."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


@app.route("/api/sensor-data", methods=["OPTIONS"])
def api_sensor_data_preflight():
    """Answer the browser CORS preflight request."""
    return "OK", 200


# ============================================================
# DATABASE HELPERS
# ============================================================

def get_db():
    """Get database connection for current request."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    """Close database connection when request ends."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Initialize the database with all required tables."""
    db = sqlite3.connect(DATABASE)
    db.execute("PRAGMA foreign_keys = ON")
    
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            location TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS farms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            crop_name TEXT NOT NULL,
            crop_variety TEXT,
            farm_area TEXT,
            soil_type TEXT,
            growth_stage TEXT,
            sowing_date TEXT,
            location TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        
        CREATE TABLE IF NOT EXISTS disease_detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            image_filename TEXT,
            prediction TEXT,
            condition_type TEXT,
            confidence REAL,
            symptoms TEXT,
            action_advised TEXT,
            prevention TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            alert_type TEXT,
            message TEXT,
            risk_level TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            recommendation_text TEXT,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        
        CREATE TABLE IF NOT EXISTS pest_nutrient_diagnoses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            crop TEXT,
            growth_stage TEXT,
            leaf_condition TEXT,
            soil_condition TEXT,
            symptoms TEXT,
            diagnosis_result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    
    # sensor_readings is handled separately (below) so it can be upgraded
    # with the new Wokwi/IoT columns even if the table already exists.
    migrate_sensor_readings(db)
    
    db.commit()
    db.close()


def migrate_sensor_readings(db):
    """
    Create or upgrade the sensor_readings table.

    The original table only stored manual readings. The Wokwi ESP32 push
    endpoint needs extra columns: drought_risk, heat_risk, recommendation
    and source. Also, IoT (Wokwi) readings do NOT belong to a logged-in
    user, so user_id must be allowed to be NULL.

    For an old database this migrates the table without losing data.
    """
    # List the columns that currently exist in the table
    columns = {row[1]: row for row in db.execute("PRAGMA table_info(sensor_readings)")}

    # Fresh database - just create the new table with everything
    if not columns:
        db.execute("""
            CREATE TABLE sensor_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,                                -- NULL for Wokwi/IoT data
                soil_moisture REAL,
                temperature REAL,
                humidity REAL,
                rainfall REAL DEFAULT 0,
                irrigation_status TEXT,
                irrigation_reason TEXT,
                drought_risk TEXT,                              -- from risk analysis
                heat_risk TEXT,                                 -- from risk analysis
                recommendation TEXT,                            -- farmer-friendly advice
                source TEXT DEFAULT 'manual',                   -- manual / wokwi / simulation
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        return

    # Add any missing columns to an existing table
    new_columns = {
        "drought_risk": "TEXT",
        "heat_risk": "TEXT",
        "recommendation": "TEXT",
        "source": "TEXT DEFAULT 'manual'",
    }
    for name, data_type in new_columns.items():
        if name not in columns:
            db.execute("ALTER TABLE sensor_readings ADD COLUMN {} {}".format(name, data_type))

    # If user_id is currently NOT NULL, rebuild the table so Wokwi readings
    # can be stored without a logged-in user. Data is preserved.
    if columns["user_id"][3]:  # index 3 in PRAGMA info = "notnull" flag
        db.execute("""
            CREATE TABLE sensor_readings_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                soil_moisture REAL,
                temperature REAL,
                humidity REAL,
                rainfall REAL DEFAULT 0,
                irrigation_status TEXT,
                irrigation_reason TEXT,
                drought_risk TEXT,
                heat_risk TEXT,
                recommendation TEXT,
                source TEXT DEFAULT 'manual',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.execute("""
            INSERT INTO sensor_readings_new
                (id, user_id, soil_moisture, temperature, humidity, rainfall,
                 irrigation_status, irrigation_reason, drought_risk, heat_risk,
                 recommendation, source, created_at)
            SELECT id, user_id, soil_moisture, temperature, humidity, rainfall,
                 irrigation_status, irrigation_reason, drought_risk, heat_risk,
                 recommendation, source, created_at
            FROM sensor_readings
        """)
        db.execute("DROP TABLE sensor_readings")
        db.execute("ALTER TABLE sensor_readings_new RENAME TO sensor_readings")


def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ============================================================
# LOGIN REQUIRED DECORATOR
# ============================================================

def login_required(f):
    """Decorator to protect pages that need login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================
# AUTH ROUTES
# ============================================================

@app.route("/")
def index():
    """Home page - redirect to login or dashboard."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    """New farmer registration."""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        mobile = request.form.get("mobile", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        location = request.form.get("location", "").strip()
        
        # Validate required fields
        if not all([name, mobile, email, password]):
            flash("Please fill in all required fields.", "error")
            return render_template("register.html")
        
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("register.html")
        
        db = get_db()
        try:
            # Check if email already exists
            existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if existing:
                flash("Email already registered. Please login.", "error")
                return render_template("register.html")
            
            # Create new user with hashed password
            hashed_pw = generate_password_hash(password)
            db.execute(
                "INSERT INTO users (name, mobile, email, password, location) VALUES (?, ?, ?, ?, ?)",
                (name, mobile, email, hashed_pw, location)
            )
            db.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("login"))
            
        except Exception as e:
            flash("Registration failed. Please try again.", "error")
            return render_template("register.html")
    
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Farmer login."""
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        
        if not email or not password:
            flash("Please enter email and password.", "error")
            return render_template("login.html")
        
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password.", "error")
    
    return render_template("login.html")


@app.route("/logout")
def logout():
    """Logout and clear session."""
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/dashboard")
@login_required
def dashboard():
    """Main dashboard showing farm overview."""
    db = get_db()
    user_id = session["user_id"]
    
    # Get latest farm info
    farm = db.execute(
        "SELECT * FROM farms WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,)
    ).fetchone()
    
    # Get the latest sensor reading for the overview stats below.
    # The Wokwi (live IoT) reading is preferred: if the virtual ESP32 has
    # pushed data, that represents the current field conditions.
    # If no Wokwi data exists yet, fall back to the logged-in user's most
    # recent reading (e.g. entered manually on the irrigation page).
    reading = db.execute(
        "SELECT * FROM sensor_readings WHERE source = 'wokwi' ORDER BY id DESC LIMIT 1"
    ).fetchone()

    if not reading:
        reading = db.execute(
            "SELECT * FROM sensor_readings WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,)
        ).fetchone()
    
    # Get latest disease detection
    disease = db.execute(
        "SELECT * FROM disease_detections WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,)
    ).fetchone()
    
    # Get latest alerts
    alerts = db.execute(
        "SELECT * FROM alerts WHERE user_id = ? ORDER BY id DESC LIMIT 5",
        (user_id,)
    ).fetchall()
    
    # Get latest recommendation
    recommendation = db.execute(
        "SELECT * FROM recommendations WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,)
    ).fetchone()
    
    # If we have sensor data, compute current status
    irrigation_status = "No Data"
    health_status = "Unknown"
    risk_level = "Unknown"
    soil_moisture = 0
    temperature = 0
    humidity = 0
    
    if reading:
        soil_moisture = reading["soil_moisture"]
        temperature = reading["temperature"]
        humidity = reading["humidity"]
        irrigation_status = reading["irrigation_status"] or "Unknown"
        
        # Compute risk
        risks = calculate_risks(soil_moisture, temperature, humidity, 
                                reading["rainfall"] or 0)
        risk_level = risks["overall"]
        
        # Determine health
        if disease:
            if "Healthy" in (disease["prediction"] or ""):
                health_status = "Good"
            else:
                health_status = "At Risk"
        else:
            health_status = "Not Assessed"
    
    return render_template("dashboard.html",
        farm=farm,
        reading=reading,
        disease=disease,
        alerts=alerts,
        recommendation=recommendation,
        irrigation_status=irrigation_status,
        health_status=health_status,
        risk_level=risk_level,
        soil_moisture=soil_moisture,
        temperature=temperature,
        humidity=humidity
    )


# ============================================================
# FARM / CROP SETUP
# ============================================================

@app.route("/farm", methods=["GET", "POST"])
@login_required
def farm():
    """Farm and crop setup page."""
    db = get_db()
    user_id = session["user_id"]
    
    if request.method == "POST":
        crop_name = request.form.get("crop_name", "").strip()
        crop_variety = request.form.get("crop_variety", "").strip()
        farm_area = request.form.get("farm_area", "").strip()
        soil_type = request.form.get("soil_type", "").strip()
        growth_stage = request.form.get("growth_stage", "").strip()
        sowing_date = request.form.get("sowing_date", "").strip()
        location = request.form.get("location", "").strip()
        
        if not crop_name:
            flash("Please enter a crop name.", "error")
        else:
            # Check if farm already exists for this user
            existing = db.execute(
                "SELECT id FROM farms WHERE user_id = ?", (user_id,)
            ).fetchone()
            
            if existing:
                # Update existing farm
                db.execute("""
                    UPDATE farms SET crop_name=?, crop_variety=?, farm_area=?,
                    soil_type=?, growth_stage=?, sowing_date=?, location=?
                    WHERE user_id=?
                """, (crop_name, crop_variety, farm_area, soil_type,
                      growth_stage, sowing_date, location, user_id))
                flash("Farm information updated successfully!", "success")
            else:
                # Create new farm
                db.execute("""
                    INSERT INTO farms (user_id, crop_name, crop_variety, farm_area,
                    soil_type, growth_stage, sowing_date, location)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, crop_name, crop_variety, farm_area, soil_type,
                      growth_stage, sowing_date, location))
                flash("Farm information saved successfully!", "success")
            
            db.commit()
            return redirect(url_for("farm"))
    
    # Get current farm info
    current_farm = db.execute(
        "SELECT * FROM farms WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,)
    ).fetchone()
    
    return render_template("farm.html", farm=current_farm)


# ============================================================
# IRRIGATION ASSISTANT
# ============================================================

@app.route("/irrigation", methods=["GET", "POST"])
@login_required
def irrigation():
    """Smart irrigation assistant page."""
    db = get_db()
    user_id = session["user_id"]
    result = None
    
    if request.method == "POST":
        try:
            soil_moisture = float(request.form.get("soil_moisture", 50))
            temperature = float(request.form.get("temperature", 30))
            humidity = float(request.form.get("humidity", 50))
            rainfall = float(request.form.get("rainfall", 0))
            
            # Validate ranges
            if not (0 <= soil_moisture <= 100 and -10 <= temperature <= 55
                    and 0 <= humidity <= 100 and 0 <= rainfall <= 100):
                flash("Please enter valid sensor values within expected ranges.", "error")
                return render_template("irrigation.html")
            
            # Get irrigation decision
            result = calculate_irrigation(soil_moisture, temperature, humidity, rainfall)
            
            # Save reading to database
            db.execute("""
                INSERT INTO sensor_readings (user_id, soil_moisture, temperature,
                humidity, rainfall, irrigation_status, irrigation_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, soil_moisture, temperature, humidity, rainfall,
                  result["status"], result["reason"]))
            db.commit()
            
            flash("Sensor reading analyzed and saved.", "success")
            
        except (ValueError, TypeError):
            flash("Please enter valid numeric values for sensor readings.", "error")
    
    # Get recent readings
    recent_readings = db.execute(
        "SELECT * FROM sensor_readings WHERE user_id = ? ORDER BY id DESC LIMIT 5",
        (user_id,)
    ).fetchall()
    
    return render_template("irrigation.html", result=result, recent_readings=recent_readings)


# ============================================================
# DISEASE DETECTION
# ============================================================

@app.route("/disease", methods=["GET", "POST"])
@login_required
def disease():
    """Crop disease detection page."""
    db = get_db()
    user_id = session["user_id"]
    result = None
    image_url = None
    
    if request.method == "POST":
        # Check if image was uploaded
        if "leaf_image" not in request.files:
            flash("Please upload an image.", "error")
            return render_template("disease.html")
        
        file = request.files["leaf_image"]
        
        if file.filename == "":
            flash("No image selected. Please choose an image.", "error")
            return render_template("disease.html")
        
        if file and allowed_file(file.filename):
            # Save the uploaded file
            filename = secure_filename(f"user{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)
            
            image_url = f"uploads/{filename}"
            
            # Run disease prediction
            result = predict_disease(filepath)
            
            # Save result to database
            db.execute("""
                INSERT INTO disease_detections (user_id, image_filename, prediction,
                condition_type, confidence, symptoms, action_advised, prevention)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, filename, result["prediction"], result["condition"],
                  result["confidence"], result["symptoms"], result["action"],
                  result["prevention"]))
            db.commit()
            
            flash("Image analyzed successfully.", "success")
        else:
            flash("Invalid file type. Please upload PNG, JPG, JPEG, or GIF.", "error")
    
    # Get recent detections
    recent_detections = db.execute(
        "SELECT * FROM disease_detections WHERE user_id = ? ORDER BY id DESC LIMIT 5",
        (user_id,)
    ).fetchall()
    
    return render_template("disease.html", result=result, image_url=image_url,
                           recent_detections=recent_detections)


# ============================================================
# PEST AND NUTRIENT ASSISTANT
# ============================================================

@app.route("/pest-nutrient", methods=["GET", "POST"])
@login_required
def pest_nutrient():
    """Pest and nutrient diagnosis page."""
    db = get_db()
    user_id = session["user_id"]
    result = None
    
    # Get current farm info for pre-filling
    farm = db.execute(
        "SELECT * FROM farms WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,)
    ).fetchone()
    
    if request.method == "POST":
        crop = request.form.get("crop", "").strip()
        growth_stage = request.form.get("growth_stage", "").strip()
        leaf_condition = request.form.get("leaf_condition", "").strip()
        soil_condition = request.form.get("soil_condition", "").strip()
        symptoms = request.form.get("symptoms", "").strip()
        
        if not symptoms:
            flash("Please describe the symptoms you observed.", "error")
        else:
            result = diagnose_pest_nutrient(crop, growth_stage, leaf_condition,
                                            soil_condition, symptoms)
            
            # Save to database
            db.execute("""
                INSERT INTO pest_nutrient_diagnoses (user_id, crop, growth_stage,
                leaf_condition, soil_condition, symptoms, diagnosis_result)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, crop, growth_stage, leaf_condition, soil_condition,
                  symptoms, str(result["diagnoses"])))
            db.commit()
            
            flash("Diagnosis completed.", "success")
    
    # Get recent diagnoses
    recent_diagnoses = db.execute(
        "SELECT * FROM pest_nutrient_diagnoses WHERE user_id = ? ORDER BY id DESC LIMIT 5",
        (user_id,)
    ).fetchall()
    
    return render_template("pest_nutrient.html", result=result, farm=farm,
                           recent_diagnoses=recent_diagnoses)


# ============================================================
# CLIMATE AND RISK MONITOR
# ============================================================

@app.route("/risk-monitor", methods=["GET", "POST"])
@login_required
def risk_monitor():
    """Farm risk monitoring page."""
    db = get_db()
    user_id = session["user_id"]
    risks = None
    
    # Get farm info
    farm = db.execute(
        "SELECT * FROM farms WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,)
    ).fetchone()
    
    if request.method == "POST":
        try:
            soil_moisture = float(request.form.get("soil_moisture", 50))
            temperature = float(request.form.get("temperature", 30))
            humidity = float(request.form.get("humidity", 50))
            rainfall = float(request.form.get("rainfall", 0))
            
            crop = farm["crop_name"] if farm else None
            growth_stage = farm["growth_stage"] if farm else None
            
            risks = calculate_risks(soil_moisture, temperature, humidity,
                                    rainfall, crop, growth_stage)
            
            # Save alert if risk is HIGH or MODERATE
            if risks["overall"] in ("HIGH", "MODERATE"):
                db.execute("""
                    INSERT INTO alerts (user_id, alert_type, message, risk_level)
                    VALUES (?, ?, ?, ?)
                """, (user_id, "Risk Alert",
                      f"Risk level: {risks['overall']}. Environmental conditions may affect crop health.",
                      risks["overall"]))
                db.commit()
                
        except (ValueError, TypeError):
            flash("Please enter valid sensor values.", "error")
    
    # Get recent alerts
    recent_alerts = db.execute(
        "SELECT * FROM alerts WHERE user_id = ? ORDER BY id DESC LIMIT 10",
        (user_id,)
    ).fetchall()
    
    return render_template("risk_monitor.html", risks=risks, farm=farm,
                           recent_alerts=recent_alerts)


# ============================================================
# SMART RECOMMENDATIONS
# ============================================================

@app.route("/recommendations", methods=["GET", "POST"])
@login_required
def recommendations():
    """Smart recommendations page combining all data."""
    db = get_db()
    user_id = session["user_id"]
    recs = None
    
    # Get latest data from all sources
    farm = db.execute(
        "SELECT * FROM farms WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,)
    ).fetchone()
    
    reading = db.execute(
        "SELECT * FROM sensor_readings WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,)
    ).fetchone()
    
    disease_det = db.execute(
        "SELECT * FROM disease_detections WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,)
    ).fetchone()
    
    pest_diag = db.execute(
        "SELECT * FROM pest_nutrient_diagnoses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,)
    ).fetchone()
    
    if request.method == "POST":
        if reading:
            soil_moisture = reading["soil_moisture"]
            temperature = reading["temperature"]
            humidity = reading["humidity"]
            rainfall = reading["rainfall"] or 0
            crop = farm["crop_name"] if farm else "General Crop"
            growth_stage = farm["growth_stage"] if farm else "Vegetative"
            
            # Get risk level
            risks = calculate_risks(soil_moisture, temperature, humidity, rainfall)
            
            # Generate recommendations
            recs = generate_recommendations(
                soil_moisture=soil_moisture,
                temperature=temperature,
                humidity=humidity,
                crop=crop,
                growth_stage=growth_stage,
                risk_level=risks["overall"],
                irrigation_result=calculate_irrigation(soil_moisture, temperature, humidity, rainfall)
            )
            
            # Save recommendation summary
            summary = "; ".join(
                recs["immediate"][:2] + recs["today"][:2]
            )[:500] if (recs["immediate"] or recs["today"]) else "Farm conditions are satisfactory."
            
            db.execute("""
                INSERT INTO recommendations (user_id, recommendation_text, category)
                VALUES (?, ?, ?)
            """, (user_id, summary, "auto"))
            db.commit()
            flash("Recommendations generated using your latest farm data.", "success")
        else:
            flash("No sensor data available. Please record sensor readings first.", "warning")
    
    # Get past recommendations
    past_recs = db.execute(
        "SELECT * FROM recommendations WHERE user_id = ? ORDER BY id DESC LIMIT 10",
        (user_id,)
    ).fetchall()
    
    return render_template("recommendations.html", recs=recs, farm=farm,
                           reading=reading, past_recs=past_recs)


# ============================================================
# HISTORY
# ============================================================

@app.route("/history")
@login_required
def history():
    """History page showing all past data."""
    db = get_db()
    user_id = session["user_id"]
    
    # Get all historical data
    readings = db.execute(
        "SELECT * FROM sensor_readings WHERE user_id = ? ORDER BY id DESC LIMIT 20",
        (user_id,)
    ).fetchall()
    
    detections = db.execute(
        "SELECT * FROM disease_detections WHERE user_id = ? ORDER BY id DESC LIMIT 20",
        (user_id,)
    ).fetchall()
    
    alerts_list = db.execute(
        "SELECT * FROM alerts WHERE user_id = ? ORDER BY id DESC LIMIT 20",
        (user_id,)
    ).fetchall()
    
    recs_list = db.execute(
        "SELECT * FROM recommendations WHERE user_id = ? ORDER BY id DESC LIMIT 20",
        (user_id,)
    ).fetchall()
    
    pest_diags = db.execute(
        "SELECT * FROM pest_nutrient_diagnoses WHERE user_id = ? ORDER BY id DESC LIMIT 20",
        (user_id,)
    ).fetchall()
    
    return render_template("history.html",
        readings=readings,
        detections=detections,
        alerts_list=alerts_list,
        recs_list=recs_list,
        pest_diags=pest_diags
    )


# ============================================================
# API ROUTES (for AJAX calls from JavaScript)
# ============================================================

@app.route("/api/generate-sensor-data")
@login_required
def api_generate_sensor_data():
    """API endpoint to generate simulated sensor data."""
    data = generate_simulated_sensor_data()
    return jsonify(data)


@app.route("/api/analyze-farm", methods=["POST"])
@login_required
def api_analyze_farm():
    """API endpoint for the Live Farm Simulation feature."""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        soil_moisture = float(data.get("soil_moisture", 50))
        temperature = float(data.get("temperature", 30))
        humidity = float(data.get("humidity", 50))
        rainfall = float(data.get("rainfall", 0))
        crop = data.get("crop", None)
        growth_stage = data.get("growth_stage", None)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid sensor values"}), 400
    
    # Get farm info if not provided
    db = get_db()
    user_id = session["user_id"]
    farm = db.execute(
        "SELECT * FROM farms WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,)
    ).fetchone()
    
    if not crop and farm:
        crop = farm["crop_name"]
        growth_stage = farm["growth_stage"]
    
    result = analyze_farm(soil_moisture, temperature, humidity, rainfall, crop, growth_stage)
    
    return jsonify(result)


@app.route("/api/save-simulation", methods=["POST"])
@login_required
def api_save_simulation():
    """Save simulation results to database."""
    data = request.get_json()
    db = get_db()
    user_id = session["user_id"]
    
    try:
        # Save sensor reading
        db.execute("""
            INSERT INTO sensor_readings (user_id, soil_moisture, temperature,
            humidity, rainfall, irrigation_status, irrigation_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, data["soil_moisture"], data["temperature"],
              data["humidity"], data.get("rainfall", 0),
              data.get("irrigation_status", ""),
              data.get("irrigation_reason", "")))
        
        # Save alert if high risk
        if data.get("risk_level") == "HIGH":
            db.execute("""
                INSERT INTO alerts (user_id, alert_type, message, risk_level)
                VALUES (?, ?, ?, ?)
            """, (user_id, "Simulation Alert",
                  f"Simulation showed HIGH risk. {data.get('recommendation', '')}",
                  "HIGH"))
        
        # Save recommendation
        if data.get("recommendation"):
            db.execute("""
                INSERT INTO recommendations (user_id, recommendation_text, category)
                VALUES (?, ?, ?)
            """, (user_id, data["recommendation"], "simulation"))
        
        db.commit()
        return jsonify({"status": "saved"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# WOKWI / ESP32 IoT API
# ============================================================
# Architecture:
#   Wokwi ESP32 -> HTTP POST -> /api/sensor-data -> validation
#   -> SQLite -> irrigation/risk logic -> recommendation -> JSON
#   -> dashboard (GET /api/latest-sensor-data)

@app.route("/iot-simulation")
@login_required
def iot_simulation():
    """Virtual Farm / IoT Simulation page (Wokwi prototype)."""
    return render_template("iot_simulation.html")


def build_iot_recommendation(irrigation, risks):
    """
    Build one short farmer-friendly recommendation sentence from the
    irrigation and risk results. Used for the Wokwi API response.
    """
    parts = []

    # Irrigation part
    if irrigation["urgency"] in ("critical", "high"):
        parts.append("Low soil moisture indicates irrigation is required to prevent crop water stress.")
    elif irrigation["urgency"] == "moderate":
        parts.append("Irrigation is recommended in the near future to maintain healthy moisture levels.")
    else:
        parts.append("Current soil moisture is sufficient for the crop.")

    # Risk parts
    if risks["drought"]["level"] == "HIGH":
        parts.append("High drought risk: act quickly to protect the field.")
    elif risks["drought"]["level"] == "MODERATE":
        parts.append("Drought risk is moderate, so monitor soil moisture closely.")
    if risks["heat_stress"]["level"] in ("HIGH", "MODERATE"):
        parts.append("Heat risk is {} - keep the crop watered.".format(risks["heat_stress"]["level"].title()))
    if risks["flood"]["level"] in ("HIGH", "MODERATE"):
        parts.append("Check field drainage because of excess water risk.")

    return " ".join(parts)


@app.route("/api/sensor-data", methods=["POST"])
def api_receive_sensor_data():
    """
    Receive sensor readings pushed by the Wokwi ESP32 simulation.

    Expected JSON body:
        {"soil_moisture": 28, "temperature": 35, "humidity": 48, "rainfall": 2}

    The endpoint validates the values, saves them to SQLite, runs the
    irrigation and risk logic, and returns a farmer-friendly analysis.
    """
    # 1. Get raw JSON data (silent=True so a bad body becomes None)
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "Invalid JSON body"}), 400

    # 2. Read and validate the sensor values
    try:
        soil_moisture = float(data.get("soil_moisture"))
        temperature = float(data.get("temperature"))
        humidity = float(data.get("humidity"))
        rainfall = float(data.get("rainfall", 0))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Invalid sensor values"}), 400

    # Check the values are inside physically possible ranges
    if not (0 <= soil_moisture <= 100 and -10 <= temperature <= 55
            and 0 <= humidity <= 100 and 0 <= rainfall <= 100):
        return jsonify({"success": False, "error": "Sensor values out of range"}), 400

    # 3. Run the decision logic
    irrigation = calculate_irrigation(soil_moisture, temperature, humidity, rainfall)
    risks = calculate_risks(soil_moisture, temperature, humidity, rainfall)
    recommendation = build_iot_recommendation(irrigation, risks)

    # 4. Save the reading (user_id = None because the ESP32 has no login)
    db = get_db()
    db.execute("""
        INSERT INTO sensor_readings (user_id, soil_moisture, temperature,
            humidity, rainfall, irrigation_status, irrigation_reason,
            drought_risk, heat_risk, recommendation, source)
        VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'wokwi')
    """, (soil_moisture, temperature, humidity, rainfall,
          irrigation["status"], irrigation["reason"],
          risks["drought"]["level"], risks["heat_stress"]["level"],
          recommendation))
    db.commit()

    # 5. Return the analysis so the ESP32 can print it in the Serial Monitor
    return jsonify({
        "success": True,
        "soil_moisture": soil_moisture,
        "temperature": temperature,
        "humidity": humidity,
        "rainfall": rainfall,
        "irrigation_status": irrigation["status"],
        "drought_risk": risks["drought"]["level"],
        "heat_risk": risks["heat_stress"]["level"],
        "recommendation": recommendation
    })


@app.route("/api/latest-sensor-data")
def api_latest_sensor_data():
    """
    Return the most recent Wokwi sensor reading plus live connection status.

    Connection logic:
      - Reading received within the last 30 seconds  -> Connected
      - No reading yet or older than 30 seconds      -> Offline / No recent data
    """
    db = get_db()

    # Fetch the latest reading that came from the Wokwi prototype
    row = db.execute(
        "SELECT * FROM sensor_readings WHERE source = 'wokwi' ORDER BY id DESC LIMIT 1"
    ).fetchone()

    if not row:
        return jsonify({
            "success": True,
            "has_data": False,
            "connected": False,
            "seconds_ago": None,
            "message": "No live sensor data received yet."
        })

    # Work out how many seconds ago the reading arrived.
    # SQLite's CURRENT_TIMESTAMP stores UTC, so compare with UTC now.
    try:
        last_time = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")
        last_time = last_time.replace(tzinfo=timezone.utc)
    except ValueError:
        last_time = datetime.now(timezone.utc)
    seconds_ago = int((datetime.now(timezone.utc) - last_time).total_seconds())

    # Wokwi is considered connected when data arrived within 30 seconds
    connected = seconds_ago <= 30

    return jsonify({
        "success": True,
        "has_data": True,
        "connected": connected,
        "seconds_ago": seconds_ago,
        "last_updated": row["created_at"],
        "soil_moisture": row["soil_moisture"],
        "temperature": row["temperature"],
        "humidity": row["humidity"],
        "rainfall": row["rainfall"],
        "irrigation_status": row["irrigation_status"],
        "drought_risk": row["drought_risk"],
        "heat_risk": row["heat_risk"],
        "recommendation": row["recommendation"]
    })


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":
    # Initialize database
    init_db()
    
    # Create uploads directory if it doesn't exist
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # Render provides a PORT environment variable - use it when deployed.
    # Locally this stays at port 5000.
    port = int(os.environ.get("PORT", 5000))
    
    # Run the debug reloader only while developing locally,
    # never on Render (renders can be identified by the PORT variable).
    is_render = "PORT" in os.environ
    use_debug = (not is_render) and os.environ.get("FLASK_DEBUG", "1").lower() in ("1", "true")
    
    print("=" * 50)
    print("  AI Smart Farming Assistant")
    print("  Starting server on port {}".format(port))
    print("=" * 50)
    print()
    print("  Demo Login Credentials:")
    print("  Email: demo@farm.com")
    print("  Password: demo123")
    print()
    print("  Wokwi API endpoint: POST /api/sensor-data")
    print("  Dashboard will show live Wokwi data on /dashboard")
    print()
    
    app.run(debug=use_debug, host="0.0.0.0", port=port)
