import re
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class BlockCmd:
    kind: str
    value: Optional[float] = None
    value2: Optional[float] = None
    value3: Optional[float] = None
    target: Optional[str] = None
    style: Optional[str] = None
    text: Optional[str] = None
    text2: Optional[str] = None
    effect: Optional[str] = None
    object: Optional[str] = None
    front_back: Optional[str] = None
    forward_backward: Optional[str] = None
    key: Optional[str] = None
    event: Optional[str] = None
    broadcast: Optional[str] = None
    backdrop: Optional[str] = None
    stop: Optional[str] = None
    clone_target: Optional[str] = None
    # Arduino/Robotics fields
    pin: Optional[str] = None
    mode: Optional[str] = None
    channel: Optional[str] = None
    level: Optional[str] = None
    motor: Optional[str] = None
    direction: Optional[str] = None
    motor2: Optional[str] = None
    direction2: Optional[str] = None


def _split_clauses(text: str) -> List[str]:
    # Keep ordering; split on common separators.
    parts = re.split(r"\s*(?:;|->|\bthen\b)\s*", text, flags=re.IGNORECASE)
    if len(parts) == 1:
        parts = re.split(r"\s*(?:,|\band\b)\s*", text, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()]


def parse_text_to_cmds(text: str) -> List[BlockCmd]:
    text = text.strip().lower()
    if not text:
        return []

    cmds: List[BlockCmd] = []
    for clause in _split_clauses(text):
        # ==== ARDUINO/ROBOTICS BLOCKS (check these first) ====
        
        # Pin Mode
        m = re.search(r"\bset\s+pin\s+(\w+|\d+)\s+mode\s+(\w+)", clause)
        if m:
            cmds.append(BlockCmd("arduino_set_pin_mode", pin=m.group(1), mode=m.group(2)))
            continue
        
        # Digital Output
        m = re.search(r"\bset\s+(?:digital\s+)?pin\s+(\w+|\d+)\s+(?:out|output)\s+(\w+)", clause)
        if m:
            cmds.append(BlockCmd("arduino_digital_output", pin=m.group(1), level=m.group(2)))
            continue
        
        # PWM Output
        m = re.search(r"\bset\s+pwm\s+pin\s+(\w+|\d+)\s+(?:channel\s+)?(\w+)\s+(?:use\s+channel\s+\w+\s+)?out\s+(-?\d+)", clause)
        if m:
            cmds.append(BlockCmd("arduino_pwm_output", pin=m.group(1), channel=m.group(2), value=float(m.group(3))))
            continue
        
        # DAC Output
        m = re.search(r"\bset\s+dac\s+pin\s+(\w+|\d+)\s+out\s+(-?\d+)", clause)
        if m:
            cmds.append(BlockCmd("arduino_dac_output", pin=m.group(1), value=float(m.group(2))))
            continue
        
        # Servo Output
        m = re.search(r"\bset\s+servo\s+pin\s+(\w+|\d+)\s+(?:channel\s+)?(\w+)\s+(?:out|angle)\s+(-?\d+)", clause)
        if m:
            cmds.append(BlockCmd("arduino_servo_output", pin=m.group(1), channel=m.group(2), value=float(m.group(3))))
            continue
        
        # Timer Controls
        if re.search(r"\breset\s+timer\b", clause):
            cmds.append(BlockCmd("arduino_reset_timer"))
            continue
        
        if re.search(r"\bget\s+timer\s+value\b", clause):
            cmds.append(BlockCmd("arduino_get_timer"))
            continue
        
        # Read Digital Pin
        m = re.search(r"\bread\s+digital\s+pin\s+(\w+|\d+)", clause)
        if m:
            cmds.append(BlockCmd("arduino_read_digital", pin=m.group(1)))
            continue
        
        # Read Touch Pin
        m = re.search(r"\bread\s+touch\s+pin\s+(\w+|\d+)", clause)
        if m:
            cmds.append(BlockCmd("arduino_read_touch", pin=m.group(1)))
            continue
        
        # Read Analog Pin
        m = re.search(r"\bread\s+analog\s+pin\s+(\w+|\d+)", clause)
        if m:
            cmds.append(BlockCmd("arduino_read_analog", pin=m.group(1)))
            continue
        
        # Hall Sensor
        if re.search(r"\bread\s+hall\s+sensor\b", clause):
            cmds.append(BlockCmd("arduino_read_hall_sensor"))
            continue
        
        # Running Time
        if re.search(r"\b(?:get\s+)?running\s+time\b", clause):
            cmds.append(BlockCmd("arduino_running_time"))
            continue
        
        # DC Motor
        m = re.search(r"\b(?:dc\s*motor|run\s+motor)\s+(\w+)\s+(\w+)\s+(?:motor\s+)?(\w+)?\s*(\w+)?", clause)
        if m:
            motor1 = m.group(1)
            dir1 = m.group(2)
            motor2 = m.group(3) if m.group(3) else motor1
            dir2 = m.group(4) if m.group(4) else dir1
            cmds.append(BlockCmd("arduino_dc_motor", motor=motor1, direction=dir1, motor2=motor2, direction2=dir2))
            continue
        
        # ==== EXISTING SCRATCH BLOCKS ====
        
        m = re.search(r"\bmove\s+(-?\d+(?:\.\d+)?)\b", clause)
        if m:
            cmds.append(BlockCmd("move", float(m.group(1))))
            continue

        m = re.search(r"\bturn\s+left\s+(-?\d+(?:\.\d+)?)\b", clause)
        if m:
            cmds.append(BlockCmd("turn_left", float(m.group(1))))
            continue

        m = re.search(r"\bturn\s+right\s+(-?\d+(?:\.\d+)?)\b", clause)
        if m:
            cmds.append(BlockCmd("turn_right", float(m.group(1))))
            continue

        m = re.search(r"\bgo\s+to\s+x\s+(-?\d+(?:\.\d+)?)\s+y\s+(-?\d+(?:\.\d+)?)\b", clause)
        if m:
            cmds.append(BlockCmd("goto_xy", float(m.group(1)), float(m.group(2))))
            continue

        m = re.search(r"\bgo\s+to\s+(.+)\b", clause)
        if m:
            target = m.group(1).strip()
            if target in ("front layer", "back layer"):
                pass
            elif target:
                cmds.append(BlockCmd("goto", target=target))
                continue

        m = re.search(r"\bglide\s+(-?\d+(?:\.\d+)?)\s*(?:sec|secs|second|seconds)?\s+to\s+x\s+(-?\d+(?:\.\d+)?)\s+y\s+(-?\d+(?:\.\d+)?)\b", clause)
        if m:
            cmds.append(BlockCmd("glide_xy", float(m.group(1)), float(m.group(2)), float(m.group(3))))
            continue

        m = re.search(r"\bglide\s+(-?\d+(?:\.\d+)?)\s*(?:sec|secs|second|seconds)?\s+to\s+(.+)\b", clause)
        if m:
            cmds.append(BlockCmd("glide", float(m.group(1)), target=m.group(2).strip()))
            continue

        m = re.search(r"\bpoint\s+in\s+direction\s+(-?\d+(?:\.\d+)?)\b", clause)
        if m:
            cmds.append(BlockCmd("point_dir", float(m.group(1))))
            continue

        m = re.search(r"\bpoint\s+towards\s+(.+)\b", clause)
        if m:
            cmds.append(BlockCmd("point_towards", target=m.group(1).strip()))
            continue

        m = re.search(r"\bchange\s+x\s+by\s+(-?\d+(?:\.\d+)?)\b", clause)
        if m:
            cmds.append(BlockCmd("change_x", float(m.group(1))))
            continue

        m = re.search(r"\bset\s+x\s+to\s+(-?\d+(?:\.\d+)?)\b", clause)
        if m:
            cmds.append(BlockCmd("set_x", float(m.group(1))))
            continue

        m = re.search(r"\bchange\s+y\s+by\s+(-?\d+(?:\.\d+)?)\b", clause)
        if m:
            cmds.append(BlockCmd("change_y", float(m.group(1))))
            continue

        m = re.search(r"\bset\s+y\s+to\s+(-?\d+(?:\.\d+)?)\b", clause)
        if m:
            cmds.append(BlockCmd("set_y", float(m.group(1))))
            continue

        if re.search(r"\bbounce\s+if\s+on\s+edge\b", clause):
            cmds.append(BlockCmd("bounce"))
            continue

        m = re.search(r"\bset\s+rotation\s+style\s+(.+)\b", clause)
        if m:
            style = m.group(1).strip()
            if style in ("left-right", "left right"):
                style = "left-right"
            elif style in ("dont rotate", "don't rotate"):
                style = "don't rotate"
            elif style in ("all around", "all-around"):
                style = "all around"
            cmds.append(BlockCmd("rotation_style", style=style))
            continue

        if re.search(r"\bx\s+position\b", clause):
            cmds.append(BlockCmd("x_position"))
            continue

        if re.search(r"\by\s+position\b", clause):
            cmds.append(BlockCmd("y_position"))
            continue

        if re.search(r"\bdirection\b", clause):
            cmds.append(BlockCmd("direction"))
            continue

        # ----- Looks -----
        m = re.search(r'\bsay\s+"([^"]+)"\s+for\s+(-?\d+(?:\.\d+)?)\b', clause)
        if m:
            cmds.append(BlockCmd("say_for", float(m.group(2)), text=m.group(1)))
            continue

        m = re.search(r'\bsay\s+for\s+(-?\d+(?:\.\d+)?)\s+"([^"]+)"\b', clause)
        if m:
            cmds.append(BlockCmd("say_for", float(m.group(1)), text=m.group(2)))
            continue

        m = re.search(r'\bsay\s+"([^"]+)"\b', clause)
        if m:
            cmds.append(BlockCmd("say", text=m.group(1)))
            continue

        m = re.search(r"\bsay\s+(\S+)\b", clause)
        if m:
            cmds.append(BlockCmd("say", text=m.group(1)))
            continue

        m = re.search(r'\bthink\s+"([^"]+)"\s+for\s+(-?\d+(?:\.\d+)?)\b', clause)
        if m:
            cmds.append(BlockCmd("think_for", float(m.group(2)), text=m.group(1)))
            continue

        m = re.search(r'\bthink\s+for\s+(-?\d+(?:\.\d+)?)\s+"([^"]+)"\b', clause)
        if m:
            cmds.append(BlockCmd("think_for", float(m.group(1)), text=m.group(2)))
            continue

        m = re.search(r'\bthink\s+"([^"]+)"\b', clause)
        if m:
            cmds.append(BlockCmd("think", text=m.group(1)))
            continue

        m = re.search(r"\bthink\s+(\S+)\b", clause)
        if m:
            cmds.append(BlockCmd("think", text=m.group(1)))
            continue

        m = re.search(r'\bobject\s+say\s+"([^"]+)"\s+"([^"]+)"\b', clause)
        if m:
            cmds.append(BlockCmd("object_say", object=m.group(1), text=m.group(2)))
            continue

        m = re.search(r'\bobject\s+say\s+for\s+(-?\d+(?:\.\d+)?)\s+"([^"]+)"\s+"([^"]+)"\b', clause)
        if m:
            cmds.append(BlockCmd("object_say_for", float(m.group(1)), object=m.group(2), text=m.group(3)))
            continue

        m = re.search(r"\bswitch\s+costume\s+to\s+(.+)\b", clause)
        if m:
            cmds.append(BlockCmd("switch_costume", target=m.group(1).strip()))
            continue

        if re.search(r"\bnext\s+costume\b", clause):
            cmds.append(BlockCmd("next_costume"))
            continue

        m = re.search(r"\bswitch\s+backdrop\s+to\s+(.+)\b", clause)
        if m:
            cmds.append(BlockCmd("switch_backdrop", target=m.group(1).strip()))
            continue

        if re.search(r"\bnext\s+backdrop\b", clause):
            cmds.append(BlockCmd("next_backdrop"))
            continue

        m = re.search(r"\bchange\s+size\s+by\s+(-?\d+(?:\.\d+)?)\b", clause)
        if m:
            cmds.append(BlockCmd("change_size", float(m.group(1))))
            continue

        m = re.search(r"\bset\s+size\s+to\s+(-?\d+(?:\.\d+)?)\b", clause)
        if m:
            cmds.append(BlockCmd("set_size", float(m.group(1))))
            continue

        m = re.search(r"\bchange\s+effect\s+(\w+)\s+by\s+(-?\d+(?:\.\d+)?)\b", clause)
        if m:
            cmds.append(BlockCmd("change_effect", float(m.group(2)), effect=m.group(1)))
            continue

        m = re.search(r"\bset\s+effect\s+(\w+)\s+to\s+(-?\d+(?:\.\d+)?)\b", clause)
        if m:
            cmds.append(BlockCmd("set_effect", float(m.group(2)), effect=m.group(1)))
            continue

        if re.search(r"\bclear\s+graphic\s+effects\b", clause):
            cmds.append(BlockCmd("clear_effects"))
            continue

        if re.search(r"\bshow\b", clause):
            cmds.append(BlockCmd("show"))
            continue

        if re.search(r"\bhide\b", clause):
            cmds.append(BlockCmd("hide"))
            continue

        if re.search(r"\bgo\s+to\s+front\s+layer\b", clause):
            cmds.append(BlockCmd("front_back", front_back="front"))
            continue

        if re.search(r"\bgo\s+to\s+back\s+layer\b", clause):
            cmds.append(BlockCmd("front_back", front_back="back"))
            continue

        m = re.search(r"\bgo\s+forward\s+(-?\d+(?:\.\d+)?)\s+layers?\b", clause)
        if m:
            cmds.append(BlockCmd("forward_backward", float(m.group(1)), forward_backward="forward"))
            continue

        m = re.search(r"\bgo\s+backward\s+(-?\d+(?:\.\d+)?)\s+layers?\b", clause)
        if m:
            cmds.append(BlockCmd("forward_backward", float(m.group(1)), forward_backward="backward"))
            continue

        if re.search(r"\bcostume\s+number\b", clause):
            cmds.append(BlockCmd("costume_number"))
            continue

        if re.search(r"\bcostume\s+name\b", clause):
            cmds.append(BlockCmd("costume_name"))
            continue

        if re.search(r"\bbackdrop\s+number\b", clause):
            cmds.append(BlockCmd("backdrop_number"))
            continue

        if re.search(r"\bbackdrop\s+name\b", clause):
            cmds.append(BlockCmd("backdrop_name"))
            continue

        if re.search(r"\bsize\b", clause):
            cmds.append(BlockCmd("size"))
            continue

        # ----- Sound -----
        m = re.search(r"\bplay\s+sound\s+(.+?)\s+until\s+done\b", clause)
        if m:
            cmds.append(BlockCmd("sound_play_until_done", target=m.group(1).strip()))
            continue

        m = re.search(r"\bplay\s+sound\s+(.+)\b", clause)
        if m:
            cmds.append(BlockCmd("sound_play", target=m.group(1).strip()))
            continue

        if re.search(r"\bstop\s+all\s+sounds\b", clause):
            cmds.append(BlockCmd("sound_stop_all"))
            continue

        m = re.search(r"\bchange\s+sound\s+effect\s+(\w+)\s+by\s+(-?\d+(?:\.\d+)?)\b", clause)
        if m:
            cmds.append(BlockCmd("sound_change_effect", float(m.group(2)), effect=m.group(1)))
            continue

        m = re.search(r"\bset\s+sound\s+effect\s+(\w+)\s+to\s+(-?\d+(?:\.\d+)?)\b", clause)
        if m:
            cmds.append(BlockCmd("sound_set_effect", float(m.group(2)), effect=m.group(1)))
            continue

        if re.search(r"\bclear\s+sound\s+effects\b", clause):
            cmds.append(BlockCmd("sound_clear_effects"))
            continue

        m = re.search(r"\bchange\s+volume\s+by\s+(-?\d+(?:\.\d+)?)\b", clause)
        if m:
            cmds.append(BlockCmd("sound_change_volume", float(m.group(1))))
            continue

        m = re.search(r"\bset\s+volume\s+to\s+(-?\d+(?:\.\d+)?)\b", clause)
        if m:
            cmds.append(BlockCmd("sound_set_volume", float(m.group(1))))
            continue

        if re.search(r"\bvolume\b", clause):
            cmds.append(BlockCmd("sound_volume"))
            continue

        # ----- Events -----
        if re.search(r"\bwhen\s+green\s+flag\s+clicked\b", clause):
            cmds.append(BlockCmd("when_flag"))
            continue

        m = re.search(r"\bwhen\s+key\s+(.+)\s+pressed\b", clause)
        if m:
            cmds.append(BlockCmd("when_key", key=m.group(1).strip()))
            continue

        if re.search(r"\bwhen\s+this\s+sprite\s+clicked\b", clause):
            cmds.append(BlockCmd("when_sprite_clicked"))
            continue

        m = re.search(r"\bwhen\s+backdrop\s+switches\s+to\s+(.+)\b", clause)
        if m:
            cmds.append(BlockCmd("when_backdrop", backdrop=m.group(1).strip()))
            continue

        m = re.search(r"\bwhen\s+(loudness|timer)\s+>\s*(-?\d+(?:\.\d+)?)\b", clause)
        if m:
            cmds.append(BlockCmd("when_greater", float(m.group(2)), event=m.group(1)))
            continue

        m = re.search(r"\bwhen\s+i\s+receive\s+(.+)\b", clause)
        if m:
            cmds.append(BlockCmd("when_broadcast", broadcast=m.group(1).strip()))
            continue

        m = re.search(r"\bbroadcast\s+(.+?)\s+and\s+wait\b", clause)
        if m:
            cmds.append(BlockCmd("broadcast_wait", broadcast=m.group(1).strip()))
            continue

        m = re.search(r"\bbroadcast\s+(.+)\b", clause)
        if m:
            cmds.append(BlockCmd("broadcast", broadcast=m.group(1).strip()))
            continue

        # ----- Control -----
        m = re.search(r"\bwait\s+(-?\d+(?:\.\d+)?)\b", clause)
        if m:
            cmds.append(BlockCmd("control_wait", float(m.group(1))))
            continue

        m = re.search(r"\brepeat\s+(-?\d+(?:\.\d+)?)\b", clause)
        if m:
            cmds.append(BlockCmd("control_repeat", float(m.group(1))))
            continue

        if re.search(r"\bforever\b", clause):
            cmds.append(BlockCmd("control_forever"))
            continue

        if re.search(r"\bif\s+else\b", clause):
            cmds.append(BlockCmd("control_if_else"))
            continue

        if re.search(r"\bif\b", clause):
            cmds.append(BlockCmd("control_if"))
            continue

        if re.search(r"\bwait\s+until\b", clause):
            cmds.append(BlockCmd("control_wait_until"))
            continue

        if re.search(r"\brepeat\s+until\b", clause):
            cmds.append(BlockCmd("control_repeat_until"))
            continue

        m = re.search(r"\bstop\s+(all|this script|other scripts)\b", clause)
        if m:
            cmds.append(BlockCmd("control_stop", stop=m.group(1)))
            continue

        if re.search(r"\bwhen\s+i\s+start\s+as\s+a\s+clone\b", clause):
            cmds.append(BlockCmd("control_start_as_clone"))
            continue

        m = re.search(r"\bcreate\s+clone\s+of\s+(.+)\b", clause)
        if m:
            cmds.append(BlockCmd("control_create_clone", clone_target=m.group(1).strip()))
            continue

        if re.search(r"\bdelete\s+this\s+clone\b", clause):
            cmds.append(BlockCmd("control_delete_clone"))
            continue

        m = re.search(r"\bswitch\s+(.+)\b", clause)
        if m:
            cmds.append(BlockCmd("control_switch", text=m.group(1).strip()))
            continue

        if re.search(r"\bdefault\b", clause):
            cmds.append(BlockCmd("control_default"))
            continue

        if re.search(r"\bexit\s+case\b", clause):
            cmds.append(BlockCmd("control_exit_case"))
            continue

        m = re.search(r"\bcase\s+next\s+(.+)\b", clause)
        if m:
            cmds.append(BlockCmd("control_case_next", text=m.group(1).strip()))
            continue

        m = re.search(r"\bcase\s+(.+)\b", clause)
        if m:
            cmds.append(BlockCmd("control_case", text=m.group(1).strip()))
            continue

        m = re.search(r"\breturn\s+(-?\d+(?:\.\d+)?)\b", clause)
        if m:
            cmds.append(BlockCmd("control_return", float(m.group(1))))
            continue

    return cmds


