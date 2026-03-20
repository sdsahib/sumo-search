from __future__ import annotations

import os
from pathlib import Path

from sumosearch.config import DEFAULT_CONFIG_PATH, load_config
from sumosearch.exceptions import AuthError, ConfigError
from sumosearch.models import Credentials


def resolve_credentials(
    access_id_flag: str | None = None,
    access_key_flag: str | None = None,
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> Credentials:
    access_id = access_id_flag or os.environ.get("SUMO_ACCESS_ID")
    access_key = access_key_flag or os.environ.get("SUMO_ACCESS_KEY")

    if not (access_id and access_key):
        try:
            cfg = load_config(config_path)
            access_id = access_id or cfg.sumo_access_id
            access_key = access_key or cfg.sumo_access_key
        except ConfigError:
            pass

    if not access_id or not access_key:
        raise AuthError("credentials not found")

    return Credentials(access_id=access_id, access_key=access_key)
