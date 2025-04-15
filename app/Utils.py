from typing import Any

def parse_value(raw: str) -> Any:
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