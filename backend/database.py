import sqlite3
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "roadvision.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inspections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_name TEXT,
            start_time TEXT,
            end_time TEXT,
            source_type TEXT,
            total_potholes INTEGER DEFAULT 0,
            critical_count INTEGER DEFAULT 0,
            moderate_count INTEGER DEFAULT 0,
            minor_count INTEGER DEFAULT 0,
            road_score REAL DEFAULT 100.0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inspection_id INTEGER,
            timestamp TEXT,
            confidence REAL,
            severity TEXT,
            bbox TEXT,
            snapshot_path TEXT,
            lat REAL,
            lng REAL,
            FOREIGN KEY (inspection_id) REFERENCES inspections(id)
        )
    """)
    conn.commit()
    conn.close()


def create_inspection_session(source_type: str = "Test Video") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    session_name = f"Session {time.strftime('%b %d, %H:%M')}"
    cursor.execute("""
        INSERT INTO inspections (session_name, start_time, source_type)
        VALUES (?, ?, ?)
    """, (session_name, now, source_type))
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id


def end_inspection_session(session_id: int, stats: Dict[str, Any]):
    conn = get_connection()
    cursor = conn.cursor()
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        UPDATE inspections
        SET end_time = ?,
            total_potholes = ?,
            critical_count = ?,
            moderate_count = ?,
            minor_count = ?,
            road_score = ?
        WHERE id = ?
    """, (
        now,
        stats.get("total_potholes", 0),
        stats.get("critical_count", 0),
        stats.get("moderate_count", 0),
        stats.get("minor_count", 0),
        stats.get("road_score", 100.0),
        session_id
    ))
    conn.commit()
    conn.close()


def record_detection(inspection_id: int, confidence: float, severity: str,
                     bbox: List[int], snapshot_path: str = "", lat: Optional[float] = None, lng: Optional[float] = None) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO detections (inspection_id, timestamp, confidence, severity, bbox, snapshot_path, lat, lng)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (inspection_id, now, confidence, severity, json.dumps(bbox), snapshot_path, lat, lng))
    det_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return det_id


def get_recent_detections(limit: int = 25) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.id, d.inspection_id, d.timestamp, d.confidence, d.severity, d.bbox, d.snapshot_path, d.lat, d.lng
        FROM detections d
        ORDER BY d.id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    results = []
    for r in rows:
        results.append({
            "id": r["id"],
            "inspection_id": r["inspection_id"],
            "timestamp": r["timestamp"],
            "confidence": round(r["confidence"], 2),
            "severity": r["severity"],
            "bbox": json.loads(r["bbox"]) if r["bbox"] else [],
            "snapshot_path": r["snapshot_path"],
            "lat": r["lat"],
            "lng": r["lng"]
        })
    conn.close()
    return results


def get_all_inspections(limit: int = 15) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM inspections
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    results = [dict(r) for r in rows]
    conn.close()
    return results


# Initialize database upon import
init_db()
