# STEMbotix AI Backend - Complete API Routes

Base URL: `http://localhost:8123`

## Authentication Endpoints (`/auth`)

### POST `/auth/register`
Register a new user
```json
{
  "email": "user@example.com",
  "password": "password123",
  "role": "student"  // or "teacher"
}
```

### POST `/auth/login`
Login with credentials
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

### GET `/auth/me`
Get current user info
- Header: `Authorization: Bearer {token}`

---

## Blockzie Visual Programming (`/blockzie`)

### POST `/blockzie/open`
Open Blockzie editor

### POST `/blockzie/close`
Close Blockzie editor

### POST `/blockzie/inject`
Inject/replace program text
```json
{
  "text": "when green_flag:\n  forever:\n    move 10 steps",
  "auto_start": true
}
```

### POST `/blockzie/append`
Append program to existing code
```json
{
  "text": "say Hello",
  "auto_start": false
}
```

### POST `/blockzie/load_xml`
Load XML-based program
```json
{
  "xml": "<xml>...</xml>",
  "auto_start": true,
  "mode": "load"
}
```

### POST `/blockzie/stop`
Stop all running programs

### POST `/blockzie/clear`
Clear workspace (delete all blocks)

### GET `/blockzie/export`
Export current workspace as XML

### POST `/blockzie/remove_type`
Remove specific block type
```json
{
  "block_type": "controls_repeat"
}
```

### GET `/blockzie/debug_frames`
Get debug information about frames

### POST `/blockzie/generate`
AI-powered Blockzie program generator (uses OpenRouter API)
```json
{
  "prompt": "Create a program that moves a sprite back and forth",
  "role": "teacher",
  "auto_start": true,
  "mode": "inject"
}
```

Response:
```json
{
  "ok": true,
  "xml": "<xml xmlns=\"http://www.w3.org/1999/xhtml\">...</xml>",
  "block_count": 5,
  "model_used": "openai/gpt-4o-mini"
}
```

---

## Chat Endpoints (`/chat`)

### POST `/chat`
Send chat message with optional image
```json
{
  "messages": [
    {
      "role": "user",
      "content": "How does a motor work?"
    }
  ],
  "image_data_url": null,
  "user_id": "demo",
  "preferred_model": "openai/gpt-4o-mini"
}
```

---

## Voice Endpoints (`/voice`)

### POST `/voice`
Send audio for voice interaction
- Content-Type: `multipart/form-data`
- Fields:
  - `audio`: File (audio file)
  - `user_id`: String (default: "demo")
  - `lang`: String (default: "en")

Response:
```json
{
  "heard_text": "What is power?",
  "text": "Power is the rate of energy transfer...",
  "audio_reply_base64": "SUQzBAAAI1JTRKM=",
  "audio_mime": "audio/mpeg"
}
```

---

## Simulator - AI Circuit Planning (`/sim_ai`)

### POST `/sim_ai`
Generate circuit simulation project with AI
```json
{
  "mode": "agent_build",
  "prompt": "Build a LED blinker circuit",
  "circuit": {}
}
```

Response:
```json
{
  "ok": true,
  "reply": "Project generated successfully",
  "project": {
    "title": "LED Blinker",
    "description": "...",
    "components": [...],
    "connections": [...],
    "code": "..."
  }
}
```

---

## IoT Device Management (`/iot`)

### POST `/iot/telemetry`
Send device telemetry data
```json
{
  "device_id": "esp32_001",
  "ts": 1234567890,
  "data": {
    "temperature": 25.5,
    "humidity": 60
  }
}
```

### GET `/iot/device/{device_id}/latest`
Get latest telemetry from device

### POST `/iot/device/{device_id}/command`
Send command to device
```json
{
  "cmd_id": "cmd_001",
  "ts": 1234567890,
  "action": "led_on",
  "Stembotix": {}
}
```

### GET `/iot/device/{device_id}/command/next`
Poll for next pending command on device

---

## Agents (`/agent`)

### POST `/agent/make`
AI agent for building Blockzie programs
```json
{
  "prompt": "Create a program that makes sprite spin in circles"
}
```

---

## Programming Lab - Code Execution (`/api/lab`)

