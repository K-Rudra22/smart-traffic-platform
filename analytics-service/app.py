from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
import psycopg2
import psycopg2.extras
from datetime import datetime

app = FastAPI(title="Analytics Service")

# Supabase gives you a standard PostgreSQL connection string
# Set this as an environment variable - never hardcode it
DATABASE_URL = os.getenv("DATABASE_URL")


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    """Create tables if they don't exist yet."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id SERIAL PRIMARY KEY,
            video_id TEXT UNIQUE NOT NULL,
            total_vehicles INT,
            entering INT,
            leaving INT,
            vehicle_counts JSONB,
            processed_at TIMESTAMP DEFAULT NOW()
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id SERIAL PRIMARY KEY,
            video_id TEXT NOT NULL,
            vehicle_id INT,
            vehicle_class TEXT,
            frame INT,
            speed_kmph FLOAT,
            FOREIGN KEY (video_id) REFERENCES sessions(video_id)
        );
    """)
    conn.commit()
    cur.close()
    conn.close()


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "analytics service running"}


class Detection(BaseModel):
    vehicle_id: int
    vehicle_class: str
    frame: int
    speed_kmph: Optional[float]


class SummaryPayload(BaseModel):
    video_id: str
    total_vehicles: int
    entering: int
    leaving: int
    vehicle_counts: Dict[str, int]
    detections: List[Detection]


@app.post("/store")
def store_results(payload: SummaryPayload):
    """Receives detection results and saves them to Supabase PostgreSQL."""
    conn = get_conn()
    cur = conn.cursor()

    # Save session summary
    cur.execute("""
        INSERT INTO sessions (video_id, total_vehicles, entering, leaving, vehicle_counts)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (video_id) DO UPDATE SET
            total_vehicles = EXCLUDED.total_vehicles,
            entering = EXCLUDED.entering,
            leaving = EXCLUDED.leaving,
            vehicle_counts = EXCLUDED.vehicle_counts,
            processed_at = NOW()
    """, (
        payload.video_id,
        payload.total_vehicles,
        payload.entering,
        payload.leaving,
        psycopg2.extras.Json(payload.vehicle_counts)
    ))

    # Save individual detections
    for d in payload.detections:
        cur.execute("""
            INSERT INTO detections (video_id, vehicle_id, vehicle_class, frame, speed_kmph)
            VALUES (%s, %s, %s, %s, %s)
        """, (payload.video_id, d.vehicle_id, d.vehicle_class, d.frame, d.speed_kmph))

    conn.commit()
    cur.close()
    conn.close()

    return {"status": "stored", "video_id": payload.video_id}


@app.get("/sessions")
def get_sessions():
    """Returns all processed video sessions for the dashboard."""
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM sessions ORDER BY processed_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"sessions": [dict(r) for r in rows]}


@app.get("/sessions/{video_id}")
def get_session_detail(video_id: str):
    """Returns detailed detections for one video session."""
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("SELECT * FROM sessions WHERE video_id = %s", (video_id,))
    session = cur.fetchone()

    cur.execute(
        "SELECT * FROM detections WHERE video_id = %s ORDER BY frame",
        (video_id,)
    )
    detections = cur.fetchall()
    cur.close()
    conn.close()

    return {
        "session": dict(session) if session else None,
        "detections": [dict(d) for d in detections]
    }


@app.get("/stats/speed-distribution/{video_id}")
def speed_distribution(video_id: str):
    """Returns speed data bucketed for charting."""
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT vehicle_class, AVG(speed_kmph) as avg_speed,
               MAX(speed_kmph) as max_speed, COUNT(*) as count
        FROM detections
        WHERE video_id = %s AND speed_kmph IS NOT NULL
        GROUP BY vehicle_class
    """, (video_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {"speed_stats": [dict(r) for r in rows]}
