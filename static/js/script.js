/**
 * AI Smart Farming Assistant - Client JavaScript
 * Handles: Mobile menu, sensor simulation, live farm analysis, form validation
 */

// ============================================================
// MOBILE SIDEBAR TOGGLE
// ============================================================

function toggleSidebar() {
    var sidebar = document.querySelector('.sidebar');
    var overlay = document.querySelector('.sidebar-overlay');
    sidebar.classList.toggle('open');
    overlay.classList.toggle('active');
}

function closeSidebar() {
    var sidebar = document.querySelector('.sidebar');
    var overlay = document.querySelector('.sidebar-overlay');
    sidebar.classList.remove('open');
    overlay.classList.remove('active');
}

// Close sidebar on overlay click
document.addEventListener('DOMContentLoaded', function() {
    var overlay = document.querySelector('.sidebar-overlay');
    if (overlay) {
        overlay.addEventListener('click', closeSidebar);
    }
});

// ============================================================
// GENERATE SIMULATED SENSOR DATA
// ============================================================

function generateSensorData() {
    var btn = document.getElementById('generateBtn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Generating...';
    }

    fetch('/api/generate-sensor-data')
        .then(function(response) { return response.json(); })
        .then(function(data) {
            // Fill in the form fields
            var sm = document.getElementById('sim_soil_moisture');
            var temp = document.getElementById('sim_temperature');
            var hum = document.getElementById('sim_humidity');
            var rain = document.getElementById('sim_rainfall');

            if (sm) sm.value = data.soil_moisture;
            if (temp) temp.value = data.temperature;
            if (hum) hum.value = data.humidity;
            if (rain) rain.value = data.rainfall;

            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '&#x1f4ca; Generate Sensor Data';
            }
        })
        .catch(function(err) {
            console.error('Error generating sensor data:', err);
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '&#x1f4ca; Generate Sensor Data';
            }
        });
}

// ============================================================
// LIVE FARM ANALYSIS (SIH Demo Feature)
// ============================================================

function analyzeFarm() {
    var btn = document.getElementById('analyzeBtn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Analyzing...';
    }

    var payload = {
        soil_moisture: parseFloat(document.getElementById('sim_soil_moisture').value) || 50,
        temperature: parseFloat(document.getElementById('sim_temperature').value) || 30,
        humidity: parseFloat(document.getElementById('sim_humidity').value) || 50,
        rainfall: parseFloat(document.getElementById('sim_rainfall').value) || 0,
        crop: document.getElementById('sim_crop') ? document.getElementById('sim_crop').value : null,
        growth_stage: document.getElementById('sim_growth_stage') ? document.getElementById('sim_growth_stage').value : null
    };

    fetch('/api/analyze-farm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        displayAnalysisResults(data);
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '&#x1f50d; Analyze Farm';
        }
    })
    .catch(function(err) {
        console.error('Error analyzing farm:', err);
        alert('Error analyzing farm data. Please try again.');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '&#x1f50d; Analyze Farm';
        }
    });
}

