"""
Model Interface - AI Prototype Logic
=====================================
This module contains all the decision logic for the Smart Farming Assistant.
For the prototype, we use rule-based systems (if-else logic).
The structure is designed so that actual ML models can be plugged in later.

Architecture:
    Sensor/Input Data -> Data Processing -> AI/Decision Logic -> Recommendations

Future Scope:
    - Replace disease prediction with trained CNN model (e.g., ResNet, MobileNet)
    - Replace risk logic with ML regression models
    - Integrate real weather API data
    - Deploy on-device TFLite models for offline use
"""

import os
import random
from PIL import Image

# ============================================================
# DISEASE DETECTION (Prototype / Demo)
# ============================================================
# In a real application, this would load a trained CNN model.
# For the prototype, we simulate predictions based on image properties
# or use a random selection from known diseases.

# Common crop diseases and their details
DISEASE_DATABASE = {
    "Healthy Leaf": {
        "condition": "Healthy",
        "confidence": 0,
        "symptoms": "No visible symptoms. Leaf appears green and healthy.",
        "action": "No action needed. Continue regular monitoring.",
        "prevention": "Maintain proper irrigation, balanced fertilization, and regular field inspection."
    },
    "Leaf Blight": {
        "condition": "Disease Detected",
        "confidence": 87,
        "symptoms": "Brown or black lesions on leaves, leaf wilting, reduced photosynthesis area.",
        "action": "Remove affected leaves immediately. Apply recommended fungicide.",
        "prevention": "Use resistant crop varieties. Ensure proper spacing between plants. Avoid overhead irrigation."
    },
    "Powdery Mildew": {
        "condition": "Disease Detected",
        "confidence": 82,
        "symptoms": "White powdery coating on leaf surfaces, leaf curling, stunted growth.",
        "action": "Apply sulfur-based fungicide. Improve air circulation around plants.",
        "prevention": "Plant in well-ventilated areas. Avoid excess nitrogen fertilization. Use resistant varieties."
    },
    "Bacterial Leaf Spot": {
        "condition": "Disease Detected",
        "confidence": 79,
        "symptoms": "Water-soaked spots on leaves, yellow halos around lesions, leaf drop.",
        "action": "Remove infected plant parts. Apply copper-based bactericide.",
        "prevention": "Use certified disease-free seeds. Practice crop rotation. Avoid working with wet plants."
    },
    "Rust Disease": {
        "condition": "Disease Detected",
        "confidence": 85,
        "symptoms": "Orange or reddish-brown pustules on leaves, premature leaf drying.",
        "action": "Apply fungicide at early stages. Remove heavily infected leaves.",
        "prevention": "Grow resistant varieties. Ensure proper plant nutrition. Monitor fields regularly."
    },
    "Pest Damage": {
        "condition": "Pest Damage Detected",
        "confidence": 76,
        "symptoms": "Holes in leaves, chewed edges, visible insect traces or webbing.",
        "action": "Identify the pest type. Apply appropriate organic or chemical pesticide.",
        "prevention": "Use integrated pest management (IPM). Introduce beneficial insects. Use neem-based sprays."
    }
}

DISEASE_LIST = list(DISEASE_DATABASE.keys())


