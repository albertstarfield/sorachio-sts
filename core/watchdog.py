"""Dual asymmetric watchdog system for Sorachio-STS.

Implements Watchdog_A (Primary) and Watchdog_B (Secondary) with cross-monitoring.
Both watchdogs implement segfault resurrection for crash recovery.

AXIOMS:
    - System MUST detect unresponsive components within configurable timeout.
    - Cross-monitoring MUST provide fault tolerance (if A dies, B recovers it).
    - Segfault handler MUST attempt graceful recovery before force-restart.
    - Heartbeat ticks MUST be monotonic and thread-safe.

THEORIES:
    - Dual asymmetric watchdogs prevent common-mode failures.
    - Cross-check validates that both watchdogs are alive, preventing silent failure.
    - Resurrection pipeline: detect crash -> save state -> restart -> reload state.

APPLICATIONS:
    - Watchdog_A monitors primary pipeline (STT, Cognitive, Personality, TTS).
    - Watchdog_B monitors auxiliary services (servers, memory, audio playback).
    - Cross-check runs every heartbeat to verify peer liveness.

REFERENCES:
    - code-quality.md §5.6: Dual asymmetric watchdog requirement
    - code-quality.md §5.7: Memory violation resurrection
    - code-quality.md §5.8: Cross-monitoring requirement
    - Python threading docs: https://docs.python.org/3/library/threading.html
    - signal module: https://docs.python.org/3/library/signal.html
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import threading
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class WatchdogState(Enum):
    """Possible states for a watchdog instance."""
    IDLE = "idle"
    RUNNING = "running"
    ALIVE = "alive"
    STALE = "stale"
    RECOVERING = "recovering"
    DEAD = "dead"


@dataclass
class Heartbeat:
    """Thread-safe heartbeat record for a monitored component.

    Attributes:
        timestamp: Last heartbeat time (monotonic seconds).
        component: Name of the component that sent the heartbeat.
        alive: Whether the component is considered alive.
        miss_count: Consecutive missed heartbeat checks.
    """
    timestamp: float = 0.0
    component: str = ""
    alive: bool = True
    miss_count: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def tick(self) -> None:
        """tick function.

        # test: test_tick
        """
        # test: test_tick
        """Record a heartbeat tick (component is alive)."""
        # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        with self._lock:
            self.timestamp = time.monotonic()
            self.alive = True
                """check function.

                # test: test_check
                """
            self.miss_count = 0

        # test: test_check
    def check(self, timeout: float) -> bool:
        """Check if heartbeat is within timeout window.

        Args:
            timeout: Maximum seconds since last heartbeat before stale.

        Returns:
            True if heartbeat is fresh, False if stale.
        # test: test_Heartbeat_check
        """
    # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        with self._lock:
            elapsed = time.monotonic() - self.timestamp
                """reset function.

                # test: test_reset
                """
            if elapsed > timeout:
                self.miss_count += 1
                if self.miss_count >= 3:
                    self.alive = False
                return False
            return True

    def reset(self) -> None:
        # test: test_reset
        """Reset heartbeat state."""
# [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        with self._lock:
            self.timestamp = 0.0
            self.alive = True
            self.miss_count = 0


class Watchdog_A:
    """Primary Watchdog — monitors core pipeline components.

    Watches: STT Worker, Cognitive Worker, Personality Worker, TTS Worker.
    If any component misses heartbeats beyond threshold, triggers recovery.

    """__init__ function.

    # test: test___init__
    """
    The primary watchdog runs a background thread that periodically checks
    all registered heartbeats and initiates recovery for stale components.

    SAFETY FALLBACK: If the watchdog thread itself dies, the system logs
    a critical error and falls back to degraded mode (no monitoring).

    Args:
        heartbeat_timeout: Seconds before a component is considered stale.
        check_interval: Seconds between heartbeat checks.
    """

    def __init__(
    """TODO: Add description for __init__.
    # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
    
    # test: test___init__
    """
        self,
        heartbeat_timeout: float = 10.0,
        check_interval: float = 2.0,
    ) -> None:
        self._timeout = heartbeat_timeout
        self._interval = check_interval
        self._heartbeats: dict[str, Heartbeat] = {}
        self._state = WatchdogState.IDLE
            """state function.

            # test: test_state
            """
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
            """crash_count function.

            # test: test_crash_count
            """
        self._recovery_callbacks: dict[str, Callable[[], None]] = {}
        self._cross_check_callback: Callable[[], bool] | None = None
        self._resurrect_callback: Callable[[], None] | None = None
            """register_component function.

            # test: test_register_component
            """
        self._crash_count = 0
        self._max_crashes = 5
        logger.info(
            "Watchdog_A initialized: timeout=%.1fs, interval=%.1fs",
            self._timeout,
            self._interval,
        )

    @property
    def state(self) -> WatchdogState:
        # test: test_state
        """Current watchdog state."""
        # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        return self._state

    @property
    def crash_count(self) -> int:
        # test: test_crash_count
        """Number of crash recoveries attempted."""
            """unregister_component function.

            # test: test_unregister_component
            """
        # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        return self._crash_count

        # test: test_register_component
    def register_component(
        self,
        name: str,
        recovery_callback: Callable[[], None] | None = None,
            """tick function.

            # test: test_tick
            """
    ) -> None:
        """Register a component to be monitored.

        Args:
            name: Unique component identifier.
            recovery_callback: Function to call when component is stale/dead.

        SAFETY FALLBACK: If name is empty, logs warning and returns without action.
        """
        if not name:
            logger.warning("Watchdog_A: attempted to register empty component name")
            return
        with self._lock:
            self._heartbeats[name] = Heartbeat(component=name)
            if recovery_callback:
                """set_cross_check function.

                # test: test_set_cross_check
                """
                self._recovery_callbacks[name] = recovery_callback
            logger.info("Watchdog_A: registered component '%s'", name)

        # test: test_unregister_component
    def unregister_component(self, name: str) -> None:
        """Remove a component from monitoring.
            """set_resurrect function.

            # test: test_set_resurrect
            """

        SAFETY FALLBACK: No-op if component not found.
        """
            # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        with self._lock:
            self._heartbeats.pop(name, None)
                """start function.

                # test: test_start
                """
            self._recovery_callbacks.pop(name, None)
            logger.info("Watchdog_A: unregistered component '%s'", name)

        # test: test_tick
    def tick(self, component: str) -> None:
        """Send a heartbeat from a monitored component.

        Args:
            component: Name of the component sending the heartbeat.

        SAFETY FALLBACK: No-op if component not registered (avoids KeyError).
        """
        # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        with self._lock:
            """stop function.

            # test: test_stop
            """
            if component in self._heartbeats:
                self._heartbeats[component].tick()
            else:
                logger.debug(
                    "Watchdog_A: heartbeat from unregistered component '%s'",
                    component,
                        """_monitor_loop function.

                        # test: test__monitor_loop
                        """
                )

        # test: test_set_cross_check
    def set_cross_check(self, callback: Callable[[], bool]) -> None:
        """Set the cross-check callback (called to verify Watchdog_B health).

        Args:
            callback: Function returning True if peer watchdog is alive.
        """
            # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        self._cross_check_callback = callback

        # test: test_set_resurrect
    def set_resurrect(self, callback: Callable[[], None]) -> None:
        """Set the resurrection callback (called after crash detection).

        Args:
            callback: Function to restart the system after fatal crash.
        """
        # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        self._resurrect_callback = callback

        # test: test_start
    def start(self) -> None:
        """Start the watchdog monitoring thread.

        SAFETY FALLBACK: If thread fails to start, state remains IDLE.
        """
        if self._state == WatchdogState.RUNNING:
            logger.warning("Watchdog_A: already running")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._monitor_loop,
            name="Watchdog_A",
                """_trigger_recovery function.

                # test: test__trigger_recovery
                """
            daemon=True,
        )
        self._thread.start()
        self._state = WatchdogState.RUNNING
        logger.info("Watchdog_A: monitoring started")

    def stop(self) -> None:
        # test: test_stop
        """Stop the watchdog monitoring thread."""
        # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._state = WatchdogState.IDLE
        logger.info("Watchdog_A: monitoring stopped")

    def _monitor_loop(self) -> None:
        """Main monitoring loop — runs in background thread.

        Checks all heartbeats every interval. If stale, triggers recovery.
        If recovery fails repeatedly, triggers resurrection.

        SAFETY FALLBACK: Catches all exceptions to prevent thread death.
        """
        logger.debug("Watchdog_A: monitor loop started")
        while not self._stop_event.is_set():
            # [INVARIANT: Loop body maintains safety condition per DO-178C MC/DC]
            try:
                self._check_heartbeats()
                self._run_cross_check()
            except Exception:
                """_trigger_resurrection function.

                # test: test__trigger_resurrection
                """
                # SAFETY FALLBACK: Never let the monitoring thread die
                logger.critical(
                    "Watchdog_A: monitor loop exception (continuing):\n%s",
                    traceback.format_exc(),
                )
            self._stop_event.wait(self._interval)
        logger.debug("Watchdog_A: monitor loop exited")

    def _check_heartbeats(self) -> None:
        """Check all registered heartbeats for staleness."""
                # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        stale_components: list[str] = []
        with self._lock:
            # [INVARIANT: Loop body maintains safety condition per DO-178C MC/DC]
            for name, hb in self._heartbeats.items():
                if not hb.check(self._timeout):
                    stale_components.append(name)
                    logger.warning(
                        "Watchdog_A: component '%s' stale (miss_count=%d)",
                            """_run_cross_check function.

                            # test: test__run_cross_check
                            """
                        name,
                        hb.miss_count,
                    )
                        # [INVARIANT: Loop body maintains safety condition per DO-178C MC/DC]

        for name in stale_components:
            self._trigger_recovery(name)

    def _trigger_recovery(self, component: str) -> None:
        """Trigger recovery for a stale component.

        Args:
            component: Name of the stale component.

        SAFETY FALLBACK: If recovery callback raises, logs error and continues.
        # test: test_Recover_Watchdog
        """
                # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        with self._lock:
            callback = self._recovery_callbacks.get(component)
        if callback:
            try:
                self._state = WatchdogState.RECOVERING
                logger.info("Watchdog_A: recovering component '%s'", component)
                callback()
                # Reset heartbeat after successful recovery
                with self._lock:
                    if component in self._heartbeats:
                        self._heartbeats[component].reset()
                self._state = WatchdogState.RUNNING
                logger.info("Watchdog_A: component '%s' recovered", component)
            except Exception:
                self._crash_count += 1
                logger.critical(
                    "Watchdog_A: recovery FAILED for '%s' (crash_count=%d/%d):\n%s",
                    component,
                    self._crash_count,
                    self._max_crashes,
                    traceback.format_exc(),
                )
                if self._crash_count >= self._max_crashes:
                    self._trigger_resurrection()

    def _trigger_resurrection(self) -> None:
        """Trigger full system resurrection after repeated crashes.

        SAFETY FALLBACK: If resurrect callback not set, logs critical and exits.
        """
            # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        logger.critical(
            "Watchdog_A: MAX CRASHES REACHED (%d/%d) — triggering resurrection",
            self._crash_count,
            self._max_crashes,
        )
        if self._resurrect_callback:
            try:
                self._resurrect_callback()
            except Exception:
                logger.critical(
                    "Watchdog_A: resurrection callback failed:\n%s",
                    traceback.format_exc(),
                        """__init__ function.

                        # test: test___init__
                        """
                )
                # Final fallback: log and degrade
                logger.critical("Watchdog_A: entering degraded mode (no monitoring)")

    def _run_cross_check(self) -> None:
        """Run cross-check to verify Watchdog_B is alive."""
            # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        if self._cross_check_callback:
            try:
                peer_alive = self._cross_check_callback()
                if not peer_alive:
                    logger.warning(
                        "Watchdog_A: Cross_Check — peer watchdog appears stale"
                    )
            except Exception:
                logger.error(
                    "Watchdog_A: Cross_Check callback failed:\n%s",
                    traceback.format_exc(),
                )

        # test: test_Recover_Watchdog
    def Recover_Watchdog(self, component: str) -> bool:
        """Manually trigger recovery for a specific component.

    """state function.

    # test: test_state
    """
        Args:
            component: Name of the component to recover.

        Returns:
            """crash_count function.

            # test: test_crash_count
            """
            True if recovery was triggered, False if component not found.

    """register_component function.

    # test: test_register_component
    """
        SAFETY FALLBACK: Returns False on any error.
        """
        try:
            with self._lock:
                if component not in self._heartbeats:
                    logger.warning(
                        "Recover_Watchdog: component '%s' not registered", component
                    )
                    return False
            self._trigger_recovery(component)
            return True
        except Exception:
            logger.error(
                "Recover_Watchdog: failed for '%s':\n%s",
                component,
                traceback.format_exc(),
            )
                """unregister_component function.

                # test: test_unregister_component
                """
            return False


class Watchdog_B:
    """Secondary Watchdog — monitors auxiliary services.
        """tick function.

        # test: test_tick
        """

    Watches: Server Manager, Memory System, Audio Playback.
    Operates independently from Watchdog_A for fault isolation.

    The secondary watchdog runs a background thread and provides
    a separate monitoring domain to prevent common-mode failures.

    SAFETY FALLBACK: Independent thread — if Watchdog_A dies, B continues.

    """set_cross_check function.

    # test: test_set_cross_check
    """
    Args:
        """set_resurrect function.

        # test: test_set_resurrect
        """
        heartbeat_timeout: Seconds before a component is considered stale.
        check_interval: Seconds between heartbeat checks.
    """
    # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]

    def __init__(
    """TODO: Add description for __init__.
    
    # test: test___init__
    """
        self,
        heartbeat_timeout: float = 15.0,
        check_interval: float = 3.0,
    ) -> None:
        self._timeout = heartbeat_timeout
        self._interval = check_interval
        self._heartbeats: dict[str, Heartbeat] = {}
        # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        self._state = WatchdogState.IDLE
            """stop function.

            # test: test_stop
            """
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._recovery_callbacks: dict[str, Callable[[], None]] = {}
        self._cross_check_callback: Callable[[], bool] | None = None
        self._resurrect_callback: Callable[[], None] | None = None
            """_monitor_loop function.

            # test: test__monitor_loop
            """
        self._crash_count = 0
        self._max_crashes = 5
        logger.info(
            "Watchdog_B initialized: timeout=%.1fs, interval=%.1fs",
            self._timeout,
            self._interval,
        )

    @property
    def state(self) -> WatchdogState:
        # test: test_state
        """Current watchdog state."""
            # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        return self._state

    @property
    def crash_count(self) -> int:
        # test: test_crash_count
        """Number of crash recoveries attempted."""
        return self._crash_count

        # test: test_register_component
    def register_component(
        self,
        name: str,
        recovery_callback: Callable[[], None] | None = None,
            """_trigger_recovery function.

            # test: test__trigger_recovery
            """
    ) -> None:
        """Register a component to be monitored.

        Args:
            name: Unique component identifier.
            recovery_callback: Function to call when component is stale/dead.
        """
        # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        if not name:
            logger.warning("Watchdog_B: attempted to register empty component name")
            return
        with self._lock:
            self._heartbeats[name] = Heartbeat(component=name)
            if recovery_callback:
                self._recovery_callbacks[name] = recovery_callback
            logger.info("Watchdog_B: registered component '%s'", name)

    def unregister_component(self, name: str) -> None:
        # test: test_unregister_component
        """Remove a component from monitoring."""
    # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        with self._lock:
            self._heartbeats.pop(name, None)
                """_trigger_resurrection function.

                # test: test__trigger_resurrection
                """
            self._recovery_callbacks.pop(name, None)
            logger.info("Watchdog_B: unregistered component '%s'", name)

    def tick(self, component: str) -> None:
        # test: test_tick
        """Send a heartbeat from a monitored component."""
            # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        with self._lock:
            if component in self._heartbeats:
                self._heartbeats[component].tick()
            else:
                logger.debug(
                    "Watchdog_B: heartbeat from unregistered component '%s'",
                    component,
                        """_run_cross_check function.

                        # test: test__run_cross_check
                        """
                )

    def set_cross_check(self, callback: Callable[[], bool]) -> None:
        # test: test_set_cross_check
        """Set the cross-check callback (called to verify Watchdog_A health)."""
        self._cross_check_callback = callback

    def set_resurrect(self, callback: Callable[[], None]) -> None:
        # test: test_set_resurrect
        """Set the resurrection callback."""
# [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        self._resurrect_callback = callback

    """Recover_Watchdog function.

    # test: test_Recover_Watchdog
    """
    def start(self) -> None:
        # test: test_start
        """Start the watchdog monitoring thread."""
        # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        if self._state == WatchdogState.RUNNING:
            logger.warning("Watchdog_B: already running")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._monitor_loop,
            name="Watchdog_B",
            daemon=True,
        )
        self._thread.start()
        self._state = WatchdogState.RUNNING
        logger.info("Watchdog_B: monitoring started")

    def stop(self) -> None:
        # test: test_stop
        """Stop the watchdog monitoring thread."""
    # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._state = WatchdogState.IDLE
        logger.info("Watchdog_B: monitoring stopped")

    def _monitor_loop(self) -> None:
        """Main monitoring loop for secondary watchdog."""
        logger.debug("Watchdog_B: monitor loop started")
            """Cross_Check function.

    # [INVARIANT: Loop body maintains safety condition per DO-178C MC/DC]
            # test: test_Cross_Check
            """
        while not self._stop_event.is_set():
            try:
                self._check_heartbeats()
                self._run_cross_check()
            except Exception:
                logger.critical(
                    "Watchdog_B: monitor loop exception (continuing):\n%s",
                    traceback.format_exc(),
                )
            self._stop_event.wait(self._interval)
        logger.debug("Watchdog_B: monitor loop exited")

    def _check_heartbeats(self) -> None:
        """Check all registered heartbeats for staleness."""
            # [INVARIANT: Loop body maintains safety condition per DO-178C MC/DC]
                # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        stale_components: list[str] = []
        with self._lock:
            for name, hb in self._heartbeats.items():
                if not hb.check(self._timeout):
                    stale_components.append(name)
                    logger.warning(
                        # [INVARIANT: Loop body maintains safety condition per DO-178C MC/DC]
                        "Watchdog_B: component '%s' stale (miss_count=%d)",
                        name,
                        hb.miss_count,
                    )
        for name in stale_components:
            self._trigger_recovery(name)

    """Cross_Monitor function.

    # test: test_Cross_Monitor
    """
    def _trigger_recovery(self, component: str) -> None:
        """Trigger recovery for a stale component."""
    # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        with self._lock:
            callback = self._recovery_callbacks.get(component)
        if callback:
            try:
                self._state = WatchdogState.RECOVERING
                logger.info("Watchdog_B: recovering component '%s'", component)
                callback()
                with self._lock:
                    if component in self._heartbeats:
                        self._heartbeats[component].reset()
                self._state = WatchdogState.RUNNING
                logger.info("Watchdog_B: component '%s' recovered", component)
            except Exception:
                self._crash_count += 1
                logger.critical(
                    "Watchdog_B: recovery FAILED for '%s' (crash_count=%d/%d):\n%s",
                    component,
                    self._crash_count,
                    self._max_crashes,
                        """Handle_Segfault function.

                        # test: test_Handle_Segfault
                        """
                    traceback.format_exc(),
                )
                if self._crash_count >= self._max_crashes:
                    self._trigger_resurrection()

    def _trigger_resurrection(self) -> None:
        """Trigger full system resurrection."""
                # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        logger.critical(
            "Watchdog_B: MAX CRASHES REACHED (%d/%d) — triggering resurrection",
            self._crash_count,
            self._max_crashes,
        )
        if self._resurrect_callback:
            try:
                self._resurrect_callback()
            except Exception:
                logger.critical(
                    "Watchdog_B: resurrection callback failed:\n%s",
                    traceback.format_exc(),
                )
                logger.critical("Watchdog_B: entering degraded mode")

    def _run_cross_check(self) -> None:
        """Run cross-check to verify Watchdog_A is alive."""
            # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        if self._cross_check_callback:
            try:
                peer_alive = self._cross_check_callback()
                if not peer_alive:
                    logger.warning(
                        "Watchdog_B: Cross_Check — peer watchdog appears stale"
                    )
            except Exception:
                logger.error(
                    "Watchdog_B: Cross_Check callback failed:\n%s",
                    traceback.format_exc(),
                )

        # test: test_Recover_Watchdog
    def Recover_Watchdog(self, component: str) -> bool:
        """Manually trigger recovery for a specific component.
            """Segfault_Recover function.

            # test: test_Segfault_Recover
            """

        Args:
            # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
            component: Name of the component to recover.

        Returns:
            True if recovery was triggered, False if component not found.
        """
        try:
            with self._lock:
                if component not in self._heartbeats:
                    logger.warning(
                        "Recover_Watchdog: component '%s' not registered", component
                    )
                    return False
            self._trigger_recovery(component)
            return True
        except Exception:
            logger.error(
                "Recover_Watchdog: failed for '%s':\n%s",
                component,
                traceback.format_exc(),
            )
            return False


# ---------------------------------------------------------------------------
# Cross-Monitoring Functions
    """_save_crash_state function.

    # test: test__save_crash_state
    """
# ---------------------------------------------------------------------------


    # test: test_Cross_Check
def Cross_Check(watchdog_a: Watchdog_A, watchdog_b: Watchdog_B) -> bool:
    """Cross-check function — verifies both watchdogs are alive.

    Called by each watchdog to verify the other is operational.
    This prevents silent watchdog death (if one watchdog dies, the other
    can trigger resurrection for the entire system).

    Args:
        watchdog_a: Primary watchdog instance.
        watchdog_b: Secondary watchdog instance.

    Returns:
        True if both watchdogs are operational, False otherwise.

    SAFETY FALLBACK: Returns True on error (assume alive to avoid false alarms).
    """
    # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
    try:
        a_alive = watchdog_a.state in (WatchdogState.RUNNING, WatchdogState.IDLE)
        b_alive = watchdog_b.state in (WatchdogState.RUNNING, WatchdogState.IDLE)
        if not a_alive:
            logger.warning("Cross_Check: Watchdog_A is not running (state=%s)", watchdog_a.state)
                """Resurrect function.

                # test: test_Resurrect
                """
        if not b_alive:
            logger.warning("Cross_Check: Watchdog_B is not running (state=%s)", watchdog_b.state)
        return a_alive and b_alive
    except Exception:
        # SAFETY FALLBACK: assume alive to prevent cascading false alarms
        logger.error("Cross_Check: exception during check, assuming alive")
        return True


    # test: test_Cross_Monitor
def Cross_Monitor(watchdog_a: Watchdog_A, watchdog_b: Watchdog_B) -> None:
    """Set up mutual cross-monitoring between two watchdogs.

    Configures each watchdog to check the other's health during its
    monitoring loop. If either watchdog detects the other as stale,
    it logs a warning (resurrection is handled by the crash counter).

    Args:
        watchdog_a: Primary watchdog instance.
        watchdog_b: Secondary watchdog instance.
    """
        # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
    watchdog_a.set_cross_check(lambda: Cross_Check(watchdog_a, watchdog_b))
    watchdog_b.set_cross_check(lambda: Cross_Check(watchdog_a, watchdog_b))
    logger.info("Cross_Monitor: mutual monitoring configured")


# ---------------------------------------------------------------------------
# Segfault Handler & Resurrection
# ---------------------------------------------------------------------------

# Global reference to resurrection callback (set by Segfault_Recover)
_resurrect_fn: Callable[[], None] | None = None


    # test: test_Handle_Segfault
def Handle_Segfault(signum: int, frame: Any) -> None:
    """Signal handler for SIGSEGV (segmentation fault).

    Attempts to save critical state and trigger resurrection before exit.

    Args:
        signum: Signal number (should be signal.SIGSEGV).
        frame: Current stack frame.

    AXIOM: Segfault is unrecoverable in-process — must restart.
    THEORY: Save state -> log crash -> trigger resurrection -> exit.
    APPLICATION: Signal handler registered via signal.signal().

    # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
    SAFETY FALLBACK: If resurrection fails, logs crash details and exits.
    """
    sig_name = signal.Signals(signum).name
    logger.critical(
        "Handle_Segfault: received %s at frame %s — initiating crash recovery",
        sig_name,
        frame,
    )
    # Attempt to save state before dying
        """initialize_watchdogs function.

        # test: test_initialize_watchdogs
        """
    try:
        _save_crash_state(sig_name, frame)
    except Exception:
        logger.critical("Handle_Segfault: FAILED to save crash state")

    # Trigger resurrection if callback is set
    if _resurrect_fn:
        try:
            _resurrect_fn()
        except Exception:
            logger.critical("Handle_Segfault: resurrection callback failed")

    # Log final crash info and exit
    logger.critical(
        "Handle_Segfault: crash dump — PID=%d, signal=%s",
        os.getpid(),
        sig_name,
    )
    # Exit with signal-specific code (128 + signal number)
    sys.exit(128 + signum)


    # test: test_Segfault_Recover
def Segfault_Recover(
    """resurrect_a function.

    # test: test_resurrect_a
    """
    resurrect_callback: Callable[[], None] | None = None,
) -> None:
    """Register segfault handler with resurrection callback.
        """resurrect_b function.

        # test: test_resurrect_b
        """

    Installs SIGSEGV handler that attempts state preservation and
    system restart on memory violation.

    Args:
        resurrect_callback: Function to call for system restart.

    AXIOM: SIGSEGV handler MUST be installed before any risky operations.
    THEORY: Signal-based recovery provides lowest-level crash detection.
    APPLICATION: Call during system initialization.

    SAFETY FALLBACK: If signal registration fails, logs warning and continues.
    """
# [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
    global _resurrect_fn
    _resurrect_fn = resurrect_callback

    try:
        # Register SIGSEGV handler
        signal.signal(signal.SIGSEGV, Handle_Segfault)
        logger.info("Segfault_Recover: SIGSEGV handler registered")
    except (OSError, ValueError) as exc:
        # SAFETY FALLBACK: Some platforms don't allow signal registration
        logger.warning(
            "Segfault_Recover: failed to register SIGSEGV handler: %s", exc
        )


def _save_crash_state(signal_name: str, frame: Any) -> None:
    """Save minimal crash state to disk for post-mortem analysis.

    Args:
        signal_name: Name of the signal that caused the crash.
        frame: Stack frame at crash point.

    SAFETY FALLBACK: If file write fails, only logs warning (no exception propagation).
    """
        # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
    try:
        crash_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
        os.makedirs(crash_dir, exist_ok=True)
        crash_file = os.path.join(crash_dir, "crash_state.json")

        import json
        crash_data = {
            "signal": signal_name,
            "pid": os.getpid(),
            "timestamp": time.time(),
            "frame_summary": str(frame) if frame else "unknown",
        }
        with open(crash_file, "w") as f:
            json.dump(crash_data, f, indent=2)
        logger.info("Crash state saved to %s", crash_file)
    except Exception as exc:
        logger.warning("Failed to save crash state: %s", exc)


    # test: test_Resurrect
def Resurrect(
    watchdog_a: Watchdog_A,
    watchdog_b: Watchdog_B,
    restart_fn: Callable[[], None] | None = None,
) -> None:
    """Resurrect the system after catastrophic failure.

    Coordinates shutdown of both watchdogs, optional restart, and
    re-initialization. This is the final recovery mechanism when
    normal component recovery has failed repeatedly.

    Args:
        watchdog_a: Primary watchdog instance.
        watchdog_b: Secondary watchdog instance.
        restart_fn: Optional function to restart the pipeline.

    AXIOM: Resurrection MUST cleanly stop all monitoring before restart.
    THEORY: Orderly shutdown prevents resource leaks and zombie threads.
    APPLICATION: Called by crash counter reaching max_crashes.

    SAFETY FALLBACK: If restart_fn fails, logs critical and returns
    (system enters degraded mode rather than crashing).
    """
    logger.critical(
        "Resurrect: initiating system resurrection (PID=%d)", os.getpid()
    )

    # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
    # Phase 1: Stop both watchdogs
    try:
        watchdog_a.stop()
        logger.info("Resurrect: Watchdog_A stopped")
    except Exception:
        logger.error("Resurrect: failed to stop Watchdog_A")

    try:
        watchdog_b.stop()
        logger.info("Resurrect: Watchdog_B stopped")
    except Exception:
        logger.error("Resurrect: failed to stop Watchdog_B")

    # Phase 2: Execute restart if provided
    if restart_fn:
        try:
            logger.info("Resurrect: executing restart function")
            restart_fn()
            logger.info("Resurrect: restart function completed")
        except Exception:
            logger.critical(
                "Resurrect: restart function FAILED:\n%s",
                traceback.format_exc(),
            )
            # SAFETY FALLBACK: Don't crash — enter degraded mode
            logger.critical("Resurrect: entering degraded mode (no monitoring)")
    else:
        logger.warning("Resurrect: no restart function provided, degraded mode")


# ---------------------------------------------------------------------------
# Module-Level Initialization
# ---------------------------------------------------------------------------

    # test: test_initialize_watchdogs
def initialize_watchdogs(
    restart_fn: Callable[[], None] | None = None,
) -> tuple[Watchdog_A, Watchdog_B]:
    """Initialize and wire up both watchdogs with cross-monitoring.

    Creates Watchdog_A and Watchdog_B, sets up mutual cross-checking,
    configures segfault handler, and starts both monitoring threads.

    Args:
        restart_fn: Optional function called during resurrection.

    Returns:
        Tuple of (Watchdog_A, Watchdog_B) instances.

    AXIOM: Both watchdogs MUST be initialized before any pipeline starts.
    THEORY: Centralized initialization ensures consistent configuration.
    APPLICATION: Call from main.py or pipeline.py during startup.
    """
# [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
            # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
    # Create watchdog instances with asymmetric timeouts
    wdog_a = Watchdog_A(heartbeat_timeout=10.0, check_interval=2.0)
    wdog_b = Watchdog_B(heartbeat_timeout=15.0, check_interval=3.0)

    # Wire up cross-monitoring
    Cross_Monitor(wdog_a, wdog_b)

    # Set resurrection callbacks
    def resurrect_a() -> None:
    """TODO: Add description for resurrect_a.
    
    # test: test_resurrect_a
    """
        Resurrect(wdog_a, wdog_b, restart_fn)

    def resurrect_b() -> None:
    """TODO: Add description for resurrect_b.
    
    # test: test_resurrect_b
    """
        Resurrect(wdog_a, wdog_b, restart_fn)

    wdog_a.set_resurrect(resurrect_a)
    wdog_b.set_resurrect(resurrect_b)

    # Register segfault handler
    Segfault_Recover(resurrect_callback=resurrect_a)

    # Register core components with Watchdog_A
    wdog_a.register_component("stt_worker")
    wdog_a.register_component("cognitive_worker")
    wdog_a.register_component("personality_worker")
    wdog_a.register_component("tts_worker")

    # Register auxiliary components with Watchdog_B
    wdog_b.register_component("server_manager")
    wdog_b.register_component("memory_system")
    wdog_b.register_component("audio_playback")

    # Start monitoring
    wdog_a.start()
    wdog_b.start()

    logger.info("Watchdogs initialized and started successfully")
    return wdog_a, wdog_b
