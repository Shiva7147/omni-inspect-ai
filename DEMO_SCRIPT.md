# OmniInspect AI — 2-Minute Hackathon Demo Video Script

**Target Duration:** 120 Seconds (2:00)  
**Format:** Screen recording with voiceover (OBS Studio / Loom, 1080p 60fps)  
**Key Goal:** Hook the judges in 15 seconds, prove the dual-layer architecture, show live Meta reasoning, and demonstrate the cyber-physical safety gate.

---

## 🎬 Scene Breakdown & Voiceover

### [0:00 - 0:20] Hook: The $3,000 First Power-On Catastrophe
- **Screen:** Show the terminal running `python -m engine.cli_audit --image data/samples/board_inspection_macro.jpg` or open the Cockpit in browser ([http://127.0.0.1:8000](http://127.0.0.1:8000)).
- **Voiceover:**
  > "Hardware engineers spend three weeks assembling a $3,000 drone flight controller or satellite avionics board. And 75% of fatal burnouts happen in under 15 milliseconds on First Power-On. Why? A single microscopic solder bridge between a +24V power rail and a 3.3V microcontroller.
  > 
  > This is **OmniInspect AI** — an autonomous cyber-physical safety gate powered by Meta's foundation models that catches physical defects *before* power is applied, and continuously intercepts electrical faults in-flight."

---

### [0:20 - 0:45] Layer 1: Pre-Power Optical In-Circuit Gate
- **Screen:** In the Cockpit, hit key `1` (State 1: Inspection Active). Show the CAD reticle overlay scanning U14. Then press `2` (State 2: Fault Detected).
- **Voiceover:**
  > "Layer 1 is our Pre-Power Optical Gate. Before the power supply is ever energized, high-resolution macro optics align to the board's KiCad netlist.
  >
  > Here, on the STM32H743 flight computer, our multimodal vision pipeline queries Meta's official reasoning API. Look at the verbatim output: the model consumed 895 reasoning tokens and diagnosed a direct solder bridge across Pin 48 (+3V3_MCU) and Pin 49 (Ground). It immediately flags an IPC-A-610G Class 3 violation and latches the power contactor OPEN in under 3.2 milliseconds."

---

### [0:45 - 1:15] Layer 2: 100 kSPS Predictive Signal ML & FFT
- **Screen:** In the Cockpit, click **[LAYER 2: 100kSPS SIGNAL ML]** tab above the image. Show the live oscilloscope and the 32-bar FFT spectrum flaring at 18.4 kHz.
- **Voiceover:**
  > "Now watch Layer 2: our In-Flight Predictive Signal Interlock. In high-reliability aerospace, intermittent micro-shorts can develop under vibration or thermal stress.
  >
  > OmniInspect monitors high-speed 100 kSPS rail micro-fluctuations and INA229 current harmonics. Notice the 18.4 kHz acoustic transducer spike (+42 dB). Our time-series pattern model recognizes this pre-fault micro-arc signature 140 milliseconds before catastrophic burnout, triggering the solid-state interlock in 3.18 milliseconds — well within our 5-millisecond specification."

---

### [1:15 - 1:40] Technician Claim, Rework & State 3 Restoral
- **Screen:** 
  1. Click **[F1 — CLAIM TICKET]** (or press `F1`). The countdown halts.
  2. Click **[F2 — VERIFY REWORK]** (or press `F2`). The screen transforms to emerald green (State 3: Cleared — Power Authorized).
  3. Toggle **[LAYER 2: IN-FLIGHT SIGNAL ML]** in State 3 to show the clean DC rail waveform and quiet FFT spectrum.
- **Voiceover:**
  > "The technician claims the safety ticket with F1, halts the failsafe auto-quarantine, and performs the micro-soldering rework.
  >
  > Pressing F2 triggers the post-rework certification. The new optical capture confirms fluid concave fillets and over 0.20mm pin clearance. Look at the telemetry: the contactor is closed, 24V bus is energized, current is a nominal 4.20A, and the harmonic spectrum is completely clean. Power is safely authorized."

---

### [1:40 - 2:00] Regulatory Integrity, RCA Report & Close
- **Screen:** Press `F5` to open the certified HTML Incident Report in a new tab ([http://127.0.0.1:8000/report](http://127.0.0.1:8000/report)). Scroll down through the side-by-side Before/After comparison, verbatim Meta quote, checklist, and SHA-256 hash.
- **Voiceover:**
  > "Every single inspection generates an immutable Root-Cause Analysis report with a cryptographic SHA-256 digest, full telemetry audit tables, and certified technician sign-offs ready for FAA and ISO-9001 compliance.
  >
  > OmniInspect AI transforms pre-power verification from a $100,000 factory bottleneck into an accessible, intelligent cyber-physical gate on every engineer's bench.
  >
  > Built by Shiva Shankar S for the Meta Global AI Developer Hackathon. Thank you."

---

## 💡 Quick Tips for Recording
- **Resolution:** 1920x1080 at 100% browser scaling.
- **Hotkeys to rehearse:**
  - `1` (Inspection)
  - `2` (Fault)
  - Click `[LAYER 2: 100kSPS SIGNAL ML]`
  - `F1` (Claim)
  - `F2` (Verify Rework)
  - `F5` (Export RCA Report)
- **Audio:** Clear USB microphone or headset with minimal room reverb.