def _new_id() -> str:
    return uuid.uuid4().hex


def _add_value_with_number(block_el: ET.Element, name: str, number: int) -> None:
    val_el = ET.SubElement(block_el, "value", {"name": name})
    shadow_el = ET.SubElement(val_el, "shadow", {"type": "math_number", "id": _new_id()})
    field_el = ET.SubElement(shadow_el, "field", {"name": "NUM"})
    field_el.text = str(number)


def _add_value_with_integer(block_el: ET.Element, name: str, number: float) -> None:
    val_el = ET.SubElement(block_el, "value", {"name": name})
    shadow_el = ET.SubElement(val_el, "shadow", {"type": "math_integer", "id": _new_id()})
    field_el = ET.SubElement(shadow_el, "field", {"name": "NUM"})
    field_el.text = str(int(number))


def _add_value_with_text(block_el: ET.Element, name: str, text: str) -> None:
    val_el = ET.SubElement(block_el, "value", {"name": name})
    shadow_el = ET.SubElement(val_el, "shadow", {"type": "text", "id": _new_id()})
    field_el = ET.SubElement(shadow_el, "field", {"name": "TEXT"})
    field_el.text = text


def _add_value_with_shadow(block_el: ET.Element, name: str, shadow_type: str, field_name: Optional[str] = None, field_value: Optional[str] = None) -> None:
    val_el = ET.SubElement(block_el, "value", {"name": name})
    shadow_el = ET.SubElement(val_el, "shadow", {"type": shadow_type, "id": _new_id()})
    if field_name:
        field_el = ET.SubElement(shadow_el, "field", {"name": field_name})
        if field_value is not None:
            field_el.text = field_value


