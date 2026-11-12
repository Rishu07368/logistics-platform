"""SQLite connection handling and schema. No business logic lives here."""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS networks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  key TEXT UNIQUE NOT NULL, name TEXT NOT NULL, description TEXT DEFAULT '',
  scenario TEXT NOT NULL, builtin INTEGER NOT NULL DEFAULT 0,
  default_metric TEXT NOT NULL DEFAULT 'cost',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS locations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  network_id INTEGER NOT NULL REFERENCES networks(id) ON DELETE CASCADE,
  code TEXT NOT NULL, name TEXT NOT NULL, country TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('city','warehouse','distribution_center','destination')),
  lat REAL NOT NULL CHECK (lat BETWEEN -90 AND 90),
  lon REAL NOT NULL CHECK (lon BETWEEN -180 AND 180),
  packages INTEGER NOT NULL DEFAULT 0 CHECK (packages >= 0),
  UNIQUE (network_id, code));
CREATE TABLE IF NOT EXISTS routes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  network_id INTEGER NOT NULL REFERENCES networks(id) ON DELETE CASCADE,
  src TEXT NOT NULL, dst TEXT NOT NULL,
  mode TEXT NOT NULL CHECK (mode IN ('road','rail','sea','air')),
  distance_km REAL NOT NULL CHECK (distance_km >= 0),
  cost_usd REAL NOT NULL, time_hours REAL NOT NULL,
  weekly_trips INTEGER NOT NULL DEFAULT 1 CHECK (weekly_trips >= 0),
  note TEXT DEFAULT '',
  UNIQUE (network_id, src, dst), CHECK (src <> dst));
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, network_id INTEGER NOT NULL,
  algorithm TEXT NOT NULL, metric TEXT NOT NULL, source TEXT, target TEXT,
  status TEXT NOT NULL, total REAL, time_ms REAL, relaxations INTEGER, iterations INTEGER,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_routes_net ON routes(network_id);
CREATE INDEX IF NOT EXISTS idx_locs_net ON locations(network_id);
"""


def connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn):
    conn.executescript(SCHEMA)
    conn.commit()
