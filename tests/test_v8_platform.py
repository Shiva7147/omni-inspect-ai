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

    def test_feature_extraction_pipeline(self):
        """Verifies 14-dimensional feature extraction runs accurately on 100kSPS window."""
        import numpy as np
        from engine.ml.feature_engineering import extract_window_features, FEATURE_NAMES
        synthetic_win = np.zeros((5000, 5), dtype=np.float32)
        synthetic_win[:, 0] = 3.30  # bus voltage
        synthetic_win[:, 1] = 180.0 # current
        synthetic_win[:, 3] = 22.0  # acoustic
        synthetic_win[:, 4] = 34.2  # temp
        features = extract_window_features(synthetic_win)
        self.assertEqual(len(features), 14)
        self.assertAlmostEqual(features[0], 3.30, places=2)  # v_rms
        self.assertAlmostEqual(features[4], 180.0, places=1) # i_rms
        self.assertEqual(len(FEATURE_NAMES), 14)

    def test_fleet_telemetry_and_alert_ingest(self):
        """Verifies multi-station fleet telemetry ingest and predictive alert handling."""
        # Test fleet list
        r_list = self.client.get("/api/stations")
        self.assertEqual(r_list.status_code, 200)
        self.assertTrue(len(r_list.json()["stations"]) >= 1)

        # Ingest telemetry frame from edge node
        telemetry_payload = {
            "station_id": "STATION-EDGE-TEST",
            "timestamp_ns": 1729000000000000000,
            "bus_voltage_v": 3.301,
            "shunt_voltage_mv": 1.82,
            "current_ma": 182.0,
            "ir_temp_c": 34.5,
            "acoustic_energy_db": 22.1,
            "contactor_closed": True
        }
        r_telem = self.client.post("/api/station/telemetry", json=telemetry_payload)
        self.assertEqual(r_telem.status_code, 200)
        self.assertEqual(r_telem.json()["status"], "INGESTED")

        # Ingest predictive interlock trip alert
        alert_payload = {
            "station_id": "STATION-EDGE-TEST",
            "timestamp_ns": 1729000000005000000,
            "reason": "PREDICTIVE ANOMALY SCORE 0.770 > 0.680",
            "anomaly_score": 0.770,
            "trip_duration_us": 1.2,
            "features": {"v_rms": 3.15, "i_rms": 290.0}
        }
        r_alert = self.client.post("/api/station/alert", json=alert_payload)
        self.assertEqual(r_alert.status_code, 200)
        self.assertEqual(r_alert.json()["status"], "ALERT_RECORDED")
        self.assertEqual(SYSTEM_STATE["current_mode"], "fault")

    def test_edge_benchmark_and_latency_budget(self):
        """Verifies edge inference completes within <5.0 ms latency budget and trips accurately."""
        r_bench = self.client.post("/api/edge/benchmark?cycles=30&fault_at=20")
        self.assertEqual(r_bench.status_code, 200)
        data = r_bench.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["tripped_at_cycle"], 20)
        self.assertTrue(data["within_5ms_budget"])
        self.assertLess(data["avg_latency_us"], 5000.0)

    def test_failsafe_watchdog_timeout(self):
        """Verifies dead-man's switch watchdog fires trip callback on missing heartbeat."""
        import time
        from engine.edge.watchdog import FailSafeWatchdog
        tripped = {"fired": False}

        def on_trip():
            tripped["fired"] = True

        wd = FailSafeWatchdog(timeout_ms=50.0, trip_callback=on_trip)
        wd.start()
        time.sleep(0.02)
        wd.kick()  # heartbeat 1
        time.sleep(0.02)
        wd.kick()  # heartbeat 2
        self.assertFalse(tripped["fired"])
        # Deliberately starve heartbeat
        time.sleep(0.08)
        self.assertTrue(tripped["fired"])
        wd.stop()


if __name__ == "__main__":
    unittest.main()
