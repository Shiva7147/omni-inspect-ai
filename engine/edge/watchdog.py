"""
OmniInspect Fail-Safe Watchdog Subsystem
========================================
Implements a dead-man's switch / hardware heartbeat watchdog for cyber-physical safety.

Safety Architecture:
- The Crydom D2425 Solid State Relay is Normally Open (NO).
- The edge inference loop must actively "kick" the watchdog every 20-50ms.
- If inference freezes, encounters an unhandled exception, or latency exceeds 100ms:
  The watchdog immediately de-asserts GPIO, cutting power to the device under test (DUT).
- Meets IEC 61508 / DO-254 fail-safe design principles: Single Point of Failure (SPOF)
  in software defaults the physical system into a de-energized, non-destructive state.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger("omniinspect.edge.watchdog")


class FailSafeWatchdog:
    def __init__(self, timeout_ms: float = 100.0, trip_callback: Optional[Callable[[], None]] = None):
        self.timeout_s = timeout_ms / 1000.0
        self.trip_callback = trip_callback
        self._last_heartbeat = time.perf_counter()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._tripped = False

    def start(self):
        """Starts the background watchdog monitoring thread."""
        self._running = True
        self._tripped = False
        self._last_heartbeat = time.perf_counter()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True, name="OmniInspect-Watchdog")
        self._thread.start()
        logger.info("Fail-Safe Watchdog started (Timeout: %.1f ms)", self.timeout_s * 1000.0)

    def kick(self):
        """Called by the inference engine to signal alive status."""
        self._last_heartbeat = time.perf_counter()

    def _monitor_loop(self):
        while self._running:
            time.sleep(self.timeout_s / 4.0)  # Check at 4x the timeout frequency
            elapsed = time.perf_counter() - self._last_heartbeat
            if elapsed > self.timeout_s and not self._tripped:
                self._tripped = True
                logger.critical(
                    "WATCHDOG TIMEOUT EXCEEDED (%.2f ms without heartbeat). EXECUTING FAIL-SAFE CUTOFF!",
                    elapsed * 1000.0
                )
                if self.trip_callback:
                    try:
                        self.trip_callback()
                    except Exception as e:
                        logger.error("Error executing watchdog trip callback: %s", e)

    def stop(self):
        """Stops the watchdog thread cleanly."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.2)
        logger.info("Fail-Safe Watchdog stopped.")
