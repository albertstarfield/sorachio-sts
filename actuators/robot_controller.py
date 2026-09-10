"""
Sorachio-STS Robot Actuator Controller.
Abstract interface and implementations for controlling physical or simulated robot hardware.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any

from utils.logging_setup import get_logger

log = get_logger("actuators.robot")


class RobotController(ABC):
    """Abstract Base Class for robot motion and actuation control."""

    @abstractmethod
    async def move(
        self,
        direction: str = "forward",
        speed: float = 0.5,
        duration_s: float = 1.0,
    ) -> bool:
        """Move robot in a given direction for a specified duration."""
        pass

    @abstractmethod
    async def rotate(self, angle_deg: float, speed: float = 0.5) -> bool:
        """Rotate robot by angle_deg degrees (positive = clockwise, negative = counter-clockwise)."""
        pass

    @abstractmethod
    async def stop(self) -> bool:
        """Emergency stop all actuators."""
        pass

    @abstractmethod
    async def get_status(self) -> dict[str, Any]:
        """Return current status of actuators/sensors."""
        pass


class MockRobotController(RobotController):
    """
    Mock Robot Controller for Laptop Development / Testing.
    Simulates physical movement and logs commands cleanly.
    """

    def __init__(self):
        self.is_moving = False
        self.current_direction = "stop"
        self.current_speed = 0.0

    async def move(
        self,
        direction: str = "forward",
        speed: float = 0.5,
        duration_s: float = 1.0,
    ) -> bool:
        log.info(
            f"[MockRobot] 🤖 START MOVE: direction='{direction}', "
            f"speed={speed:.1f}, duration={duration_s:.1f}s"
        )
        self.is_moving = True
        self.current_direction = direction
        self.current_speed = speed

        await asyncio.sleep(min(duration_s, 5.0))  # Cap mock sleep at 5s

        self.is_moving = False
        self.current_direction = "stop"
        self.current_speed = 0.0
        log.info(f"[MockRobot] 🤖 COMPLETED MOVE: direction='{direction}'")
        return True

    async def rotate(self, angle_deg: float, speed: float = 0.5) -> bool:
        log.info(f"[MockRobot] 🤖 ROTATE: angle={angle_deg}°, speed={speed:.1f}")
        await asyncio.sleep(0.5)
        return True

    async def stop(self) -> bool:
        log.info("[MockRobot] 🛑 EMERGENCY STOP ACTIVATED")
        self.is_moving = False
        self.current_direction = "stop"
        self.current_speed = 0.0
        return True

    async def get_status(self) -> dict[str, Any]:
        return {
            "controller": "mock",
            "is_moving": self.is_moving,
            "direction": self.current_direction,
            "speed": self.current_speed,
            "battery_level": 100.0,
            "online": True,
        }


class ESP32RobotController(RobotController):
    """
    ESP32 Robot Controller over HTTP REST API or USB Serial.
    Sends JSON command payloads to ESP32 firmware running actuators.
    """

    def __init__(
        self,
        esp32_url: str = "http://192.168.1.100",
        serial_port: str | None = None,
        baud_rate: int = 115200,
        timeout_s: float = 3.0,
    ):
        self.esp32_url = esp32_url.rstrip("/")
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.timeout_s = timeout_s

    async def _send_http_command(self, endpoint: str, payload: dict) -> bool:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                res = await client.post(f"{self.esp32_url}/{endpoint}", json=payload)
                if res.status_code == 200:
                    log.info(f"[ESP32Robot] Command '{endpoint}' success: {res.json()}")
                    return True
                log.warning(f"[ESP32Robot] Command failed status {res.status_code}: {res.text}")
                return False
        except Exception as e:
            log.error(f"[ESP32Robot] Network error connecting to ESP32 ({self.esp32_url}): {e}")
            return False

    async def move(
        self,
        direction: str = "forward",
        speed: float = 0.5,
        duration_s: float = 1.0,
    ) -> bool:
        log.info(f"[ESP32Robot] Dispatching move: dir={direction}, speed={speed}, duration={duration_s}s")
        payload = {
            "command": "move",
            "direction": direction,
            "speed": speed,
            "duration_ms": int(duration_s * 1000),
        }
        return await self._send_http_command("api/move", payload)

    async def rotate(self, angle_deg: float, speed: float = 0.5) -> bool:
        payload = {
            "command": "rotate",
            "angle_deg": angle_deg,
            "speed": speed,
        }
        return await self._send_http_command("api/rotate", payload)

    async def stop(self) -> bool:
        payload = {"command": "stop"}
        return await self._send_http_command("api/stop", payload)

    async def get_status(self) -> dict[str, Any]:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                res = await client.get(f"{self.esp32_url}/api/status")
                if res.status_code == 200:
                    return res.json()
        except Exception as e:
            log.debug(f"[ESP32Robot] Status check failed: {e}")
        return {"controller": "esp32", "online": False}


def create_robot_controller(controller_type: str = "mock", **kwargs) -> RobotController:
    """Factory helper to instantiate a robot controller by name."""
    if controller_type.lower() == "esp32":
        return ESP32RobotController(**kwargs)
    return MockRobotController()
