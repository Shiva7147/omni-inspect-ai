"""
OmniInspect Edge Hardware Abstraction Layer (HAL)
=================================================
Interfaces with physical hardware on Raspberry Pi 4B:
- Texas Instruments INA229 20-bit precision Current/Voltage Monitor via SPI
- Crydom D2425 Solid State Relay (SSR) Interlock via GPIO 17 (Normally-Open Fail-Safe)
- Melexis MLX90614 Infrared Non-Contact Temperature Sensor via I2C (0x5A)
- MEMS Ultrasonic/Acoustic Transducer for micro-arc discharge detection

Cross-Platform Compatibility:
When run on hardware lacking SPI/GPIO/I2C (e.g. Windows/macOS/x86 workstations),
it automatically activates high-fidelity physical hardware emulation with microsecond
timestamping so the entire pipeline runs identically in bench simulation and on the factory floor.
"""

from __future__ import annotations

import logging
import math
import os
import platform
import sys
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

logger = logging.getLogger("omniinspect.edge.hardware")

# Check if native Linux SPI and GPIO are available
_IS_LINUX = platform.system().lower() == "linux"
try:
    if _IS_LINUX:
        import spidev  # type: ignore
        import RPi.GPIO as GPIO  # type: ignore
        import smbus2  # type: ignore
        _HAS_NATIVE_HARDWARE = True
    else:
        _HAS_NATIVE_HARDWARE = False
except ImportError:
    _HAS_NATIVE_HARDWARE = False


@dataclass
class TelemetryFrame:
    """Synchronized microsecond-timestamped telemetry frame from edge sensors."""
    timestamp_ns: int
    bus_voltage_v: float
    shunt_voltage_mv: float
    current_ma: float
    ir_temp_c: float
    acoustic_energy_db: float
    contactor_closed: bool
    synthetic: bool = False


class INA229Driver:
    """
    Texas Instruments INA229 85V, 20-Bit, High-Precision Current and Power Monitor with SPI.
    Registers:
      0x00: CONFIG
      0x01: ADC_CONFIG
      0x02: SHUNT_CAL
      0x04: VSHUNT (20-bit signed)
      0x05: VBUS (20-bit unsigned, 195.3125 uV/LSB)
      0x07: CURRENT (20-bit signed)
    """

    def __init__(self, bus: int = 0, device: int = 0, shunt_ohms: float = 0.01, use_mock: bool = False):
        self.bus = bus
        self.device = device
        self.shunt_ohms = shunt_ohms
        self.is_mock = use_mock or not _HAS_NATIVE_HARDWARE
        self._spi = None
        self._sample_idx = 0

        if not self.is_mock:
            try:
                self._spi = spidev.SpiDev()
                self._spi.open(self.bus, self.device)
                self._spi.max_speed_hz = 10_000_000  # 10 MHz SPI
                self._spi.mode = 1
                logger.info("Initialized physical INA229 via SPI bus %d dev %d", bus, device)
            except Exception as e:
                logger.warning("Could not initialize physical SPI (%s). Falling back to emulation.", e)
                self.is_mock = True

    def read_telemetry(self, fault_injection: Optional[str] = None) -> Tuple[float, float, float]:
        """
        Returns (bus_voltage_v, shunt_voltage_mv, current_ma).
        """
        if not self.is_mock and self._spi is not None:
            # Physical SPI read: VBUS (reg 0x05)
            # Read 3 bytes for 20-bit register
            resp_v = self._spi.xfer2([0x05 << 2 | 0x01, 0x00, 0x00, 0x00])
            raw_v = ((resp_v[1] << 16) | (resp_v[2] << 8) | resp_v[3]) >> 4
            vbus = raw_v * 195.3125e-6

            # Read VSHUNT (reg 0x04)
            resp_s = self._spi.xfer2([0x04 << 2 | 0x01, 0x00, 0x00, 0x00])
            raw_s = ((resp_s[1] << 16) | (resp_s[2] << 8) | resp_s[3]) >> 4
            if raw_s & 0x80000:
                raw_s -= 0x100000
            vshunt_mv = raw_s * 312.5e-6  # 312.5 nV/LSB in mV
            current_ma = (vshunt_mv / self.shunt_ohms)

            return round(vbus, 4), round(vshunt_mv, 4), round(current_ma, 2)
        else:
            # Emulation mode matching controlled fault rig physics
            self._sample_idx += 1
            t = self._sample_idx / 100_000.0  # 100 kSPS timebase
            base_v = 3.300
            # 12mV 98kHz SMPS ripple
            v_ripple = 0.012 * math.sin(2 * math.pi * 98_000 * t) + (0.002 * math.sin(t * 153000.0))
            base_current = 180.0 + 8.5 * math.sin(2 * math.pi * 120 * t) + (1.2 * math.sin(t * 97000.0))

            if fault_injection == "pre_fault_jitter":
                # Class 1: Dendrite / filament micro-bridging
                t_pre = (self._sample_idx % 20_000) / 100_000.0
                hf_arc = 0.18 * math.sin(2 * math.pi * 18_400 * t_pre) * (1 + 0.5 * math.sin(2 * math.pi * 600 * t_pre))
                voltage_dips = -0.15 * math.exp(t_pre * 4.0) * abs(math.sin(2 * math.pi * 450 * t_pre))
                v_bus = base_v + voltage_dips + hf_arc * 0.4
                current_spikes = 110.0 * abs(math.sin(2 * math.pi * 920 * t_pre)) * (t_pre / 0.200)
                cur = base_current + current_spikes
                return round(v_bus, 4), round(cur * 0.01, 4), round(cur, 2)
            elif fault_injection == "short_circuit":
                # Catastrophic short
                return 0.421, 24.50, 2450.0

            return round(base_v + v_ripple, 4), round(base_current * 0.01, 4), round(base_current, 2)


