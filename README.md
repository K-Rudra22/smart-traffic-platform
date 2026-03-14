# 🚦 Smart Traffic Analytics Platform

A cloud-native microservices application for real-time vehicle detection, tracking, and speed estimation using YOLOv8 — deployed on free-tier cloud infrastructure.

[![Live Dashboard](https://img.shields.io/badge/Dashboard-Live-brightgreen)](https://smart-traffic-dashboard-fwcz.onrender.com)
[![Analytics API](https://img.shields.io/badge/Analytics_API-Live-blue)](https://smart-traffic-platform.onrender.com/health)
[![Detection API](https://img.shields.io/badge/Detection_API-Live-orange)](https://smart-traffic-detection.onrender.com/health)
[![GitHub](https://img.shields.io/badge/GitHub-K--Rudra22-black)](https://github.com/K-Rudra22/smart-traffic-platform)

---

## 📌 Overview

This project re-architects a monolithic vehicle tracking system into a **4-service cloud-native microservices application** as part of the Cloud Microservices and Applications (CMA) subject.

The platform:
- Detects and tracks vehicles (cars, buses, trucks, motorbikes) using **YOLOv8**
- Estimates vehicle speeds using pixel-to-meter calibration
- Counts vehicles entering and leaving a monitored zone
- Persists all analytics to a **cloud PostgreSQL database** (Supabase)
- Serves results through a **live public Streamlit dashboard**

---

## 🏗️ Architecture

```
User / Browser
      │
      ▼
┌─────────────────┐     HTTP      ┌──────────────────────┐     HTTP      ┌──────────────────┐
│ Ingestion       │ ────────────► │ Detection Service     │ ────────────► │ Analytics Service│
│ Service         │               │ YOLOv8 + OpenCV       │               │ FastAPI + PG     │
│ FastAPI         │               │ Speed Estimation       │               │ Supabase         │
└─────────────────┘               └──────────────────────┘               └──────────────────┘
                                                                                    │
                                                                                    ▼
                                                                          ┌──────────────────┐
                                                                          │ Dashboard        │
                                                                          │ Streamlit        │
                                                                          │ Charts + Tables  │
                                                                          └──────────────────┘
```

All services are containerized with **Docker** and deployed on **Render.com** (free tier).

---

## 🚀 Live URLs

| Service | URL |
|---|---|
| 🖥️ Dashboard | https://smart-traffic-dashboard-fwcz.onrender.com |
| 📊 Analytics API | https://smart-traffic-platform.onrender.com/health |
| 🔍 Detection API | https://smart-traffic-detection.onrender.com/health |
| 📥 Ingestion API | https://smart-traffic-ingestion.onrender.com/health |

> **Note:** Free tier services sleep after 15 minutes of inactivity. First request may take ~50 seconds to wake up.

---

## 🧩 Microservices

### 1. Ingestion Service (`/ingestion-service`)
- Accepts video file uploads via `POST /upload`
- Assigns a UUID to each video
- Forwards video path and parameters to the Detection Service

### 2. Detection Service (`/detection-service`)
- Runs **YOLOv8n** detection on each frame
- Tracks vehicles with consistent IDs using built-in ByteTrack
- Estimates speed: `(pixel_displacement / px_per_meter / time) × 3.6`
- Counts entries/exits using a virtual counting line
- Produces annotated output video with bounding boxes and speed labels

### 3. Analytics Service (`/analytics-service`)
- Stores session summaries and per-frame detection logs in **Supabase PostgreSQL**
- Exposes query APIs for the dashboard:
  - `GET /sessions` — all processed sessions
  - `GET /sessions/{id}` — session detail
  - `GET /stats/speed-distribution/{id}` — speed stats by vehicle class

### 4. Dashboard (`/dashboard`)
- Streamlit web UI with zero ML or database code
- Communicates exclusively with Ingestion and Analytics services via HTTP
- Shows: session history, vehicle type charts, speed over frames, CSV export

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Object Detection | Ultralytics YOLOv8n |
| Video Processing | OpenCV (headless) |
| API Framework | FastAPI + Uvicorn |
| Async HTTP | httpx |
| Database | Supabase PostgreSQL 15 |
| Dashboard | Streamlit |
| Containerization | Docker + Docker Compose |
| Cloud Hosting | Render.com (free tier) |
| CI/CD | GitHub → Render auto-deploy |
| Language | Python 3.10 |

---

## 🖥️ Run Locally

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [Git](https://git-scm.com/)

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/K-Rudra22/smart-traffic-platform.git
cd smart-traffic-platform

# 2. Create .env file in root folder
echo "DATABASE_URL=your_supabase_connection_string" > .env

# 3. Start all 4 services
docker-compose up --build
```

Then open:
- Dashboard → http://localhost:8501
- Analytics API → http://localhost:8002/health
- Detection API → http://localhost:8001/health
- Ingestion API → http://localhost:8000/health

---

## 📁 Project Structure

```
smart-traffic-platform/
├── ingestion-service/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── detection-service/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── analytics-service/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── dashboard/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml
└── .gitignore
```

---

## 📊 Sample Results

Tested on a 38-second overhead highway video (98MB, 30FPS, 1280×720):

| Metric | Result |
|---|---|
| Total vehicles detected | 157 |
| Vehicles entering zone | 36 |
| Vehicles leaving zone | 51 |
| Average car speed | 25.1 km/h |
| Average truck speed | 37.7 km/h |
| Processing time (CPU) | ~3 minutes |

---

## ☁️ Cloud Infrastructure (All Free)

| Service | Provider | Purpose |
|---|---|---|
| PostgreSQL Database | Supabase | Persistent storage |
| 4× Service Hosting | Render.com | Docker container hosting |
| CI/CD | GitHub + Render | Auto-deploy on git push |

---

## 📚 Related Project

This project is a cloud re-architecture of an earlier monolithic vehicle tracking system:
👉 [Object-Tracking-with-YOLOv8](https://github.com/K-Rudra22/Object-Tracking-with-YOLOv8-Vehicles-Tracking-Counting-Entering-Leaving-and-Speed-Estimation)

---

## 👤 Author

**Rudra K** — [@K-Rudra22](https://github.com/K-Rudra22)

*Mini Project — Cloud Microservices and Applications (CMA) | 2025–2026*