def predict_disease(image_path):
    """
    Prototype disease prediction function.
    
    In production, this would:
        1. Load a pre-trained CNN model (e.g., trained on PlantVillage dataset)
        2. Preprocess the image (resize, normalize)
        3. Run inference
        4. Return predicted class and confidence
    
    For this prototype, we use image file hash to deterministically
    select a disease so the same image always gives the same result.
    
    Args:
        image_path: Path to the uploaded leaf/crop image
    
    Returns:
        dict with prediction results
    """
    try:
        # Open image to verify it's valid
        img = Image.open(image_path)
        img.verify()
        
        # Generate a deterministic seed from the file so same image = same result
        file_size = os.path.getsize(image_path)
        seed = file_size % 1000
        random.seed(seed)
        
        # Select a disease (weighted - healthy is less likely when user uploads)
        selected_disease = random.choice(DISEASE_LIST[1:])  # Skip "Healthy" for uploads
        disease_info = DISEASE_DATABASE[selected_disease]
        
        # Add some randomness to confidence
        base_confidence = disease_info["confidence"]
        confidence = base_confidence + random.randint(-5, 5)
        confidence = max(60, min(98, confidence))  # Keep in reasonable range
        
        return {
            "prediction": selected_disease,
            "condition": disease_info["condition"],
            "confidence": confidence,
            "symptoms": disease_info["symptoms"],
            "action": disease_info["action"],
            "prevention": disease_info["prevention"],
            "status": "success"
        }
        
    except Exception as e:
        return {
            "prediction": "Unable to analyze",
            "condition": "Error",
            "confidence": 0,
            "symptoms": "Could not process the image.",
            "action": "Please upload a clear image of the crop leaf.",
            "prevention": "Ensure the image is well-lit and in focus.",
            "status": "error",
            "error": str(e)
        }


# ============================================================
# IRRIGATION DECISION SYSTEM
# ============================================================

def calculate_irrigation(soil_moisture, temperature, humidity, rainfall=0):
    """
    Decision logic for irrigation recommendation.
    
    Uses soil moisture, temperature, humidity and rainfall to determine
    if irrigation is needed.
    
    Args:
        soil_moisture: Soil moisture percentage (0-100)
        temperature: Temperature in Celsius
        humidity: Relative humidity percentage (0-100)
        rainfall: Recent rainfall in mm (0-100, default 0)
    
    Returns:
        dict with irrigation status, reason, and action
    """
    # Ensure values are in valid range
    soil_moisture = max(0, min(100, soil_moisture))
    temperature = max(-10, min(55, temperature))
    humidity = max(0, min(100, humidity))
    rainfall = max(0, min(100, rainfall))
    
    status = ""
    reason = ""
    action = ""
    urgency = "normal"
    
    # Decision logic
    if rainfall > 20:
        # Recent heavy rainfall - no irrigation needed
        status = "Not Required"
        reason = f"Recent rainfall of {rainfall}mm has sufficiently moistened the soil."
        action = "Skip irrigation today. Check field for waterlogging and drainage issues."
        urgency = "low"
        
    elif soil_moisture < 25:
        if temperature > 35:
            status = "Urgently Required"
            reason = f"Soil moisture is critically low ({soil_moisture}%) and temperature is high ({temperature}\u00b0C). Crop is under severe water stress."
            action = "Irrigate immediately during early morning or late evening. Prioritize drought-sensitive areas."
            urgency = "critical"
        elif temperature > 30:
            status = "Required"
            reason = f"Soil moisture is low ({soil_moisture}%) and temperature is elevated ({temperature}\u00b0C). Crop may face water stress."
            action = "Irrigate within the next few hours. Use drip irrigation for water efficiency."
            urgency = "high"
        else:
            status = "Required"
            reason = f"Soil moisture is low ({soil_moisture}%). The crop needs water."
            action = "Schedule irrigation today. Apply water at the base of plants."
            urgency = "high"
            
    elif soil_moisture < 40:
        if temperature > 33 and humidity < 50:
            status = "Recommended"
            reason = f"Soil moisture is moderate ({soil_moisture}%) but high temperature ({temperature}\u00b0C) and low humidity ({humidity}%) will increase water loss."
            action = "Consider light irrigation in the evening to prevent water stress."
            urgency = "moderate"
        elif rainfall > 5:
            status = "Not Required"
            reason = f"Moderate soil moisture ({soil_moisture}%) with recent rainfall ({rainfall}mm). Current moisture should be sufficient."
            action = "Monitor soil moisture again tomorrow. No irrigation needed now."
            urgency = "low"
        else:
            status = "Recommended Soon"
            reason = f"Soil moisture is moderate ({soil_moisture}%). Plan irrigation within 1-2 days."
            action = "Prepare for irrigation. Check water availability and schedule accordingly."
            urgency = "moderate"
            
    elif soil_moisture < 60:
        status = "Not Required"
        reason = f"Soil moisture is adequate ({soil_moisture}%). Current moisture level is suitable for crop growth."
        action = "No irrigation needed. Continue monitoring soil moisture daily."
        urgency = "low"
        
    else:
        status = "Not Required"
        reason = f"Soil moisture is high ({soil_moisture}%). The soil has sufficient water."
        action = "No irrigation needed. Check drainage to prevent waterlogging."
        urgency = "low"
    
    return {
        "status": status,
        "reason": reason,
        "action": action,
        "urgency": urgency,
        "soil_moisture": soil_moisture,
        "temperature": temperature,
        "humidity": humidity,
        "rainfall": rainfall
    }


