from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class BlockzieReq(BaseModel):
    text: str = ""
    auto_start: bool = True


class BlockzieXMLReq(BaseModel):
    xml: str = ""
    auto_start: bool = True
    mode: str = "inject"  # inject | append


class RemoveTypeReq(BaseModel):
    block_type: str = ""


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatReq(BaseModel):
    text: str = ""
    messages: List[ChatMessage] = Field(default_factory=list)
    image_data_url: Optional[str] = None
    want_voice: bool = False
    voice_lang: str = "en"


class MakeReq(BaseModel):
    user_id: str = "demo"
    prompt: str = ""
    auto_open: bool = True
    auto_start: bool = True


class Telemetry(BaseModel):
    device_id: str
    ts: Optional[int] = None
    data: Dict[str, Any] = {}


class Command(BaseModel):
    cmd_id: Optional[str] = None
    ts: Optional[int] = None
    action: str
    Stembotix: Dict[str, Any] = {}


class OTARegisterReq(BaseModel):
    device_id: str = "esp32-01"
    ip: str
    token: str = "stembotix123"
    fqbn: str = "esp32:esp32:esp32"


class FirmwareAIGenReq(BaseModel):
    device_id: str = "esp32-01"
    prompt: str = "Make ESP32 firmware: telemetry + command LED + OTA update"
    led_pin: int = 5
    dht_pin: int = 25
    adc_pin: int = 34


class FirmwarePushCodeReq(BaseModel):
    device_id: str = "esp32-01"
    ino: str


class SerialUploadReq(BaseModel):
    ino: str
    port: str
    fqbn: str = "esp32:esp32:esp32"


class SimAIReq(BaseModel):
    mode: str = "agent_build"  # help | agent_build | improve | explain
    prompt: str = ""
    circuit: Dict[str, Any] = {}


class AuthRegisterReq(BaseModel):
    email: str
    password: str
    role: str = "student"  # student | teacher


class AuthLoginReq(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    ok: bool = True
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    role: str


class AuthMeResponse(BaseModel):
    ok: bool = True
    user_id: str
    email: str
    role: str
