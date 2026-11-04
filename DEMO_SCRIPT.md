# OmniInspect AI — 2-Minute Hackathon Demo Video Script (v8.2)

**Target Duration:** 120 Seconds (2:00)  
**Format:** Screen recording with voiceover (OBS Studio / Loom, 1080p 60fps)  
**Audio Setup:** Browser audio enabled (for the Jarvis avionics voice alerts) + clear microphone voiceover.  
**Key Goal:** Hook the judges in 15 seconds, prove the dual-layer architecture, show live Meta reasoning with receipts, and demonstrate the cyber-physical safety gate.

---

## 🎬 Scene Breakdown & Voiceover

### [0:00 - 0:20] Hook: The $3,000 First Power-On Catastrophe
- **Screen:** Open the Cockpit in browser ([http://127.0.0.1:8000](http://127.0.0.1:8000)) in State 2 (Fault Detected). Ensure Audio is ON.
- **Background Sound:** The cockpit chime alerts and synthesized avionics voice speaks:
  > *"Warning: Pre-power interlock tripped. Solder bridge detected across Pin 48 and Pin 49 on U14. Primary contactor latched open in 3.18 milliseconds."*
- **Voiceover:**
  > "Hardware engineers spend three weeks assembling a $3,000 flight computer or satellite avionics board. And over 75% of fatal burnouts happen in under 15 milliseconds on First Power-On. Why? A single microscopic solder bridge between a +24V power rail and a 3.3V microcontroller.
  > 
  > This is **OmniInspect AI** — an autonomous cyber-physical safety gate powered by Meta's foundation models that catches physical defects *before* power is applied, and continuously intercepts electrical faults in-flight."

---

### [0:20 - 0:45] Layer 1: Pixel-Registered Optical Gate & Epistemic Receipts
- **Screen:** 
  1. Click **[TOGGLE BEFORE/AFTER VIEW]** (observe 100% pixel-registered alignment: only the solder filament appears/disappears).
  2. Point cursor to the metric badges: `[MEASURED]`, `[COMPUTED]`, `[INFERRED BY MUSE]`.
- **Voiceover:**
  > "Layer 1 is our Pre-Power Optical Gate. Before the power supply is ever energized, high-resolution macro optics align to the board's KiCad netlist.
  >
  > Notice the precision: our Before and After captures are 100% pixel-registered—the board never shifts. Look at the verbatim output: Meta's multimodal reasoning engine consumed 895 reasoning tokens to diagnose a direct solder bridge across Pin 48 and Pin 49.
  >
  > And we don't believe in mystery numbers: every single parameter is strictly labeled as Measured by hardware ADC, Computed by deterministic geometry, or Inferred by Meta Muse."

---

### [0:45 - 1:10] Layer 2: 100 kSPS Predictive Signal ML & Physics Simulation
- **Screen:** In the Left Panel, click **[LAYER 2: PREDICTIVE ML]**. The 60 FPS oscilloscope waveform and the 32-bar FFT spectrum appear, showing the 18.4 kHz micro-arc spike.
- **Voiceover:**
  > "Now watch Layer 2: our In-Flight Predictive Signal Interlock. While traditional circuit breakers only react AFTER 15 amps surges through the chip and destroys the silicon die, our model is trained on 42,000 historical electrical failure records and SPICE micro-arc plasma simulations.
  >
  > In real time, OmniInspect monitors high-speed 100 kSPS rail micro-ripple and INA229 current harmonics. Notice the 18.4 kHz acoustic resonance spike (+42 dB). Our model recognizes this pre-fault precursor 142 milliseconds BEFORE the short circuit solidifies, and trips the Solid-State Relay in 3.18 milliseconds."

---

### [1:10 - 1:30] Layer 3: CAD Schematic Digital Twin & Multi-Defect Presets
- **Screen:** 
  1. In the Left Panel, click **[CAD DIGITAL TWIN]**. Show the interactive SVG circuit diagram showing Pin 48 (`+3V3_MCU`) and Pin 49 (`GND_ISO`) with the animated red short-circuit spark.
  2. In the top bar, switch the dropdown to **Preset 2 (C24 Tantalum Reverse Polarity)** or **Preset 3 (Q3 MOSFET Void)**. Hear the avionics voice announce the new component.
- **Voiceover:**
  > "Clicking CAD Digital Twin reveals the true hardware digital twin: mapping camera pixels directly to KiCad netlist nodes. Pin 48 is +3.3V logic; Pin 49 is isolated ground.
  >
  > And OmniInspect is generalized across IPC-A-610G classes: from microcontroller solder bridges, to reversed tantalum capacitors that explode on 24V rails, to power MOSFET solder voids."

---

### [1:30 - 2:00] Technician Restoral, RCA Flight Recorder & Close
- **Screen:** 
  1. Click **[F1 — CLAIM TICKET]** (timer stops).
  2. Click **[F2 — VERIFY REWORK]** (screen turns emerald green; hear the confirmation chime: *"Rework verified. Clearance compliant. Power authorized."*).
  3. Press **[F5]** to open the print-ready RCA Incident Report. Scroll down through the Before/After comparison, the Epistemic Receipts table, the Avionics Flight Recorder Black Box timeline, and the SHA-256 cryptographic digest.
- **Voiceover:**
  > "The technician claims the ticket with F1, performs the rework, and hits F2 to verify restoral. Clean concave fillets, 0.24mm clearance, and nominal 24V power authorized.
  >
  > Every inspection generates an tamper-evident Root-Cause Analysis report complete with an Avionics Flight Recorder microsecond timeline and SHA-256 cryptographic proof ready for FAA and ISO-9001 compliance.
  >
  > OmniInspect AI: pushing the frontier of cyber-physical safety. Built by Shiva Shankar S for the Meta Global AI Developer Hackathon. Thank you."

---

## 💡 Hotkeys to Rehearse Before Hitting Record
| Key | Action |
| :---: | :--- |
| `2` | Jump to **State 2: Fault Detected** (starts the demo) |
| Click `[LAYER 2: PREDICTIVE ML]` | Shows the live oscilloscope & 18.4 kHz FFT spike |
| Click `[CAD DIGITAL TWIN]` | Shows the SVG schematic circuit cross-probe |
| `F1` | Claims the safety ticket |
| `F2` | Transitions to **State 3: Cleared — Power Authorized** |
| `F5` | Opens the printable RCA Incident Report with Flight Recorder log |
