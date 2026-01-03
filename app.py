from flask import Flask, jsonify, request, render_template
from twilio.rest import Client
from datetime import datetime
from collections import defaultdict
from flask import render_template
app = Flask(__name__)

# =========================
# HOME
# =========================

@app.route("/")
def dashboard():
    return render_template("index.html")
# =========================

twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)

# =========================
# GLOBAL STATE (FIXED)
# =========================
latest_data = {
    "Room1": {},
    "Room2": {}
}

history_data = {
    "Room1": [],
    "Room2": []
}

rover_mode = "IDLE"
emergency_active = False

# =========================
# LIVE DATA
# =========================
@app.route("/latest")
def latest():
    room = request.args.get("room", "Room1")
    data = latest_data.get(room, {})
    return jsonify(data)


@app.route("/update", methods=["POST"])
def update():
    data = request.json
    room = data.get("room", "Room1")

    data["time"] = datetime.now().strftime("%H:%M:%S")

    # Store latest
    latest_data[room] = data

    # Store history
    history_data[room].append({
        "time": data["time"],
        "date": datetime.now().strftime("%Y-%m-%d"),
        "aqi": data.get("aqi", 0)
    })

    print(f"📥 Data stored in {room}")

    return jsonify({"status": "ok", "room": room})
# =========================
# HISTORY (ROOM + MODE)
# =========================
@app.route("/history")
def history():
    room = request.args.get("room", "Room1")
    mode = request.args.get("mode", "hourly")

    data = history_data.get(room, [])

    if mode == "hourly":
        return jsonify(data[-20:])

    daily = defaultdict(list)
    for d in data:
        daily[d["date"]].append(d["aqi"])

    result = [
        {"date": date, "aqi": sum(v)//len(v)}
        for date, v in daily.items()
    ]

    return jsonify(result)

# =========================
# ROVER CONTROL
# =========================
@app.route("/control", methods=["POST"])
def control():
    global rover_mode
    rover_mode = request.json.get("command", "IDLE").upper()
    print("ROVER MODE:", rover_mode)
    return jsonify({"status": "received", "mode": rover_mode})

@app.route("/rover/status")
def rover_status():
    return jsonify({"mode": rover_mode})

# =========================
# EMERGENCY (UNCHANGED)
# =========================
@app.route("/emergency", methods=["POST"])
def emergency():
    global emergency_active
    emergency_active = True

    try:
        twilio_client.messages.create(
            body="🚨 AQI ROVER ALERT!\nEmergency Activated.",
            from_=TWILIO_NUMBER,
            to=ALERT_TO
        )
        print("✅ SMS SENT")
    except Exception as e:
        print("❌ SMS ERROR:", e)

    return jsonify({"status": "emergency_on"})

@app.route("/emergency/clear", methods=["POST"])
def clear_emergency():
    global emergency_active
    emergency_active = False
    print("🟢 Emergency Cleared")
    return jsonify({"status": "emergency_off"})

# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