# ============================================================
# RISK ASSESSMENT SYSTEM
# ============================================================

def calculate_risks(soil_moisture, temperature, humidity, rainfall=0, crop=None, growth_stage=None):
    """
    Calculate various agricultural risks based on environmental conditions.
    
    Args:
        soil_moisture: Soil moisture percentage (0-100)
        temperature: Temperature in Celsius
        humidity: Relative humidity percentage (0-100)
        rainfall: Recent rainfall in mm (0-100)
        crop: Crop name (optional, for crop-specific thresholds)
        growth_stage: Growth stage (optional)
    
    Returns:
        dict with risk levels for various conditions
    """
    risks = {}
    
    # Drought Risk
    if soil_moisture < 20 and temperature > 35:
        risks["drought"] = {"level": "HIGH", "message": "Critical drought conditions. Very low soil moisture with extreme heat."}
    elif soil_moisture < 30 and temperature > 32:
        risks["drought"] = {"level": "MODERATE", "message": "Developing drought conditions. Low moisture and rising temperature."}
    elif soil_moisture < 40 and temperature > 30:
        risks["drought"] = {"level": "LOW", "message": "Early signs of water stress. Monitor soil moisture closely."}
    else:
        risks["drought"] = {"level": "LOW", "message": "No drought risk detected. Soil moisture is adequate."}
    
    # Flood / Waterlogging Risk
    if rainfall > 50 and soil_moisture > 80:
        risks["flood"] = {"level": "HIGH", "message": "High flood/waterlogging risk. Heavy rainfall with saturated soil."}
    elif rainfall > 30 or soil_moisture > 85:
        risks["flood"] = {"level": "MODERATE", "message": "Moderate waterlogging risk. Monitor drainage systems."}
    elif rainfall > 15 and soil_moisture > 70:
        risks["flood"] = {"level": "LOW", "message": "Slight waterlogging possibility. Check field drainage."}
    else:
        risks["flood"] = {"level": "LOW", "message": "No flood or waterlogging risk detected."}
    
    # Heat Stress Risk
    if temperature > 42:
        risks["heat_stress"] = {"level": "HIGH", "message": "Extreme heat! Severe heat stress expected for most crops."}
    elif temperature > 38:
        risks["heat_stress"] = {"level": "MODERATE", "message": "High temperature may cause heat stress. Ensure adequate moisture."}
    elif temperature > 35:
        risks["heat_stress"] = {"level": "LOW", "message": "Warm conditions. Monitor crop for heat-related symptoms."}
    else:
        risks["heat_stress"] = {"level": "LOW", "message": "Temperature is within safe range for crop growth."}
    
    # Excess Rainfall Risk
    if rainfall > 40:
        risks["excess_rain"] = {"level": "HIGH", "message": "Heavy rainfall detected. Risk of crop damage and disease spread."}
    elif rainfall > 20:
        risks["excess_rain"] = {"level": "MODERATE", "message": "Moderate rainfall. Watch for signs of waterlogging."}
    else:
        risks["excess_rain"] = {"level": "LOW", "message": "Rainfall is within normal range."}
    
    # Low Soil Moisture Risk
    if soil_moisture < 20:
        risks["low_moisture"] = {"level": "HIGH", "message": "Critically low soil moisture! Immediate irrigation needed."}
    elif soil_moisture < 35:
        risks["low_moisture"] = {"level": "MODERATE", "message": "Soil moisture is declining. Plan irrigation soon."}
    else:
        risks["low_moisture"] = {"level": "LOW", "message": "Soil moisture is at healthy levels."}
    
    # Overall Risk Level
    levels = [r["level"] for r in risks.values()]
    if "HIGH" in levels:
        overall = "HIGH"
    elif "MODERATE" in levels:
        overall = "MODERATE"
    else:
        overall = "LOW"
    
    risks["overall"] = overall
    
    return risks


