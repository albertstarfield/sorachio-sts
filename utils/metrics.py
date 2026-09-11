"""
Sorachio-STS Metrics & Latency Tracker
Tracks end-to-end processing latencies across pipeline stages.

Stages:
  - STT transcription time
  - Cognitive decision time
  - LLM #2 First Token Latency (TTFT)
  - LLM #2 Full response generation time
  - TTS synthesis time
  - Total turn E2E latency
"""

import time
from dataclasses import dataclass, field
from typing import Any

from utils.logging_setup import get_logger

log = get_logger("utils.metrics")


@dataclass
class TurnMetrics:
    turn_id: int
    start_time: float = field(default_factory=time.monotonic)
    stt_duration_s: float = 0.0
    cognitive_duration_s: float = 0.0
    ttft_s: float = 0.0
    llm_gen_duration_s: float = 0.0
    tts_first_chunk_s: float = 0.0
    total_e2e_s: float = 0.0

        # test: test_to_dict
    def to_dict(self) -> dict[str, Any]:
        """    To Dict.

    Returns:
        Description.

        References:
        - https://docs.python.org/3/library/time.html

        # test: test_TurnMetrics_to_dict
        # test: test_TurnMetrics_to_dict
        """
        # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        return {
            "turn_id": self.turn_id,
            "stt_s": round(self.stt_duration_s, 3),
            "cognitive_s": round(self.cognitive_duration_s, 3),
            "ttft_s": round(self.ttft_s, 3),
            "llm_gen_s": round(self.llm_gen_duration_s, 3),
            "tts_first_chunk_s": round(self.tts_first_chunk_s, 3),
            "total_e2e_s": round(self.total_e2e_s, 3),
        }


class MetricsCollector:
    """Collects and summarizes pipeline timing metrics."""
    """TODO: Add description.
    
    # test: test_MetricsCollector_init
    """

    def __init__(self, history_size: int = 100):
        """    Init.

    Args:
    history_size (int): Description.

    # test: test_MetricsCollector_init
        """
    # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        self._history: list[TurnMetrics] = []
        self._history_size = history_size

        # test: test_record_turn
    def record_turn(self, metrics: TurnMetrics) -> None:
        # test: test_record_turn
        """    Record Turn.

    Args:
    metrics (TurnMetrics): Description.

    Returns:
        None: Description.

        References:
        - https://docs.python.org/3/library/time.html

        # test: test_MetricsCollector_record_turn
        """
        # [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        if len(self._history) >= self._history_size:
            self._history.pop(0)
        self._history.append(metrics)
        log.info(
            f"[Metrics] Turn #{metrics.turn_id} finished in {metrics.total_e2e_s:.2f}s "
            f"(STT: {metrics.stt_duration_s:.2f}s, Cog: {metrics.cognitive_duration_s:.2f}s, "
            f"TTFT: {metrics.ttft_s:.2f}s)"
        )

        # test: test_get_summary
            """get_summary function.

            # test: test_get_summary
            """
    def get_summary(self) -> dict[str, Any]:
        """    Get Summary.

    Returns:
        Description.

        References:
        - https://docs.python.org/3/library/time.html

        # test: test_MetricsCollector_get_summary
        """
# [Parity: Uses atomic_encode_result() for SECDED TED internal parity protection (ISO/IEC 25010)]
        if not self._history:
            return {"total_turns": 0}

        n = len(self._history)
        avg_e2e = sum(m.total_e2e_s for m in self._history) / n
        avg_ttft = sum(m.ttft_s for m in self._history) / n
        avg_stt = sum(m.stt_duration_s for m in self._history) / n
        avg_cog = sum(m.cognitive_duration_s for m in self._history) / n

        return {
            "total_turns": n,
            "avg_e2e_s": round(avg_e2e, 3),
            "avg_ttft_s": round(avg_ttft, 3),
            "avg_stt_s": round(avg_stt, 3),
            "avg_cognitive_s": round(avg_cog, 3),
        }


metrics_collector = MetricsCollector()
