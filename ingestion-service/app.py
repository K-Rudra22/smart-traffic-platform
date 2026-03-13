from fastapi import FastAPI, UploadFile, File, Form
import httpx
import shutil
import os
import uuid

app = FastAPI(title="Ingestion Service")

UPLOAD_DIR = "uploaded_videos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

DETECTION_SERVICE_URL = os.getenv("DETECTION_SERVICE_URL", "http://localhost:8001")


@app.get("/health")
def health():
    return {"status": "ingestion service running"}


@app.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    px_per_meter: float = Form(50.0)
):
    """
    Accepts a video upload from the dashboard,
    saves it locally, then tells the detection service to process it.
    """
    # Give the video a unique filename to avoid collisions
    video_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[-1]
    video_path = os.path.join(UPLOAD_DIR, f"{video_id}{ext}")

    with open(video_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Tell the detection service to process this video
    async with httpx.AsyncClient(timeout=600) as client:
        response = await client.post(
            f"{DETECTION_SERVICE_URL}/process",
            json={
                "video_path": video_path,
                "video_id": video_id,
                "px_per_meter": px_per_meter
            }
        )
        result = response.json()

    return {
        "video_id": video_id,
        "message": "Video uploaded and sent for processing",
        "detection_result": result
    }