# ============================================================
# PEST AND NUTRIENT DIAGNOSIS
# ============================================================

def diagnose_pest_nutrient(crop, growth_stage, leaf_condition, soil_condition, symptoms):
    """
    Simple rule-based system to diagnose possible pest or nutrient issues.
    
    Args:
        crop: Crop name
        growth_stage: Current growth stage
        leaf_condition: Description of leaf condition
        soil_condition: Description of soil condition
        symptoms: Observed symptoms
    
    Returns:
        dict with diagnosis results
    """
    results = []
    symptoms_lower = symptoms.lower() + " " + leaf_condition.lower() + " " + soil_condition.lower()
    
    # Nitrogen Deficiency
    nitrogen_signs = ["yellowing", "yellow leaf", "pale green", "stunted growth", "lower leaf yellow", "light green"]
    if any(sign in symptoms_lower for sign in nitrogen_signs):
        results.append({
            "issue": "Possible Nitrogen Deficiency",
            "type": "Nutrient",
            "severity": "Moderate",
            "symptoms": "Yellowing of older/lower leaves, stunted growth, pale green color.",
            "recommendation": "Apply nitrogen-rich fertilizer (Urea or Ammonium Sulphate). Conduct soil testing for precise dosage. Consider green manuring."
        })
    
    # Phosphorus Deficiency
    phosphorus_signs = ["purple", "dark green", "poor root", "delayed maturity", "small leaves", "purplish"]
    if any(sign in symptoms_lower for sign in phosphorus_signs):
        results.append({
            "issue": "Possible Phosphorus Deficiency",
            "type": "Nutrient",
            "severity": "Moderate",
            "symptoms": "Purple/dark discoloration of leaves, poor root development, delayed maturity.",
            "recommendation": "Apply Single Super Phosphate (SSP) or DAP. Ensure soil pH is suitable (6.0-7.0) for phosphorus availability."
        })
    
    # Potassium Deficiency
    potassium_signs = ["brown edge", "leaf burn", "scorching", "weak stem", "brown margin", "wilting"]
    if any(sign in symptoms_lower for sign in potassium_signs):
        results.append({
            "issue": "Possible Potassium Deficiency",
            "type": "Nutrient",
            "severity": "Moderate",
            "symptoms": "Brown/scorched leaf edges, weak stems, poor disease resistance.",
            "recommendation": "Apply Muriate of Potash (MOP). Ensure balanced fertilization. Add organic matter to improve potassium retention."
        })
    
    # Pest indicators
    pest_signs = ["holes", "chewed", "web", "insect", "bite", "crawl", "spot with hole", "eaten"]
    if any(sign in symptoms_lower for sign in pest_signs):
        results.append({
            "issue": "Possible Pest Attack",
            "type": "Pest",
            "severity": "High",
            "symptoms": "Visible holes in leaves, chewed leaf edges, insect traces or webbing.",
            "recommendation": "Identify the specific pest. Use integrated pest management (IPM). Apply neem oil spray for general protection. Consult local agricultural officer for specific pesticide recommendations."
        })
    
    # Fungal infection
    fungal_signs = ["spot", "mold", "fungus", "powder", "rot", "blight", "rust", "mildew"]
    if any(sign in symptoms_lower for sign in fungal_signs):
        results.append({
            "issue": "Possible Fungal Infection",
            "type": "Disease",
            "severity": "High",
            "symptoms": "Visible spots, mold, or discoloration on leaves indicating fungal activity.",
            "recommendation": "Remove and destroy affected plant parts. Apply fungicide (Mancozeb or Carbendazim). Improve air circulation and avoid overhead irrigation."
        })
    
    # If no specific issue found
    if not results:
        results.append({
            "issue": "No Specific Issue Detected",
            "type": "Information",
            "severity": "Low",
            "symptoms": "Based on the provided information, no clear pest or nutrient deficiency was identified.",
            "recommendation": "Continue regular monitoring. Conduct a soil test for detailed nutrient analysis. If symptoms persist, consult a local agricultural expert."
        })
    
    return {
        "crop": crop,
        "growth_stage": growth_stage,
        "diagnoses": results,
        "disclaimer": "These are preliminary recommendations based on observable symptoms. For accurate diagnosis, consult a qualified agricultural expert."
    }


