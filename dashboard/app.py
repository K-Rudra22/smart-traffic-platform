import streamlit as st
import requests
import pandas as pd
import os

# The dashboard talks ONLY to the analytics service
# It no longer runs any ML code itself
INGESTION_URL  = os.getenv("INGESTION_SERVICE_URL",  "http://localhost:8000")
ANALYTICS_URL  = os.getenv("ANALYTICS_SERVICE_URL",  "http://localhost:8002")

st.set_page_config(page_title="Smart Traffic Analytics", layout="wide")
st.title("🚦 Smart Traffic Analytics Platform")

# ── Sidebar: upload ──────────────────────────────────────────────
st.sidebar.header("Upload a video")
uploaded = st.sidebar.file_uploader("Traffic video", type=["mp4", "avi", "mov"])
px_per_meter = st.sidebar.number_input("Pixels per meter", value=50.0, min_value=1.0)

if uploaded and st.sidebar.button("▶️ Process"):
    with st.spinner("Uploading and processing... (this may take a minute)"):
        resp = requests.post(
            f"{INGESTION_URL}/upload",
            files={"file": (uploaded.name, uploaded.getvalue(), "video/mp4")},
            data={"px_per_meter": px_per_meter},
            timeout=600
        )
    if resp.status_code == 200:
        st.sidebar.success("✅ Done!")
        st.rerun()
    else:
        st.sidebar.error(f"Error: {resp.text}")

# ── Main: session history ─────────────────────────────────────────
st.header("Session History")

try:
    sessions_resp = requests.get(f"{ANALYTICS_URL}/sessions", timeout=10)
    sessions = sessions_resp.json().get("sessions", [])
except Exception as e:
    st.warning(f"Could not reach analytics service: {e}")
    sessions = []

if not sessions:
    st.info("No sessions yet. Upload a video to get started.")
else:
    # Summary table
    summary_df = pd.DataFrame([{
        "Video ID": s["video_id"][:8] + "...",
        "Total Vehicles": s["total_vehicles"],
        "Entering": s["entering"],
        "Leaving": s["leaving"],
        "Processed At": s["processed_at"],
        "_video_id": s["video_id"]   # hidden, for detail lookup
    } for s in sessions])

    st.dataframe(
        summary_df.drop(columns=["_video_id"]),
        use_container_width=True
    )

    # ── Detail view ────────────────────────────────────────────────
    st.header("Session Detail")
    video_ids = [s["video_id"] for s in sessions]
    selected = st.selectbox(
        "Select a session",
        video_ids,
        format_func=lambda x: x[:8] + "..."
    )

    if selected:
        detail = requests.get(
            f"{ANALYTICS_URL}/sessions/{selected}", timeout=10
        ).json()
        sess = detail.get("session", {})
        detections = detail.get("detections", [])

        if sess:
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Vehicles", sess["total_vehicles"])
            col2.metric("Entering",       sess["entering"])
            col3.metric("Leaving",        sess["leaving"])

            # Vehicle class breakdown
            counts = sess.get("vehicle_counts", {})
            if counts:
                st.subheader("Vehicle type breakdown")
                st.bar_chart(pd.DataFrame(
                    counts.items(), columns=["Type", "Count"]
                ).set_index("Type"))

        if detections:
            df = pd.DataFrame(detections)

            # Speed chart
            speed_df = df[df["speed_kmph"].notna()]
            if not speed_df.empty:
                st.subheader("Speed over frames")
                chart_df = speed_df.groupby("frame")["speed_kmph"].mean().reset_index()
                st.line_chart(chart_df.set_index("frame"))

            # Speed stats per class
            stats = requests.get(
                f"{ANALYTICS_URL}/stats/speed-distribution/{selected}", timeout=10
            ).json().get("speed_stats", [])
            if stats:
                st.subheader("Speed stats by vehicle type")
                st.dataframe(pd.DataFrame(stats), use_container_width=True)

            # Raw detections table + download
            st.subheader("Raw detection log")
            st.dataframe(df[["vehicle_id","vehicle_class","frame","speed_kmph"]],
                         use_container_width=True)
            st.download_button(
                "📥 Download CSV",
                data=df.to_csv(index=False),
                file_name=f"detections_{selected[:8]}.csv",
                mime="text/csv"
            )