### POST `/api/lab/run`
Execute code (Python, JavaScript, C++)
```json
{
  "code": "print('Hello, World!')",
  "language": "python"
}
```

Supported languages: `python`, `javascript`, `c`, `cpp`

Response:
```json
{
  "success": true,
  "output": "Hello, World!\n",
  "error": "",
  "time": 0.2
}
```

### POST `/api/lab/terminal/start`
Start a terminal session
```json
{
  "code": "print('Starting session')",
  "language": "python"
}
```

Response:
```json
{
  "success": true,
  "session_id": "uuid-string",
  "output": "Starting session\n"
}
```

### POST `/api/lab/terminal/send`
Send input to running terminal session
```json
{
  "session_id": "uuid-string",
  "command": "print('test')"
}
```

### POST `/api/lab/terminal/kill`
Kill a terminal session
```json
{
  "session_id": "uuid-string"
}
```

### POST `/api/lab/agentic`
AI-powered code generation with execution
```json
{
  "prompt": "Write a program to calculate factorial",
  "language": "python"
}
```

Response:
```json
{
  "success": true,
  "code": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)\nprint(factorial(5))",
  "execution": {
    "success": true,
    "output": "120\n",
    "error": "",
    "time": 0.3
  },
  "label": "gpt-4o-mini"
}
```

### POST `/api/lab/generate/stream`
Stream-based code generation (for real-time UI updates)

---

## ESP32 Simulator - AI Circuit Generation (`/api/sim_ai`, `/api/sim`)

### POST `/api/sim_ai`
Generate ESP32 circuit simulation
```json
{
  "prompt": "Create temperature monitoring with DHT11",
  "mode": "agent_build"
}
```

### POST `/api/sim`
Simulate circuit design
```json
{
  "prompt": "Design an LED blinker circuit"
}
```

---

## Firmware Studio (`/firmware`)

### POST `/firmware/ai_generate`
AI-powered Arduino firmware generator
```json
{
  "prompt": "Create servo motor control program",
  "device_id": "my_device",
  "board": "ESP32",
  "fqbn": "esp32:esp32:esp32",
  "libraries": ["Servo.h"],
  "led_pin": "2",
  "dht_pin": "4",
  "adc_pin": "34"
}
```

### POST `/firmware/device_ping`
Ping device to check connectivity
```json
{
  "device_id": "my_device",
  "ip": "192.168.1.100"
}
```

### POST `/firmware/ota_push`
Push code to device via OTA (Over-The-Air)
```json
{
  "device_id": "my_device",
  "code": "void setup() {}\nvoid loop() {}"
}
```

### POST `/firmware/register_device`
Register/store device configuration
```json
{
  "device_id": "my_device",
  "ip": "192.168.1.100",
  "board": "ESP32",
  "fqbn": "esp32:esp32:esp32"
}
```

---

## Environment Variables for Requests

Set these in Postman as Collection Variables:

```
token: your_jwt_token_here
api_base: http://localhost:8000
device_id: esp32_001
```

---

## Route Mapping Summary

Routes are registered **both with and without `/api` prefix** due to Vercel proxy:
- `/chat` → also available as `/api/chat`
- `/voice` → also available as `/api/voice`
- `/simulator` → also available as `/api/simulator`
- `/iot/*` → also available as `/api/iot/*`
- `/agents/*` → also available as `/api/agents/*`
- `/auth/*` → also available as `/api/auth/*`
- `/blockzie/*` → stays as `/blockzie/*` (Blockzie specific)

---

## Quick Import Guide

### Option 1: Manual Import in Postman
1. Create a new collection named "STEMbotix AI Backend API"
2. For each endpoint above, create a new request
3. Set the method (GET/POST), URL, and body parameters as shown

### Option 2: Use Variables
Set collection variables for:
- `{{api_base}}` - Base URL (http://localhost:8000)
- `{{token}}` - JWT token from login
- `{{device_id}}` - Device identifier

Then use URLs like: `{{api_base}}/chat`

### Option 3: Authentication Flow
1. First call: `POST /auth/login` → get token in response
2. Set `token` variable to the `access_token` value
3. Use `Bearer {{token}}` in Authorization header for protected routes