# ============================================================
# SMART RECOMMENDATIONS ENGINE
# ============================================================

def generate_recommendations(soil_moisture, temperature, humidity, crop, growth_stage,
                             disease_result=None, pest_result=None, risk_level="LOW",
                             irrigation_result=None):
    """
    Generate comprehensive farmer-friendly recommendations by combining
    all available data from different analysis modules.
    
    Args:
        soil_moisture: Current soil moisture %
        temperature: Current temperature in Celsius
        humidity: Current humidity %
        crop: Crop name
        growth_stage: Current growth stage
        disease_result: Result from disease detection (optional)
        pest_result: Result from pest/nutrient diagnosis (optional)
        risk_level: Overall risk level (LOW/MODERATE/HIGH)
        irrigation_result: Result from irrigation analysis (optional)
    
    Returns:
        dict with categorized recommendations
    """
    recommendations = {
        "immediate": [],   # Actions needed right now
        "today": [],       # Actions for today
        "this_week": [],   # Actions for this week
        "general": []      # General advice
    }
    
    # --- Irrigation-based recommendations ---
    if irrigation_result:
        if irrigation_result["urgency"] == "critical":
            recommendations["immediate"].append(
                "URGENT: Irrigate your field immediately. Crop is under severe water stress."
            )
        elif irrigation_result["urgency"] == "high":
            recommendations["today"].append(
                "Schedule irrigation today. Your crop needs water soon."
            )
        elif irrigation_result["urgency"] == "moderate":
            recommendations["today"].append(
                "Plan irrigation within the next day or two to maintain healthy moisture levels."
            )
    
    # --- Temperature-based recommendations ---
    if temperature > 40:
        recommendations["immediate"].append(
            "Extreme heat detected. Provide shade protection if possible. Irrigate during early morning or late evening."
        )
    elif temperature > 35:
        recommendations["today"].append(
            "High temperature expected. Ensure adequate soil moisture to prevent heat stress."
        )
    
    # --- Humidity-based recommendations ---
    if humidity > 80:
        recommendations["today"].append(
            "High humidity increases risk of fungal diseases. Inspect crop for any signs of infection."
        )
        recommendations["this_week"].append(
            "Monitor crop closely for powdery mildew or leaf blight symptoms due to high humidity."
        )
    elif humidity < 30:
        recommendations["today"].append(
            "Very low humidity. Consider light irrigation or misting to prevent moisture stress."
        )
    
    # --- Disease-based recommendations ---
    if disease_result and disease_result.get("status") == "success":
        if disease_result["condition"] == "Disease Detected":
            recommendations["immediate"].append(
                f"Disease detected: {disease_result['prediction']}. {disease_result['action']}"
            )
        elif disease_result["condition"] == "Pest Damage Detected":
            recommendations["immediate"].append(
                f"Pest damage detected. {disease_result['action']}"
            )
    
    # --- Pest/nutrient-based recommendations ---
    if pest_result and pest_result.get("diagnoses"):
        for diag in pest_result["diagnoses"]:
            if diag["severity"] == "High":
                recommendations["immediate"].append(
                    f"{diag['issue']}: {diag['recommendation']}"
                )
            elif diag["severity"] == "Moderate":
                recommendations["today"].append(
                    f"{diag['issue']}: {diag['recommendation']}"
                )
    
    # --- Risk-based recommendations ---
    if risk_level == "HIGH":
        recommendations["immediate"].append(
            "HIGH RISK detected! Take immediate protective action for your crop."
        )
    elif risk_level == "MODERATE":
        recommendations["today"].append(
            "Moderate risk conditions detected. Stay alert and monitor your field closely."
        )
    
    # --- Growth stage recommendations ---
    if growth_stage:
        stage = growth_stage.lower()
        if "seedling" in stage:
            recommendations["this_week"].append(
                "Seedling stage: Ensure gentle irrigation. Protect young plants from extreme weather."
            )
        elif "flowering" in stage:
            recommendations["this_week"].append(
                "Flowering stage: Maintain consistent moisture. Avoid water stress during this critical period."
            )
        elif "harvest" in stage:
            recommendations["general"].append(
                "Approaching harvest: Reduce irrigation gradually. Check crop readiness."
            )
    
    # --- General crop care ---
    recommendations["general"].append(
        "Inspect your field daily for early signs of any issues."
    )
    recommendations["general"].append(
        "Maintain proper record of all activities for future reference."
    )
    
    # If no specific recommendations
    total_recs = sum(len(v) for v in recommendations.values())
    if total_recs <= 2:
        recommendations["general"].insert(0,
            "Your farm conditions look good! Continue regular monitoring and maintenance."
        )
    
    return recommendations


