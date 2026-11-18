import json
import os
import sqlite3
import time
from pathlib import Path

DB = os.getenv("DATABASE", "data/incidents.db")

def connect():
    Path(DB).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS incidents (id INTEGER PRIMARY KEY, created REAL, updated REAL, status TEXT, payload TEXT);
    CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, incident INTEGER, time REAL, kind TEXT, payload TEXT);
    """)
    return db

def setting(key, default=None):
    with connect() as db:
        row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return json.loads(row[0]) if row else default

def set_setting(key, value):
    with connect() as db:
        db.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key,json.dumps(value)))

def create(payload):
    with connect() as db:
        cur = db.execute("INSERT INTO incidents(created,updated,status,payload) VALUES(?,?,?,?)", (time.time(),time.time(),'detected',json.dumps(payload)))
        return cur.lastrowid

def update(ident, status):
    with connect() as db:
        db.execute("UPDATE incidents SET status=?,updated=? WHERE id=?", (status,time.time(),ident))

def event(ident, kind, payload):
    with connect() as db:
        db.execute("INSERT INTO events(incident,time,kind,payload) VALUES(?,?,?,?)", (ident,time.time(),kind,json.dumps(payload)))

def incidents():
    with connect() as db:
        rows = db.execute("SELECT * FROM incidents ORDER BY id DESC LIMIT 200").fetchall()
    return [{**dict(r), 'payload':json.loads(r['payload'])} for r in rows]

def events(ident):
    with connect() as db:
        rows = db.execute("SELECT * FROM events WHERE incident=? ORDER BY id", (ident,)).fetchall()
    return [{**dict(r), 'payload':json.loads(r['payload'])} for r in rows]
