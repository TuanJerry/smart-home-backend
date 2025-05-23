import asyncio

from typing import Any
from app.core.config import settings

send_queue = asyncio.Queue()
aio = settings.ADAFRUIT_IO_CLIENT

def parse_value(raw: str) -> Any:
    if type(raw) is not str:
        pass
    lowered = raw.lower()
    if lowered == "true":
        return True
    elif lowered == "false":
        return False
    try:
        if '.' in raw:
            return float(raw)
        return int(raw)
    except ValueError:
        return raw  # fallback: string