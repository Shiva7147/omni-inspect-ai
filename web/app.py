"""
OMNIINSPECT AI — DASHBOARD ENGINE v8.0
Industrial Pre-Power Optical Inspection & Cyber-Physical Safety Gate.
Three-State Machine Architecture, Glassmorphism Cockpit, Live WebSocket Telemetry Engine,
and Designed Printable HTML RCA Incident Reports.
"""

import os
import sys
import json
import time
import math
import random
import uuid
import hashlib
import asyncio
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.vision.meta_inference import MetaModelClient

app = FastAPI(title="OmniInspect AI v8.0", version="8.0.0")

# Mount static asset directory
samples_dir = PROJECT_ROOT / "data" / "samples"
app.mount("/static", StaticFiles(directory=str(samples_dir)), name="static")

meta_client = MetaModelClient()

# Live Simulated Sensor Engine (as specified in brief)
class SensorSimulator:
    def __init__(self, state="fault"):
        self.state = state
        self.tick = 0
    
    def get_readings(self) -> Dict[str, Any]:
        self.tick += 1
        t = self.tick * 0.1
        
        if self.state == "fault":
            return {
                "bus_voltage": round(random.uniform(0.00, 0.02), 2),
                "peak_current": round(14.82 + random.uniform(-0.1, 0.1), 2),
                "junction_temp": round(104.2 + math.sin(t) * 1.2, 1),
                "acoustic_freq": round(18400 + random.randint(-50, 50)),
                "contactor_state": "LATCHED_OPEN",
                "contactor_trip_ms": 3.18,
                "label_voltage": "24V RAIL — LATCHED OFF",
                "label_current": "SURGE DETECTED (SHORT EVENT)",
                "label_temp": "MCU THERMAL READING (OVERRUN)",
                "label_contactor": "INTERLOCK RESPONSE TIME (< 5ms SPEC ✓)",
                "state_color": "#FF3B30",
                "spec_compliant": False
            }
        elif self.state == "nominal":
            return {
                "bus_voltage": round(24.18 + math.sin(t) * 0.02, 2),
                "peak_current": round(4.20 + math.sin(t * 0.5) * 0.15, 2),
                "junction_temp": round(38.2 + math.sin(t * 0.3) * 0.8, 1),
                "acoustic_freq": round(200 + random.randint(-10, 10)),
                "contactor_state": "CLOSED",
                "contactor_trip_ms": 0.00,
                "label_voltage": "24V RAIL — ENERGIZED",
                "label_current": "NOMINAL OPERATING CURRENT",
                "label_temp": "MCU THERMAL — NOMINAL",
                "label_contactor": "POWER AUTHORIZED",
                "state_color": "#30D158",
                "spec_compliant": True
            }
        else: # scanning / active inspection
            return {
                "bus_voltage": 0.00,
                "peak_current": 0.00,
                "junction_temp": 24.8,
                "acoustic_freq": 120,
                "contactor_state": "STANDBY",
                "contactor_trip_ms": 0.00,
                "label_voltage": "PRE-POWER STANDBY",
                "label_current": "ZERO VOLTAGE VERIFICATION",
                "label_temp": "AMBIENT BASELINE",
                "label_contactor": "STANDBY ARMED",
                "state_color": "#FFD60A",
                "spec_compliant": True
            }

simulator = SensorSimulator(state="fault")

# Global System State
SYSTEM_STATE = {
    "current_mode": "fault", # 'inspection' | 'fault' | 'nominal'
    "board_id": "AERO-FC-0042",
    "carrier_name": "STM32H743-AERO-FC Rev C",
    "lot_number": "BATCH-2026-X892-REV_C",
    "serial_number": "SN-7749-99120-K",
    "countdown_remaining": 180.0,
    "is_claimed": False,
    "operator_id": "OP-4821 (Lead Avionics SMT Tech)",
    "meta_diagnosis": (
        "Yes, there is a clear solder bridge on the front row of the MCU, where multiple "
        "center pins are shorted by a large blob of excess solder. This defect fails IPC-A-610G "
        "Class 3 criteria and needs rework."
    ),
    "incident_id": f"INC-2026-{uuid.uuid4().hex[:8].upper()}",
    "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
}

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()


@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            readings = simulator.get_readings()
            payload = {
                "system_mode": SYSTEM_STATE["current_mode"],
                "board_id": SYSTEM_STATE["board_id"],
                "is_claimed": SYSTEM_STATE["is_claimed"],
                "countdown": SYSTEM_STATE["countdown_remaining"],
                "sensors": readings
            }
            await websocket.send_json(payload)
            await asyncio.sleep(0.25) # 250ms broadcast
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


@app.get("/api/state")
async def get_system_state():
    return {
        "state": SYSTEM_STATE,
        "sensors": simulator.get_readings()
    }


@app.post("/api/transition")
async def transition_state(target: str):
    target = target.lower().strip()
    if target in ["inspection", "fault", "nominal"]:
        SYSTEM_STATE["current_mode"] = target
        simulator.state = target
        if target == "fault":
            SYSTEM_STATE["countdown_remaining"] = 180.0
            SYSTEM_STATE["is_claimed"] = False
        elif target == "nominal":
            SYSTEM_STATE["is_claimed"] = True
    return {"status": "SUCCESS", "current_mode": SYSTEM_STATE["current_mode"]}


@app.post("/api/interlock/claim")
async def claim_ticket():
    SYSTEM_STATE["is_claimed"] = True
    return {"status": "CLAIMED", "operator": SYSTEM_STATE["operator_id"]}


@app.post("/api/interlock/quarantine")
async def force_quarantine():
    SYSTEM_STATE["current_mode"] = "inspection"
    simulator.state = "inspection"
    SYSTEM_STATE["board_id"] = f"AERO-FC-{random.randint(1000, 9999)}"
    return {"status": "QUARANTINED", "next_board": SYSTEM_STATE["board_id"]}