function displayAnalysisResults(data) {
    var resultsDiv = document.getElementById('analysis-results');
    if (!resultsDiv) return;

    var irrigation = data.irrigation;
    var risks = data.risks;
    var recs = data.recommendations;
    var input = data.input_data;

    // Build irrigation section
    var irrigationColor = irrigation.urgency === 'critical' ? 'danger' :
                          irrigation.urgency === 'high' ? 'warning' :
                          irrigation.urgency === 'moderate' ? 'info' : 'success';

    var html = '<div class="sim-results">';
    html += '<h3>&#x1f4ca; Analysis Results</h3>';

    // Input summary
    html += '<div class="stats-grid" style="margin-bottom:20px;">';
    html += '<div class="stat-card"><div class="stat-label">Soil Moisture</div><div class="stat-value">' + input.soil_moisture + '%</div></div>';
    html += '<div class="stat-card"><div class="stat-label">Temperature</div><div class="stat-value">' + input.temperature + '&deg;C</div></div>';
    html += '<div class="stat-card"><div class="stat-label">Humidity</div><div class="stat-value">' + input.humidity + '%</div></div>';
    html += '<div class="stat-card"><div class="stat-label">Crop Stress</div><div class="stat-value">' + data.stress_level + '</div></div>';
    html += '</div>';

    // Irrigation
    html += '<div class="card" style="border-left:4px solid var(--' + irrigationColor + ');">';
    html += '<h4 style="margin-bottom:8px;">&#x1f4a7; Irrigation Recommendation</h4>';
    html += '<span class="badge badge-' + irrigationColor + '">' + irrigation.status + '</span>';
    html += '<p style="margin-top:8px;font-size:14px;">' + irrigation.reason + '</p>';
    html += '<p style="margin-top:6px;font-size:13px;color:var(--text-secondary);"><strong>Action:</strong> ' + irrigation.action + '</p>';
    html += '</div>';

    // Risk Assessment
    html += '<div class="risk-grid" style="margin:20px 0;">';
    var riskTypes = [
        { key: 'drought', label: 'Drought Risk', icon: '&#x2600;&#xfe0f;' },
        { key: 'flood', label: 'Flood Risk', icon: '&#x1f30a;' },
        { key: 'heat_stress', label: 'Heat Stress', icon: '&#x1f525;' },
        { key: 'excess_rain', label: 'Excess Rain', icon: '&#x1f327;&#xfe0f;' },
        { key: 'low_moisture', label: 'Low Moisture', icon: '&#x1f4a7;' }
    ];

    riskTypes.forEach(function(rt) {
        var risk = risks[rt.key];
        if (risk) {
            var levelClass = risk.level.toLowerCase();
            html += '<div class="risk-card risk-' + levelClass + '">';
            html += '<div class="risk-label">' + rt.icon + ' ' + rt.label + '</div>';
            html += '<div class="risk-level">' + risk.level + '</div>';
            html += '<div class="risk-message">' + risk.message + '</div>';
            html += '</div>';
        }
    });
    html += '</div>';

    // Overall Risk
    var overallColor = risks.overall === 'HIGH' ? 'danger' : risks.overall === 'MODERATE' ? 'warning' : 'success';
    html += '<div style="text-align:center;margin:16px 0;">';
    html += '<span style="font-size:14px;color:var(--text-secondary);">Overall Risk Level: </span>';
    html += '<span class="badge badge-' + overallColor + '" style="font-size:16px;padding:6px 18px;">' + risks.overall + '</span>';
    html += '</div>';

    // Recommendations
    html += '<div style="margin-top:20px;">';
    html += '<div class="section-title">Smart Recommendations</div>';

    if (recs.immediate.length > 0) {
        html += '<div class="rec-section"><h4>&#x26a0;&#xfe0f; Immediate Actions</h4>';
        recs.immediate.forEach(function(r) {
            html += '<div class="rec-item urgent">' + r + '</div>';
        });
        html += '</div>';
    }

    if (recs.today.length > 0) {
        html += '<div class="rec-section"><h4>&#x1f4c5; Today</h4>';
        recs.today.forEach(function(r) {
            html += '<div class="rec-item moderate">' + r + '</div>';
        });
        html += '</div>';
    }

    if (recs.this_week.length > 0) {
        html += '<div class="rec-section"><h4>&#x1f4c6; This Week</h4>';
        recs.this_week.forEach(function(r) {
            html += '<div class="rec-item">' + r + '</div>';
        });
        html += '</div>';
    }

    if (recs.general.length > 0) {
        html += '<div class="rec-section"><h4>&#x1f4cb; General Advice</h4>';
        recs.general.forEach(function(r) {
            html += '<div class="rec-item">' + r + '</div>';
        });
        html += '</div>';
    }

    html += '</div>';
    html += '<div class="disclaimer">&#x26a0;&#xfe0f; These are prototype recommendations based on sensor data analysis. For critical decisions, always consult a qualified agricultural expert.</div>';
    html += '</div>';

    resultsDiv.innerHTML = html;
    resultsDiv.scrollIntoView({ behavior: 'smooth' });
}

// ============================================================
// SAVE SIMULATION TO DATABASE
// ============================================================

function saveSimulation() {
    var payload = {
        soil_moisture: parseFloat(document.getElementById('sim_soil_moisture').value) || 0,
        temperature: parseFloat(document.getElementById('sim_temperature').value) || 0,
        humidity: parseFloat(document.getElementById('sim_humidity').value) || 0,
        rainfall: parseFloat(document.getElementById('sim_rainfall').value) || 0,
        irrigation_status: '',
        irrigation_reason: '',
        recommendation: 'Saved from Live Farm Simulation',
        risk_level: 'LOW'
    };

    fetch('/api/save-simulation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        if (data.status === 'saved') {
            alert('Simulation results saved to history!');
        }
    })
    .catch(function(err) {
        console.error('Error saving:', err);
    });
}

// ============================================================
// IMAGE UPLOAD PREVIEW
// ============================================================

function previewImage(input) {
    var preview = document.getElementById('image-preview');
    if (!preview) return;

    if (input.files && input.files[0]) {
        var reader = new FileReader();
        reader.onload = function(e) {
            preview.src = e.target.result;
            preview.style.display = 'block';
        };
        reader.readAsDataURL(input.files[0]);
    }
}

// ============================================================
// FORM VALIDATION HELPERS
// ============================================================

