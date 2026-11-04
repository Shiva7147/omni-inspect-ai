import sys
sys.path.insert(0, "D:/omni-inspect-ai")
from web.app import simulator, app
from fastapi.testclient import TestClient
import numpy as np

client = TestClient(app)

print("=== TEST 1: NOMINAL READINGS & Z-SCORES ===")
simulator.reset_nominal()
r = simulator.get_readings()
print(f"State: {r['status_pill']} | Tripped: {r['tripped']} | Consecutive: {r['consecutive_above']}/3")
print(f"Smoothed Score: {r['smoothed_score']} | Raw Score: {r['raw_score']}")
max_z = max(abs(f['z_score']) for f in r['top_features'])
print("Top 5 Features Deviation from Baseline:")
for f in r['top_features']:
    print(f"  {f['name']:22s}: val={f['val']:10.3f}, z={f['z_score']:+6.2f} sigma")
print(f"Max |z| in nominal state: {max_z:.2f} sigma -> PASS: {max_z < 3.0} (within +-3 sigma)")

print("\n=== TEST 2: RAMP MONOTONIC PROGRESSION & TRIP ===")
simulator.start_precursor(speed=1.0)
scores_raw = []
scores_ema = []
for step in range(11):
    simulator.ramp_start_time = simulator.ramp_start_time - 2.5  # advance 2.5s (10% ramp each step)
    frame = simulator.get_readings()
    scores_raw.append(frame['raw_score'])
    scores_ema.append(frame['smoothed_score'])
    print(f"Progress {step*10:3d}%: Raw={frame['raw_score']:.4f} | Smoothed={frame['smoothed_score']:.4f} | Consecutive={frame['consecutive_above']}/3 | Tripped={frame['tripped']}")

print("\n=== TEST 3: RESET TO NOMINAL ===")
simulator.reset_nominal()
r_reset = simulator.get_readings()
print(f"Status pill:      {r_reset['status_pill']} (expect NOMINAL)")
print(f"Tripped:          {r_reset['tripped']} (expect False)")
print(f"Rule counter:     {r_reset['consecutive_above']}/3 (expect 0/3)")
print(f"Auto Log entries: {len(r_reset['auto_log'])} (expect 0)")
print(f"Signatures:       S1={r_reset['signatures']['s1']}, S2={r_reset['signatures']['s2']}, S3={r_reset['signatures']['s3']} (all False/WAITING)")
print(f"Smoothed score:   {r_reset['smoothed_score']:.4f}")
print(f"Lead time:        {r_reset['lead_time_s']} s")

print("\n=== TEST 4: SOAK TEST (SERVER-SIDE) ===")
soak_resp = client.post("/api/soak_test?cycles=10000")
data = soak_resp.json()
print(f"Windows scored: {data['windows_scored']}")
print(f"False trips:    {data['trips']}")
print(f"Peak score:     {data['peak_score']}")
print(f"p99 score:      {data['p99_score']}")
print(f"Mean score:     {data['mean_score']}")
print(f"Threshold:      {data['threshold']}")
print(f"95% Bound:      {data['false_trip_rate_bound_95pct']} ({data['bound_description']})")
print(f"Data label:     {data['data_label']}")
print(f"Status:         {data['status']}")