def _add_value_with_angle(block_el: ET.Element, name: str, number: float) -> None:
    val_el = ET.SubElement(block_el, "value", {"name": name})
    shadow_el = ET.SubElement(val_el, "shadow", {"type": "math_angle", "id": _new_id()})
    field_el = ET.SubElement(shadow_el, "field", {"name": "NUM"})
    field_el.text = str(number)


def _add_value_with_menu(block_el: ET.Element, name: str, menu_type: str, field_name: str, value: str) -> None:
    val_el = ET.SubElement(block_el, "value", {"name": name})
    shadow_el = ET.SubElement(val_el, "shadow", {"type": menu_type, "id": _new_id()})
    field_el = ET.SubElement(shadow_el, "field", {"name": field_name})
    field_el.text = value


def _normalize_target(target: Optional[str]) -> str:
    if not target:
        return "_random_"
    t = target.strip().lower()
    if t in ("random", "random position", "_random_"):
        return "_random_"
    if t in ("mouse", "mouse pointer", "_mouse_"):
        return "_mouse_"
    return target


def _normalize_effect(effect: Optional[str]) -> str:
    if not effect:
        return "COLOR"
    e = effect.strip().lower()
    mapping = {
        "color": "COLOR",
        "colour": "COLOR",
        "fisheye": "FISHEYE",
        "whirl": "WHIRL",
        "pixelate": "PIXELATE",
        "mosaic": "MOSAIC",
        "brightness": "BRIGHTNESS",
        "ghost": "GHOST",
    }
    return mapping.get(e, effect.upper())


