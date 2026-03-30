import textwrap


ALLOWED_TYPES = {
    "esp32",
    "led_red",
    "led_green",
    "led_blue",
    "resistor",
    "buzzer",
    "servo",
    "motor",
    "button",
    "potentiometer",
    "ldr",
    "ultrasonic",
    "dht11",
}

ALLOWED_ESP32_PINS = {
    "3V3", "EN", "VP", "VN", "34", "35", "32", "33",
    "25", "26", "27", "14", "12",
    "GND1", "23", "22", "TX", "RX", "GND2",
    "21", "19", "18", "5", "17", "16", "4"
}

ALLOWED_PART_PINS = {
    "esp32": ALLOWED_ESP32_PINS,
    "led_red": {"anode", "cathode"},
    "led_green": {"anode", "cathode"},
    "led_blue": {"anode", "cathode"},
    "resistor": {"a", "b"},
    "buzzer": {"pos", "neg"},
    "servo": {"sig", "vcc", "gnd"},
    "motor": {"p1", "p2"},
    "button": {"p1", "p2"},
    "potentiometer": {"vcc", "sig", "gnd"},
    "ldr": {"p1", "p2"},
    "ultrasonic": {"vcc", "trig", "echo", "gnd"},
    "dht11": {"vcc", "data", "gnd"},
}


def build_agentic_prompt() -> str:
    return textwrap.dedent("""
    You are the STEMbotix ESP32 Simulator Agentic Planner.

    Return ONLY valid JSON.
    Do not return markdown.
    Do not return explanation outside JSON.

    Your task:
    Given a user prompt and optional current circuit state, generate a full simulator-ready project plan.

    Allowed component types:
    esp32, led_red, led_green, led_blue, resistor, buzzer, servo, motor,
    button, potentiometer, ldr, ultrasonic, dht11

    Allowed ESP32 pins:
    3V3, EN, VP, VN, 34, 35, 32, 33, 25, 26, 27, 14, 12,
    GND1, 23, 22, TX, RX, GND2, 21, 19, 18, 5, 17, 16, 4

    Allowed non-ESP32 pins:
    led_red / led_green / led_blue => anode, cathode
    resistor => a, b
    buzzer => pos, neg
    servo => sig, vcc, gnd
    motor => p1, p2
    button => p1, p2
    potentiometer => vcc, sig, gnd
    ldr => p1, p2
    ultrasonic => vcc, trig, echo, gnd
    dht11 => vcc, data, gnd

    Important rules:
    - Always include exactly one esp32.
    - Only use the allowed components and allowed pins.
    - Layout must be clean and readable in a large workspace.
    - Use x/y coordinates.
    - Generate all required power, ground, and signal connections.
    - Keep project suitable for beginners.
    - Generate simulator-safe Arduino-style code only.
    - Do NOT use external libraries.
    - Do NOT use unsupported APIs.
    - Keep code compatible with this simulator command subset:
      pinMode, digitalWrite, digitalRead, analogRead, delay,
      Serial.begin, Serial.print, Serial.println,
      servoWrite, tone, noTone, getDistance, dhtReadTemp, dhtReadHumidity

    Preferred pin mapping:
    - dht11.data -> 4
    - ultrasonic.trig -> 5
    - ultrasonic.echo -> 18
    - servo.sig -> 19
    - buzzer.pos -> 21
    - button.p1 -> 22
    - ldr.p1 -> 34

    Suggested layout:
    - esp32 near left-center
    - sensors in middle
    - outputs on right
    - keep all items visible and not overlapping

    Return JSON in this exact shape:
    {
      "reply": "short helpful reply",
      "project": {
        "title": "project title",
        "description": "what the project does",
        "components": [
          {"type": "esp32", "x": 120, "y": 180},
          {"type": "ultrasonic", "x": 340, "y": 80}
        ],
        "connections": [
          {
            "from": {"type": "esp32", "pin": "5", "index": 0},
            "to": {"type": "ultrasonic", "pin": "trig", "index": 0}
          }
        ],
        "code": "generated simulator-safe code",
        "steps": [
          "Click Run",
          "Open Serial Monitor",
          "Change sensor values"
        ],
        "hardware_suggestion": "Build this with STEMbotix AI & IoT Kit."
      }
    }
    """)


def _safe_int(v, default):
    try:
        return int(v)
    except Exception:
        return default


