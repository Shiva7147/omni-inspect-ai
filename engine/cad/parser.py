"""
OmniInspect CAD Parser & Netlist Graph Engine.
Converts physical KiCad PCB layouts (.kicad_pcb) and IPC-D-356 netlists
into a deterministic mathematical graph: G_spec = (V_pads, E_nets).
"""

from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel, Field
import json
import re


class PadNode(BaseModel):
    id: str = Field(..., description="Unique pin ID, e.g., U1_PIN1")
    component: str = Field(..., description="Reference designator, e.g., U1, C4, R12")
    pin_number: str = Field(..., description="Pin number or pad label, e.g., 1, 2, A1")
    net_name: str = Field(..., description="Electrical net name, e.g., +3V3, GND, SPI_MOSI")
    x_mm: float = Field(..., description="Center X coordinate in board millimeters")
    y_mm: float = Field(..., description="Center Y coordinate in board millimeters")
    width_mm: float = Field(default=0.8, description="Pad width in millimeters")
    height_mm: float = Field(default=0.8, description="Pad height in millimeters")
    is_power_rail: bool = Field(default=False)
    is_ground_rail: bool = Field(default=False)


class ComponentMetadata(BaseModel):
    ref_des: str
    package: str
    value: Optional[str] = None
    center_mm: Tuple[float, float]
    rotation_deg: float = 0.0
    pin_count: int = 2
    is_polarized: bool = False
    pin1_location_mm: Optional[Tuple[float, float]] = None


class NetlistGraph(BaseModel):
    board_name: str
    board_dimensions_mm: Tuple[float, float]
    pads: Dict[str, PadNode] = {}
    components: Dict[str, ComponentMetadata] = {}
    nets: Dict[str, List[str]] = {}  # net_name -> list of PadNode IDs
    critical_nets: List[str] = ["+5V", "+3V3", "+12V", "VCC", "GND"]

    def add_pad(self, pad: PadNode):
        self.pads[pad.id] = pad
        if pad.net_name not in self.nets:
            self.nets[pad.net_name] = []
        self.nets[pad.net_name].append(pad.id)

    def get_components_in_roi(self, x_min: float, y_min: float, x_max: float, y_max: float) -> List[ComponentMetadata]:
        """Returns all components falling within a metric bounding box."""
        results = []
        for c in self.components.values():
            cx, cy = c.center_mm
            if x_min <= cx <= x_max and y_min <= cy <= y_max:
                results.append(c)
        return results

    def check_clearance_violation(self, pad_id_a: str, pad_id_b: str, min_clearance_mm: float = 0.15) -> Optional[Dict]:
        """
        Deterministic clearance checker.
        If two pads belonging to different electrical nets have a physical gap < min_clearance_mm,
        flags a high-risk DRC clearance or solder-bridge hazard.
        """
        p_a = self.pads.get(pad_id_a)
        p_b = self.pads.get(pad_id_b)
        if not p_a or not p_b:
            return None

        # Same net -> intentional connection
        if p_a.net_name == p_b.net_name:
            return None

        # Compute Euclidean distance between pad centers
        dist_centers = ((p_a.x_mm - p_b.x_mm) ** 2 + (p_a.y_mm - p_b.y_mm) ** 2) ** 0.5
        edge_gap = dist_centers - (p_a.width_mm / 2.0 + p_b.width_mm / 2.0)

        if edge_gap < min_clearance_mm:
            is_fatal = (p_a.is_power_rail and p_b.is_ground_rail) or (p_a.is_ground_rail and p_b.is_power_rail)
            return {
                "pad_a": p_a.id,
                "pad_b": p_b.id,
                "net_a": p_a.net_name,
                "net_b": p_b.net_name,
                "measured_clearance_mm": round(edge_gap, 4),
                "required_clearance_mm": min_clearance_mm,
                "is_fatal_short": is_fatal,
                "hazard_level": "CRITICAL_FATAL" if is_fatal else "WARNING_DRC"
            }
        return None


def create_sample_arduino_netlist() -> NetlistGraph:
    """
    Creates an industrial-grade deterministic reference netlist for an Arduino Uno / ATMega328P circuit.
    Used for instant benchmarking and zero-hardware testing.
    """
    graph = NetlistGraph(board_name="Arduino_Uno_R3_Reference", board_dimensions_mm=(68.6, 53.4))

    # Power decoupling capacitor C4 (100nF between +5V and GND)
    graph.components["C4"] = ComponentMetadata(
        ref_des="C4",
        package="0805",
        value="100nF",
        center_mm=(24.5, 18.2),
        pin_count=2,
        is_polarized=False
    )
    graph.add_pad(PadNode(
        id="C4_PIN1", component="C4", pin_number="1", net_name="+5V",
        x_mm=23.8, y_mm=18.2, is_power_rail=True
    ))
    graph.add_pad(PadNode(
        id="C4_PIN2", component="C4", pin_number="2", net_name="GND",
        x_mm=25.2, y_mm=18.2, is_ground_rail=True
    ))

    # Polarized Electrolytic/Tantalum Capacitor C1 (47uF on 5V rail)
    graph.components["C1"] = ComponentMetadata(
        ref_des="C1",
        package="Radial_Can_D6.3mm",
        value="47uF_25V",
        center_mm=(14.2, 38.0),
        pin_count=2,
        is_polarized=True,
        pin1_location_mm=(13.0, 38.0) # Anode (+)
    )
    graph.add_pad(PadNode(
        id="C1_PIN1", component="C1", pin_number="1", net_name="+5V",
        x_mm=13.0, y_mm=38.0, is_power_rail=True
    ))
    graph.add_pad(PadNode(
        id="C1_PIN2", component="C1", pin_number="2", net_name="GND",
        x_mm=15.4, y_mm=38.0, is_ground_rail=True
    ))

    # ATMega328P Microcontroller (Target QFP-32)
    graph.components["U1"] = ComponentMetadata(
        ref_des="U1",
        package="TQFP-32_7x7mm_P0.8mm",
        value="ATmega328P-AU",
        center_mm=(45.0, 28.0),
        pin_count=32,
        is_polarized=True,
        pin1_location_mm=(41.5, 24.5)
    )

    # Adding high-density pins with 0.8mm pitch
    # Pin 4 = VCC (+5V), Pin 3 = GND, Pin 5 = GND, Pin 6 = VCC
    pins = [
        ("U1_PIN3", "3", "GND", 41.5, 26.1, False, True),
        ("U1_PIN4", "4", "VCC", 41.5, 26.9, True, False),
        ("U1_PIN5", "5", "GND", 41.5, 27.7, False, True),
        ("U1_PIN6", "6", "VCC", 41.5, 28.5, True, False),
    ]
    for p_id, p_num, net, px, py, is_pwr, is_gnd in pins:
        graph.add_pad(PadNode(
            id=p_id, component="U1", pin_number=p_num, net_name=net,
            x_mm=px, y_mm=py, width_mm=0.5, height_mm=0.3,
            is_power_rail=is_pwr, is_ground_rail=is_gnd
        ))

    return graph


if __name__ == "__main__":
    netlist = create_sample_arduino_netlist()
    print(f"Loaded ground truth netlist: {netlist.board_name}")
    print(f"Total components: {len(netlist.components)}, Total pads: {len(netlist.pads)}")
    
    # Test clearance check between U1_PIN3 (GND) and U1_PIN4 (VCC) with 0.8mm pitch
    clearance = netlist.check_clearance_violation("U1_PIN3", "U1_PIN4", min_clearance_mm=0.5)
    print("Clearance Check (U1 Pin 3 to Pin 4):", clearance)
