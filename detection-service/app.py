from fastapi import FastAPI
from pydantic import BaseModel
import cv2
import math
import httpx
import os
from ultralytics import YOLO

app = FastAPI(title="Detection Service")

model = YOLO("yolov8n.pt")
VEHICLE_CLASSES = [2, 3, 5, 7]  # car, motorbike, bus, truck

ANALYTICS_SERVICE_URL = os.getenv("ANALYTICS_SERVICE_URL", "http://localhost:8002")

OUTPUT_DIR = "output_videos"
os.makedirs(OUTPUT_DIR, exist_ok=True)


class ProcessRequest(BaseModel):
    video_path: str
    video_id: str
    px_per_meter: float = 50.0


@app.get("/health")
def health():
    return {"status": "detection service running"}


@app.post("/process")
async def process_video(req: ProcessRequest):
    cap = cv2.VideoCapture(req.video_path)
    fps    = int(cap.get(cv2.CAP_PROP_FPS)) or 25
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Output video writer
    out_path = os.path.join(OUTPUT_DIR, f"{req.video_id}_tracked.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(out_path, fourcc, fps, (width, height))

    history        = {}
    last_positions = {}
    counted_ids    = set()
    rows           = []

    vehicle_counts = {cls: 0 for cls in VEHICLE_CLASSES}
    entering = 0
    leaving  = 0

    frame_id = 0
    line_y   = height // 2

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        frame_id += 1

        results = model.track(frame, persist=True, classes=VEHICLE_CLASSES, conf=0.35)

        if results and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            ids   = results[0].boxes.id.cpu().numpy()
            clss  = results[0].boxes.cls.cpu().numpy()

            for box, tid, cls in zip(boxes, ids, clss):
                x1, y1, x2, y2 = map(int, box)
                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)

                # Speed estimation
                speed_kmph = None
                prev = history.get(tid)
                if prev is not None:
                    px, py, pframe = prev
                    dist_px = math.hypot(cx - px, cy - py)
                    dist_m  = dist_px / req.px_per_meter
                    time_s  = max((frame_id - pframe) / fps, 1e-6)
                    speed_kmph = round((dist_m / time_s) * 3.6, 2)

                history[tid] = (cx, cy, frame_id)

                # Count unique vehicles
                if tid not in counted_ids:
                    vehicle_counts[int(cls)] += 1
                    counted_ids.add(tid)

                # Entry / exit detection
                if tid in last_positions:
                    prev_y = last_positions[tid]
                    if prev_y < line_y and cy >= line_y:
                        entering += 1
                    elif prev_y > line_y and cy <= line_y:
                        leaving += 1
                last_positions[tid] = cy

                # Draw annotations like your original project
                label = f"{int(tid)}:{model.names[int(cls)]}"
                if speed_kmph:
                    label += f" {int(speed_kmph)}km/h"

                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                cv2.rectangle(frame, (x1, y1 - 25), (x1 + tw, y1), (0, 0, 0), -1)
                cv2.putText(frame, label, (x1, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2, cv2.LINE_AA)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 255), 2)

                rows.append({
                    "vehicle_id":    int(tid),
                    "vehicle_class": model.names[int(cls)],
                    "frame":         frame_id,
                    "speed_kmph":    speed_kmph
                })

        # Top bar - left side (leaving counts)
        cv2.rectangle(frame, (0, 0), (width // 2, 50), (139, 0, 0), -1)
        left_text = "  ".join([f"{model.names[c]}:{vehicle_counts[c]}" for c in VEHICLE_CLASSES])
        cv2.putText(frame, left_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

        # Top bar - right side (entering counts)
        cv2.rectangle(frame, (width // 2, 0), (width, 50), (0, 100, 0), -1)
        right_text = f"Entering: {entering}   Leaving: {leaving}"
        cv2.putText(frame, right_text, (width // 2 + 10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

        # Red counting line in the middle
        cv2.line(frame, (0, line_y), (width, line_y), (0, 0, 255), 2)

        out.write(frame)

    cap.release()
    out.release()

    summary = {
        "video_id":       req.video_id,
        "total_vehicles": len(counted_ids),
        "entering":       entering,
        "leaving":        leaving,
        "vehicle_counts": {model.names[cls]: vehicle_counts[cls] for cls in vehicle_counts},
        "detections":     rows,
        "output_video":   out_path
    }

    async with httpx.AsyncClient(timeout=60) as client:
        await client.post(f"{ANALYTICS_SERVICE_URL}/store", json=summary)

    return {
        "status":       "processing complete",
        "video_id":     req.video_id,
        "output_video": out_path,
        "summary":      summary
    }