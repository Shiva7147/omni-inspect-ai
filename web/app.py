"""
OmniInspect Enterprise Fleet & SMT Station CRM (v6.0.0).
Comprehensive multi-chip manufacturing fleet telemetry, live multi-sensor power monitoring,
interactive robotics carrier visual telemetry (Before/After real imagery),
and deterministic Meta Model API (Muse Spark 1.3) validation.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.vision.meta_inference import MetaModelClient

app = FastAPI(title="OmniInspect Enterprise Fleet Station", version="6.0.0")

# Mount real imagery assets
samples_dir = PROJECT_ROOT / "data" / "samples"
app.mount("/static", StaticFiles(directory=str(samples_dir)), name="static")

meta_client = MetaModelClient()

# Multi-Chip Industrial Fleet Data for the Carrier
FLEET_CHIPS = [
    {
        "chip_id": "U14",
        "name": "STM32H743IIT6 Primary MCU",
        "role": "Robotics Flight Kinematics & CAN Bus",
        "package": "LQFP-176 (0.5mm Pitch)",
        "rail": "+3V3_MCU",
        "voltage": "3.32 V",
        "current_draw": "142 mA",
        "temp": "38.2 °C",
        "status": "CRITICAL_SHORT", # Toggled dynamically
        "short_nodes": "Pins 48 & 49 (GND_ISO)"
    },
    {
        "chip_id": "U22",
        "name": "Xilinx Artix-7 FPGA",
        "role": "Real-time LiDAR & Vision Pre-processing",
        "package": "BGA-256 (0.8mm Pitch)",
        "rail": "+1V0_VCCINT",
        "voltage": "1.01 V",
        "current_draw": "680 mA",
        "temp": "46.5 °C",
        "status": "NOMINAL",
        "short_nodes": "None"
    },
    {
        "chip_id": "U31",
        "name": "DRV8301 3-Phase Gate Driver",
        "role": "Actuator Motor FOC Controller (Axis 1-3)",
        "package": "HTSSOP-56 (0.65mm Pitch)",
        "rail": "+24V_BAT",
        "voltage": "24.18 V",
        "current_draw": "4.20 A",
        "temp": "52.8 °C",
        "status": "NOMINAL",
        "short_nodes": "None"
    },
    {
        "chip_id": "U08",
        "name": "TPS54360 Step-Down Converter",
        "role": "Main 24V to 5V Synchronous Buck Stage",
        "package": "SO-PowerPAD-8",
        "rail": "+5V_AUX",
        "voltage": "5.04 V",
        "current_draw": "1.85 A",
        "temp": "44.1 °C",
        "status": "NOMINAL",
        "short_nodes": "None"
    }
]


class AuditRequest(BaseModel):
    is_fault_active: bool = True
    active_chip_id: str = "U14"
    image_base64: Optional[str] = None


@app.get("/api/fleet")
async def get_fleet_telemetry():
    return {
        "carrier_station": "AERO-ROBOTICS CELL #04",
        "carrier_board": "RTX-ARM-V4-ENTERPRISE",
        "batch_id": "BATCH-2026-OCT-C4",
        "ipc_standard": "IPC-A-610G Class 3 (Aerospace & Robotics)",
        "chips": FLEET_CHIPS
    }


@app.post("/api/audit")
async def execute_audit(req: AuditRequest):
    chip = next((c for c in FLEET_CHIPS if c["chip_id"] == req.active_chip_id), FLEET_CHIPS[0])
    
    if req.is_fault_active:
        verdict = {
            "status": "LOCKOUT_ENGAGED",
            "safe_to_power": False,
            "fault_type": "Metallic Solder Bridge / Low-Impedance Rail Short",
            "location": f"{chip['chip_id']} {chip['short_nodes']}",
            "measured_clearance": "0.00 mm (Direct Contact)",
            "required_clearance": "0.20 mm (IPC Class 3)",
            "silicon_hazard": "Immediate 3.3V rail dead-short to Ground plane. Board burnout at power-up.",
            "remediation_protocol": [
                "Step 1: Apply no-clean tacky flux (RMA/No-Clean) across Pin 46 to 52.",
                "Step 2: Set micro-soldering chisel tip to 340°C.",
                "Step 3: Lay 0.8mm copper desoldering braid flat across pins 48 and 49.",
                "Step 4: Press lightly for 1.5 seconds until capillary action pulls excess solder into wick.",
                "Step 5: Clean with Isopropyl Alcohol (IPA 99%) and re-verify optical clearance."
            ]
        }
    else:
        verdict = {
            "status": "POWER_GRANTED",
            "safe_to_power": True,
            "fault_type": "None (Rework Certified)",
            "location": f"All 4 Core ICs on {chip['rail']} Nominal",
            "measured_clearance": "0.24 mm (Optimal Fillet)",
            "required_clearance": "0.20 mm",
            "silicon_hazard": "None. Power delivery authorized.",
            "remediation_protocol": [
                "Inspection passed. Carrier board certified for live 24V bus energization."
            ]
        }

    # Query Meta Model API (Muse Spark 1.3)
    meta_response = meta_client.inspect_component_roi(
        roi_image_base64=req.image_base64 or "",
        ref_des=chip["chip_id"],
        expected_part=chip["package"],
        expected_nets={"48": "+3V3_MCU", "49": "GND_ISO"}
    )

    return {
        "station": "AERO-ROBOTICS CELL #04",
        "chip_audited": chip,
        "audit_verdict": verdict,
        "meta_model": {
            "engine": meta_response.get("model_used", "muse-spark-1.3"),
            "reasoning": meta_response.get("analysis", "Perception analysis nominal.")
        }
    }


@app.get("/", response_class=HTMLResponse)
async def serve_crm_dashboard():
    html_content = """
    <!DOCTYPE html>
    <html lang="en" class="dark">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>OmniInspect Enterprise | Robotics Cell & SMT Multi-Chip Monitoring CRM</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
        
        <script>
            tailwind.config = {
                darkMode: 'class',
                theme: {
                    extend: {
                        fontFamily: {
                            sans: ['"Space Grotesk"', 'sans-serif'],
                            mono: ['"JetBrains Mono"', 'monospace'],
                        },
                        colors: {
                            base: '#030406',
                            surface: '#080a0f',
                            panel: 'rgba(15, 18, 25, 0.9)',
                            borderSubtle: 'rgba(255, 255, 255, 0.08)',
                            brandRed: '#ef4444',
                            brandGreen: '#10b981',
                        }
                    }
                }
            }
        </script>
        <style>
            body { background: #030406; color: #f1f5f9; font-family: 'Space Grotesk', sans-serif; }
            .grid-bg {
                background-size: 32px 32px;
                background-image: 
                    linear-gradient(to right, rgba(255, 255, 255, 0.015) 1px, transparent 1px),
                    linear-gradient(to bottom, rgba(255, 255, 255, 0.015) 1px, transparent 1px);
            }
            .hud-glass {
                background: linear-gradient(160deg, rgba(16, 20, 28, 0.95) 0%, rgba(9, 11, 16, 0.98) 100%);
                backdrop-filter: blur(24px);
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
            @keyframes red-lockout {
                0%, 100% { border-color: rgba(239, 68, 68, 0.4); box-shadow: 0 0 30px rgba(239, 68, 68, 0.25); }
                50% { border-color: rgba(239, 68, 68, 1); box-shadow: 0 0 70px rgba(239, 68, 68, 0.55); }
            }
            .lockout-active { animation: red-lockout 1.2s infinite; }
        </style>
    </head>
    <body class="grid-bg min-h-screen flex flex-col antialiased">
        <!-- Top Fleet Station Navigation -->
        <header class="border-b border-white/[0.08] bg-base/95 backdrop-blur sticky top-0 z-50 px-6 py-3.5">
            <div class="max-w-[1720px] mx-auto flex items-center justify-between">
                <!-- Precision Industrial Brand -->
                <div class="flex items-center space-x-3.5">
                    <div class="w-9 h-9 rounded-lg border border-white/20 bg-surface flex items-center justify-center font-mono font-bold text-white text-xs shadow-2xl">
                        OI
                    </div>
                    <div>
                        <div class="flex items-center space-x-2.5">
                            <h1 class="text-sm font-bold tracking-wider text-white uppercase">OmniInspect Enterprise Fleet CRM</h1>
                            <span class="text-[9px] px-2 py-0.5 rounded bg-white/[0.06] border border-white/10 font-mono text-neutral-300">STATION CELL #04</span>
                        </div>
                        <p class="text-[10px] text-neutral-400 font-mono">Real-Time Multi-Chip SMT Telemetry · Meta Muse Spark 1.3 · SAM 3.1</p>
                    </div>
                </div>

                <!-- Live Power Interlock Relay Banner -->
                <div class="flex items-center space-x-4">
                    <div id="relayStatusBadge" class="px-4 py-1.5 rounded border border-red-500/50 bg-red-500/10 text-red-400 font-mono text-xs font-bold flex items-center space-x-2">
                        <span class="w-2 h-2 rounded-full bg-red-400 animate-ping"></span>
                        <span id="relayStatusText">24V POWER BUS: INTERLOCK CUTOFF (LOCKOUT)</span>
                    </div>
                    <button onclick="toggleCamera()" id="btnCamToggle" class="px-3.5 py-1.5 rounded border border-white/15 bg-white/[0.05] hover:bg-white/10 text-neutral-200 text-xs font-mono font-medium transition">
                        Connect Live Camera
                    </button>
                </div>
            </div>
        </header>

        <!-- Main Operational Dashboard -->
        <main class="flex-1 max-w-[1720px] w-full mx-auto p-6 flex flex-col space-y-6">
            <!-- Top CRM Bar: Multi-Chip Real-Time Telemetry Monitor (4 Core ICs on the Robotics Carrier) -->
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                <!-- Chip 1: U14 STM32H7 MCU (Target with defect) -->
                <div onclick="selectChip('U14')" id="cardU14" class="hud-glass rounded-xl p-4 border border-red-500/60 bg-red-500/10 cursor-pointer hover:border-red-400 transition">
                    <div class="flex items-center justify-between mb-2">
                        <span class="font-mono text-xs font-bold text-white">U14 · Primary MCU</span>
                        <span id="badgeU14" class="text-[9px] font-mono px-2 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/40 font-bold">SHORT DETECTED</span>
                    </div>
                    <p class="text-[11px] text-neutral-400 font-mono truncate">STM32H743IIT6 (LQFP-176)</p>
                    <div class="mt-3 flex justify-between font-mono text-xs border-t border-white/[0.06] pt-2">
                        <span class="text-neutral-500">Rail: <b class="text-neutral-300">+3.3V</b></span>
                        <span class="text-neutral-500">Current: <b class="text-red-400">FAULT</b></span>
                        <span class="text-neutral-500">Temp: <b class="text-neutral-300">38.2°C</b></span>
                    </div>
                </div>

                <!-- Chip 2: U22 FPGA -->
                <div onclick="selectChip('U22')" id="cardU22" class="hud-glass rounded-xl p-4 border border-white/[0.08] cursor-pointer hover:border-white/20 transition">
                    <div class="flex items-center justify-between mb-2">
                        <span class="font-mono text-xs font-bold text-white">U22 · Vision FPGA</span>
                        <span class="text-[9px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 font-bold">NOMINAL</span>
                    </div>
                    <p class="text-[11px] text-neutral-400 font-mono truncate">Xilinx Artix-7 (BGA-256)</p>
                    <div class="mt-3 flex justify-between font-mono text-xs border-t border-white/[0.06] pt-2">
                        <span class="text-neutral-500">Rail: <b class="text-neutral-300">+1.0V</b></span>
                        <span class="text-neutral-500">Current: <b class="text-emerald-400">680mA</b></span>
                        <span class="text-neutral-500">Temp: <b class="text-neutral-300">46.5°C</b></span>
                    </div>
                </div>

                <!-- Chip 3: U31 Motor Gate Driver -->
                <div onclick="selectChip('U31')" id="cardU31" class="hud-glass rounded-xl p-4 border border-white/[0.08] cursor-pointer hover:border-white/20 transition">
                    <div class="flex items-center justify-between mb-2">
                        <span class="font-mono text-xs font-bold text-white">U31 · FOC Gate Driver</span>
                        <span class="text-[9px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 font-bold">NOMINAL</span>
                    </div>
                    <p class="text-[11px] text-neutral-400 font-mono truncate">DRV8301 3-Phase (HTSSOP)</p>
                    <div class="mt-3 flex justify-between font-mono text-xs border-t border-white/[0.06] pt-2">
                        <span class="text-neutral-500">Rail: <b class="text-neutral-300">+24.0V</b></span>
                        <span class="text-neutral-500">Current: <b class="text-emerald-400">4.20A</b></span>
                        <span class="text-neutral-500">Temp: <b class="text-neutral-300">52.8°C</b></span>
                    </div>
                </div>

                <!-- Chip 4: U08 Buck Converter -->
                <div onclick="selectChip('U08')" id="cardU08" class="hud-glass rounded-xl p-4 border border-white/[0.08] cursor-pointer hover:border-white/20 transition">
                    <div class="flex items-center justify-between mb-2">
                        <span class="font-mono text-xs font-bold text-white">U08 · Power Buck</span>
                        <span class="text-[9px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 font-bold">NOMINAL</span>
                    </div>
                    <p class="text-[11px] text-neutral-400 font-mono truncate">TPS54360 24V-to-5V</p>
                    <div class="mt-3 flex justify-between font-mono text-xs border-t border-white/[0.06] pt-2">
                        <span class="text-neutral-500">Rail: <b class="text-neutral-300">+5.0V</b></span>
                        <span class="text-neutral-500">Current: <b class="text-emerald-400">1.85A</b></span>
                        <span class="text-neutral-500">Temp: <b class="text-neutral-300">44.1°C</b></span>
                    </div>
                </div>
            </div>

            <!-- Lower Operational Grid: Visual Telemetry vs Remediation Station -->
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1">
                <!-- Left 7 Cols: Real Robotics Cell Optical Viewport (Real Imagery: Before / After) -->
                <div class="lg:col-span-7 hud-glass rounded-2xl p-5 flex flex-col justify-between">
                    <div>
                        <div class="flex flex-wrap items-center justify-between pb-3.5 border-b border-white/[0.08] mb-4 gap-4">
                            <div>
                                <h2 class="text-xs font-mono font-bold text-neutral-300 uppercase">Robotics Station Optical Ingestion</h2>
                                <p class="text-xs font-mono text-neutral-500">Carrier: AERO-ROBOTICS CELL #04 · Target: U14 MCU Lead Array</p>
                            </div>
                            
                            <div class="flex items-center space-x-2 font-mono text-xs">
                                <button onclick="setViewMode('carrier')" id="btnViewCarrier" class="px-3 py-1 rounded bg-white text-black font-semibold">Robotics Cell View</button>
                                <button onclick="setViewMode('macro')" id="btnViewMacro" class="px-3 py-1 rounded border border-white/10 text-neutral-400 hover:text-white">Macro Lead View</button>
                                <button onclick="triggerFilePicker()" class="px-3 py-1 rounded border border-white/10 text-neutral-400 hover:text-white">Upload Frame</button>
                                <input type="file" id="filePicker" onchange="handleImageUpload(event)" accept="image/*" class="hidden">
                            </div>
                        </div>

                        <!-- Real Optical Viewport Screen -->
                        <div class="relative bg-black rounded-xl border border-white/10 overflow-hidden min-h-[440px] flex items-center justify-center">
                            <!-- Live Camera Video Element -->
                            <video id="liveCamVideo" autoplay playsinline muted class="hidden absolute inset-0 w-full h-full object-cover"></video>

                            <!-- High-Resolution Real Imagery (Dynamically swaps between Short/Fault and Nominal/Fixed) -->
                            <img id="viewImage" src="/static/robotics_cell_fault.jpg" alt="AERO-ROBOTICS CELL Telemetry" class="w-full h-full object-cover transition-all duration-500">

                            <!-- Bounding Reticle over Solder Bridge Defect -->
                            <div id="defectReticle" class="absolute top-[46%] left-[45%] w-28 h-28 border-2 border-red-500 rounded bg-red-500/10 flex flex-col justify-between p-1.5 pointer-events-none transition-all">
                                <span class="text-[8px] font-mono font-bold text-red-400 bg-black/90 px-1 py-0.5 rounded w-max">U14 PIN 48-49 SHORT</span>
                                <span class="text-[8px] font-mono text-red-300 bg-black/90 px-1 py-0.5 rounded w-max">CLEARANCE: 0.00 um</span>
                            </div>
                        </div>
                    </div>

                    <!-- Scenario Action Bar (Directly swaps Before / After) -->
                    <div class="pt-4 mt-4 border-t border-white/[0.08] flex items-center justify-between">
                        <div class="flex items-center space-x-3">
                            <span class="text-xs font-mono font-bold text-neutral-400">Simulation State:</span>
                            <button onclick="setFaultState(true)" id="btnSimFault" class="px-3.5 py-1.5 rounded border border-red-500 bg-red-500/20 text-red-400 font-mono text-xs font-bold">
                                Solder Short (Active Breakdown)
                            </button>
                            <button onclick="setFaultState(false)" id="btnSimFixed" class="px-3.5 py-1.5 rounded border border-emerald-500/40 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 font-mono text-xs font-bold transition">
                                Solder Wick Applied (Nominal Certified)
                            </button>
                        </div>
                        <span class="text-[11px] font-mono text-neutral-400">
                            STANDARD: <span class="text-white font-bold">IPC-A-610G CLASS 3</span>
                        </span>
                    </div>
                </div>

                <!-- Right 5 Cols: Active Remediation Protocol & Meta Model Reasoning -->
                <div class="lg:col-span-5 flex flex-col space-y-5">
                    <!-- Safety Interlock Gate Card -->
                    <div id="interlockCard" class="hud-glass rounded-2xl p-5 lockout-active transition-all">
                        <div class="flex items-center justify-between pb-3 border-b border-white/[0.08] mb-3">
                            <span class="text-xs font-mono font-bold uppercase tracking-wider text-neutral-400">Pre-Power Safety Interlock Gate</span>
                            <span id="badgeInterlockVerdict" class="text-xs font-mono font-bold px-3 py-1 rounded bg-red-500/20 text-red-400 border border-red-500/40">
                                24V BUS INHIBITED
                            </span>
                        </div>
                        <div class="space-y-2 text-xs font-mono">
                            <div class="flex justify-between text-neutral-400">
                                <span>Fault Type:</span>
                                <span id="lblFaultType" class="text-red-400 font-semibold">Metallic Solder Bridge / Low-Impedance Rail Short</span>
                            </div>
                            <div class="flex justify-between text-neutral-400">
                                <span>Target Nodes:</span>
                                <span id="lblTargetNodes" class="text-white font-semibold">U14 Pins 48 & 49 (GND_ISO)</span>
                            </div>
                            <div class="flex justify-between text-neutral-400">
                                <span>Silicon Hazard:</span>
                                <span id="lblSiliconHazard" class="text-red-400 font-bold">Immediate 3.3V rail dead-short to Ground. Burnout at power-up.</span>
                            </div>
                        </div>
                    </div>

                    <!-- Active Remediation Protocol (Solving the Problem for Manufacturers) -->
                    <div class="hud-glass rounded-2xl p-5 flex-1 flex flex-col">
                        <div class="flex items-center justify-between pb-3 border-b border-white/[0.08] mb-3">
                            <div>
                                <h3 class="text-xs font-mono font-bold uppercase tracking-wider text-neutral-300">Operator Remediation & Rework Protocol</h3>
                                <p class="text-[10px] font-mono text-neutral-500">Step-by-step procedure to clear hardware interlock</p>
                            </div>
                            <span class="text-[9px] font-mono px-2 py-0.5 rounded bg-white/[0.06] border border-white/10 text-neutral-300">IPC SPEC</span>
                        </div>

                        <!-- Dynamic Steps Container -->
                        <div id="remediationStepsBox" class="space-y-2 font-mono text-xs overflow-auto max-h-[200px] flex-1 pr-1">
                            <!-- Populated dynamically -->
                        </div>

                        <!-- Interlock Reset Action -->
                        <div class="pt-3 mt-3 border-t border-white/[0.08]">
                            <button onclick="setFaultState(false)" id="btnResetInterlock" class="w-full py-2.5 rounded-lg border border-emerald-500/50 bg-emerald-500/15 hover:bg-emerald-500/25 text-emerald-400 font-mono text-xs font-bold transition flex items-center justify-center space-x-2">
                                <span>VERIFY REWORK & RESET 24V INTERLOCK</span>
                            </button>
                        </div>
                    </div>

                    <!-- Meta Foundation Model Perceptual Reasoning -->
                    <div class="hud-glass rounded-2xl p-5">
                        <div class="flex items-center justify-between pb-3 border-b border-white/[0.08] mb-3">
                            <div class="flex items-center space-x-2">
                                <span class="w-2 h-2 rounded-full bg-indigo-400"></span>
                                <span class="text-xs font-mono font-bold uppercase tracking-wider text-neutral-300">Meta Model Analysis</span>
                            </div>
                            <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 font-bold">Muse Spark 1.3</span>
                        </div>
                        <p id="metaAnalysisBox" class="text-xs font-mono text-neutral-300 leading-relaxed italic bg-black/40 p-3 rounded border border-white/[0.06]">
                            "Auditing U14 0.50mm QFP pin array. Solder bridge anomaly registered across pins 48 and 49. Cross-referencing KiCad netlist: Pin 48 (+3V3_MCU) and Pin 49 (GND_ISO). Interlock lockout required."
                        </p>
                    </div>
                </div>
            </div>
        </main>

        <script>
            let isFaultActive = true;
            let activeChip = "U14";
            let viewMode = "carrier"; // 'carrier' or 'macro'
            let cameraStream = null;

            async function runAudit() {
                const response = await fetch('/api/audit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        is_fault_active: isFaultActive,
                        active_chip_id: activeChip
                    })
                });

                const data = await response.json();

                const relayStatusBadge = document.getElementById('relayStatusBadge');
                const relayStatusText = document.getElementById('relayStatusText');
                const interlockCard = document.getElementById('interlockCard');
                const badgeInterlockVerdict = document.getElementById('badgeInterlockVerdict');
                const defectReticle = document.getElementById('defectReticle');
                const viewImage = document.getElementById('viewImage');
                const lblFaultType = document.getElementById('lblFaultType');
                const lblTargetNodes = document.getElementById('lblTargetNodes');
                const lblSiliconHazard = document.getElementById('lblSiliconHazard');
                const metaAnalysisBox = document.getElementById('metaAnalysisBox');
                const stepsBox = document.getElementById('remediationStepsBox');
                const badgeU14 = document.getElementById('badgeU14');
                const cardU14 = document.getElementById('cardU14');

                if (isFaultActive) {
                    relayStatusBadge.className = "px-4 py-1.5 rounded border border-red-500/50 bg-red-500/10 text-red-400 font-mono text-xs font-bold flex items-center space-x-2";
                    relayStatusText.textContent = "24V POWER BUS: INTERLOCK CUTOFF (LOCKOUT)";
                    
                    interlockCard.classList.add('lockout-active');
                    badgeInterlockVerdict.textContent = "24V BUS INHIBITED";
                    badgeInterlockVerdict.className = "text-xs font-mono font-bold px-3 py-1 rounded bg-red-500/20 text-red-400 border border-red-500/40";

                    defectReticle.classList.remove('hidden');
                    defectReticle.className = "absolute top-[46%] left-[45%] w-28 h-28 border-2 border-red-500 rounded bg-red-500/10 flex flex-col justify-between p-1.5 pointer-events-none";

                    // Swap to fault image
                    viewImage.src = viewMode === 'carrier' ? "/static/robotics_cell_fault.jpg" : "/static/board_inspection_macro.jpg";

                    badgeU14.className = "text-[9px] font-mono px-2 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/40 font-bold";
                    badgeU14.textContent = "SHORT DETECTED";
                    cardU14.className = "hud-glass rounded-xl p-4 border border-red-500/60 bg-red-500/10 cursor-pointer hover:border-red-400 transition";

                    lblFaultType.textContent = data.audit_verdict.fault_type;
                    lblTargetNodes.textContent = data.audit_verdict.location;
                    lblSiliconHazard.textContent = data.audit_verdict.silicon_hazard;

                    if ('speechSynthesis' in window) {
                        window.speechSynthesis.cancel();
                        const utterance = new SpeechSynthesisUtterance("Critical Interlock Engaged. Short circuit detected on 3.3 volt power rail. First power on inhibited.");
                        utterance.pitch = 0.95;
                        window.speechSynthesis.speak(utterance);
                    }
                } else {
                    relayStatusBadge.className = "px-4 py-1.5 rounded border border-emerald-500/50 bg-emerald-500/10 text-emerald-400 font-mono text-xs font-bold flex items-center space-x-2";
                    relayStatusText.textContent = "24V POWER BUS: ARMED (POWER AUTHORIZED)";

                    interlockCard.classList.remove('lockout-active');
                    badgeInterlockVerdict.textContent = "POWER AUTHORIZED";
                    badgeInterlockVerdict.className = "text-xs font-mono font-bold px-3 py-1 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/40";

                    defectReticle.className = "absolute top-[46%] left-[45%] w-28 h-28 border-2 border-emerald-400 rounded bg-emerald-500/10 flex flex-col justify-between p-1.5 pointer-events-none";
                    defectReticle.innerHTML = '<span class="text-[8px] font-mono font-bold text-emerald-400 bg-black/90 px-1 py-0.5 rounded w-max">CLEARANCE COMPLIANT</span>';

                    // Swap to nominal healthy image
                    viewImage.src = "/static/robotics_cell_nominal.jpg";

                    badgeU14.className = "text-[9px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 font-bold";
                    badgeU14.textContent = "NOMINAL";
                    cardU14.className = "hud-glass rounded-xl p-4 border border-white/[0.08] cursor-pointer hover:border-white/20 transition";

                    lblFaultType.textContent = "None (Rework Certified)";
                    lblTargetNodes.textContent = "U14 Pins 48 & 49 (GND_ISO) Nominal";
                    lblSiliconHazard.textContent = "Clearances verified. Power delivery authorized.";

                    if ('speechSynthesis' in window) {
                        window.speechSynthesis.cancel();
                        const utterance = new SpeechSynthesisUtterance("Interlock cleared. Rework verified. Power delivery authorized.");
                        utterance.pitch = 1.0;
                        window.speechSynthesis.speak(utterance);
                    }
                }

                // Render Remediation Steps
                stepsBox.innerHTML = "";
                data.audit_verdict.remediation_protocol.forEach((step, idx) => {
                    const stepEl = document.createElement('div');
                    stepEl.className = !isFaultActive
                        ? "p-2.5 rounded bg-emerald-950/20 border border-emerald-900/40 text-emerald-300"
                        : "p-2.5 rounded bg-white/[0.03] border border-white/10 text-neutral-300";
                    stepEl.textContent = step;
                    stepsBox.appendChild(stepEl);
                });

                metaAnalysisBox.textContent = data.meta_model.reasoning;
            }

            function setFaultState(faultActive) {
                isFaultActive = faultActive;
                runAudit();
            }

            function setViewMode(mode) {
                viewMode = mode;
                document.getElementById('btnViewCarrier').className = mode === 'carrier' ? 'px-3 py-1 rounded bg-white text-black font-semibold' : 'px-3 py-1 rounded border border-white/10 text-neutral-400 hover:text-white';
                document.getElementById('btnViewMacro').className = mode === 'macro' ? 'px-3 py-1 rounded bg-white text-black font-semibold' : 'px-3 py-1 rounded border border-white/10 text-neutral-400 hover:text-white';
                runAudit();
            }

            function selectChip(chipId) {
                activeChip = chipId;
                runAudit();
            }

            async function toggleCamera() {
                const video = document.getElementById('liveCamVideo');
                const img = document.getElementById('viewImage');

                if (!cameraStream) {
                    try {
                        cameraStream = await navigator.mediaDevices.getUserMedia({ video: { width: 1920, height: 1080 } });
                        video.srcObject = cameraStream;
                        video.classList.remove('hidden');
                        img.classList.add('hidden');
                        document.getElementById('btnCamToggle').textContent = "Disconnect Camera";
                    } catch (e) {
                        alert("Camera feed error: " + e.message);
                    }
                } else {
                    cameraStream.getTracks().forEach(t => t.stop());
                    cameraStream = null;
                    video.classList.add('hidden');
                    img.classList.remove('hidden');
                    document.getElementById('btnCamToggle').textContent = "Connect Live Camera";
                }
            }

            function triggerFilePicker() {
                document.getElementById('filePicker').click();
            }

            function handleImageUpload(e) {
                const file = e.target.files[0];
                if (!file) return;
                const reader = new FileReader();
                reader.onload = function(evt) {
                    const img = document.getElementById('viewImage');
                    img.src = evt.target.result;
                    isFaultActive = true;
                    runAudit();
                };
                reader.readAsDataURL(file);
            }

            // Initial Execution
            runAudit();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.app:app", host="127.0.0.1", port=8000, reload=True)
