"""
OmniInspect Signal Feature Engineering
======================================
Transforms raw 100kSPS time-series windows into rich statistical and frequency-domain
feature vectors for millisecond-scale electrical fault prediction.

Window Parameters:
- Window length: 50 ms (5,000 samples @ 100 kSPS)
- Channels: [v_bus, i_load, v_shunt, acoustic, temp]

Features (14 total):
1. v_rms: Root-mean-square of bus voltage
2. v_kurtosis: Kurtosis of bus voltage (peakedness / impulse transients)
3. v_crest_factor: Peak-to-RMS ratio of voltage
4. v_min: Minimum instantaneous voltage in window
5. i_rms: Root-mean-square of load current
6. i_kurtosis: Kurtosis of current waveform
7. i_crest_factor: Peak-to-RMS ratio of current
8. i_max: Maximum instantaneous current peak
9. v_thd: Total Harmonic Distortion of voltage rail (Welch PSD harmonics)
10. hf_arc_energy_15_25k: Spectral energy in 15-25 kHz band (micro-arc signature)
11. acoustic_rms: Acoustic transducer RMS power
12. acoustic_peak_db: Peak acoustic energy (dB)
13. temp_c: Mean junction temperature
14. temp_slope: Rate of temperature change (dT/dt in °C/s)
"""

from __future__ import annotations

import numpy as np
from scipy import signal, stats
from typing import List, Union

FEATURE_NAMES = [
    "v_rms",
    "v_kurtosis",
    "v_crest_factor",
    "v_min",
    "i_rms",
    "i_kurtosis",
    "i_crest_factor",
    "i_max",
    "v_thd",
    "hf_arc_energy_15_25k",
    "acoustic_rms",
    "acoustic_peak_db",
    "temp_c",
    "temp_slope",
]


def extract_window_features(
    window: np.ndarray,
    fs: int = 100_000,
    prev_temp: float = 34.2,
    dt_s: float = 0.050
) -> np.ndarray:
    """
    Extracts a 14-dimensional feature vector from a single 2D window [N_samples, 5].
    Optimized for hard real-time execution (< 0.8 ms).
    """
    if window.ndim != 2 or window.shape[1] < 5:
        raise ValueError(f"Expected window shape (N, 5), got {window.shape}")

    v_bus = window[:, 0]
    i_load = window[:, 1]
    acoustic = window[:, 3]
    temp = window[:, 4]

    # --- Time Domain: Voltage ---
    v_mean = float(np.mean(v_bus))
    v_rms = float(np.sqrt(np.mean(v_bus ** 2)))
    v_std = float(np.std(v_bus)) + 1e-6
    v_kurt = float(np.mean(((v_bus - v_mean) / v_std) ** 4) - 3.0)
    v_peak = float(np.max(np.abs(v_bus)))
    v_crest = float(v_peak / (v_rms + 1e-6))
    v_min = float(np.min(v_bus))

    # --- Time Domain: Current ---
    i_mean = float(np.mean(i_load))
    i_rms = float(np.sqrt(np.mean(i_load ** 2)))
    i_std = float(np.std(i_load)) + 1e-6
    i_kurt = float(np.mean(((i_load - i_mean) / i_std) ** 4) - 3.0)
    i_peak = float(np.max(np.abs(i_load)))
    i_crest = float(i_peak / (i_rms + 1e-6))
    i_max = float(np.max(i_load))

    # --- Frequency Domain: Voltage Harmonics & HF Arc Band ---
    # Fast real FFT on downsampled window for sub-millisecond execution
    v_ac = v_bus - v_mean
    # 256-point RFFT represents 0 to 50 kHz
    rfft_spec = np.abs(np.fft.rfft(v_ac[:2048], n=256)) ** 2
    freq_bins = np.fft.rfftfreq(256, d=1.0 / fs)

    # 15 kHz - 25 kHz band energy (acoustic/electrical micro-discharge)
    hf_mask = (freq_bins >= 15_000) & (freq_bins <= 25_000)
    hf_energy = float(np.sum(rfft_spec[hf_mask])) if np.any(hf_mask) else 0.0

    # Total Harmonic Distortion
    total_energy = float(np.sum(rfft_spec) + 1e-12)
    fund_idx = int(np.argmax(rfft_spec))
    harm_energy = total_energy - rfft_spec[fund_idx]
    v_thd = float(np.sqrt(max(0.0, harm_energy) / (rfft_spec[fund_idx] + 1e-6)))

    # --- Acoustic Transducer ---
    acoustic_rms = float(np.sqrt(np.mean(acoustic ** 2)))
    acoustic_peak = float(np.max(acoustic))

    # --- Thermal & Derivative ---
    mean_temp = float(np.mean(temp))
    temp_slope = float((mean_temp - prev_temp) / dt_s)

    return np.array([
        v_rms,
        v_kurt,
        v_crest,
        v_min,
        i_rms,
        i_kurt,
        i_crest,
        i_max,
        v_thd,
        hf_energy,
        acoustic_rms,
        acoustic_peak,
        mean_temp,
        temp_slope,
    ], dtype=np.float32)


def extract_batch_features(
    signals: np.ndarray,
    labels: np.ndarray,
    window_samples: int = 5_000,
    step_samples: int = 2_500,
    fs: int = 100_000,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Slides over multi-trial signals and extracts feature matrix and window labels.
    signals: (N_trials, N_samples, 5)
    labels: (N_trials, N_samples)
    Returns:
      (X, y) where X is (N_windows, 14) and y is (N_windows,)
    """
    n_trials, n_samples, n_channels = signals.shape
    X_list = []
    y_list = []

    dt_s = window_samples / fs

    for t in range(n_trials):
        prev_temp = float(signals[t, 0, 4])
        for start in range(0, n_samples - window_samples + 1, step_samples):
            end = start + window_samples
            win = signals[t, start:end, :]
            # Window label: 1 if any pre-fault/fault in window, else 0
            win_label = 1 if np.any(labels[t, start:end] > 0) else 0

            feat = extract_window_features(win, fs=fs, prev_temp=prev_temp, dt_s=dt_s)
            prev_temp = float(np.mean(win[:, 4]))

            X_list.append(feat)
            y_list.append(win_label)

    return np.array(X_list, dtype=np.float32), np.array(y_list, dtype=np.int32)
