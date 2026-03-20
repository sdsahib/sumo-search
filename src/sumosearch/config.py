from __future__ import annotations

import os
from pathlib import Path

from sumosearch.exceptions import ConfigError
from sumosearch.models import DEFAULT_ENDPOINT, Config

DEFAULT_CONFIG_PATH: Path = Path.home() / ".sumosearch"


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> Config:
    if not path.exists():
        raise ConfigError(f"config file not found: {path}")
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"cannot read config file: {exc}") from exc

    data: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            data[key.strip()] = value.strip()

    required = ("SUMO_ACCESS_ID", "SUMO_ACCESS_KEY")
    for key in required:
        if not data.get(key):
            raise ConfigError(f"missing required config key: {key}")

    try:
        page_size = int(data.get("PAGE_SIZE", "100"))
        pages = int(data.get("PAGES", "1"))
    except ValueError as exc:
        raise ConfigError(f"invalid numeric config value: {exc}") from exc

    return Config(
        sumo_access_id=data["SUMO_ACCESS_ID"],
        sumo_access_key=data["SUMO_ACCESS_KEY"],
        timezone=data.get("TIMEZONE", "UTC"),
        page_size=page_size,
        pages=pages,
        endpoint=data.get("ENDPOINT", DEFAULT_ENDPOINT),
    )


def save_config(config: Config, path: Path = DEFAULT_CONFIG_PATH) -> None:
    content = (
        f"SUMO_ACCESS_ID={config.sumo_access_id}\n"
        f"SUMO_ACCESS_KEY={config.sumo_access_key}\n"
        f"TIMEZONE={config.timezone}\n"
        f"PAGE_SIZE={config.page_size}\n"
        f"PAGES={config.pages}\n"
        f"ENDPOINT={config.endpoint}\n"
    )
    try:
        path.write_text(content, encoding="utf-8")
        os.chmod(path, 0o600)
    except OSError as exc:
        raise ConfigError(f"cannot write config file: {exc}") from exc
