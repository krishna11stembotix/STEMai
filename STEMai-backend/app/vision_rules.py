from dataclasses import dataclass
from typing import List, Dict

@dataclass
class RuleFinding:
    level: str   # "warning" | "error" | "tip"
    message: str

def rules_check(meta: Dict) -> List[RuleFinding]:
    """
    meta is model-extracted facts (best effort), e.g.:
    {
      "board": "ESP32",
      "has_common_gnd": True/False/Unknown,
      "sensor_voltage": 5 or 3.3 or None,
      "uses_adc_pin": True/False/Unknown,
      "uses_pwm_pin": True/False/Unknown,
      "breadboard_rails_connected": True/False/Unknown
    }
    """
    f = []
    board = (meta.get("board") or "").lower()

    # GND
    if meta.get("has_common_gnd") is False:
        f.append(RuleFinding("error", "No common GND detected. Connect GND of sensor + board + power together."))

    # Voltage
    v = meta.get("sensor_voltage")
    if "esp32" in board and v == 5:
        f.append(RuleFinding("warning", "ESP32 GPIO is NOT 5V tolerant. Use 3.3V sensor or level shifter."))

    # ADC
    if "esp32" in board and meta.get("uses_adc_pin") is False:
        f.append(RuleFinding("tip", "If reading analog sensors, use ESP32 ADC pins (ADC1 preferred)."))

    # PWM
    if meta.get("uses_pwm_pin") is False:
        f.append(RuleFinding("tip", "For motors/servos/LED dimming, use PWM-capable pins and set correct PWM frequency."))

    # Rails
    if meta.get("breadboard_rails_connected") is False:
        f.append(RuleFinding("warning", "Breadboard power rails may be split. Bridge the rails or power both sides."))

    return f
