import math

from pylon_service.settings import settings

LOW_TEMPO = 50

# 2 factor for safety reason in case blocks progress slower
MAX_WEIGHT_REVEAL_WAIT_TIME = 2 * math.ceil(settings.block_duration_seconds * (LOW_TEMPO + 1))


def log_step(message: str) -> None:
    print(f"\n{'=' * 40}")
    print(f"  {message}")
    print(f"{'=' * 40}\n")