# ============================================================
# SENSOR DATA SIMULATION (for Live Demo)
# ============================================================

def generate_simulated_sensor_data():
    """
    Generate realistic random sensor data for demonstration.
    Useful for the Live Farm Simulation feature during SIH presentation.
    
    Returns:
        dict with simulated sensor values
    """
    return {
        "soil_moisture": round(random.uniform(15, 85), 1),
        "temperature": round(random.uniform(22, 44), 1),
        "humidity": round(random.uniform(25, 90), 1),
        "rainfall": round(random.uniform(0, 30), 1)
    }


# ============================================================
# FULL FARM ANALYSIS (combines all modules)
# ============================================================

def analyze_farm(soil_moisture, temperature, humidity, rainfall=0, crop=None, growth_stage=None):
    """
    Complete farm analysis combining all modules.
    Used by the Live Farm Simulation feature.
    
    Returns:
        dict with irrigation, risks, and recommendations
    """
    # Get irrigation recommendation
    irrigation = calculate_irrigation(soil_moisture, temperature, humidity, rainfall)
    
    # Get risk assessment
    risks = calculate_risks(soil_moisture, temperature, humidity, rainfall, crop, growth_stage)
    
    # Get smart recommendations
    recommendations = generate_recommendations(
        soil_moisture=soil_moisture,
        temperature=temperature,
        humidity=humidity,
        crop=crop or "General Crop",
        growth_stage=growth_stage or "Vegetative",
        risk_level=risks["overall"],
        irrigation_result=irrigation
    )
    
    # Determine crop stress level
    if soil_moisture < 25 and temperature > 35:
        stress_level = "Severe"
    elif soil_moisture < 35 or temperature > 38:
        stress_level = "Moderate"
    elif soil_moisture > 80:
        stress_level = "Waterlogged"
    else:
        stress_level = "Normal"
    
    return {
        "irrigation": irrigation,
        "risks": risks,
        "recommendations": recommendations,
        "stress_level": stress_level,
        "input_data": {
            "soil_moisture": soil_moisture,
            "temperature": temperature,
            "humidity": humidity,
            "rainfall": rainfall,
            "crop": crop or "Not specified",
            "growth_stage": growth_stage or "Not specified"
        }
    }