function validateRequired(formId) {
    var form = document.getElementById(formId);
    if (!form) return true;

    var inputs = form.querySelectorAll('[required]');
    var valid = true;

    inputs.forEach(function(input) {
        if (!input.value.trim()) {
            input.style.borderColor = '#c62828';
            valid = false;
        } else {
            input.style.borderColor = '';
        }
    });

    return valid;
}

// ============================================================
// AUTO-DISMISS FLASH MESSAGES
// ============================================================

document.addEventListener('DOMContentLoaded', function() {
    var flashes = document.querySelectorAll('.flash');
    flashes.forEach(function(flash) {
        setTimeout(function() {
            flash.style.opacity = '0';
            flash.style.transition = 'opacity 0.3s';
            setTimeout(function() { flash.remove(); }, 300);
        }, 5000);
    });
});

// ============================================================
// LIVE WOKWI SENSOR DATA (auto-updating dashboard)
// ============================================================
// Fetches GET /api/latest-sensor-data every 5 seconds and updates
// both the Dashboard "LIVE FARM SENSOR DATA" section (live- IDs)
// and the IoT Simulation page (iot- IDs). No fake data is shown:
// if nothing has been received yet, placeholders stay as "--".
// ============================================================

function setText(id, value) {
    var el = document.getElementById(id);
    if (el) el.innerHTML = value;
}

function riskBadge(level, prefix) {
    if (!level || level === '--') return '--';
    var klass = 'badge-low';
    if (level === 'HIGH') klass = 'badge-high';
    else if (level === 'MODERATE') klass = 'badge-moderate';
    return prefix + '<span class="badge ' + klass + '">' + level + '</span>';
}

function loadLatestSensorData() {
    fetch('/api/latest-sensor-data')
        .then(function(response) { return response.json(); })
        .then(function(data) {
            // --- Dashboard section ---
            if (data.has_data) {
                setText('live-soil-moisture', data.soil_moisture + '%');
                setText('live-temperature', data.temperature + '&deg;C');
                setText('live-humidity', data.humidity + '%');
                setText('live-rainfall', data.rainfall + ' mm');
                setText('live-irrigation', data.irrigation_status);
                setText('live-drought', riskBadge(data.drought_risk, ''));
                setText('live-heat', riskBadge(data.heat_risk, ''));
                setText('live-recommendation', data.recommendation);

                if (data.connected) {
                    setText('live-connection-badge', '&#x1f7e2; Live Sensor: Connected');
                    setText('live-sensor-status', '&#x1f7e2;');
                } else {
                    setText('live-connection-badge', '&#x1f534; Live Sensor: Offline');
                    setText('live-sensor-status', '&#x1f534;');
                }
                setText('live-last-updated',
                    'Last updated: ' + data.seconds_ago + ' seconds ago (' + data.last_updated + ')');
            } else {
                setText('live-connection-badge', '&#x1f534; Wokwi Sensor: Offline / No recent data');
                setText('live-sensor-status', '&#x1f534;');
                setText('live-last-updated', 'No live sensor data received yet.');
                setText('live-recommendation', 'No live sensor data received yet. Start the Wokwi ESP32 simulation to push readings here.');
            }

            // --- IoT Simulation page section ---
            if (data.has_data) {
                setText('iot-soil-moisture', data.soil_moisture + '%');
                setText('iot-temperature', data.temperature + '&deg;C');
                setText('iot-humidity', data.humidity + '%');
                setText('iot-rainfall', data.rainfall + ' mm');
                setText('iot-irrigation', data.irrigation_status);
                setText('iot-drought', riskBadge(data.drought_risk, ''));
                setText('iot-heat', riskBadge(data.heat_risk, ''));
                setText('iot-recommendation', data.recommendation);

                if (data.connected) {
                    setText('iot-connection-badge', '&#x1f7e2; Wokwi Sensor: Connected');
                    setText('iot-last-updated',
                        'Last received: ' + data.seconds_ago + ' seconds ago (' + data.last_updated + ')');
                } else {
                    setText('iot-connection-badge', '&#x1f534; Wokwi Sensor: Offline / No recent data');
                    setText('iot-last-updated',
                        'Last reading is over 30 seconds old. Is the Wokwi simulation running?');
                }
            } else {
                setText('iot-connection-badge', '&#x1f534; Wokwi Sensor: Offline / No recent data');
                setText('iot-last-updated', 'No live sensor data received yet.');
                setText('iot-recommendation', 'No data yet. Start the Wokwi ESP32 simulation so it can POST readings to /api/sensor-data.');
            }
        })
        .catch(function(err) {
            console.error('Error fetching latest sensor data:', err);
        });
}

// Start polling every 5 seconds and do one immediate load
document.addEventListener('DOMContentLoaded', function() {
    loadLatestSensorData();
    setInterval(loadLatestSensorData, 5000);
});