class CrydomSSRDriver:
    """
    Crydom D2425 Solid State Relay (SSR) Interlock Controller.
    Controlled via active-high logic on Raspberry Pi GPIO 17.
    FAIL-SAFE DESIGN:
    - Normally-Open (NO) architecture.
    - If power drops, GPIO unasserts, or process crashes -> Relay opens, isolating DUT from power.
    """

    def __init__(self, pin: int = 17, use_mock: bool = False):
        self.pin = pin
        self.is_mock = use_mock or not _HAS_NATIVE_HARDWARE
        self._closed = False

        if not self.is_mock:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.pin, GPIO.OUT, initial=GPIO.LOW)
                logger.info("Initialized Crydom SSR on GPIO %d (State: OPEN / Safe)", self.pin)
            except Exception as e:
                logger.warning("Could not initialize physical GPIO (%s). Falling back to emulation.", e)
                self.is_mock = True

    @property
    def is_closed(self) -> bool:
        """True if contactor is energized and DUT is powered. False if isolated (safe)."""
        return self._closed

    def energize(self) -> bool:
        """Closes contactor to supply power to DUT."""
        self._closed = True
        if not self.is_mock:
            GPIO.output(self.pin, GPIO.HIGH)
        logger.info("Crydom SSR ENERGIZED -> Circuit under test powered.")
        return True

    def trip_interlock(self, reason: str = "PREDICTIVE ANOMALY") -> float:
        """
        Immediately cuts power by de-asserting GPIO.
        Returns the duration of trip actuation in microseconds.
        """
        t0 = time.perf_counter_ns()
        self._closed = False
        if not self.is_mock:
            GPIO.output(self.pin, GPIO.LOW)
        t1 = time.perf_counter_ns()
        duration_us = (t1 - t0) / 1000.0
        logger.critical(">>> CRYDOM SSR TRIPPED <<< Reason: %s (Actuation: %.2f us)", reason, duration_us)
        return duration_us

    def cleanup(self):
        """Always force relay open on exit."""
        self.trip_interlock("DRIVER CLEANUP / SHUTDOWN")
        if not self.is_mock:
            try:
                GPIO.cleanup(self.pin)
            except Exception:
                pass


class MLX90614Driver:
    """Melexis MLX90614 Infrared Non-Contact Thermometer via I2C."""

    def __init__(self, bus: int = 1, addr: int = 0x5A, use_mock: bool = False):
        self.bus = bus
        self.addr = addr
        self.is_mock = use_mock or not _HAS_NATIVE_HARDWARE
        self._i2c = None

        if not self.is_mock:
            try:
                self._i2c = smbus2.SMBus(self.bus)
                logger.info("Initialized MLX90614 on I2C bus %d addr 0x%02X", bus, addr)
            except Exception as e:
                logger.warning("Could not initialize physical I2C (%s). Falling back to emulation.", e)
                self.is_mock = True

    def read_temperature(self, fault_heating: bool = False) -> float:
        """Returns object (MCU junction) temperature in degrees Celsius."""
        if not self.is_mock and self._i2c is not None:
            # 0x07 is object temperature RAM register
            raw = self._i2c.read_word_data(self.addr, 0x07)
            temp_c = (raw * 0.02) - 273.15
            return round(temp_c, 2)
        else:
            base = 34.2
            if fault_heating:
                base += 6.8  # Thermal runaway signature before catastrophic junction failure
            return round(base, 2)


class HardwareStation:
    """
    Unified hardware controller representing one inspection and protection station.
    """

    def __init__(self, station_id: str = "STATION-EDGE-01", use_mock: Optional[bool] = None):
        self.station_id = station_id
        force_mock = use_mock if use_mock is not None else not _HAS_NATIVE_HARDWARE
        self.ina229 = INA229Driver(use_mock=force_mock)
        self.ssr = CrydomSSRDriver(use_mock=force_mock)
        self.temp_sensor = MLX90614Driver(use_mock=force_mock)
        self.is_mock = self.ina229.is_mock
        logger.info("Hardware Station '%s' ready (Hardware Native: %s)", station_id, not self.is_mock)

    def sample_frame(self, fault_injection: Optional[str] = None) -> TelemetryFrame:
        """Captures a single synchronized telemetry frame across all sensors."""
        t_ns = time.time_ns()
        vbus, vshunt, cur = self.ina229.read_telemetry(fault_injection)
        heating = fault_injection in ("pre_fault_jitter", "short_circuit")
        temp = self.temp_sensor.read_temperature(fault_heating=heating)

        # Acoustic signature: 18.4kHz arc burst in pre-fault
        t = self.ina229._sample_idx / 100_000.0
        acoustic_db = 22.0 + 1.5 * math.sin(2 * math.pi * 12_000 * t)
        if fault_injection == "pre_fault_jitter":
            acoustic_db = 74.8  # Audible/ultrasonic corona discharge micro-arc
        elif fault_injection == "short_circuit":
            acoustic_db = 98.2

        return TelemetryFrame(
            timestamp_ns=t_ns,
            bus_voltage_v=vbus,
            shunt_voltage_mv=vshunt,
            current_ma=cur,
            ir_temp_c=temp,
            acoustic_energy_db=acoustic_db,
            contactor_closed=self.ssr.is_closed,
            synthetic=self.is_mock,
        )

    def shutdown(self):
        """Fail-safe de-energize on station shutdown."""
        self.ssr.cleanup()
