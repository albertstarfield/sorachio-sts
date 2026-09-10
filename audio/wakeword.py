"""
Sorachio-STS Real-Time Wake Word Detector.
Wraps OpenWakeWord to process 16kHz 16-bit Mono PCM audio streams.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from pathlib import Path

import numpy as np

log = logging.getLogger("sorachio.audio.wakeword")

try:
    import openwakeword
    import openwakeword.utils
    from openwakeword.model import Model
    OPENWAKEWORD_AVAILABLE = True
except ImportError:
    OPENWAKEWORD_AVAILABLE = False
    Model = None  # type: ignore[assignment]


class WakeWordDetector:
    """
    Real-time Wake Word Detector using OpenWakeWord.
    Accepts 16kHz 16-bit Mono PCM audio chunks and yields detection events.
    """

    def __init__(
        self,
        target_words: Sequence[str] = ("hey_sorachio", "alexa", "hey_jarvis"),
        threshold: float = 0.5,
        model_dir: str | Path | None = None,
        custom_model_paths: Sequence[str | Path] | None = None,
        inference_framework: str = "onnx",
    ):
        """
        Initialize WakeWordDetector.

        Args:
            target_words: Names or substrings of wake words to trigger on.
            threshold: Confidence score threshold (0.0 to 1.0) to trigger wake word.
            model_dir: Directory containing openwakeword ONNX model files.
            custom_model_paths: Specific model file paths.
            inference_framework: ONNX or TFLite engine.
        """
        if not OPENWAKEWORD_AVAILABLE or Model is None:
            raise ImportError(
                "openwakeword package is required for wake word detection. "
                "Install it using `pip install openwakeword`."
            )

        self.threshold = threshold
        self.target_words = [tw.lower() for tw in target_words]

        # Determine model file paths
        model_paths: list[str] = []
        if custom_model_paths:
            for p in custom_model_paths:
                model_paths.append(str(p))
        elif model_dir and Path(model_dir).exists():
            onnx_files = list(Path(model_dir).glob("*.onnx"))
            if onnx_files:
                model_paths = [str(f) for f in onnx_files]

        if not model_paths:
            # Download built-in pretrained openwakeword models if none specified
            try:
                if hasattr(openwakeword, "utils") and hasattr(openwakeword.utils, "download_models"):
                    openwakeword.utils.download_models()
            except Exception as e:
                log.warning(f"Could not auto-download openwakeword models: {e}")

        try:
            if model_paths:
                self.model = Model(wakeword_model_paths=model_paths)
            else:
                self.model = Model()
            log.info(f"WakeWordDetector loaded models: {list(self.model.models.keys())}")
        except Exception as e:
            log.error(f"Failed to initialize OpenWakeWord model: {e}")
            raise e

    def process_pcm(self, pcm_data: bytes | np.ndarray) -> tuple[bool, str, float]:
        """
        Process a chunk of 16kHz 16-bit Mono PCM audio.

        Args:
            pcm_data: Raw PCM audio bytes or numpy int16 array.

        Returns:
            Tuple of (detected: bool, word_name: str, score: float)
        """
        if isinstance(pcm_data, bytes):
            audio_array = np.frombuffer(pcm_data, dtype=np.int16)
        else:
            audio_array = pcm_data

        if len(audio_array) == 0:
            return False, "", 0.0

        # Predict confidence scores using openwakeword
        prediction = self.model.predict(audio_array)

        # Check prediction results against target threshold
        if isinstance(prediction, dict):
            for word, score in prediction.items():
                score_val = float(score)
                word_lower = word.lower()

                # Check if word matches target list (or trigger on any pretrained word if target list is empty)
                is_target = not self.target_words or any(tw in word_lower for tw in self.target_words)

                if is_target and score_val >= self.threshold:
                    log.info(f"Wake word detected! Model='{word}', Score={score_val:.3f}")
                    self.reset()
                    return True, word, score_val

        return False, "", 0.0

    def reset(self) -> None:
        """Reset internal state buffer and preprocessor feature buffers of openwakeword model."""
        if not hasattr(self, "model") or self.model is None:
            return

        if hasattr(self.model, "reset"):
            self.model.reset()

        if hasattr(self.model, "prediction_buffer"):
            self.model.prediction_buffer.clear()

        # Deep reset openwakeword preprocessor feature buffers to prevent ghost triggers
        if hasattr(self.model, "preprocessor"):
            pr = self.model.preprocessor
            if hasattr(pr, "raw_data_buffer"):
                pr.raw_data_buffer.clear()
            if hasattr(pr, "feature_buffer") and hasattr(pr.feature_buffer, "shape"):
                pr.feature_buffer = np.zeros_like(pr.feature_buffer)
            if hasattr(pr, "melspectrogram_buffer") and hasattr(pr.melspectrogram_buffer, "shape"):
                pr.melspectrogram_buffer = np.zeros_like(pr.melspectrogram_buffer)
