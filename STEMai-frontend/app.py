# =========================
# VERCEL FRONTEND app.py
# Only serves HTML templates.
# ALL /api/* calls are proxied to VPS via vercel.json
# =========================
import os
from flask import Flask, render_template, send_from_directory
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

BLOCKZIE_DIR = os.path.join(os.path.dirname(__file__), "static", "blockzie")

# ── Pages ────────────────────────────────────────────────────

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/ide")
def ide():
    return render_template("ide.html")

@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")

@app.route("/iot")
def iot_dashboard():
    return render_template("dashboard.html")

@app.route("/simulator")
def simulator_page():
    return render_template("simulator.html")

@app.route("/esp32-simulator")
def esp32_simulator_page():
    return render_template("Esp32 simulator.html")

@app.route("/blockzie")
def blockzie_app():
    return send_from_directory(BLOCKZIE_DIR, "index.html")

@app.route("/blockzie/<path:filename>")
def blockzie_static(filename):
    return send_from_directory(BLOCKZIE_DIR, filename)

@app.route("/blockzie_bridge")
def blockzie_bridge():
    return render_template("blockzie_bridge.html")

@app.route("/programming-lab")
def programming_lab():
    return render_template("programming_lab.html")

# ── Run ──────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=False)