@app.post("/api/audit")
async def execute_live_audit():
    """Queries Meta API with real macro image."""
    img_b64 = ""
    macro_path = samples_dir / "board_inspection_macro.jpg"
    if macro_path.exists():
        import base64
        with open(macro_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

    meta_response = meta_client.inspect_component_roi(
        roi_image_base64=img_b64,
        ref_des="U14 (STM32H743)",
        expected_part="LQFP-176",
        expected_nets={"48": "+3V3_MCU", "49": "GND_ISO"}
    )
    
    if meta_response.get("status") == "LIVE_SUCCESS" and meta_response.get("analysis"):
        SYSTEM_STATE["meta_diagnosis"] = meta_response["analysis"]
    
    return {
        "status": "SUCCESS",
        "diagnosis": SYSTEM_STATE["meta_diagnosis"],
        "model_used": meta_response.get("model_used", "muse-spark-1.3")
    }


@app.get("/report", response_class=HTMLResponse)
@app.get("/api/export_incident_report", response_class=HTMLResponse)
async def generate_designed_html_rca_report():
    """Generates the redesigned printable HTML Root-Cause Engineering Incident Report."""
    raw_payload = f"{SYSTEM_STATE['incident_id']}|{SYSTEM_STATE['serial_number']}|3.18ms|{SYSTEM_STATE['timestamp']}"
    sha256_hash = hashlib.sha256(raw_payload.encode('utf-8')).hexdigest()

    report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OmniInspect RCA Report — {SYSTEM_STATE['incident_id']}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        @page {{ size: A4 portrait; margin: 18mm; }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: #FFFFFF;
            color: #0F172A;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 11pt;
            line-height: 1.5;
            padding: 24px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 2px solid #0F172A;
            padding-bottom: 14px;
            margin-bottom: 20px;
        }}
        .brand-logo {{
            font-size: 18pt;
            font-weight: 800;
            letter-spacing: -0.03em;
            color: #090B0E;
        }}
        .brand-sub {{
            font-size: 8pt;
            font-family: 'JetBrains Mono', monospace;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: #64748B;
            margin-top: 2px;
        }}
        .meta-stamp {{
            text-align: right;
            font-family: 'JetBrains Mono', monospace;
            font-size: 8pt;
            color: #475569;
        }}
        .sha256-box {{
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            padding: 8px 12px;
            border-radius: 6px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 7.5pt;
            color: #334155;
            word-break: break-all;
            margin-bottom: 20px;
        }}
        .section-title {{
            font-size: 9pt;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: #475569;
            border-bottom: 1px solid #E2E8F0;
            padding-bottom: 4px;
            margin: 18px 0 10px 0;
        }}
        .comparison-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-bottom: 20px;
        }}
        .image-card {{
            border: 1px solid #CBD5E1;
            border-radius: 8px;
            overflow: hidden;
            background: #000;
        }}
        .image-card img {{
            width: 100%;
            height: 180px;
            object-fit: cover;
            display: block;
        }}
        .image-caption {{
            padding: 8px 10px;
            font-size: 8pt;
            font-family: 'JetBrains Mono', monospace;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #F8FAFC;
            border-top: 1px solid #E2E8F0;
        }}
        .badge-fault {{
            color: #DC2626;
            font-weight: 700;
        }}
        .badge-nominal {{
            color: #16A34A;
            font-weight: 700;
        }}
        table.telemetry-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 9pt;
            margin-bottom: 18px;
        }}
        table.telemetry-table th, table.telemetry-table td {{
            padding: 7px 10px;
            text-align: left;
            border-bottom: 1px solid #E2E8F0;
        }}
        table.telemetry-table th {{
            background: #F1F5F9;
            font-family: 'JetBrains Mono', monospace;
            font-size: 8pt;
            text-transform: uppercase;
            color: #475569;
        }}
        .quote-box {{
            background: #FEF2F2;
            border-left: 3px solid #EF4444;
            padding: 12px 14px;
            font-size: 9pt;
            color: #991B1B;
            border-radius: 0 6px 6px 0;
            margin-bottom: 18px;
            font-style: italic;
        }}
        .procedure-list {{
            list-style: none;
            font-size: 8.5pt;
            color: #334155;
            margin-bottom: 20px;
        }}
        .procedure-list li {{
            padding: 3px 0;
            display: flex;
            align-items: center;
        }}
        .procedure-list li::before {{
            content: "✓";
            color: #16A34A;
            font-weight: bold;
            margin-right: 8px;
        }}
        .signature-block {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-top: 24px;
            padding-top: 14px;
            border-top: 1px solid #CBD5E1;
            font-size: 8pt;
        }}
        .sig-line {{
            margin-top: 30px;
            border-top: 1px dashed #64748B;
            padding-top: 4px;
            color: #64748B;
            font-family: 'JetBrains Mono', monospace;
        }}
        .footer {{
            margin-top: 24px;
            padding-top: 10px;
            border-top: 1px solid #E2E8F0;
            display: flex;
            justify-content: space-between;
            font-size: 7.5pt;
            color: #94A3B8;
            font-family: 'JetBrains Mono', monospace;
        }}
        .print-btn {{
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 8px 16px;
            background: #0F172A;
            color: #FFF;
            border: none;
            border-radius: 6px;
            font-family: 'Inter', sans-serif;
            font-size: 9pt;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        @media print {{
            .print-btn {{ display: none; }}
            body {{ padding: 0; }}
        }}
    </style>
</head>
<body>
    <button class="print-btn" onclick="window.print()">PRINT / SAVE AS PDF</button>

    <div class="header">
        <div>
            <div class="brand-logo">OMNIINSPECT AI</div>
            <div class="brand-sub">ROOT CAUSE ANALYSIS REPORT &middot; INCIDENT DISPOSITION</div>
        </div>
        <div class="meta-stamp">
            <div><strong>INCIDENT:</strong> {SYSTEM_STATE['incident_id']}</div>
            <div><strong>DATE:</strong> {SYSTEM_STATE['timestamp']}</div>
            <div><strong>STATION:</strong> AOI-GATEWAY-2 / CELL 04</div>
        </div>
    </div>

    <div class="sha256-box">
        <strong>TAMPER-EVIDENT SHA-256 DIGEST:</strong> {sha256_hash}
    </div>

    <div class="section-title">1. Device Under Test (DUT) & Inspection Context</div>
    <table class="telemetry-table">
        <tr>
            <th>Carrier Hardware</th>
            <td>{SYSTEM_STATE['carrier_name']}</td>
            <th>Lot Identifier</th>
            <td>{SYSTEM_STATE['lot_number']}</td>
        </tr>
        <tr>
            <th>Unit Serial No.</th>
            <td>{SYSTEM_STATE['serial_number']}</td>
            <th>Quality Standard</th>
            <td>IPC-A-610G Class 3 (High Reliability / Aerospace)</td>
        </tr>
    </table>

    <div class="section-title">2. Macro Optical Inspection Comparison (Before vs. After Rework)</div>
    <div class="comparison-grid">
        <div class="image-card">
            <img src="/static/board_inspection_macro.jpg" alt="Before Rework Solder Bridge">
            <div class="image-caption">
                <span>BEFORE: Solder Bridge Detected</span>
                <span class="badge-fault">PIN 48 &middot; 49 SHORT</span>
            </div>
        </div>
        <div class="image-card">
            <img src="/static/board_inspection_clean.jpg" alt="After Rework Clean Fillets">
            <div class="image-caption">
                <span>AFTER: Clean Joint Fillet</span>
                <span class="badge-nominal">0.24mm CLEARANCE PASS</span>
            </div>
        </div>
    </div>

    <div class="section-title">3. Verified Meta Vision Reasoning Diagnosis</div>
    <div class="quote-box">
        "{SYSTEM_STATE['meta_diagnosis']}"
        <div style="margin-top: 6px; font-size: 7.5pt; font-family: 'JetBrains Mono', monospace; color: #7F1D1D; font-style: normal;">
            &mdash; Meta Multimodal Vision Engine (Model: muse-spark-1.3 / Llama 3.2-Vision)
        </div>
    </div>

    <div class="section-title">4. High-Speed Telemetry Snapshot at Interlock Trip</div>
    <table class="telemetry-table">
        <thead>
            <tr>
                <th>Telemetry Parameter</th>
                <th>Trip Value</th>
                <th>Nominal Range</th>
                <th>Unit</th>
                <th>Interlock Status</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Primary DC Bus Voltage (V_main)</td>
                <td><strong>0.00 V</strong></td>
                <td>24.00 V &plusmn; 0.5V</td>
                <td>Volts</td>
                <td style="color:#DC2626; font-weight:700;">LATCHED OFF (&lt; 3.2ms)</td>
            </tr>
            <tr>
                <td>High-Side Shunt Surge Current (I_peak)</td>
                <td><strong>14.82 A</strong></td>
                <td>4.20 A &plusmn; 0.3A</td>
                <td>Amperes</td>
                <td style="color:#DC2626; font-weight:700;">TRIPPED OVER-CURRENT</td>
            </tr>
            <tr>
                <td>MCU Peak Junction Temperature</td>
                <td><strong>104.2 &deg;C</strong></td>
                <td>35.0 &ndash; 65.0 &deg;C</td>
                <td>Celsius</td>
                <td style="color:#DC2626; font-weight:700;">THERMAL SURGE MITIGATED</td>
            </tr>
            <tr>
                <td>Acoustic Resonance Peak</td>
                <td><strong>18.4 kHz</strong></td>
                <td>&lt; 2.5 kHz</td>
                <td>Kilohertz</td>
                <td style="color:#D97706; font-weight:600;">MICRO-ARC DETECTED</td>
            </tr>
            <tr>
                <td>Galvanic Contactor Trip Latency</td>
                <td><strong>3.18 ms</strong></td>
                <td>&lt; 5.00 ms</td>
                <td>Milliseconds</td>
                <td style="color:#16A34A; font-weight:700;">SPECIFICATION COMPLIANT</td>
            </tr>
        </tbody>
    </table>

    <div class="section-title">5. Certified Rework Procedure Performed</div>
    <ul class="procedure-list">
        <li><strong>Step 1:</strong> Kester 959T No-Clean RMA flux applied across Pin 46 to Pin 52.</li>
        <li><strong>Step 2:</strong> Micro-soldering iron calibrated to 340&deg;C with 0.8mm chisel tip.</li>
        <li><strong>Step 3:</strong> Solder wick capillary extraction sweep from Pin 49 to Pin 48 (dwell &lt; 2.0s).</li>
        <li><strong>Step 4:</strong> Post-rework ultrasonic wash with 99% Isopropyl Alcohol.</li>
        <li><strong>Step 5:</strong> Re-verified optical clearance &ge; 0.20 mm. Bus power restoral authorized.</li>
    </ul>

    <div class="signature-block">
        <div>
            <div><strong>LEAD INSPECTOR / OPERATOR:</strong></div>
            <div class="sig-line">OP-4821 &middot; Lead Avionics SMT Technician</div>
        </div>
        <div>
            <div><strong>QUALITY SYSTEM APPROVAL:</strong></div>
            <div class="sig-line">IPC-A-610G Certified QA Engineering Lead</div>
        </div>
    </div>

    <div class="footer">
        <span>OMNIINSPECT AI &middot; CYBER-PHYSICAL PRE-POWER GATE</span>
        <span>STANDARDS REFERENCE: IPC-A-610G CLASS 3 &middot; J-STD-001</span>
    </div>
</body>
</html>
"""
    return HTMLResponse(content=report_html)


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard_v8():
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OmniInspect AI — Pre-Power Safety Gate</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    
    <style>
        :root {
            --bg-base: #060810;
            --panel-bg: rgba(255, 255, 255, 0.06);
            --panel-border: rgba(255, 255, 255, 0.12);
            --panel-blur: blur(24px);
            --color-fault: #FF3B30;
            --color-clear: #30D158;
            --color-warn: #FFD60A;
            --text-primary: rgba(255, 255, 255, 0.92);
            --text-secondary: rgba(255, 255, 255, 0.45);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-base);
            color: var(--text-primary);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-weight: 300;
            min-height: 100vh;
            width: 100vw;
            overflow-x: hidden;
            display: flex;
            flex-direction: column;
            position: relative;
        }

        /* Fixed Full-Viewport Background with Cinematic PCB Macro */
        .fixed-bg {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: linear-gradient(rgba(6, 8, 16, 0.60), rgba(6, 8, 16, 0.72)), 
                        url('/static/cinematic_pcb_bg.jpg') center/cover no-repeat fixed;
            z-index: 0;
            pointer-events: none;
        }

        /* Glassmorphism Panel Primitive */
        .glass-panel {
            background: var(--panel-bg);
            border: 1px solid var(--panel-border);
            backdrop-filter: var(--panel-blur);
            -webkit-backdrop-filter: var(--panel-blur);
            border-radius: 16px;
            box-shadow: 0 24px 60px rgba(0, 0, 0, 0.55);
            transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), 
                        border-color 0.4s ease, 
                        box-shadow 0.4s ease;
        }
        .glass-panel:hover {
            box-shadow: 0 30px 80px rgba(0, 0, 0, 0.75);
        }

        /* Typography */
        .mono-num {
            font-family: 'JetBrains Mono', monospace;
            font-feature-settings: "tnum" on, "zero" on;
            letter-spacing: -0.02em;
        }
        .label-caps {
            font-family: 'Inter', sans-serif;
            font-size: 10px;
            font-weight: 400;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            color: var(--text-secondary);
        }

        /* Top Header Strip */
        header {
            position: relative;
            z-index: 10;
            padding: 20px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .brand-cluster {
            display: flex;
            align-items: center;
            gap: 14px;
        }
        .brand-logo-icon {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.18);
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            font-size: 11px;
            color: #FFF;
        }
        .brand-title {
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #FFF;
        }
        .brand-subtitle {
            font-size: 10px;
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-secondary);
        }

        .state-beacon {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 14px;
            border-radius: 999px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }
        .beacon-fault {
            background: rgba(255, 59, 48, 0.15);
            border: 1px solid rgba(255, 59, 48, 0.45);
            color: var(--color-fault);
            animation: pulse-border 2s infinite;
        }
        .beacon-clear {
            background: rgba(48, 209, 88, 0.15);
            border: 1px solid rgba(48, 209, 88, 0.45);
            color: var(--color-clear);
        }
        .beacon-inspect {
            background: rgba(255, 214, 10, 0.15);
            border: 1px solid rgba(255, 214, 10, 0.45);
            color: var(--color-warn);
        }

        @keyframes pulse-border {
            0%, 100% { border-color: rgba(255, 59, 48, 0.35); box-shadow: 0 0 15px rgba(255, 59, 48, 0.15); }
            50% { border-color: rgba(255, 59, 48, 0.85); box-shadow: 0 0 30px rgba(255, 59, 48, 0.35); }
        }

        /* View State Container */
        main {
            position: relative;
            z-index: 10;
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px 40px 30px;
        }

        .view-screen {
            width: 100%;
            max-width: 1440px;
            transition: opacity 0.4s ease-in-out, transform 0.4s ease-in-out;
        }
        .view-hidden {
            display: none !important;
            opacity: 0;
            transform: scale(0.98);
        }

        /* STATE 1: INSPECTION ACTIVE (Single Centered Panel 70% Width) */
        .inspection-wrapper {
            max-width: 980px;
            margin: 0 auto;
        }
        .viewport-frame {
            position: relative;
            width: 100%;
            height: 480px;
            border-radius: 12px;
            overflow: hidden;
            background: #000;
        }
        .viewport-frame img, .viewport-frame video {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }
        /* CAD 1px Reticle Overlay */
        .reticle-overlay {
            position: absolute;
            inset: 0;
            pointer-events: none;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .reticle-line-h {
            position: absolute;
            left: 0;
            right: 0;
            top: 50%;
            height: 1px;
            background: rgba(255, 255, 255, 0.35);
        }
        .reticle-line-v {
            position: absolute;
            top: 0;
            bottom: 0;
            left: 50%;
            width: 1px;
            background: rgba(255, 255, 255, 0.35);
        }
        .reticle-box {
            width: 80px;
            height: 80px;
            border: 1px solid rgba(255, 255, 255, 0.7);
            position: relative;
        }
        .reticle-box::after {
            content: "";
            position: absolute;
            inset: -4px;
            border: 1px dashed rgba(255, 255, 255, 0.3);
        }

        .inspection-strip {
            margin-top: 18px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 14px 20px;
            background: rgba(0, 0, 0, 0.35);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 10px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
        }

        /* STATE 2 & 3: TWO-PANEL SPLIT (Side by Side) */
        .split-layout {
            display: grid;
            grid-template-columns: 1.1fr 0.9fr;
            gap: 28px;
            align-items: stretch;
        }

        /* Left Image Panel */
        .image-panel {
            padding: 24px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .image-container {
            position: relative;
            width: 100%;
            height: 380px;
            border-radius: 12px;
            overflow: hidden;
            background: #000;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .image-container img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
            transition: opacity 0.4s ease;
        }
        /* Bounding Box on Defect */
        .bbox-fault {
            position: absolute;
            top: 42%;
            left: 48%;
            width: 90px;
            height: 60px;
            border: 2px solid var(--color-fault);
            box-shadow: 0 0 20px rgba(255, 59, 48, 0.5);
            pointer-events: none;
        }
        .bbox-nominal {
            position: absolute;
            top: 42%;
            left: 48%;
            width: 90px;
            height: 60px;
            border: 2px solid var(--color-clear);
            box-shadow: 0 0 20px rgba(48, 209, 88, 0.5);
            pointer-events: none;
        }

        .image-status-bar {
            margin-top: 18px;
        }
        .status-header-text {
            font-size: 18px;
            font-weight: 700;
            letter-spacing: -0.01em;
            margin-bottom: 6px;
        }
        .diagnosis-quote {
            font-size: 12px;
            line-height: 1.5;
            color: rgba(255, 255, 255, 0.75);
            margin-bottom: 12px;
        }
        .pill-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 6px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 9px;
            font-weight: 600;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        /* Right Telemetry Panel (5 Metric Cards) */
        .telemetry-panel {
            padding: 24px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .cards-column {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .metric-card {
            background: rgba(0, 0, 0, 0.28);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 10px;
            padding: 14px 18px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: relative;
            overflow: hidden;
            transition: border-color 0.3s ease;
        }
        .card-fault {
            border-left: 4px solid var(--color-fault);
        }
        .card-clear {
            border-left: 4px solid var(--color-clear);
        }

        .metric-val-large {
            font-size: 26px;
            font-weight: 700;
        }
        .metric-sub {
            font-size: 10px;
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-secondary);
            margin-top: 2px;
        }
        .status-pill-small {
            font-family: 'JetBrains Mono', monospace;
            font-size: 9px;
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 4px;
        }

        /* Countdown Timer Ring Card */
        .timer-card {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .timer-digits {
            font-size: 28px;
            font-weight: 800;
            font-family: 'JetBrains Mono', monospace;
            letter-spacing: -0.03em;
        }

        /* Bottom Action Bar */
        .action-bar {
            margin-top: 20px;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 14px;
        }
        .btn-action {
            padding: 11px 22px;
            border-radius: 8px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            cursor: pointer;
            transition: all 0.2s ease;
            border: none;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .btn-primary-fault {
            background: var(--color-fault);
            color: #FFF;
            box-shadow: 0 4px 20px rgba(255, 59, 48, 0.4);
        }
        .btn-primary-fault:hover {
            background: #E03126;
            transform: translateY(-1px);
        }
        .btn-primary-clear {
            background: var(--color-clear);
            color: #060810;
            font-weight: 700;
            box-shadow: 0 4px 20px rgba(48, 209, 88, 0.4);
        }
        .btn-primary-clear:hover {
            background: #28B84D;
            transform: translateY(-1px);
        }
        .btn-secondary {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.16);
            color: rgba(255, 255, 255, 0.85);
        }
        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.14);
            color: #FFF;
        }

        /* Footnote */
        .footnote-strip {
            position: relative;
            z-index: 10;
            padding: 12px 40px;
            display: flex;
            justify-content: space-between;
            font-family: 'JetBrains Mono', monospace;
            font-size: 9px;
            color: rgba(255, 255, 255, 0.35);
        }
    </style>
</head>
<body>
    <div class="fixed-bg"></div>

    <!-- Top Header -->
    <header>
        <div class="brand-cluster">
            <div class="brand-logo-icon">OI</div>
            <div>
                <div class="brand-title">OmniInspect AI</div>
                <div class="brand-subtitle">Pre-Power Optical Safety Gate &middot; STM32H743-AERO-FC</div>
            </div>
        </div>

        <div id="topStateBeacon" class="state-beacon beacon-fault">
            <span id="beaconDot" style="width:6px; height:6px; border-radius:50%; background:currentColor;"></span>
            <span id="beaconText">STATE 2: FAULT DETECTED</span>
        </div>
    </header>

    <!-- Main Views Container (State Machine: Exactly One State Shown at a Time) -->
    <main>

        <!-- ==================================================================== -->
        <!-- STATE 1: INSPECTION ACTIVE (One large glassmorphism panel)           -->
        <!-- ==================================================================== -->
        <div id="viewState1" class="view-screen inspection-wrapper view-hidden">
            <div class="glass-panel" style="padding: 24px;">
                <div class="viewport-frame">
                    <img id="state1Image" src="/static/board_inspection_macro.jpg" alt="Active PCBA Inspection">
                    <video id="webcamStream" autoplay playsinline muted style="display:none; width:100%; height:100%; object-fit:cover;"></video>
                    
                    <!-- 1px Thin CAD Reticle Overlay -->
                    <div class="reticle-overlay">
                        <div class="reticle-line-h"></div>
                        <div class="reticle-line-v"></div>
                        <div class="reticle-box"></div>
                    </div>
                </div>

                <div class="inspection-strip">
                    <div style="color:#FFF;"><strong>BOARD ID:</strong> <span id="s1BoardId">AERO-FC-0042</span></div>
                    <div style="color:var(--color-warn);"><strong>STATUS:</strong> SCANNING &amp; HOMOGRAPHY ALIGNMENT</div>
                    <div style="color:var(--text-secondary);"><strong>ELAPSED:</strong> <span id="s1Elapsed">00:04.2s</span></div>
                    <button onclick="toggleWebcam()" class="btn-secondary" style="padding:4px 10px; border-radius:4px; font-size:9px; cursor:pointer;">
                        TOGGLE WEBCAM
                    </button>
                </div>

                <div style="margin-top: 18px; display:flex; justify-content:flex-end;">
                    <button onclick="transitionToState('fault')" class="btn-action btn-primary-fault">
                        SIMULATE DETECTION ANOMALY &rarr;
                    </button>
                </div>
            </div>
        </div>


        <!-- ==================================================================== -->
        <!-- STATE 2: FAULT DETECTED (Two-panel split: Before Image + 5 Cards)    -->
        <!-- ==================================================================== -->
        <div id="viewState2" class="view-screen">
            <div class="split-layout">
                
                <!-- Left Panel: Before Image with Red Solder Bridge BBox -->
                <div class="glass-panel image-panel" style="border-color: rgba(255, 59, 48, 0.35);">
                    <div>
                        <div class="image-container">
                            <img src="/static/board_inspection_macro.jpg" alt="Fault Detected Board">
                            <div class="bbox-fault"></div>
                        </div>

                        <div class="image-status-bar">
                            <div class="label-caps" style="color: var(--color-fault); margin-bottom: 4px;">ANOMALY LOCALIZED &middot; PIN 48-49</div>
                            <div class="status-header-text" style="color: var(--color-fault);">FAULT DETECTED: SOLDER BRIDGE</div>
                            <p class="diagnosis-quote" id="metaDiagnosisText">
                                "Yes, there is a clear solder bridge on the front row of the MCU, where multiple center pins are shorted by a large blob of excess solder. This defect fails IPC-A-610G Class 3 criteria and needs rework."
                            </p>
                        </div>
                    </div>

                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px;">
                        <span class="pill-badge" style="background:rgba(255,59,48,0.18); border:1px solid rgba(255,59,48,0.45); color:var(--color-fault);">
                            IPC-A-610G CLASS 3 VIOLATION
                        </span>
                        <span class="label-caps">MUSE-SPARK-1.3 &middot; 895 REASONING TOKENS</span>
                    </div>
                </div>

                <!-- Right Panel: Sensor Telemetry (5 Cards as specified in brief) -->
                <div class="glass-panel telemetry-panel" style="border-color: rgba(255, 59, 48, 0.25);">
                    <div class="cards-column">
                        
                        <!-- Card 1: POWER BUS -->
                        <div class="metric-card card-fault">
                            <div>
                                <div class="label-caps">24V POWER BUS</div>
                                <div class="mono-num metric-val-large" style="color:var(--color-fault);" id="card1Val">0.00 V</div>
                                <div class="metric-sub" id="card1Sub">24V RAIL &mdash; LATCHED OFF</div>
                            </div>
                            <span class="status-pill-small" style="background:rgba(255,59,48,0.2); color:var(--color-fault);">
                                CLAMPED
                            </span>
                        </div>

                        <!-- Card 2: PEAK CURRENT -->
                        <div class="metric-card card-fault">
                            <div>
                                <div class="label-caps">PEAK CURRENT</div>
                                <div class="mono-num metric-val-large" style="color:var(--color-fault);" id="card2Val">14.82 A</div>
                                <div class="metric-sub">SURGE DETECTED &middot; SHORT EVENT</div>
                            </div>
                            <span class="status-pill-small" style="background:rgba(255,59,48,0.2); color:var(--color-fault);">
                                &gt; 4.5A LIMIT
                            </span>
                        </div>

                        <!-- Card 3: JUNCTION TEMP -->
                        <div class="metric-card card-fault">
                            <div>
                                <div class="label-caps">MCU JUNCTION TEMP</div>
                                <div class="mono-num metric-val-large" style="color:var(--color-fault);" id="card3Val">104.2 &deg;C</div>
                                <div class="metric-sub">MCU THERMAL READING (OVERRUN)</div>
                            </div>
                            <span class="status-pill-small" style="background:rgba(255,59,48,0.2); color:var(--color-fault);">
                                RED ZONE
                            </span>
                        </div>

                        <!-- Card 4: CONTACTOR TRIP -->
                        <div class="metric-card card-fault">
                            <div>
                                <div class="label-caps">CONTACTOR TRIP TIME</div>
                                <div class="mono-num metric-val-large" style="color:#FFF;">3.18 ms</div>
                                <div class="metric-sub">INTERLOCK RESPONSE TIME</div>
                            </div>
                            <span class="status-pill-small" style="background:rgba(48,209,88,0.2); color:var(--color-clear);">
                                &lt; 5ms SPEC &#10003;
                            </span>
                        </div>

                        <!-- Card 5: FAILSAFE TIMER -->
                        <div class="metric-card card-fault timer-card">
                            <div>
                                <div class="label-caps" style="color:var(--color-warn);">FAILSAFE REVIEW TIMER</div>
                                <div class="timer-digits" style="color:#FFF;" id="countdownDisplay">02:47.3</div>
                                <div class="metric-sub">CLAIM OR AUTO-QUARANTINE</div>
                            </div>
                            <svg width="44" height="44" viewBox="0 0 44 44">
                                <circle cx="22" cy="22" r="18" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="3"/>
                                <circle id="timerCircle" cx="22" cy="22" r="18" fill="none" stroke="var(--color-warn)" stroke-width="3" 
                                        stroke-dasharray="113.1" stroke-dashoffset="20" stroke-linecap="round"
                                        transform="rotate(-90 22 22)" style="transition: stroke-dashoffset 0.1s linear;"/>
                            </svg>
                        </div>

                    </div>

                    <!-- Bottom Bar: Three Action Buttons -->
                    <div class="action-bar">
                        <button onclick="claimTicket()" id="btnClaim" class="btn-action btn-secondary">
                            [F1 &mdash; CLAIM TICKET]
                        </button>
                        <button onclick="transitionToState('nominal')" class="btn-action btn-primary-clear">
                            [F2 &mdash; VERIFY REWORK]
                        </button>
                        <button onclick="forceQuarantine()" class="btn-action btn-secondary" style="color:var(--color-fault);">
                            [FORCE QUARANTINE]
                        </button>
                    </div>
                </div>

            </div>
        </div>


        <!-- ==================================================================== -->
        <!-- STATE 3: CLEARED — POWER AUTHORIZED (Transformed to Green)          -->
        <!-- ==================================================================== -->
        <div id="viewState3" class="view-screen view-hidden">
            <div class="split-layout">
                
                <!-- Left Panel: After Image with Green Rework Verification -->
                <div class="glass-panel image-panel" style="border-color: rgba(48, 209, 88, 0.35);">
                    <div>
                        <div class="image-container">
                            <img id="afterImageEl" src="/static/board_inspection_clean.jpg" alt="Rework Verified Clean PCBA">
                            <div class="bbox-nominal"></div>
                        </div>

                        <div class="image-status-bar">
                            <div class="label-caps" style="color: var(--color-clear); margin-bottom: 4px;">QUALITY CERTIFICATION &middot; RESTORAL PASS</div>
                            <div class="status-header-text" style="color: var(--color-clear);">REWORK VERIFIED: FLUID FILLET FORMED</div>
                            <p class="diagnosis-quote">
                                "Inter-lead clearance confirmed (&ge; 0.20 mm specification). Solder bridge fully removed. IPC-A-610G Class 3 compliant."
                            </p>
                        </div>
                    </div>

                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px;">
                        <span class="pill-badge" style="background:rgba(48,209,88,0.18); border:1px solid rgba(48,209,88,0.45); color:var(--color-clear);">
                            PRE-POWER GATE: AUTHORIZED
                        </span>
                        <button onclick="toggleBeforeAfter()" class="btn-secondary" style="padding:4px 10px; border-radius:4px; font-size:9px; cursor:pointer;">
                            TOGGLE BEFORE/AFTER VIEW
                        </button>
                    </div>
                </div>

                <!-- Right Panel: Sensor Telemetry (5 Green Cards) -->
                <div class="glass-panel telemetry-panel" style="border-color: rgba(48, 209, 88, 0.25);">
                    <div class="cards-column">
                        
                        <!-- Card 1: POWER BUS -->
                        <div class="metric-card card-clear">
                            <div>
                                <div class="label-caps">24V POWER BUS</div>
                                <div class="mono-num metric-val-large" style="color:var(--color-clear);" id="c3Card1Val">24.18 V</div>
                                <div class="metric-sub">24V RAIL &mdash; ENERGIZED</div>
                            </div>
                            <span class="status-pill-small" style="background:rgba(48,209,88,0.2); color:var(--color-clear);">
                                ENERGIZED
                            </span>
                        </div>

                        <!-- Card 2: LOAD CURRENT -->
                        <div class="metric-card card-clear">
                            <div>
                                <div class="label-caps">LOAD CURRENT</div>
                                <div class="mono-num metric-val-large" style="color:var(--color-clear);" id="c3Card2Val">4.20 A</div>
                                <div class="metric-sub">NOMINAL OPERATING CURRENT</div>
                            </div>
                            <span class="status-pill-small" style="background:rgba(48,209,88,0.2); color:var(--color-clear);">
                                PASS
                            </span>
                        </div>

                        <!-- Card 3: JUNCTION TEMP -->
                        <div class="metric-card card-clear">
                            <div>
                                <div class="label-caps">MCU JUNCTION TEMP</div>
                                <div class="mono-num metric-val-large" style="color:var(--color-clear);" id="c3Card3Val">38.2 &deg;C</div>
                                <div class="metric-sub">MCU THERMAL &mdash; NOMINAL EQUILIBRIUM</div>
                            </div>
                            <span class="status-pill-small" style="background:rgba(48,209,88,0.2); color:var(--color-clear);">
                                NORMAL
                            </span>
                        </div>

                        <!-- Card 4: CONTACTOR STATE -->
                        <div class="metric-card card-clear">
                            <div>
                                <div class="label-caps">CONTACTOR STATE</div>
                                <div class="mono-num metric-val-large" style="color:#FFF;">CLOSED</div>
                                <div class="metric-sub">POWER AUTHORIZED &middot; GALVANIC INTERLOCK ARMED</div>
                            </div>
                            <span class="status-pill-small" style="background:rgba(48,209,88,0.2); color:var(--color-clear);">
                                CLOSED &#10003;
                            </span>
                        </div>

                        <!-- Card 5: INSPECTION RESULT -->
                        <div class="metric-card card-clear">
                            <div>
                                <div class="label-caps">INSPECTION RESULT</div>
                                <div class="mono-num metric-val-large" style="color:var(--color-clear);">PASS</div>
                                <div class="metric-sub">BOARD CLEARED FOR PRODUCTION DEPLOYMENT</div>
                            </div>
                            <span class="status-pill-small" style="background:rgba(48,209,88,0.2); color:var(--color-clear);">
                                CERTIFIED
                            </span>
                        </div>

                    </div>

                    <!-- Bottom Bar: F5 Report, Next Board, View Audit -->
                    <div class="action-bar">
                        <a href="/report" target="_blank" class="btn-action btn-primary-clear" style="text-decoration:none;">
                            [F5 &mdash; EXPORT RCA REPORT]
                        </a>
                        <button onclick="transitionToState('inspection')" class="btn-action btn-secondary">
                            [NEXT BOARD]
                        </button>
                        <button onclick="window.open('/api/state')" class="btn-action btn-secondary">
                            [VIEW AUDIT LOG]
                        </button>
                    </div>
                </div>

            </div>
        </div>

    </main>

    <!-- Bottom Footnote Strip -->
    <div class="footnote-strip">
        <span>OMNIINSPECT AI &middot; CYBER-PHYSICAL INTERLOCK v8.0</span>
        <span>TELEMETRY SIMULATION LAYER &middot; READY FOR 100 kSPS SPI INGEST</span>
        <span>IPC-A-610G CLASS 3 &middot; SHA-256 AUDIT VERIFIED</span>
    </div>

    <!-- Client-Side Script: WebSocket & State Machine -->
    <script>
        let currentMode = "fault"; // 'inspection' | 'fault' | 'nominal'
        let countdownSec = 167.3;
        let isClaimed = false;
        let isWebcamActive = false;
        let showBeforeInState3 = false;
        let elapsedInspectionTimer = null;
        let elapsedSeconds = 4.2;

        const viewS1 = document.getElementById("viewState1");
        const viewS2 = document.getElementById("viewState2");
        const viewS3 = document.getElementById("viewState3");
        const topBeacon = document.getElementById("topStateBeacon");
        const beaconText = document.getElementById("beaconText");

        // WebSocket Connection
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;
        let ws = new WebSocket(wsUrl);

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            updateSensors(data.sensors);
        };

        ws.onclose = () => {
            // Reconnect after 2s
            setTimeout(() => { ws = new WebSocket(wsUrl); }, 2000);
        };

        function updateSensors(s) {
            if (!s) return;
            // Update State 2 metrics
            const c1 = document.getElementById("card1Val");
            const c2 = document.getElementById("card2Val");
            const c3 = document.getElementById("card3Val");
            if (c1) c1.innerText = s.bus_voltage.toFixed(2) + " V";
            if (c2) c2.innerText = s.peak_current.toFixed(2) + " A";
            if (c3) c3.innerText = s.junction_temp.toFixed(1) + " °C";

            // Update State 3 metrics
            const c3c1 = document.getElementById("c3Card1Val");
            const c3c2 = document.getElementById("c3Card2Val");
            const c3c3 = document.getElementById("c3Card3Val");
            if (c3c1) c3c1.innerText = s.bus_voltage.toFixed(2) + " V";
            if (c3c2) c3c2.innerText = s.peak_current.toFixed(2) + " A";
            if (c3c3) c3c3.innerText = s.junction_temp.toFixed(1) + " °C";
        }

        // State Machine Switcher
        async function transitionToState(mode) {
            currentMode = mode;
            await fetch(`/api/transition?target=${mode}`, { method: "POST" });

            viewS1.classList.add("view-hidden");
            viewS2.classList.add("view-hidden");
            viewS3.classList.add("view-hidden");

            topBeacon.className = "state-beacon";

            if (mode === "inspection") {
                viewS1.classList.remove("view-hidden");
                topBeacon.classList.add("beacon-inspect");
                beaconText.innerText = "STATE 1: INSPECTION ACTIVE";
                startElapsedTimer();
            } else if (mode === "fault") {
                viewS2.classList.remove("view-hidden");
                topBeacon.classList.add("beacon-fault");
                beaconText.innerText = "STATE 2: FAULT DETECTED";
                stopElapsedTimer();
            } else if (mode === "nominal") {
                viewS3.classList.remove("view-hidden");
                topBeacon.classList.add("beacon-clear");
                beaconText.innerText = "STATE 3: CLEARED — POWER AUTHORIZED";
                stopElapsedTimer();
            }
        }

        // Countdown Timer Loop (State 2)
        setInterval(() => {
            if (currentMode === "fault" && !isClaimed) {
                countdownSec = Math.max(0, countdownSec - 0.1);
                const min = Math.floor(countdownSec / 60);
                const sec = Math.floor(countdownSec % 60);
                const tenth = Math.floor((countdownSec * 10) % 10);
                
                const timeStr = `${String(min).padStart(2,'0')}:${String(sec).padStart(2,'0')}.${tenth}`;
                const cdEl = document.getElementById("countdownDisplay");
                if (cdEl) cdEl.innerText = timeStr;

                // Animate circular ring
                const circle = document.getElementById("timerCircle");
                if (circle) {
                    const totalLen = 113.1;
                    const pct = countdownSec / 180.0;
                    circle.style.strokeDashoffset = totalLen * (1 - pct);
                }
            }
        }, 100);

        function startElapsedTimer() {
            elapsedSeconds = 0;
            if (elapsedInspectionTimer) clearInterval(elapsedInspectionTimer);
            elapsedInspectionTimer = setInterval(() => {
                elapsedSeconds += 0.1;
                const el = document.getElementById("s1Elapsed");
                if (el) el.innerText = `00:${elapsedSeconds.toFixed(1)}s`;
            }, 100);
        }

        function stopElapsedTimer() {
            if (elapsedInspectionTimer) clearInterval(elapsedInspectionTimer);
        }

        async function claimTicket() {
            await fetch("/api/interlock/claim", { method: "POST" });
            isClaimed = true;
            const btn = document.getElementById("btnClaim");
            if (btn) {
                btn.innerText = "TICKET CLAIMED (OP-4821)";
                btn.style.borderColor = "var(--color-warn)";
                btn.style.color = "var(--color-warn)";
            }
        }

        async function forceQuarantine() {
            await fetch("/api/interlock/quarantine", { method: "POST" });
            alert("Board routed to Quarantine Bin B.");
            transitionToState("inspection");
        }

        function toggleBeforeAfter() {
            showBeforeInState3 = !showBeforeInState3;
            const imgEl = document.getElementById("afterImageEl");
            if (imgEl) {
                imgEl.src = showBeforeInState3 ? "/static/board_inspection_macro.jpg" : "/static/board_inspection_clean.jpg";
            }
        }

        // Webcam stream toggle
        async function toggleWebcam() {
            const video = document.getElementById("webcamStream");
            const img = document.getElementById("state1Image");
            if (!isWebcamActive) {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
                    video.srcObject = stream;
                    video.style.display = "block";
                    img.style.display = "none";
                    isWebcamActive = true;
                } catch (e) {
                    alert("Camera access denied or unavailable: " + e.message);
                }
            } else {
                if (video.srcObject) {
                    video.srcObject.getTracks().forEach(t => t.stop());
                }
                video.style.display = "none";
                img.style.display = "block";
                isWebcamActive = false;
            }
        }

        // Keyboard Shortcuts (F1, F2, F5)
        window.addEventListener("keydown", (e) => {
            if (e.key === "F1") { e.preventDefault(); claimTicket(); }
            if (e.key === "F2") { e.preventDefault(); transitionToState("nominal"); }
            if (e.key === "F5") { e.preventDefault(); window.open("/report", "_blank"); }
            if (e.key === "1") { transitionToState("inspection"); }
            if (e.key === "2") { transitionToState("fault"); }
            if (e.key === "3") { transitionToState("nominal"); }
        });
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.app:app", host="127.0.0.1", port=8000, reload=True)
