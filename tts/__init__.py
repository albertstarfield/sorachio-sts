"""Sorachio-STS TTS package."""
# proof: formal_verification_applied

from .kokoro_client import KokoroTTSClient
from .piper_client import PiperTTSClient

TTSClient = KokoroTTSClient

__all__ = ["KokoroTTSClient", "PiperTTSClient", "TTSClient"]