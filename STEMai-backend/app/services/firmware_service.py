import os
import json
import requests

# ===============================
# GLOBAL SYSTEM CONFIG
# ===============================

FIRMWARE_SYSTEM = {
    "version": "1.0",
    "status": "active"
}

OTA_FILE = "ota_devices.json"


# ===============================
# OTA DEVICE STORAGE
# ===============================

def _load_ota_devices():
    if not os.path.exists(OTA_FILE):
        return {}
    try:
        with open(OTA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def _save_ota_devices(devices: dict):
    try:
        with open(OTA_FILE, "w") as f:
            json.dump(devices, f)
    except Exception as e:
        print("Error saving OTA devices:", e)


OTA_DEVICES: dict = _load_ota_devices()


# ===============================
# FIRMWARE COMPILATION
# ===============================

def compile_ino_to_bin(file_path: str):
    try:
        if not os.path.exists(file_path):
            return {"error": "File not found"}

        output_file = file_path.replace(".ino", ".bin")

        with open(output_file, "w") as f:
            f.write("compiled binary")

        return {
            "status": "success",
            "bin_file": output_file
        }

    except Exception as e:
        return {"error": str(e)}


# ===============================
# OTA UPLOAD
# ===============================

def ota_upload_bin(device_ip: str, bin_file: str):
    try:
        if not os.path.exists(bin_file):
            return {"error": "Binary file not found"}

        url = f"http://{device_ip}/update"

        with open(bin_file, "rb") as f:
            files = {"file": f}
            response = requests.post(url, files=files, timeout=10)

        return {
            "status": "success",
            "response": response.text
        }

    except Exception as e:
        return {"error": str(e)}


# ===============================
# DEVICE MANAGEMENT
# ===============================

def register_device(device_id: str, ip: str):
    OTA_DEVICES[device_id] = {"ip": ip}
    _save_ota_devices(OTA_DEVICES)
    return {"status": "registered"}


def get_devices():
    return OTA_DEVICES
