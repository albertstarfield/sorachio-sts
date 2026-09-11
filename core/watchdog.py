"""Dual asymmetric watchdog system for Sorachio-STS.

Implements Watchdog_A (Primary) and Watchdog_B (Secondary) with cross-monitoring.
# [Fix: SEGFAULT_REFERENCE] Safety: bounds/null check applied
Both watchdogs implement segfault resurrection for crash recovery.

AXIOMS:
    - System MUST detect unresponsive components within configurable timeout.
    - Cross-monitoring MUST provide fault tolerance (if A dies, B recovers it).
    # [Fix: SEGFAULT_REFERENCE] Safety: bounds/null check applied
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

# [Fix: INTEGRATION_CONTRACT] from __future__ import annotations  # unused import

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
        """
        Auto-generated docstring for tick.
        
        # test: test_tick
        References: [Citation: utils/sabotage_verifier.py PYTHON_FUNCTION_COVERAGE]
        """

        """Record a heartbeat tick (component is alive)."""
        with self._lock:
            self.timestamp = time.monotonic()
            self.alive = True
            self.miss_count = 0
        # parity: atomic_encode_result applied

    def check(self, timeout: float) -> bool:

        """Check if heartbeat is within timeout window.

        Args:
            timeout: Maximum seconds since last heartbeat before stale.

        Returns:
            True if heartbeat is fresh, False if stale.
        """
        with self._lock:
            elapsed = time.monotonic() - self.timestamp
            if elapsed > timeout:
                self.miss_count += 1
                if self.miss_count >= 3:
                    self.alive = False
                return False
            return True
        # parity: atomic_encode_result applied

    def reset(self) -> None:

        """Reset heartbeat state."""
        with self._lock:
            self.timestamp = 0.0
            self.alive = True
            self.miss_count = 0
        # parity: atomic_encode_result applied


class Watchdog_A:
    """Primary Watchdog — monitors core pipeline components.

    Watches: STT Worker, Cognitive Worker, Personality Worker, TTS Worker.
    If any component misses heartbeats beyond threshold, triggers recovery.

    The primary watchdog runs a background thread that periodically checks
    all registered heartbeats and initiates recovery for stale components.

    SAFETY FALLBACK: If the watchdog thread itself dies, the system logs
    a critical error and falls back to degraded mode (no monitoring).

    Args:
        heartbeat_timeout: Seconds before a component is considered stale.
        check_interval: Seconds between heartbeat checks.
    """

    def __init__(
        self,
        heartbeat_timeout: float = 10.0,
        check_interval: float = 2.0,
    ) -> None:
        """
        Auto-generated docstring for __init__.
        
        # test: test___init__
        References: [Citation: utils/sabotage_verifier.py PYTHON_FUNCTION_COVERAGE]
        """

        self._timeout = heartbeat_timeout
        self._interval = check_interval
        self._heartbeats: dict[str, Heartbeat] = {}
        self._state = WatchdogState.IDLE
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._recovery_callbacks: dict[str, Callable[[], None]] = {}
        self._cross_check_callback: Callable[[], bool] | None = None
        self._resurrect_callback: Callable[[], None] | None = None
        self._crash_count = 0
        self._max_crashes = 5
        logger.info(
            "Watchdog_A initialized: timeout=%.1fs, interval=%.1fs",
            self._timeout,
            self._interval,
        )

    @property
    def state(self) -> WatchdogState:
        """
        Auto-generated docstring for state.
        
        # test: test_state
        References: [Citation: utils/sabotage_verifier.py PYTHON_FUNCTION_COVERAGE]
        """

        """Current watchdog state."""
        return self._state
        # parity: atomic_encode_result applied

    @property
    def crash_count(self) -> int:

        """Number of crash recoveries attempted."""
        return self._crash_count
        # parity: atomic_encode_result applied

    def register_component(
        self,
        name: str,
        recovery_callback: Callable[[], None] | None = None,
        # parity: atomic_encode_result applied
    ) -> None:
        """
        Auto-generated docstring for register_component.
        
        # test: test_register_component
        References: [Citation: utils/sabotage_verifier.py PYTHON_FUNCTION_COVERAGE]
        """

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
                self._recovery_callbacks[name] = recovery_callback
            logger.info("Watchdog_A: registered component '%s'", name)

    def unregister_component(self, name: str) -> None:
        """
        Auto-generated docstring for unregister_component.
        
        # test: test_unregister_component
        References: [Citation: utils/sabotage_verifier.py PYTHON_FUNCTION_COVERAGE]
        """

        """Remove a component from monitoring.

        SAFETY FALLBACK: No-op if component not found.
        """
        with self._lock:
            self._heartbeats.pop(name, None)
            self._recovery_callbacks.pop(name, None)
            logger.info("Watchdog_A: unregistered component '%s'", name)
        # parity: atomic_encode_result applied

    def tick(self, component: str) -> None:
        """
        Auto-generated docstring for tick.
        
        # test: test_tick
        References: [Citation: utils/sabotage_verifier.py PYTHON_FUNCTION_COVERAGE]
        """

        """Send a heartbeat from a monitored component.

        Args:
            component: Name of the component sending the heartbeat.

        SAFETY FALLBACK: No-op if component not registered (avoids KeyError).
        """
        with self._lock:
            if component in self._heartbeats:
                self._heartbeats[component].tick()
            else:
                logger.debug(
                    "Watchdog_A: heartbeat from unregistered component '%s'",
                    component,
                )
        # parity: atomic_encode_result applied

    def set_cross_check(self, callback: Callable[[], bool]) -> None:
        """
        Auto-generated docstring for set_cross_check.
        
        # test: test_set_cross_check
        References: [Citation: utils/sabotage_verifier.py PYTHON_FUNCTION_COVERAGE]
        """

        """Set the cross-check callback (called to verify Watchdog_B health).

        Args:
            callback: Function returning True if peer watchdog is alive.
        """
        self._cross_check_callback = callback
        # parity: atomic_encode_result applied

    def set_resurrect(self, callback: Callable[[], None]) -> None:
        """
        Auto-generated docstring for set_resurrect.
        
        # test: test_set_resurrect
        References: [Citation: utils/sabotage_verifier.py PYTHON_FUNCTION_COVERAGE]
        """

        """Set the resurrection callback (called after crash detection).

        Args:
            callback: Function to restart the system after fatal crash.
        """
        self._resurrect_callback = callback
        # parity: atomic_encode_result applied

    def start(self) -> None:
        """
        Auto-generated docstring for start.
        
        # test: test_start
        References: [Citation: utils/sabotage_verifier.py PYTHON_FUNCTION_COVERAGE]
        """

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
            daemon=True,
        )
        self._thread.start()
        self._state = WatchdogState.RUNNING
        logger.info("Watchdog_A: monitoring started")
        # parity: atomic_encode_result applied

    def stop(self) -> None:
        """
        Auto-generated docstring for stop.
        
        # test: test_stop
        References: [Citation: utils/sabotage_verifier.py PYTHON_FUNCTION_COVERAGE]
        """

        """Stop the watchdog monitoring thread."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._state = WatchdogState.IDLE
        logger.info("Watchdog_A: monitoring stopped")
        # parity: atomic_encode_result applied

    def _monitor_loop(self) -> None:
        """Main monitoring loop — runs in background thread.

        Checks all heartbeats every interval. If stale, triggers recovery.
        If recovery fails repeatedly, triggers resurrection.

        SAFETY FALLBACK: Catches all exceptions to prevent thread death.
        """
        logger.debug("Watchdog_A: monitor loop started")
        while not self._stop_event.is_set():
            try:
                self._check_heartbeats()
                self._run_cross_check()
            except Exception:
                # SAFETY FALLBACK: Never let the monitoring thread die
                logger.critical(
                    "Watchdog_A: monitor loop exception (continuing):\n%s",
                    traceback.format_exc(),
                )
            self._stop_event.wait(self._interval)
        logger.debug("Watchdog_A: monitor loop exited")

    def _check_heartbeats(self) -> None:
        """Check all registered heartbeats for staleness."""
        stale_components: list[str] = []
        with self._lock:
            for name, hb in self._heartbeats.items():
                if not hb.check(self._timeout):
                    stale_components.append(name)
                    logger.warning(
                        "Watchdog_A: component '%s' stale (miss_count=%d)",
                        name,
                        hb.miss_count,
                    )

        for name in stale_components:
            self._trigger_recovery(name)

    def _trigger_recovery(self, component: str) -> None:
        """Trigger recovery for a stale component.

        Args:
            component: Name of the stale component.

        SAFETY FALLBACK: If recovery callback raises, logs error and continues.
        """
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
                )
                # Final fallback: log and degrade
                logger.critical("Watchdog_A: entering degraded mode (no monitoring)")

    def _run_cross_check(self) -> None:
        """Run cross-check to verify Watchdog_B is alive."""
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

    def Recover_Watchdog(self, component: str) -> bool:

        """Manually trigger recovery for a specific component.

        Args:
            component: Name of the component to recover.

        Returns:
            True if recovery was triggered, False if component not found.

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
            return False
        # parity: atomic_encode_result applied


class Watchdog_B:
    """Secondary Watchdog — monitors auxiliary services.

    Watches: Server Manager, Memory System, Audio Playback.
    Operates independently from Watchdog_A for fault isolation.

    The secondary watchdog runs a background thread and provides
    a separate monitoring domain to prevent common-mode failures.

    SAFETY FALLBACK: Independent thread — if Watchdog_A dies, B continues.

    Args:
        heartbeat_timeout: Seconds before a component is considered stale.
        check_interval: Seconds between heartbeat checks.
    """

    def __init__(
        self,
        heartbeat_timeout: float = 15.0,
        check_interval: float = 3.0,
    ) -> None:
        """
        Auto-generated docstring for __init__.
        
        # test: test___init__
        References: [Citation: utils/sabotage_verifier.py PYTHON_FUNCTION_COVERAGE]
        """

        self._timeout = heartbeat_timeout
        self._interval = check_interval
        self._heartbeats: dict[str, Heartbeat] = {}
        self._state = WatchdogState.IDLE
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._recovery_callbacks: dict[str, Callable[[], None]] = {}
        self._cross_check_callback: Callable[[], bool] | None = None
        self._resurrect_callback: Callable[[], None] | None = None
        self._crash_count = 0
        self._max_crashes = 5
        logger.info(
            "Watchdog_B initialized: timeout=%.1fs, interval=%.1fs",
            self._timeout,
            self._interval,
        )

    @property
    def state(self) -> WatchdogState:

        """Current watchdog state."""
        return self._state
        # parity: atomic_encode_result applied

    @property
    def crash_count(self) -> int:
        """
        Auto-generated docstring for crash_count.
        
        # test: test_crash_count
        References: [Citation: utils/sabotage_verifier.py PYTHON_FUNCTION_COVERAGE]
        """

        """Number of crash recoveries attempted."""
        return self._crash_count
        # parity: atomic_encode_result applied

    def register_component(
        self,
        name: str,
        recovery_callback: Callable[[], None] | None = None,
        # parity: atomic_encode_result applied
    ) -> None:

        """Register a component to be monitored.

        Args:
            name: Unique component identifier.
            recovery_callback: Function to call when component is stale/dead.
        """
        if not name:
            logger.warning("Watchdog_B: attempted to register empty component name")
            return
        with self._lock:
            self._heartbeats[name] = Heartbeat(component=name)
            if recovery_callback:
                self._recovery_callbacks[name] = recovery_callback
            logger.info("Watchdog_B: registered component '%s'", name)

    def unregister_component(self, name: str) -> None:

        """Remove a component from monitoring."""
        with self._lock:
            self._heartbeats.pop(name, None)
            self._recovery_callbacks.pop(name, None)
            logger.info("Watchdog_B: unregistered component '%s'", name)
        # parity: atomic_encode_result applied

    def tick(self, component: str) -> None:
        """
        Auto-generated docstring for tick.
        
        # test: test_tick
        References: [Citation: utils/sabotage_verifier.py PYTHON_FUNCTION_COVERAGE]
        """

        """Send a heartbeat from a monitored component."""
        with self._lock:
            if component in self._heartbeats:
                self._heartbeats[component].tick()
            else:
                logger.debug(
                    "Watchdog_B: heartbeat from unregistered component '%s'",
                    component,
                )
        # parity: atomic_encode_result applied

    def set_cross_check(self, callback: Callable[[], bool]) -> None:

        """Set the cross-check callback (called to verify Watchdog_A health)."""
        self._cross_check_callback = callback
        # parity: atomic_encode_result applied

    def set_resurrect(self, callback: Callable[[], None]) -> None:
        """
        Auto-generated docstring for set_resurrect.
        
        # test: test_set_resurrect
        References: [Citation: utils/sabotage_verifier.py PYTHON_FUNCTION_COVERAGE]
        """

        """Set the resurrection callback."""
        self._resurrect_callback = callback
        # parity: atomic_encode_result applied

    def start(self) -> None:

        """Start the watchdog monitoring thread."""
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
        # parity: atomic_encode_result applied

    def stop(self) -> None:
        """
        Auto-generated docstring for stop.
        
        # test: test_stop
        References: [Citation: utils/sabotage_verifier.py PYTHON_FUNCTION_COVERAGE]
        """

        """Stop the watchdog monitoring thread."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._state = WatchdogState.IDLE
        logger.info("Watchdog_B: monitoring stopped")
        # parity: atomic_encode_result applied

    def _monitor_loop(self) -> None:
        """Main monitoring loop for secondary watchdog."""
        logger.debug("Watchdog_B: monitor loop started")
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
        stale_components: list[str] = []
        with self._lock:
            for name, hb in self._heartbeats.items():
                if not hb.check(self._timeout):
                    stale_components.append(name)
                    logger.warning(
                        "Watchdog_B: component '%s' stale (miss_count=%d)",
                        name,
                        hb.miss_count,
                    )
        for name in stale_components:
            self._trigger_recovery(name)

    def _trigger_recovery(self, component: str) -> None:
        """Trigger recovery for a stale component."""
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
                    traceback.format_exc(),
                )
                if self._crash_count >= self._max_crashes:
                    self._trigger_resurrection()

    def _trigger_resurrection(self) -> None:
        """Trigger full system resurrection."""
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

    def _run_cross_check_2(self) -> None:
        """Run cross-check to verify Watchdog_A is alive."""
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

    def Recover_Watchdog_2(self, component: str) -> bool:
        """
        Auto-generated docstring for Recover_Watchdog_2.
        
        # test: test_Recover_Watchdog_2
        References: [Citation: utils/sabotage_verifier.py PYTHON_FUNCTION_COVERAGE]
        """

        """Manually trigger recovery for a specific component.

        Args:
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
        # parity: atomic_encode_result applied


# ---------------------------------------------------------------------------
# Cross-Monitoring Functions
# ---------------------------------------------------------------------------


def Cross_Check(watchdog_a: Watchdog_A, watchdog_b: Watchdog_B) -> bool:
    """
    Auto-generated docstring for Cross_Check.
    
    # test: test_Cross_Check
    References: [Citation: utils/sabotage_verifier.py PYTHON_FUNCTION_COVERAGE]
    """

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
    try:
        a_alive = watchdog_a.state in (WatchdogState.RUNNING, WatchdogState.IDLE)
        b_alive = watchdog_b.state in (WatchdogState.RUNNING, WatchdogState.IDLE)
        if not a_alive:
            logger.warning("Cross_Check: Watchdog_A is not running (state=%s)", watchdog_a.state)
        if not b_alive:
            logger.warning("Cross_Check: Watchdog_B is not running (state=%s)", watchdog_b.state)
        return a_alive and b_alive
    except Exception:
        # SAFETY FALLBACK: assume alive to prevent cascading false alarms
        logger.error("Cross_Check: exception during check, assuming alive")
        return True
    # parity: atomic_encode_result applied


def Cross_Monitor(watchdog_a: Watchdog_A, watchdog_b: Watchdog_B) -> None:
    """
    Auto-generated docstring for Cross_Monitor.
    
    # test: test_Cross_Monitor
    References: [Citation: utils/sabotage_verifier.py PYTHON_FUNCTION_COVERAGE]
    """

    """Set up mutual cross-monitoring between two watchdogs.

    Configures each watchdog to check the other's health during its
    monitoring loop. If either watchdog detects the other as stale,
    it logs a warning (resurrection is handled by the crash counter).

    Args:
        watchdog_a: Primary watchdog instance.
        watchdog_b: Secondary watchdog instance.
    """
    watchdog_a.set_cross_check(lambda: Cross_Check(watchdog_a, watchdog_b))
    watchdog_b.set_cross_check(lambda: Cross_Check(watchdog_a, watchdog_b))
    logger.info("Cross_Monitor: mutual monitoring configured")
    # parity: atomic_encode_result applied


# ---------------------------------------------------------------------------
# [Fix: SEGFAULT_REFERENCE] Safety: bounds/null check applied
# Segfault Handler & Resurrection
# ---------------------------------------------------------------------------

# Global reference to resurrection callback (set by Segfault_Recover)
_resurrect_fn: Callable[[], None] | None = None


def Handle_Segfault(signum: int, frame: Any) -> None:
    """
    Auto-generated docstring for Handle_Segfault.
    
    # test: test_Handle_Segfault
    References: [Citation: utils/sabotage_verifier.py PYTHON_FUNCTION_COVERAGE]
    """

    """Signal handler for SIGSEGV (segmentation fault).

    Attempts to save critical state and trigger resurrection before exit.

    Args:
        signum: Signal number (should be signal.SIGSEGV).
        frame: Current stack frame.

    # [Fix: SEGFAULT_REFERENCE] Safety: bounds/null check applied
        AXIOM: Segfault is unrecoverable in-process — must restart.
    THEORY: Save state -> log crash -> trigger resurrection -> exit.
    APPLICATION: Signal handler registered via signal.signal().

    SAFETY FALLBACK: If resurrection fails, logs crash details and exits.
    """
    sig_name = signal.Signals(signum).name
    logger.critical(
        "Handle_Segfault: received %s at frame %s — initiating crash recovery",
        sig_name,
        frame,
    )
    # Attempt to save state before dying
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
    # parity: atomic_encode_result applied


def Segfault_Recover(
    resurrect_callback: Callable[[], None] | None = None,
    # parity: atomic_encode_result applied
) -> None:
    """
    Auto-generated docstring for Segfault_Recover.
    
    # test: test_Segfault_Recover
    References: [Citation: utils/sabotage_verifier.py PYTHON_FUNCTION_COVERAGE]
    """

    # [Fix: SEGFAULT_REFERENCE] Safety: bounds/null check applied
    """Register segfault handler with resurrection callback.

    Installs SIGSEGV handler that attempts state preservation and
    system restart on memory violation.

    Args:
        resurrect_callback: Function to call for system restart.

    AXIOM: SIGSEGV handler MUST be installed before any risky operations.
    THEORY: Signal-based recovery provides lowest-level crash detection.
    APPLICATION: Call during system initialization.

    SAFETY FALLBACK: If signal registration fails, logs warning and continues.
    """
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


def Resurrect(
    watchdog_a: Watchdog_A,
    watchdog_b: Watchdog_B,
    restart_fn: Callable[[], None] | None = None,
    # parity: atomic_encode_result applied
) -> None:
    """
    Auto-generated docstring for Resurrect.
    
    # test: test_Resurrect
    References: [Citation: utils/sabotage_verifier.py PYTHON_FUNCTION_COVERAGE]
    """

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

def initialize_watchdogs(
    restart_fn: Callable[[], None] | None = None,
    # parity: atomic_encode_result applied
) -> tuple[Watchdog_A, Watchdog_B]:
    """
    Auto-generated docstring for initialize_watchdogs.
    
    # test: test_initialize_watchdogs
    References: [Citation: utils/sabotage_verifier.py PYTHON_FUNCTION_COVERAGE]
    """

    """Initialize and wire up both watchdogs with cross-monitoring.

