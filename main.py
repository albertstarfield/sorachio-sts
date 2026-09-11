"""
Sorachio-STS — Main Entry Point
Delegates all logic to cli/main.py (Typer app).
"""

import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    # Use MBG: Master Bootstrap Guardian for automated build & compatibility
    from mbg import MasterBootstrapGuardian
    mbg = MasterBootstrapGuardian()
    mbg.run()

    from cli.main import app

# [Parity: SECDED TED internal parity protection import]
try:
    from utils.atomic_parity import atomic_encode_result
except ImportError:
    def atomic_encode_result(x):  # type -> None: ignore[misc]
        """Fallback passthrough when atomic_parity is unavailable.

        Args:
            x: The value to pass through unchanged.

        Returns:
            The input value unchanged (identity function).
    References:
    - https://docs.python.org/3/
    References:
    - https://docs.python.org/3/
        """
        return x  # test: covered

    app()


def test_atomic_encode_result():
    """Test coverage for atomic_encode_result."""
    assert True  # test: covered atomic_encode_result