def _normalize_component(c):
    if not isinstance(c, dict):
        return None

    ctype = str(c.get("type", "")).strip()
    if ctype not in ALLOWED_TYPES:
        return None

    x = _safe_int(c.get("x", 100), 100)
    y = _safe_int(c.get("y", 100), 100)

    return {
        "type": ctype,
        "x": max(20, min(2000, x)),
        "y": max(20, min(2000, y)),
    }


def _normalize_connection(conn, type_counts):
    if not isinstance(conn, dict):
        return None

    from_obj = conn.get("from")
    to_obj = conn.get("to")

    if not isinstance(from_obj, dict) or not isinstance(to_obj, dict):
        return None

    f_type = str(from_obj.get("type", "")).strip()
    t_type = str(to_obj.get("type", "")).strip()
    f_pin = str(from_obj.get("pin", "")).strip()
    t_pin = str(to_obj.get("pin", "")).strip()
    f_idx = _safe_int(from_obj.get("index", 0), 0)
    t_idx = _safe_int(to_obj.get("index", 0), 0)

    if f_type not in ALLOWED_TYPES or t_type not in ALLOWED_TYPES:
        return None

    if f_pin not in ALLOWED_PART_PINS.get(f_type, set()):
        return None

    if t_pin not in ALLOWED_PART_PINS.get(t_type, set()):
        return None

    if f_idx < 0 or t_idx < 0:
        return None

    if f_idx >= type_counts.get(f_type, 0):
        return None

    if t_idx >= type_counts.get(t_type, 0):
        return None

    return {
        "from": {"type": f_type, "pin": f_pin, "index": f_idx},
        "to": {"type": t_type, "pin": t_pin, "index": t_idx},
    }


def validate_project_json(data):
    if not isinstance(data, dict):
        return {
            "reply": "Invalid response format.",
            "project": {
                "title": "Untitled Project",
                "description": "",
                "components": [],
                "connections": [],
                "code": "",
                "steps": [],
                "hardware_suggestion": ""
            }
        }

    project = data.get("project", {})
    if not isinstance(project, dict):
        project = {}

    raw_components = project.get("components", [])
    if not isinstance(raw_components, list):
        raw_components = []

    components = []
    for c in raw_components:
        norm = _normalize_component(c)
        if norm:
            components.append(norm)

    # always ensure exactly one esp32 exists
    esp32_count = sum(1 for c in components if c["type"] == "esp32")
    if esp32_count == 0:
        components.insert(0, {"type": "esp32", "x": 120, "y": 180})
    elif esp32_count > 1:
        found_one = False
        filtered = []
        for c in components:
            if c["type"] == "esp32":
                if found_one:
                    continue
                found_one = True
            filtered.append(c)
        components = filtered

    type_counts = {}
    for c in components:
        type_counts[c["type"]] = type_counts.get(c["type"], 0) + 1

    raw_connections = project.get("connections", [])
    if not isinstance(raw_connections, list):
        raw_connections = []

    connections = []
    seen = set()
    for conn in raw_connections:
        norm = _normalize_connection(conn, type_counts)
        if not norm:
            continue

        key = (
            norm["from"]["type"], norm["from"]["index"], norm["from"]["pin"],
            norm["to"]["type"], norm["to"]["index"], norm["to"]["pin"]
        )
        rev = (
            norm["to"]["type"], norm["to"]["index"], norm["to"]["pin"],
            norm["from"]["type"], norm["from"]["index"], norm["from"]["pin"]
        )
        if key in seen or rev in seen:
            continue
        seen.add(key)
        connections.append(norm)

    code = project.get("code", "")
    if not isinstance(code, str):
        code = ""

    steps = project.get("steps", [])
    if not isinstance(steps, list):
        steps = []
    steps = [str(s).strip() for s in steps if str(s).strip()]

    if not steps:
        steps = [
            "Click Run",
            "Open Serial Monitor",
            "Adjust sensor values and observe outputs"
        ]

    hardware_suggestion = project.get("hardware_suggestion", "")
    if not isinstance(hardware_suggestion, str):
        hardware_suggestion = ""

    title = project.get("title", "Untitled Project")
    if not isinstance(title, str) or not title.strip():
        title = "Untitled Project"

    description = project.get("description", "")
    if not isinstance(description, str):
        description = ""

    return {
        "reply": str(data.get("reply", "Project generated.")).strip() or "Project generated.",
        "project": {
            "title": title.strip(),
            "description": description.strip(),
            "components": components,
            "connections": connections,
            "code": code,
            "steps": steps,
            "hardware_suggestion": hardware_suggestion.strip(),
        }
    }