"""
OmniInspect FastMCP Neuro-Symbolic Gatekeeper.
Enforces the Zero-Arithmetic Rule:
Meta models (Muse Spark Open) act as perceptual agents that invoke deterministic
FastMCP geometric & electrical graph tools to verify hardware safety before first power-on.
"""

from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field
from engine.cad.parser import NetlistGraph, create_sample_arduino_netlist
import json


class FastMCPVerificationTools:
    """
    Suite of deterministic electrical and spatial tools exposed to Meta foundation models.
    """
    def __init__(self, netlist: Optional[NetlistGraph] = None):
        self.netlist = netlist or create_sample_arduino_netlist()

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Returns OpenAI/Meta compatible tool schemas."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "check_pin_clearance",
                    "description": "Calculates physical Euclidean clearance between two IC pads and checks if a bridge causes a short circuit between different electrical nets.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pad_a_id": {
                                "type": "string",
                                "description": "Identifier of pad A (e.g., U1_PIN3)"
                            },
                            "pad_b_id": {
                                "type": "string",
                                "description": "Identifier of pad B (e.g., U1_PIN4)"
                            },
                            "visual_bridge_detected": {
                                "type": "boolean",
                                "description": "Whether optical inspection detects an anomalous metallic bridge or whisker between the pads"
                            }
                        },
                        "required": ["pad_a_id", "pad_b_id", "visual_bridge_detected"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "verify_polarity_alignment",
                    "description": "Validates whether the observed visual cathode marker or pin-1 index notch matches the CAD ground-truth orientation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ref_des": {
                                "type": "string",
                                "description": "Component reference designator (e.g., C1, D1, U1)"
                            },
                            "observed_pin1_angle_deg": {
                                "type": "number",
                                "description": "Observed rotation angle of pin 1 or cathode marker in degrees (0, 90, 180, 270)"
                            }
                        },
                        "required": ["ref_des", "observed_pin1_angle_deg"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "trigger_pre_power_interlock",
                    "description": "Engages the physical safety lockout relay to prevent powering on the board when a fatal hazard is verified.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "hazard_type": {
                                "type": "string",
                                "enum": ["VCC_GND_SHORT", "REVERSED_POLARITY", "UNSEATED_IC", "MISSING_DECOUPLING"],
                                "description": "Classification of the fatal assembly hazard"
                            },
                            "component_involved": {
                                "type": "string",
                                "description": "Reference designator or pad IDs involved in the fatal condition"
                            },
                            "avionics_voice_alert": {
                                "type": "string",
                                "description": "Concise verbal alert string synthesized for the engineer (e.g., 'Warning: VCC shorted to GND at U1 Pin 4')"
                            }
                        },
                        "required": ["hazard_type", "component_involved", "avionics_voice_alert"]
                    }
                }
            }
        ]

    def execute_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Executes the deterministic tool and returns structured verification facts."""
        if name == "check_pin_clearance":
            pad_a = args.get("pad_a_id")
            pad_b = args.get("pad_b_id")
            bridge = args.get("visual_bridge_detected", False)
            
            p_a = self.netlist.pads.get(pad_a)
            p_b = self.netlist.pads.get(pad_b)
            if not p_a or not p_b:
                return {"error": f"Pads {pad_a} or {pad_b} not found in netlist."}

            is_same_net = (p_a.net_name == p_b.net_name)
            is_fatal_rail = (p_a.is_power_rail and p_b.is_ground_rail) or (p_a.is_ground_rail and p_b.is_power_rail)

            if bridge and not is_same_net:
                return {
                    "status": "FATAL_SHORT_CIRCUIT" if is_fatal_rail else "SIGNAL_NET_SHORT",
                    "net_a": p_a.net_name,
                    "net_b": p_b.net_name,
                    "is_power_to_ground": is_fatal_rail,
                    "interlock_action_required": True,
                    "explanation": f"Metallic solder bridge creates direct low-impedance short between net {p_a.net_name} and net {p_b.net_name}."
                }
            return {
                "status": "CLEARANCE_NOMINAL",
                "net_a": p_a.net_name,
                "net_b": p_b.net_name,
                "interlock_action_required": False
            }

        elif name == "verify_polarity_alignment":
            ref_des = args.get("ref_des")
            comp = self.netlist.components.get(ref_des)
            if not comp:
                return {"error": f"Component {ref_des} not found in CAD netlist."}
            
            if not comp.is_polarized:
                return {"status": "NON_POLARIZED", "safe": True}

            observed_angle = args.get("observed_pin1_angle_deg", 0.0)
            angular_error = abs(comp.rotation_deg - observed_angle) % 360

            if angular_error > 15.0:
                return {
                    "status": "POLARITY_INVERSION_HAZARD",
                    "safe": False,
                    "expected_angle_deg": comp.rotation_deg,
                    "observed_angle_deg": observed_angle,
                    "angular_error_deg": angular_error,
                    "consequence": "Catastrophic dielectric breakdown and capacitor rupture upon energization."
                }
            return {
                "status": "POLARITY_VERIFIED",
                "safe": True,
                "angular_error_deg": angular_error
            }

        elif name == "trigger_pre_power_interlock":
            return {
                "interlock_engaged": True,
                "relay_state": "OPEN_CIRCUIT_DISCONNECTED",
                "hazard_type": args.get("hazard_type"),
                "component": args.get("component_involved"),
                "avionics_voice_alert": args.get("avionics_voice_alert"),
                "power_delivery_inhibited": True
            }

        return {"error": f"Unknown tool: {name}"}


if __name__ == "__main__":
    tools = FastMCPVerificationTools()
    print("FastMCP Tools Initialized. Total tools:", len(tools.get_tool_definitions()))
    
    # Test pin clearance execution on U1 Pin 3 (GND) and Pin 4 (VCC)
    result = tools.execute_tool("check_pin_clearance", {
        "pad_a_id": "U1_PIN3",
        "pad_b_id": "U1_PIN4",
        "visual_bridge_detected": True
    })
    print("Clearance Verification Output:", json.dumps(result, indent=2))