def _normalize_sound_effect(effect: Optional[str]) -> str:
    if not effect:
        return "PITCH"
    e = effect.strip().lower()
    mapping = {
        "pitch": "PITCH",
        "pan": "PAN",
        "left-right": "PAN",
        "left right": "PAN",
    }
    return mapping.get(e, effect.upper())


def _normalize_key(key: Optional[str]) -> str:
    if not key:
        return "space"
    k = key.strip().lower()
    mapping = {
        "space": "space",
        "spacebar": "space",
        "up": "up arrow",
        "down": "down arrow",
        "left": "left arrow",
        "right": "right arrow",
        "any": "any",
    }
    return mapping.get(k, key)


def _normalize_broadcast(name: Optional[str]) -> str:
    return (name or "message1").strip()


def _normalize_backdrop(name: Optional[str]) -> str:
    return (name or "backdrop1").strip()


def _normalize_when_gt(event: Optional[str]) -> str:
    if not event:
        return "LOUDNESS"
    e = event.strip().lower()
    if e == "timer":
        return "TIMER"
    return "LOUDNESS"


def _normalize_stop_option(value: Optional[str]) -> str:
    if not value:
        return "all"
    v = value.strip().lower()
    if v == "this script":
        return "this script"
    if v == "other scripts":
        return "other scripts in sprite"
    return "all"


def _normalize_clone_target(target: Optional[str]) -> str:
    if not target:
        return "myself"
    t = target.strip().lower()
    if t in ("myself", "self"):
        return "myself"
    return target


