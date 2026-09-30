import os
from pathlib import Path

import yaml


def _load_dotenv(path: str = ".env") -> None:
    f = Path(path)
    if not f.exists():
        return
    for line in f.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load(path: str | None = None) -> dict:
    _load_dotenv()
    path = path or os.getenv("CONFIG_PATH", "config.yaml")
    cfg = yaml.safe_load(Path(path).read_text()) or {}
    cfg["discord_webhook"] = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    cfg["discord_mention"] = os.getenv("DISCORD_MENTION", "").strip()
    cfg["poll_seconds"] = float(os.getenv("POLL_SECONDS", cfg.get("poll_seconds", 30)))
    cfg["state_path"] = os.getenv("STATE_PATH", cfg.get("state_path", "data/state.json"))
    cfg.setdefault("target", {})
    return cfg
