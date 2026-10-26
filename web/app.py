"""
OmniInspect Interactive Defect Workbench & Pre-Power Verification Server.
FastAPI backend powering the live web client, webcam stream, synthetic defect injector,
and Meta Foundation Model inference pipeline (Muse Spark Open / Muse Glimmer).
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import json

from engine.cad.parser import NetlistGraph, create_sample_arduino_netlist
from engine.vision.meta_inference import MetaModelClient, MetaInferenceConfig
from engine.tools.fastmcp_gate import FastMCPVerificationTools

app = FastAPI(title="OmniInspect Pre-Power Safety Interlock", version="1.0.0")

# Initialize global engine states
netlist_graph = create_sample_arduino_netlist()
fastmcp_tools = FastMCPVerificationTools(netlist_graph)
meta_client = MetaModelClient()


class DefectSimulationRequest(BaseModel):
    ref_des: str = "U1"
    pad_a: str = "U1_PIN3"  # GND
    pad_b: str = "U1_PIN4"  # VCC
    inject_solder_bridge: bool = True
    observed_polarity_angle: float = 0.0


@app.get("/api/netlist", response_model=Dict[str, Any])
async def get_netlist():
    """Returns the deterministic reference CAD netlist graph."""
    return {
        "board_name": netlist_graph.board_name,
        "board_dimensions_mm": netlist_graph.board_dimensions_mm,
        "components": {k: v.model_dump() for k, v in netlist_graph.components.items()},
        "pads": {k: v.model_dump() for k, v in netlist_graph.pads.items()}
    }


@app.post("/api/verify_assembly")
async def verify_assembly(req: DefectSimulationRequest):
    """
    Core verification loop:
    1. Meta model evaluates perception.
    2. FastMCP tools verify deterministic electrical DRC & clearances.
    3. Safety interlock activates if a fatal condition is detected.
    """
    # 1. Run deterministic clearance check via FastMCP
    clearance_result = fastmcp_tools.execute_tool("check_pin_clearance", {
        "pad_a_id": req.pad_a,
        "pad_b_id": req.pad_b,
        "visual_bridge_detected": req.inject_solder_bridge
    })

    # 2. Check polarity alignment if component is polarized
    polarity_result = fastmcp_tools.execute_tool("verify_polarity_alignment", {
        "ref_des": req.ref_des,
        "observed_pin1_angle_deg": req.observed_polarity_angle
    })

    # 3. Interlock Logic
    is_fatal = clearance_result.get("is_power_to_ground", False) or not polarity_result.get("safe", True)
    
    interlock_state = {}
    if is_fatal:
        interlock_state = fastmcp_tools.execute_tool("trigger_pre_power_interlock", {
            "hazard_type": "VCC_GND_SHORT" if clearance_result.get("is_power_to_ground") else "REVERSED_POLARITY",
            "component_involved": f"{req.ref_des} ({req.pad_a} <-> {req.pad_b})",
            "avionics_voice_alert": f"CRITICAL HAZARD: Direct short between {req.pad_a} and {req.pad_b} on rail {clearance_result.get('net_b')}. Power-on inhibited."
        })

    # 4. Meta Inference Output
    meta_response = meta_client.inspect_component_roi(
        roi_image_base64="",
        ref_des=req.ref_des,
        expected_part=netlist_graph.components[req.ref_des].package,
        expected_nets={p.pin_number: p.net_name for p in netlist_graph.pads.values() if p.component == req.ref_des},
        tools_schema=fastmcp_tools.get_tool_definitions()
    )

    return {
        "status": "DETERMINISTIC_VERIFIED",
        "power_permitted": not is_fatal,
        "clearance_check": clearance_result,
        "polarity_check": polarity_result,
        "safety_interlock": interlock_state,
        "meta_model_reasoning": meta_response
    }


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Returns the Interactive Cyber-Physical Workbench Dashboard for judges."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>OmniInspect | Pre-Power Optical Safety Interlock</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            @keyframes pulse-red {
                0%, 100% { background-color: rgba(239, 68, 68, 0.2); border-color: rgba(239, 68, 68, 0.8); }
                50% { background-color: rgba(239, 68, 68, 0.4); border-color: rgba(239, 68, 68, 1); }
            }
            .interlock-alert { animation: pulse-red 1.2s infinite; }
        </style>
    </head>
    <body class="bg-slate-950 text-slate-100 min-h-screen font-mono">
        <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur px-6 py-4 flex items-center justify-between sticky top-0 z-50">
            <div class="flex items-center space-x-3">
                <div class="h-3.5 w-3.5 rounded-full bg-emerald-500 animate-ping"></div>
                <h1 class="text-xl font-bold tracking-wider text-white">OMNI<span class="text-indigo-400">INSPECT</span></h1>
                <span class="text-xs px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">Meta Model API · Muse Spark Open · SAM 3.1</span>
            </div>
            <div class="flex items-center space-x-4 text-xs">
                <div id="relayStatus" class="px-3 py-1 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 font-semibold">
                    RELAY: ARMED (NOMINAL)
                </div>
            </div>
        </header>

        <main class="max-w-7xl mx-auto p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
            <!-- Left Panel: CAD Board & Optical Canvas -->
            <div class="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-2xl flex flex-col">
                <div class="flex justify-between items-center mb-4">
                    <h2 class="text-sm font-semibold tracking-wide text-slate-300">CAD HOMOGRAPHY TELEMETRY VIEW</h2>
                    <span class="text-xs text-slate-400">Target: Arduino Uno R3 (ATMega328P)</span>
                </div>
                
                <div class="relative bg-slate-950 border border-slate-800 rounded-lg overflow-hidden flex-1 min-h-[380px] flex items-center justify-center p-4">
                    <!-- Circuit Board Visualization Canvas -->
                    <div id="boardCanvas" class="relative w-full max-w-[480px] h-[320px] bg-emerald-950/40 border-2 border-emerald-600/60 rounded-lg p-4">
                        <div class="text-[10px] text-emerald-500 font-bold tracking-widest uppercase">PCB SUBSTRATE · 68.6 x 53.4 mm</div>
                        
                        <!-- ATMega328P QFP-32 Chip Representation -->
                        <div class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-44 h-44 bg-slate-900 border-2 border-slate-700 rounded-sm shadow-inner flex flex-col items-center justify-center">
                            <div class="absolute top-1 left-1 w-2.5 h-2.5 bg-slate-600 rounded-full" title="Pin 1 Index Notch"></div>
                            <span class="text-xs font-bold text-slate-200">ATmega328P-AU</span>
                            <span class="text-[9px] text-slate-500">TQFP-32 · P0.8mm</span>
                            
                            <!-- Pins Overlay -->
                            <div class="absolute -left-3 top-6 flex flex-col space-y-2">
                                <div id="pin3" class="w-3 h-2 bg-amber-400 rounded-l text-[7px] text-black font-bold pl-0.5">P3</div>
                                <div id="pin4" class="w-3 h-2 bg-amber-400 rounded-l text-[7px] text-black font-bold pl-0.5">P4</div>
                            </div>

                            <!-- Dynamic Solder Bridge Marker -->
                            <div id="bridgeMarker" class="hidden absolute -left-4 top-7 w-5 h-5 border-2 border-red-500 rounded-full animate-ping"></div>
                        </div>

                        <!-- C4 Decoupling Cap -->
                        <div class="absolute left-16 top-16 w-8 h-4 bg-amber-800/80 border border-amber-600 rounded-xs flex items-center justify-center">
                            <span class="text-[8px] text-amber-200">C4</span>
                        </div>
                    </div>
                </div>

                <!-- Simulation Controls -->
                <div class="mt-4 pt-4 border-t border-slate-800 grid grid-cols-2 gap-4">
                    <button onclick="runVerification(true)" class="py-2.5 px-4 rounded-lg bg-red-600/80 hover:bg-red-600 text-white font-semibold text-xs tracking-wide transition shadow-lg shadow-red-950">
                        ⚡ INJECT SOLDER BRIDGE (P3 & P4)
                    </button>
                    <button onclick="runVerification(false)" class="py-2.5 px-4 rounded-lg bg-emerald-600/80 hover:bg-emerald-600 text-white font-semibold text-xs tracking-wide transition shadow-lg shadow-emerald-950">
                        🛡️ RESET TO NOMINAL STATE
                    </button>
                </div>
            </div>

            <!-- Right Panel: Neuro-Symbolic Safety Gate & LLM Output -->
            <div class="lg:col-span-5 flex flex-col space-y-6">
                <!-- Safety Interlock Gate Card -->
                <div id="interlockCard" class="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-2xl">
                    <div class="flex items-center justify-between mb-3">
                        <h3 class="text-sm font-semibold text-slate-200">PRE-POWER SAFETY INTERLOCK</h3>
                        <span id="gateBadge" class="text-xs px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800">
                            POWER GRANTED
                        </span>
                    </div>
                    <div id="gateMessage" class="text-xs text-slate-400 leading-relaxed">
                        Deterministic geometric clearance check nominal. No solder bridging detected between VCC (+5V) rail and GND.
                    </div>
                </div>

                <!-- FastMCP Tool Execution Trace -->
                <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-2xl flex-1 flex flex-col">
                    <div class="flex items-center justify-between mb-3">
                        <h3 class="text-sm font-semibold text-slate-200">FASTMCP ZERO-ARITHMETIC TRACE</h3>
                        <span class="text-[10px] text-slate-400">IPC-A-610G Class 3</span>
                    </div>
                    <div class="bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs flex-1 overflow-auto max-h-[220px]">
                        <pre id="jsonTrace" class="text-emerald-400">// Awaiting telemetry stream...</pre>
                    </div>
                </div>

                <!-- Meta Foundation Model Reasoning -->
                <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-2xl">
                    <div class="flex items-center space-x-2 mb-2">
                        <div class="w-2 h-2 rounded-full bg-indigo-400"></div>
                        <h3 class="text-sm font-semibold text-slate-200">META MUSE SPARK OPEN REASONING</h3>
                    </div>
                    <p id="metaReasoning" class="text-xs text-slate-400 leading-relaxed italic">
                        "Pre-power audit initialized. Standing by for optical crop ingestion."
                    </p>
                </div>
            </div>
        </main>

        <script>
            async function runVerification(injectBridge) {
                const response = await fetch('/api/verify_assembly', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        ref_des: 'U1',
                        pad_a: 'U1_PIN3',
                        pad_b: 'U1_PIN4',
                        inject_solder_bridge: injectBridge,
                        observed_polarity_angle: 0.0
                    })
                });

                const data = await response.json();
                document.getElementById('jsonTrace').textContent = JSON.stringify(data, null, 2);

                const relayStatus = document.getElementById('relayStatus');
                const gateBadge = document.getElementById('gateBadge');
                const gateMessage = document.getElementById('gateMessage');
                const bridgeMarker = document.getElementById('bridgeMarker');
                const interlockCard = document.getElementById('interlockCard');
                const metaReasoning = document.getElementById('metaReasoning');

                if (!data.power_permitted) {
                    relayStatus.textContent = "RELAY: INTERLOCK ENGAGED (CUTOFF)";
                    relayStatus.className = "px-3 py-1 rounded-full bg-red-950 text-red-400 border border-red-800 font-bold";
                    
                    gateBadge.textContent = "CRITICAL LOCKOUT";
                    gateBadge.className = "text-xs px-2.5 py-0.5 rounded-full bg-red-950 text-red-400 border border-red-800";
                    
                    gateMessage.textContent = data.safety_interlock.avionics_voice_alert;
                    bridgeMarker.classList.remove('hidden');
                    interlockCard.classList.add('interlock-alert');

                    // Audio Alert synthesis
                    if ('speechSynthesis' in window) {
                        const utterance = new SpeechSynthesisUtterance("Warning: Critical short circuit between VCC rail and Ground. Power-on inhibited.");
                        utterance.pitch = 0.9;
                        utterance.rate = 1.05;
                        window.speechSynthesis.speak(utterance);
                    }
                } else {
                    relayStatus.textContent = "RELAY: ARMED (NOMINAL)";
                    relayStatus.className = "px-3 py-1 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800 font-semibold";
                    
                    gateBadge.textContent = "POWER GRANTED";
                    gateBadge.className = "text-xs px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800";
                    
                    gateMessage.textContent = "Deterministic clearance check nominal. No solder bridging detected between VCC (+5V) rail and GND.";
                    bridgeMarker.classList.add('hidden');
                    interlockCard.classList.remove('interlock-alert');
                }

                metaReasoning.textContent = data.meta_model_reasoning.analysis;
            }

            // Initial Nominal Check
            runVerification(false);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.app:app", host="0.0.0.0", port=8000, reload=True)