def _make_block(cmd: BlockCmd) -> ET.Element:
    if cmd.kind == "move":
        block = ET.Element("block", {"type": "motion_movesteps", "id": _new_id()})
        _add_value_with_number(block, "STEPS", cmd.value or 0)
        return block

    if cmd.kind == "turn_left":
        block = ET.Element("block", {"type": "motion_turnleft", "id": _new_id()})
        _add_value_with_number(block, "DEGREES", cmd.value or 0)
        return block

    if cmd.kind == "turn_right":
        block = ET.Element("block", {"type": "motion_turnright", "id": _new_id()})
        _add_value_with_number(block, "DEGREES", cmd.value or 0)
        return block

    if cmd.kind == "goto":
        block = ET.Element("block", {"type": "motion_goto", "id": _new_id()})
        target = _normalize_target(cmd.target)
        _add_value_with_menu(block, "TO", "motion_goto_menu", "TO", target)
        return block

    if cmd.kind == "goto_xy":
        block = ET.Element("block", {"type": "motion_gotoxy", "id": _new_id()})
        _add_value_with_number(block, "X", cmd.value or 0)
        _add_value_with_number(block, "Y", cmd.value2 or 0)
        return block

    if cmd.kind == "glide":
        block = ET.Element("block", {"type": "motion_glideto", "id": _new_id()})
        _add_value_with_number(block, "SECS", cmd.value or 0)
        target = _normalize_target(cmd.target)
        _add_value_with_menu(block, "TO", "motion_glideto_menu", "TO", target)
        return block

    if cmd.kind == "glide_xy":
        block = ET.Element("block", {"type": "motion_glidesecstoxy", "id": _new_id()})
        _add_value_with_number(block, "SECS", cmd.value or 0)
        _add_value_with_number(block, "X", cmd.value2 or 0)
        _add_value_with_number(block, "Y", cmd.value3 or 0)
        return block

    if cmd.kind == "point_dir":
        block = ET.Element("block", {"type": "motion_pointindirection", "id": _new_id()})
        _add_value_with_angle(block, "DIRECTION", cmd.value or 0)
        return block

    if cmd.kind == "point_towards":
        block = ET.Element("block", {"type": "motion_pointtowards", "id": _new_id()})
        target = _normalize_target(cmd.target)
        _add_value_with_menu(block, "TOWARDS", "motion_pointtowards_menu", "TOWARDS", target)
        return block

    if cmd.kind == "change_x":
        block = ET.Element("block", {"type": "motion_changexby", "id": _new_id()})
        _add_value_with_number(block, "DX", cmd.value or 0)
        return block

    if cmd.kind == "set_x":
        block = ET.Element("block", {"type": "motion_setx", "id": _new_id()})
        _add_value_with_number(block, "X", cmd.value or 0)
        return block

    if cmd.kind == "change_y":
        block = ET.Element("block", {"type": "motion_changeyby", "id": _new_id()})
        _add_value_with_number(block, "DY", cmd.value or 0)
        return block

    if cmd.kind == "set_y":
        block = ET.Element("block", {"type": "motion_sety", "id": _new_id()})
        _add_value_with_number(block, "Y", cmd.value or 0)
        return block

    if cmd.kind == "bounce":
        return ET.Element("block", {"type": "motion_ifonedgebounce", "id": _new_id()})

    if cmd.kind == "rotation_style":
        block = ET.Element("block", {"type": "motion_setrotationstyle", "id": _new_id()})
        field_el = ET.SubElement(block, "field", {"name": "STYLE"})
        field_el.text = cmd.style or "left-right"
        return block

    if cmd.kind == "x_position":
        return ET.Element("block", {"type": "motion_xposition", "id": _new_id()})

    if cmd.kind == "y_position":
        return ET.Element("block", {"type": "motion_yposition", "id": _new_id()})

    if cmd.kind == "direction":
        return ET.Element("block", {"type": "motion_direction", "id": _new_id()})

    # ----- Looks -----
    if cmd.kind == "say_for":
        block = ET.Element("block", {"type": "looks_sayforsecs", "id": _new_id()})
        _add_value_with_text(block, "MESSAGE", cmd.text or "")
        _add_value_with_number(block, "SECS", cmd.value or 0)
        return block

    if cmd.kind == "say":
        block = ET.Element("block", {"type": "looks_say", "id": _new_id()})
        _add_value_with_text(block, "MESSAGE", cmd.text or "")
        return block

    if cmd.kind == "think_for":
        block = ET.Element("block", {"type": "looks_thinkforsecs", "id": _new_id()})
        _add_value_with_text(block, "MESSAGE", cmd.text or "")
        _add_value_with_number(block, "SECS", cmd.value or 0)
        return block

    if cmd.kind == "think":
        block = ET.Element("block", {"type": "looks_think", "id": _new_id()})
        _add_value_with_text(block, "MESSAGE", cmd.text or "")
        return block

    if cmd.kind == "object_say":
        block = ET.Element("block", {"type": "looks_setObjectSay", "id": _new_id()})
        field_el = ET.SubElement(block, "field", {"name": "OBJECT"})
        field_el.text = cmd.object or "NONE"
        _add_value_with_text(block, "MESSAGE", cmd.text or "")
        return block

    if cmd.kind == "object_say_for":
        block = ET.Element("block", {"type": "looks_setObjectSayFor", "id": _new_id()})
        _add_value_with_text(block, "MESSAGE", cmd.text or "")
        _add_value_with_number(block, "TIME", cmd.value or 0)
        return block

    if cmd.kind == "switch_costume":
        block = ET.Element("block", {"type": "looks_switchcostumeto", "id": _new_id()})
        _add_value_with_menu(block, "COSTUME", "looks_costume", "COSTUME", cmd.target or "")
        return block

    if cmd.kind == "next_costume":
        return ET.Element("block", {"type": "looks_nextcostume", "id": _new_id()})

    if cmd.kind == "switch_backdrop":
        block = ET.Element("block", {"type": "looks_switchbackdropto", "id": _new_id()})
        _add_value_with_menu(block, "BACKDROP", "looks_backdrops", "BACKDROP", cmd.target or "")
        return block

    if cmd.kind == "next_backdrop":
        return ET.Element("block", {"type": "looks_nextbackdrop", "id": _new_id()})

    if cmd.kind == "change_size":
        block = ET.Element("block", {"type": "looks_changesizeby", "id": _new_id()})
        _add_value_with_number(block, "CHANGE", cmd.value or 0)
        return block

    if cmd.kind == "set_size":
        block = ET.Element("block", {"type": "looks_setsizeto", "id": _new_id()})
        _add_value_with_number(block, "SIZE", cmd.value or 0)
        return block

    if cmd.kind == "change_effect":
        block = ET.Element("block", {"type": "looks_changeeffectby", "id": _new_id()})
        field_el = ET.SubElement(block, "field", {"name": "EFFECT"})
        field_el.text = _normalize_effect(cmd.effect)
        _add_value_with_number(block, "CHANGE", cmd.value or 0)
        return block

    if cmd.kind == "set_effect":
        block = ET.Element("block", {"type": "looks_seteffectto", "id": _new_id()})
        field_el = ET.SubElement(block, "field", {"name": "EFFECT"})
        field_el.text = _normalize_effect(cmd.effect)
        _add_value_with_number(block, "VALUE", cmd.value or 0)
        return block

    if cmd.kind == "clear_effects":
        return ET.Element("block", {"type": "looks_cleargraphiceffects", "id": _new_id()})

    if cmd.kind == "show":
        return ET.Element("block", {"type": "looks_show", "id": _new_id()})

    if cmd.kind == "hide":
        return ET.Element("block", {"type": "looks_hide", "id": _new_id()})

    if cmd.kind == "front_back":
        block = ET.Element("block", {"type": "looks_gotofrontback", "id": _new_id()})
        field_el = ET.SubElement(block, "field", {"name": "FRONT_BACK"})
        field_el.text = cmd.front_back or "front"
        return block

    if cmd.kind == "forward_backward":
        block = ET.Element("block", {"type": "looks_goforwardbackwardlayers", "id": _new_id()})
        field_el = ET.SubElement(block, "field", {"name": "FORWARD_BACKWARD"})
        field_el.text = cmd.forward_backward or "forward"
        _add_value_with_integer(block, "NUM", cmd.value or 1)
        return block

    if cmd.kind == "costume_number":
        block = ET.Element("block", {"type": "looks_costumenumbername", "id": _new_id()})
        field_el = ET.SubElement(block, "field", {"name": "NUMBER_NAME"})
        field_el.text = "number"
        return block

    if cmd.kind == "costume_name":
        block = ET.Element("block", {"type": "looks_costumenumbername", "id": _new_id()})
        field_el = ET.SubElement(block, "field", {"name": "NUMBER_NAME"})
        field_el.text = "name"
        return block

    if cmd.kind == "backdrop_number":
        block = ET.Element("block", {"type": "looks_backdropnumbername", "id": _new_id()})
        field_el = ET.SubElement(block, "field", {"name": "NUMBER_NAME"})
        field_el.text = "number"
        return block

    if cmd.kind == "backdrop_name":
        block = ET.Element("block", {"type": "looks_backdropnumbername", "id": _new_id()})
        field_el = ET.SubElement(block, "field", {"name": "NUMBER_NAME"})
        field_el.text = "name"
        return block

    if cmd.kind == "size":
        return ET.Element("block", {"type": "looks_size", "id": _new_id()})

    # ----- Sound -----
    if cmd.kind == "sound_play_until_done":
        block = ET.Element("block", {"type": "sound_playuntildone", "id": _new_id()})
        _add_value_with_menu(block, "SOUND_MENU", "sound_sounds_menu", "SOUND_MENU", cmd.target or "")
        return block

    if cmd.kind == "sound_play":
        block = ET.Element("block", {"type": "sound_play", "id": _new_id()})
        _add_value_with_menu(block, "SOUND_MENU", "sound_sounds_menu", "SOUND_MENU", cmd.target or "")
        return block

    if cmd.kind == "sound_stop_all":
        return ET.Element("block", {"type": "sound_stopallsounds", "id": _new_id()})

    if cmd.kind == "sound_change_effect":
        block = ET.Element("block", {"type": "sound_changeeffectby", "id": _new_id()})
        field_el = ET.SubElement(block, "field", {"name": "EFFECT"})
        field_el.text = _normalize_sound_effect(cmd.effect)
        _add_value_with_number(block, "VALUE", cmd.value or 0)
        return block

    if cmd.kind == "sound_set_effect":
        block = ET.Element("block", {"type": "sound_seteffectto", "id": _new_id()})
        field_el = ET.SubElement(block, "field", {"name": "EFFECT"})
        field_el.text = _normalize_sound_effect(cmd.effect)
        _add_value_with_number(block, "VALUE", cmd.value or 0)
        return block

    if cmd.kind == "sound_clear_effects":
        return ET.Element("block", {"type": "sound_cleareffects", "id": _new_id()})

    if cmd.kind == "sound_change_volume":
        block = ET.Element("block", {"type": "sound_changevolumeby", "id": _new_id()})
        _add_value_with_number(block, "VOLUME", cmd.value or 0)
        return block

    if cmd.kind == "sound_set_volume":
        block = ET.Element("block", {"type": "sound_setvolumeto", "id": _new_id()})
        _add_value_with_number(block, "VOLUME", cmd.value or 0)
        return block

    if cmd.kind == "sound_volume":
        return ET.Element("block", {"type": "sound_volume", "id": _new_id()})

    # ----- Events -----
    if cmd.kind == "when_flag":
        return ET.Element("block", {"type": "event_whenflagclicked", "id": _new_id()})

    if cmd.kind == "when_key":
        block = ET.Element("block", {"type": "event_whenkeypressed", "id": _new_id()})
        field_el = ET.SubElement(block, "field", {"name": "KEY_OPTION"})
        field_el.text = _normalize_key(cmd.key)
        return block

    if cmd.kind == "when_sprite_clicked":
        return ET.Element("block", {"type": "event_whenthisspriteclicked", "id": _new_id()})

    if cmd.kind == "when_backdrop":
        block = ET.Element("block", {"type": "event_whenbackdropswitchesto", "id": _new_id()})
        field_el = ET.SubElement(block, "field", {"name": "BACKDROP"})
        field_el.text = _normalize_backdrop(cmd.backdrop)
        return block

    if cmd.kind == "when_greater":
        block = ET.Element("block", {"type": "event_whengreaterthan", "id": _new_id()})
        field_el = ET.SubElement(block, "field", {"name": "WHENGREATERTHANMENU"})
        field_el.text = _normalize_when_gt(cmd.event)
        _add_value_with_number(block, "VALUE", cmd.value or 0)
        return block

    if cmd.kind == "when_broadcast":
        block = ET.Element("block", {"type": "event_whenbroadcastreceived", "id": _new_id()})
        field_el = ET.SubElement(block, "field", {"name": "BROADCAST_OPTION"})
        field_el.text = _normalize_broadcast(cmd.broadcast)
        return block

    if cmd.kind == "broadcast":
        block = ET.Element("block", {"type": "event_broadcast", "id": _new_id()})
        _add_value_with_menu(block, "BROADCAST_INPUT", "event_broadcast_menu", "BROADCAST_OPTION", _normalize_broadcast(cmd.broadcast))
        return block

    if cmd.kind == "broadcast_wait":
        block = ET.Element("block", {"type": "event_broadcastandwait", "id": _new_id()})
        _add_value_with_menu(block, "BROADCAST_INPUT", "event_broadcast_menu", "BROADCAST_OPTION", _normalize_broadcast(cmd.broadcast))
        return block

    # ----- Control -----
    if cmd.kind == "control_wait":
        block = ET.Element("block", {"type": "control_wait", "id": _new_id()})
        _add_value_with_number(block, "DURATION", cmd.value or 0)
        return block

    if cmd.kind == "control_repeat":
        block = ET.Element("block", {"type": "control_repeat", "id": _new_id()})
        _add_value_with_number(block, "TIMES", cmd.value or 0)
        return block

    if cmd.kind == "control_forever":
        return ET.Element("block", {"type": "control_forever", "id": _new_id()})

    if cmd.kind == "control_if":
        block = ET.Element("block", {"type": "control_if", "id": _new_id()})
        _add_value_with_shadow(block, "CONDITION", "operator_true")
        return block

    if cmd.kind == "control_if_else":
        block = ET.Element("block", {"type": "control_if_else", "id": _new_id()})
        _add_value_with_shadow(block, "CONDITION", "operator_true")
        return block

    if cmd.kind == "control_wait_until":
        block = ET.Element("block", {"type": "control_wait_until", "id": _new_id()})
        _add_value_with_shadow(block, "CONDITION", "operator_true")
        return block

    if cmd.kind == "control_repeat_until":
        block = ET.Element("block", {"type": "control_repeat_until", "id": _new_id()})
        _add_value_with_shadow(block, "CONDITION", "operator_true")
        return block

    if cmd.kind == "control_stop":
        block = ET.Element("block", {"type": "control_stop", "id": _new_id()})
        field_el = ET.SubElement(block, "field", {"name": "STOP_OPTION"})
        field_el.text = _normalize_stop_option(cmd.stop)
        return block

    if cmd.kind == "control_start_as_clone":
        return ET.Element("block", {"type": "control_start_as_clone", "id": _new_id()})

    if cmd.kind == "control_create_clone":
        block = ET.Element("block", {"type": "control_create_clone_of", "id": _new_id()})
        _add_value_with_menu(block, "CLONE_OPTION", "control_create_clone_of_menu", "CLONE_OPTION", _normalize_clone_target(cmd.clone_target))
        return block

    if cmd.kind == "control_delete_clone":
        block = ET.Element("block", {"type": "control_delete_this_clone", "id": _new_id()})
        _add_value_with_menu(block, "CLONE_OPTION", "control_delete_clone_of_menu", "CLONE_OPTION", "this clone")
        return block

    if cmd.kind == "control_switch":
        block = ET.Element("block", {"type": "control_switch", "id": _new_id()})
        _add_value_with_text(block, "CONDITION", cmd.text or "")
        return block

    if cmd.kind == "control_default":
        return ET.Element("block", {"type": "control_default", "id": _new_id()})

    if cmd.kind == "control_exit_case":
        return ET.Element("block", {"type": "control_exitCase", "id": _new_id()})

    if cmd.kind == "control_case_next":
        block = ET.Element("block", {"type": "control_case_next", "id": _new_id()})
        _add_value_with_text(block, "CONDITION", cmd.text or "")
        return block

    if cmd.kind == "control_case":
        block = ET.Element("block", {"type": "control_case", "id": _new_id()})
        _add_value_with_text(block, "CONDITION", cmd.text or "")
        return block

    if cmd.kind == "control_return":
        block = ET.Element("block", {"type": "control_return", "id": _new_id()})
        _add_value_with_number(block, "VALUE", cmd.value or 0)
        return block
    if cmd.kind == "sensing_ask":
        block = ET.Element("block", {
        "type": "sensing_askandwait",
        "id": _new_id()
    })
        value = ET.SubElement(block, "value", {"name": "QUESTION"})
        shadow = ET.SubElement(value, "shadow", {"type": "text"})
        field = ET.SubElement(shadow, "field", {"name": "TEXT"})
        field.text = cmd.text or "Your answer?"
        return block

    if cmd.kind == "control_if_answer":
        block = ET.Element("block", {
        "type": "control_if",
        "id": _new_id()
    })

          # condition
        value = ET.SubElement(block, "value", {"name": "CONDITION"})
        op = ET.SubElement(value, "block", {"type": "operator_equals", "id": _new_id()})

         #  left side = answer
        left = ET.SubElement(op, "value", {"name": "OPERAND5"})
        left_block = ET.SubElement(left, "block", {"type": "sensing_answer", "id": _new_id()})

         # right side = correct text
        right = ET.SubElement(op, "value", {"name": "OPERAND2"})
        shadow = ET.SubElement(right, "shadow", {"type": "text"})
        field = ET.SubElement(shadow, "field", {"name": "TEXT"})
        field.text = cmd.text or ""
        return block

    
    




    # ==== ARDUINO/ROBOTICS BLOCKS ====
    
    if cmd.kind == "arduino_set_pin_mode":
        block = ET.Element("block", {"type": "arduino_pin_setPinMode", "id": _new_id()})
        pin_field = ET.SubElement(block, "field", {"name": "PIN"})
        pin_field.text = str(cmd.pin or "2").upper()
        mode_field = ET.SubElement(block, "field", {"name": "MODE"})
        mode_field.text = (cmd.mode or "INPUT").upper()
        return block
    
    if cmd.kind == "arduino_digital_output":
        block = ET.Element("block", {"type": "arduino_pin_setDigitalOutput", "id": _new_id()})
        pin_field = ET.SubElement(block, "field", {"name": "PIN"})
        pin_field.text = str(cmd.pin or "2").upper()
        value_el = ET.SubElement(block, "value", {"name": "LEVEL"})
        shadow = ET.SubElement(value_el, "shadow", {"type": "arduino_pin_menu_level", "id": _new_id()})
        level_field = ET.SubElement(shadow, "field", {"name": "level"})
        level_field.text = (cmd.level or "HIGH").upper()
        return block
    
    if cmd.kind == "arduino_pwm_output":
        block = ET.Element("block", {"type": "arduino_pin_esp32SetPwmOutput", "id": _new_id()})
        pin_field = ET.SubElement(block, "field", {"name": "PIN"})
        pin_field.text = str(cmd.pin or "2")
        ch_field = ET.SubElement(block, "field", {"name": "CH"})
        ch_field.text = str(cmd.channel or "0")
        value_el = ET.SubElement(block, "value", {"name": "OUT"})
        shadow = ET.SubElement(value_el, "shadow", {"type": "math_number", "id": _new_id()})
        num_field = ET.SubElement(shadow, "field", {"name": "NUM"})
        num_field.text = str(int(cmd.value or 0))
        return block
    
    if cmd.kind == "arduino_dac_output":
        block = ET.Element("block", {"type": "arduino_pin_esp32SetDACOutput", "id": _new_id()})
        pin_field = ET.SubElement(block, "field", {"name": "PIN"})
        pin_field.text = str(cmd.pin or "25")
        value_el = ET.SubElement(block, "value", {"name": "OUT"})
        shadow = ET.SubElement(value_el, "shadow", {"type": "math_number", "id": _new_id()})
        num_field = ET.SubElement(shadow, "field", {"name": "NUM"})
        num_field.text = str(int(cmd.value or 0))
        return block
    
    if cmd.kind == "arduino_servo_output":
        block = ET.Element("block", {"type": "arduino_pin_esp32SetServoOutput", "id": _new_id()})
        pin_field = ET.SubElement(block, "field", {"name": "PIN"})
        pin_field.text = str(cmd.pin or "2")
        ch_field = ET.SubElement(block, "field", {"name": "CH"})
        ch_field.text = str(cmd.channel or "0")
        value_el = ET.SubElement(block, "value", {"name": "OUT"})
        shadow = ET.SubElement(value_el, "shadow", {"type": "math_angle", "id": _new_id()})
        num_field = ET.SubElement(shadow, "field", {"name": "NUM"})
        num_field.text = str(int(cmd.value or 0))
        return block
    
    if cmd.kind == "arduino_reset_timer":
        return ET.Element("block", {"type": "arduino_pin_resetTimer", "id": _new_id()})
    
    if cmd.kind == "arduino_get_timer":
        return ET.Element("block", {"type": "arduino_pin_getTimer", "id": _new_id()})
    
    if cmd.kind == "arduino_read_digital":
        block = ET.Element("block", {"type": "arduino_pin_readDigitalPin", "id": _new_id()})
        pin_field = ET.SubElement(block, "field", {"name": "PIN"})
        pin_field.text = str(cmd.pin or "2")
        return block
    
    if cmd.kind == "arduino_read_touch":
        block = ET.Element("block", {"type": "arduino_pin_esp32ReadTouchPin", "id": _new_id()})
        pin_field = ET.SubElement(block, "field", {"name": "PIN"})
        pin_field.text = str(cmd.pin or "2")
        return block
    
    if cmd.kind == "arduino_read_analog":
        block = ET.Element("block", {"type": "arduino_pin_readAnalogPin", "id": _new_id()})
        pin_field = ET.SubElement(block, "field", {"name": "PIN"})
        pin_field.text = str(cmd.pin or "2")
        return block
    
    if cmd.kind == "arduino_read_hall_sensor":
        return ET.Element("block", {"type": "arduino_sensor_esp32ReadHallSensor", "id": _new_id()})
    
    if cmd.kind == "arduino_running_time":
        return ET.Element("block", {"type": "arduino_sensor_runningTime", "id": _new_id()})
    
    if cmd.kind == "arduino_dc_motor":
        block = ET.Element("block", {"type": "arduino_dcomtor_runMotor", "id": _new_id()})
        motor_field = ET.SubElement(block, "field", {"name": "MOTOR"})
        motor_field.text = (cmd.motor or "M1").upper()
        dir_field = ET.SubElement(block, "field", {"name": "DIRECTION"})
        dir_field.text = (cmd.direction or "forward").lower()
        motor2_field = ET.SubElement(block, "field", {"name": "MOTOR1"})
        motor2_field.text = (cmd.motor2 or cmd.motor or "M1").upper()
        dir2_field = ET.SubElement(block, "field", {"name": "DIRECTION1"})
        dir2_field.text = (cmd.direction2 or cmd.direction or "forward").lower()
        return block
    

    raise ValueError(f"Unknown cmd kind: {cmd.kind}")


