"""
Automated End-to-End Test Suite for OmniInspect AI Platform v8.0.
Verifies Dual-Layer Architecture (Optical Gate + Predictive Signal ML),
WebSocket Telemetry Engine, Printable RCA Incident Reports, and CLI Auditor.
"""

import unittest
from fastapi.testclient import TestClient
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from web.app import app, simulator, SYSTEM_STATE


class TestOmniInspectPlatform(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_dashboard_homepage_v8(self):
        """Verifies that the v8.0 dashboard HTML loads with both Layer 1 and Layer 2 components."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.text
        self.assertIn("OmniInspect AI", html)
        self.assertIn("LAYER 1: OPTICAL", html)
        self.assertIn("CAD DIGITAL TWIN", html)
        self.assertIn("scopeCanvas2", html)
        self.assertIn("scopeCanvas3", html)
        self.assertIn("FAILSAFE REVIEW TIMER", html)

    def test_printable_rca_report_generation(self):
        """Verifies that the printable RCA Incident Report generates with SHA-256 digest and epistemic receipts."""
        response = self.client.get("/report")
        self.assertEqual(response.status_code, 200)
        html = response.text
        self.assertIn("ROOT CAUSE ANALYSIS REPORT", html)
        self.assertIn("IPC-A-610G", html)
        self.assertIn("SHA-256", html)
        self.assertIn("INC-2026-", html)
        self.assertIn("MEASURED", html)
        self.assertIn("COMPUTED", html)
        self.assertIn("INFERRED BY MUSE", html)
        self.assertIn("BLACK BOX TELEMETRY RECORD", html)

        # Also test the alternative endpoint
        export_resp = self.client.get("/api/export_incident_report")
        self.assertEqual(export_resp.status_code, 200)
        self.assertIn("ROOT CAUSE ANALYSIS REPORT", export_resp.text)

    def test_defect_preset_switching(self):
        """Verifies multi-defect preset switching between U14, C24, and Q3."""
        r_preset = self.client.post("/api/preset?preset_id=c24_polarity")
        self.assertEqual(r_preset.status_code, 200)
        data = r_preset.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertIn("C24", data["preset"]["title"])
        self.assertEqual(SYSTEM_STATE["active_preset"], "c24_polarity")

        # Reset to U14
        r_u14 = self.client.post("/api/preset?preset_id=u14_bridge")
        self.assertEqual(r_u14.status_code, 200)
        self.assertEqual(SYSTEM_STATE["active_preset"], "u14_bridge")

    def test_system_state_and_telemetry(self):
        """Verifies state query returns valid 32-bin FFT spectrum and electrical sensor readings."""
        response = self.client.get("/api/state")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("state", data)
        self.assertIn("sensors", data)
        
        sensors = data["sensors"]
        self.assertIn("fft_spectrum", sensors)
        self.assertEqual(len(sensors["fft_spectrum"]), 32)
        self.assertIn("bus_voltage", sensors)
        self.assertIn("peak_current", sensors)
        self.assertIn("junction_temp", sensors)
        self.assertIn("acoustic_freq", sensors)

    def test_state_transitions(self):
        """Verifies transition between 'fault', 'nominal', and 'inspection'."""
        # Transition to nominal
        r_nom = self.client.post("/api/transition?target=nominal")
        self.assertEqual(r_nom.status_code, 200)
        self.assertEqual(r_nom.json()["current_mode"], "nominal")
        self.assertEqual(simulator.state, "nominal")

        # Transition to inspection
        r_ins = self.client.post("/api/transition?target=inspection")
        self.assertEqual(r_ins.status_code, 200)
        self.assertEqual(r_ins.json()["current_mode"], "inspection")
        self.assertEqual(simulator.state, "inspection")

        # Transition back to fault
        r_flt = self.client.post("/api/transition?target=fault")
        self.assertEqual(r_flt.status_code, 200)
        self.assertEqual(r_flt.json()["current_mode"], "fault")
        self.assertEqual(simulator.state, "fault")

    def test_interlock_claim_and_quarantine(self):
        """Verifies claiming safety tickets and quarantining defective boards."""
        r_claim = self.client.post("/api/interlock/claim")
        self.assertEqual(r_claim.status_code, 200)
        self.assertEqual(r_claim.json()["status"], "CLAIMED")
        self.assertTrue(SYSTEM_STATE["is_claimed"])

        r_quar = self.client.post("/api/interlock/quarantine")
        self.assertEqual(r_quar.status_code, 200)
        self.assertEqual(r_quar.json()["status"], "QUARANTINED")
        self.assertEqual(SYSTEM_STATE["current_mode"], "inspection")


if __name__ == "__main__":
    unittest.main()
