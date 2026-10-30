"""SQLite database layer for ECO-SHIELD."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, UTC
from pathlib import Path
from typing import Generator, List, Optional

DB_PATH = Path(__file__).parent.parent.parent / "ecoshield.db"

SCHEMA_VERSION = 2


def _connect(path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_conn(path: Path = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    conn = _connect(path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

DDL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS app_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    settings_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS datasets (
    dataset_id TEXT PRIMARY KEY,
    filename TEXT,
    source TEXT NOT NULL,
    upload_time TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    column_names TEXT NOT NULL,
    detected_types TEXT NOT NULL,
    timestamp_range_start TEXT,
    timestamp_range_end TEXT,
    file_size_bytes INTEGER,
    scenario_id TEXT,
    data_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analyses (
    analysis_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    dataset_id TEXT NOT NULL,
    source TEXT NOT NULL,
    algorithm_version TEXT NOT NULL,
    configuration_json TEXT NOT NULL,
    quality_report_json TEXT NOT NULL,
    anomaly_summary_json TEXT NOT NULL,
    diagnosis_json TEXT NOT NULL,
    recommendations_json TEXT NOT NULL,
    warnings_json TEXT NOT NULL,
    limitations_json TEXT NOT NULL,
    FOREIGN KEY (dataset_id) REFERENCES datasets(dataset_id)
);

CREATE INDEX IF NOT EXISTS idx_analyses_created ON analyses(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analyses_dataset ON analyses(dataset_id);
CREATE INDEX IF NOT EXISTS idx_analyses_source ON analyses(source);
"""


def init_db(path: Path = DB_PATH) -> None:
    """Initialise the database schema (idempotent)."""
    with get_conn(path) as conn:
        conn.executescript(DDL)
        row = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1").fetchone()
        current = row["version"] if row else 0
        if current < SCHEMA_VERSION:
            conn.execute(
                "INSERT OR REPLACE INTO schema_version VALUES (?, ?)",
                (SCHEMA_VERSION, datetime.now(UTC).isoformat()),
            )


# ---------------------------------------------------------------------------
# Dataset helpers
# ---------------------------------------------------------------------------

def save_dataset(
    conn: sqlite3.Connection,
    dataset_id: str,
    filename: Optional[str],
    source: str,
    row_count: int,
    column_names: List[str],
    detected_types: dict,
    ts_start: Optional[str],
    ts_end: Optional[str],
    file_size: Optional[int],
    scenario_id: Optional[str],
    data_json: str,
) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO datasets
           (dataset_id, filename, source, upload_time, row_count, column_names,
            detected_types, timestamp_range_start, timestamp_range_end,
            file_size_bytes, scenario_id, data_json)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            dataset_id,
            filename,
            source,
            datetime.now(UTC).isoformat(),
            row_count,
            json.dumps(column_names),
            json.dumps(detected_types),
            ts_start,
            ts_end,
            file_size,
            scenario_id,
            data_json,
        ),
    )


def get_dataset(conn: sqlite3.Connection, dataset_id: str) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM datasets WHERE dataset_id=?", (dataset_id,)).fetchone()


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------

def save_analysis(conn: sqlite3.Connection, analysis: dict) -> None:
    conn.execute(
        """INSERT INTO analyses
           (analysis_id, status, created_at, dataset_id, source, algorithm_version,
            configuration_json, quality_report_json, anomaly_summary_json,
            diagnosis_json, recommendations_json, warnings_json, limitations_json)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            analysis["analysis_id"],
            analysis["status"],
            analysis["created_at"],
            analysis["dataset_id"],
            analysis["source"],
            analysis["algorithm_version"],
            json.dumps(analysis.get("configuration_used", {})),
            json.dumps(analysis.get("quality_report", {})),
            json.dumps(analysis.get("anomaly_summary", {})),
            json.dumps(analysis.get("diagnosis", {})),
            json.dumps(analysis.get("recommendations", [])),
            json.dumps(analysis.get("warnings", [])),
            json.dumps(analysis.get("limitations", [])),
        ),
    )


def get_analysis(conn: sqlite3.Connection, analysis_id: str) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM analyses WHERE analysis_id=?", (analysis_id,)).fetchone()


def list_analyses(
    conn: sqlite3.Connection,
    source: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[sqlite3.Row]:
    if source:
        return conn.execute(
            "SELECT * FROM analyses WHERE source=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (source, limit, offset),
        ).fetchall()
    return conn.execute(
        "SELECT * FROM analyses ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()


# ---------------------------------------------------------------------------
# Settings helpers
# ---------------------------------------------------------------------------

def get_settings_row(conn: sqlite3.Connection) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM app_settings WHERE id=1").fetchone()


def save_settings_row(conn: sqlite3.Connection, settings_json: str) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO app_settings (id, settings_json, updated_at) VALUES (1, ?, ?)",
        (settings_json, datetime.now(UTC).isoformat()),
    )