def build_xml_from_cmds(cmds: List[BlockCmd]) -> str:
    xml_root = ET.Element("xml", {"xmlns": "http://www.w3.org/1999/xhtml"})
    ET.SubElement(xml_root, "variables")

    if not cmds:
        return ET.tostring(xml_root, encoding="unicode")

    first_block = _make_block(cmds[0])
    first_block.set("x", "20")
    first_block.set("y", "20")
    xml_root.append(first_block)

    current = first_block
    for cmd in cmds[1:]:
        next_el = ET.SubElement(current, "next")
        new_block = _make_block(cmd)
        next_el.append(new_block)
        current = new_block

    return ET.tostring(xml_root, encoding="unicode")


def text_to_xml(text: str) -> Tuple[str, List[BlockCmd]]:
    cmds = parse_text_to_cmds(text)
    xml = build_xml_from_cmds(cmds)
    return xml, cmds

def dsl_to_blockzie_xml(dsl_lines: list[str], title: str = "Project") -> str:
    def num_shadow(n: str) -> str:
        return f'<shadow type="math_number"><field name="NUM">{n}</field></shadow>'
    def text_shadow(t: str) -> str:
        return f'<shadow type="text"><field name="TEXT">{t}</field></shadow>'

    next_id = 1000
    def new_id():
        nonlocal next_id
        next_id += 1
        return str(next_id)

    def hat_block(line_s: str) -> str | None:
        low = line_s.strip().lower()
        if low == "when green_flag:":
            return f'<block type="event_whenflagclicked" id="{new_id()}" x="120" y="120"></block>'
        m = re.match(r"when key (.+) pressed:", low)
        if m:
            key = m.group(1).strip()
            # Scratch key field names usually: "space", "a", "1" etc
            return f'<block type="event_whenkeypressed" id="{new_id()}" x="120" y="120"><field name="KEY_OPTION">{key}</field></block>'
        return None

    def stmt_block(line_s: str) -> str | None:
        low = line_s.strip().lower()

        if low.startswith("wait "):
            sec = low.replace("wait", "").strip()
            return f'<block type="control_wait" id="{new_id()}"><value name="DURATION">{num_shadow(sec)}</value></block>'

        if low.startswith("move "):
            steps = low.replace("move", "").replace("steps", "").strip()
            return f'<block type="motion_movesteps" id="{new_id()}"><value name="STEPS">{num_shadow(steps)}</value></block>'

        if low.startswith("turn right"):
            deg = low.replace("turn right", "").replace("degrees", "").strip()
            return f'<block type="motion_turnright" id="{new_id()}"><value name="DEGREES">{num_shadow(deg)}</value></block>'

        if low.startswith("turn left"):
            deg = low.replace("turn left", "").replace("degrees", "").strip()
            return f'<block type="motion_turnleft" id="{new_id()}"><value name="DEGREES">{num_shadow(deg)}</value></block>'

        if low.startswith("say "):
            msg = line_s[4:].strip().strip('"').strip("'")
            return f'<block type="looks_say" id="{new_id()}"><value name="MESSAGE">{text_shadow(msg)}</value></block>'

        return None

    def set_next(block_xml: str, next_block_xml: str) -> str:
        if block_xml.endswith("</block>"):
            return block_xml[:-8] + f'<next>{next_block_xml}</next></block>'
        return block_xml

    scripts = []
    current_hat = None
    current_chain = []

    for raw in dsl_lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        hb = hat_block(line)
        if hb:
            # flush previous script
            if current_hat:
                root = current_chain[-1] if current_chain else None
                if root:
                    for i in range(len(current_chain) - 2, -1, -1):
                        root = set_next(current_chain[i], root)
                    current_hat = set_next(current_hat, root)
                scripts.append(current_hat)
            current_hat = hb
            current_chain = []
            continue

        b = stmt_block(line)
        if b:
            current_chain.append(b)

    # flush last script
    if current_hat:
        if current_chain:
            root = current_chain[-1]
            for i in range(len(current_chain) - 2, -1, -1):
                root = set_next(current_chain[i], root)
            current_hat = set_next(current_hat, root)
        scripts.append(current_hat)

    if not scripts:
        scripts = [f'<block type="looks_say" id="{new_id()}" x="120" y="120"><value name="MESSAGE">{text_shadow("Hello!")}</value></block>']

    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<xml xmlns="http://www.w3.org/1999/xhtml">']
    xml.extend(scripts)
    xml.append("</xml>")
    return "\n".join(xml)

