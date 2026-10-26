"""
OmniInspect CLI: Run Meta Foundation Models directly from your terminal.
Supports Meta Model API, Baseten, and Modal inference for Muse Spark Open and Muse Glimmer.
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.cad.parser import create_sample_arduino_netlist
from engine.vision.meta_inference import MetaModelClient, MetaInferenceConfig
from engine.tools.fastmcp_gate import FastMCPVerificationTools
import json


def run_terminal_muse_audit(ref_des: str = "U1", bridge_pins: bool = True):
    print("=" * 70)
    print("  OMNIINSPECT: META FOUNDATION MODEL TERMINAL AUDITOR")
    print("=" * 70)

    # 1. Initialize Netlist & FastMCP Gate
    netlist = create_sample_arduino_netlist()
    fastmcp = FastMCPVerificationTools(netlist)
    client = MetaModelClient()

    print(f"\n[1] Target Component: {ref_des}")
    comp = netlist.components.get(ref_des)
    if not comp:
        print(f"Error: {ref_des} not found in netlist.")
        return

    print(f"    Package: {comp.package} | Value: {comp.value}")
    print(f"    Board Dimensions: {netlist.board_dimensions_mm} mm")
    print(f"    Inference Provider: {client.config.provider.upper()}")
    print(f"    Model ID: {client.config.model_name}")

    # 2. Check Pin Clearance via FastMCP Tool
    pad_a = "U1_PIN3"  # GND
    pad_b = "U1_PIN4"  # VCC (+5V)
    print(f"\n[2] Executing FastMCP Deterministic Tool...")
    print(f"    Checking pads {pad_a} <-> {pad_b} (Visual Bridge = {bridge_pins})")
    
    tool_output = fastmcp.execute_tool("check_pin_clearance", {
        "pad_a_id": pad_a,
        "pad_b_id": pad_b,
        "visual_bridge_detected": bridge_pins
    })
    print("    FastMCP Output:", json.dumps(tool_output, indent=4))

    # 3. Trigger Safety Interlock if Fatal
    if tool_output.get("is_power_to_ground"):
        interlock = fastmcp.execute_tool("trigger_pre_power_interlock", {
            "hazard_type": "VCC_GND_SHORT",
            "component_involved": f"{ref_des} ({pad_a}-{pad_b})",
            "avionics_voice_alert": f"CRITICAL: Direct short between {pad_a} and {pad_b}. Power cutoff engaged."
        })
        print(f"\n[3] [ALERT] PRE-POWER SAFETY INTERLOCK TRIPPED:")
        print(f"    Relay State: {interlock['relay_state']}")
        print(f"    Voice Warning: '{interlock['avionics_voice_alert']}'")

    # 4. Query Meta Foundation Model
    print(f"\n[4] Querying Meta Model ({client.config.model_name})...")
    expected_nets = {p.pin_number: p.net_name for p in netlist.pads.values() if p.component == ref_des}
    response = client.inspect_component_roi(
        roi_image_base64="",
        ref_des=ref_des,
        expected_part=comp.package,
        expected_nets=expected_nets,
        tools_schema=fastmcp.get_tool_definitions()
    )
    print("    Model Status:", response.get("status"))
    print("    Model Reasoning:")
    print("   ", response.get("analysis"))
    print("\n" + "=" * 70)


if __name__ == "__main__":
    ref = sys.argv[1] if len(sys.argv) > 1 else "U1"
    run_terminal_muse_audit(ref_des=ref, bridge_pins=True)
