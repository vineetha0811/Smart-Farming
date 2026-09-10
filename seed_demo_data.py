from datetime import datetime

"""
Seed script - creates the demo user and sample farm data.
Run once (optional) with:  python seed_demo_data.py
The app also works without this - use the Register page instead.
"""

import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = "database.db"

db = sqlite3.connect(DB_PATH)
db.execute("PRAGMA foreign_keys = ON")

# Create tables (same as in app.py init_db)
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

    CREATE TABLE IF NOT EXISTS sensor_readings (
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

# Check if demo user already exists
existing = db.execute("SELECT id FROM users WHERE email = ?", ("demo@farm.com",)).fetchone()

if not existing:
    # Create demo user
    hashed_pw = generate_password_hash("demo123")
    cursor = db.execute(
        "INSERT INTO users (name, mobile, email, password, location) VALUES (?, ?, ?, ?, ?)",
        ("Ramesh Kumar", "9876543210", "demo@farm.com", hashed_pw, "Nashik, Maharashtra")
    )
    user_id = cursor.lastrowid

    # Create sample farm
    db.execute(
        """INSERT INTO farms (user_id, crop_name, crop_variety, farm_area,
           soil_type, growth_stage, sowing_date, location)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, "Rice", "Basmati", "2 acres", "Loamy", "Vegetative",
         datetime.now().strftime("%Y-%m-%d"), "Nashik, Maharashtra")
    )

    # Sample sensor reading
    db.execute(
        """INSERT INTO sensor_readings (user_id, soil_moisture, temperature,
           humidity, rainfall, irrigation_status, irrigation_reason,
           drought_risk, heat_risk, recommendation, source)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, 45, 32, 55, 0,
         "Not Required",
         "Soil moisture is adequate (45%). Current moisture level is suitable for crop growth.",
         "LOW", "LOW",
         "Current soil moisture is sufficient for the crop.", "seed")
    )

    # Sample alert
    db.execute(
        "INSERT INTO alerts (user_id, alert_type, message, risk_level) VALUES (?, ?, ?, ?)",
        (user_id, "Info", "Farm setup completed successfully. Keep monitoring crop health regularly.", "LOW")
    )

    # Sample recommendation
    db.execute(
        "INSERT INTO recommendations (user_id, recommendation_text, category) VALUES (?, ?, ?)",
        (user_id, "Continue regular monitoring. No irrigation needed at this time.", "seed")
    )

    db.commit()
    print("Demo user created!")
    print("  Email: demo@farm.com")
    print("  Password: demo123")
    print("  Sample farm: Rice (Basmati), Loamy soil, Vegetative stage")
else:
    print("Demo user already exists. Nothing to do.")

db.close()
print("Done.")