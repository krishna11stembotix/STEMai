from fastapi import APIRouter, File, UploadFile
from typing import Dict, Any
import time

from app.models.schemas import Telemetry, Command

router = APIRouter()

IOT_LATEST: Dict[str, Dict[str, Any]] = {}
IOT_PENDING_CMD: Dict[str, Dict[str, Any]] = {}


@router.post("/iot/telemetry")
def iot_telemetry(payload: Telemetry):
    now = int(time.time())
    ts = payload.ts or now
    IOT_LATEST[payload.device_id] = {
        "device_id": payload.device_id,
        "ts": ts,
        "data": payload.data,
        "server_ts": now,
    }
    return {"ok": True, "device_id": payload.device_id, "server_ts": now}


@router.get("/iot/device/{device_id}/latest")
def iot_latest(device_id: str):
    return {"ok": True, "latest": IOT_LATEST.get(device_id)}


@router.post("/iot/device/{device_id}/command")
def iot_set_command(device_id: str, payload: Command):
    now = int(time.time())
    cmd = {
        "cmd_id": payload.cmd_id or f"cmd-{now}",
        "ts": payload.ts or now,
        "action": payload.action,
        "Stembotix": payload.Stembotix,
    }
    IOT_PENDING_CMD[device_id] = cmd
    return {"ok": True, "queued": cmd}


@router.get("/iot/device/{device_id}/command/next")
def iot_get_next_command(device_id: str):
    cmd = IOT_PENDING_CMD.pop(device_id, None)
    return {"ok": True, "cmd": cmd}