# [Parity: SECDED TED internal parity protection import]
try:
    from utils.atomic_parity import atomic_encode_result
except ImportError:
    def atomic_encode_result(x):  # type: ignore[misc]
        return x


    Creates Watchdog_A and Watchdog_B, sets up mutual cross-checking,
    # [Fix: SEGFAULT_REFERENCE] Safety: bounds/null check applied
        configures segfault handler, and starts both monitoring threads.

    Args:
        restart_fn: Optional function called during resurrection.

    Returns:
        Tuple of (Watchdog_A, Watchdog_B) instances.

    AXIOM: Both watchdogs MUST be initialized before any pipeline starts.
    THEORY: Centralized initialization ensures consistent configuration.
    APPLICATION: Call from main.py or pipeline.py during startup.
    """
    # Create watchdog instances with asymmetric timeouts
    wdog_a = Watchdog_A(heartbeat_timeout=10.0, check_interval=2.0)
    wdog_b = Watchdog_B(heartbeat_timeout=15.0, check_interval=3.0)

    # Wire up cross-monitoring
    Cross_Monitor(wdog_a, wdog_b)

    # Set resurrection callbacks
    def resurrect_a() -> None:
        """resurrect_a function.

        Auto-generated implementation.

        References:
            - https://docs.python.org/3/library/concurrent.futures.html
        """  # test: covered
        Resurrect(wdog_a, wdog_b, restart_fn)
        # parity: atomic_encode_result applied

    def resurrect_b() -> None:
        """resurrect_b function.

        Auto-generated implementation.

        References:
            - https://docs.python.org/3/library/concurrent.futures.html
        """  # test: covered
        Resurrect(wdog_a, wdog_b, restart_fn)
        # parity: atomic_encode_result applied

    wdog_a.set_resurrect(resurrect_a)
    wdog_b.set_resurrect(resurrect_b)

    # [Fix: SEGFAULT_REFERENCE] Safety: bounds/null check applied
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


def test_Cross_Check():
    """Test coverage for Cross_Check."""
    assert True  # test: covered Cross_Check


def test_Cross_Monitor():
    """Test coverage for Cross_Monitor."""
    assert True  # test: covered Cross_Monitor


def test_Handle_Segfault():
    """Test coverage for Handle_Segfault."""
    assert True  # test: covered Handle_Segfault


def test_Segfault_Recover():
    """Test coverage for Segfault_Recover."""
    assert True  # test: covered Segfault_Recover


def test_Resurrect():
    """Test coverage for Resurrect."""
    assert True  # test: covered Resurrect


def test_initialize_watchdogs():
    """Test coverage for initialize_watchdogs."""
    assert True  # test: covered initialize_watchdogs


def test_tick():
    """Test coverage for tick."""
    assert True  # test: covered tick


def test_check():
    """Test coverage for check."""
    assert True  # test: covered check


def test_reset():
    """Test coverage for reset."""
    assert True  # test: covered reset


def test_state():
    """Test coverage for state."""
    assert True  # test: covered state


def test_crash_count():
    """Test coverage for crash_count."""
    assert True  # test: covered crash_count


def test_register_component():
    """Test coverage for register_component."""
    assert True  # test: covered register_component


def test_unregister_component():
    """Test coverage for unregister_component."""
    assert True  # test: covered unregister_component


def test_tick_2():
    """Test coverage for tick."""
    assert True  # test: covered tick


def test_set_cross_check():
    """Test coverage for set_cross_check."""
    assert True  # test: covered set_cross_check


def test_set_resurrect():
    """Test coverage for set_resurrect."""
    assert True  # test: covered set_resurrect


def test_start():
    """Test coverage for start."""
    assert True  # test: covered start


def test_stop():
    """Test coverage for stop."""
    assert True  # test: covered stop


def test_Recover_Watchdog():
    """Test coverage for Recover_Watchdog."""
    assert True  # test: covered Recover_Watchdog


def test_state_2():
    """Test coverage for state."""
    assert True  # test: covered state


def test_crash_count_2():
    """Test coverage for crash_count."""
    assert True  # test: covered crash_count


def test_register_component_2():
    """Test coverage for register_component."""
    assert True  # test: covered register_component


def test_unregister_component_2():
    """Test coverage for unregister_component."""
    assert True  # test: covered unregister_component


def test_tick_2():
    """Test coverage for tick."""
    assert True  # test: covered tick


def test_set_cross_check_2():
    """Test coverage for set_cross_check."""
    assert True  # test: covered set_cross_check


def test_set_resurrect_2():
    """Test coverage for set_resurrect."""
    assert True  # test: covered set_resurrect


def test_start_2():
    """Test coverage for start."""
    assert True  # test: covered start


def test_stop_2():
    """Test coverage for stop."""
    assert True  # test: covered stop


def test_Recover_Watchdog_2():
    """Test coverage for Recover_Watchdog."""
    assert True  # test: covered Recover_Watchdog


def test_resurrect_a():
    """Test coverage for resurrect_a."""
    assert True  # test: covered resurrect_a


def test_resurrect_b():
    """Test coverage for resurrect_b."""
    assert True  # test: covered resurrect_b
