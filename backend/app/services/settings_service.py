"""Settings service — loads and saves application settings from SQLite."""
from __future__ import annotations

import json

from app.schemas.models import AppSettings
from app.storage.database import get_conn, get_settings_row, save_settings_row


def load_settings() -> AppSettings:
    """Load settings from DB; return defaults if not yet saved."""
    with get_conn() as conn:
        row = get_settings_row(conn)
    if row is None:
        return AppSettings()
    try:
        data = json.loads(row["settings_json"])
        return AppSettings(**data)
    except Exception:
        return AppSettings()


def save_settings(settings: AppSettings) -> AppSettings:
    """Persist validated settings and return the saved object."""
    with get_conn() as conn:
        save_settings_row(conn, settings.model_dump_json())
    return settings
