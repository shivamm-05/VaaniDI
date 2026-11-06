import time
import os
import uuid
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.config import (
    BASE_DIR,
    UPLOADS_DIR,
    OUTPUTS_DIR,
    SAMPLE_DATA_DIR,
    FRONTEND_DIR,
    MAX_UPLOAD_BYTES,
    MAX_UPLOAD_MB,
    SUPPORTED_LANGUAGES,
    SUPPORTED_VOICES,
    GNANI_DEFAULT_LANGUAGE,
    GNANI_DEFAULT_VOICE,
)
from backend.models import QueryRequest, QueryResponse, HealthResponse, DatasetProfile
from backend.audio import is_ffmpeg_available, convert_to_wav
from backend.speech import speech_service
from backend.analytics import active_session, QuestionPlanner

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("vaanibi.server")

app = FastAPI(
    title="VaaniBI — Voice-powered Data Intelligence",
    description="Conversational voice and text intelligence for CSV & Excel datasets using Gnani Prisma STT, Gnani Timbre TTS, Pandas, and Plotly.",
    version="1.0.0",
)

# Enable CORS for local testing and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# Auto-load sample dataset if available on startup
@app.on_event("startup")
def startup_event():
    default_sample = SAMPLE_DATA_DIR / "supermarket_sales.csv"
    if default_sample.exists() and active_session.df is None:
        try:
            active_session.load_file(str(default_sample), "supermarket_sales.csv")
            logger.info("Auto-loaded default sample dataset: supermarket_sales.csv")
        except Exception as e:
            logger.warning(f"Could not load default sample dataset: {e}")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    with open(index_file, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/health", response_model=HealthResponse)
async def get_health():
    return HealthResponse(
        status="ok",
        gnani_configured=speech_service.is_configured(),
        ffmpeg_available=is_ffmpeg_available(),
        active_dataset=active_session.filename,
        supported_languages=SUPPORTED_LANGUAGES,
    )

@app.get("/api/voices")
async def get_voices(language: str = "hi-IN"):
    voices = SUPPORTED_VOICES.get(language, ["Nalini", "Pranav"])
    return {"language": language, "voices": voices}

@app.get("/api/dataset")
async def get_dataset_info():
    if active_session.profile is None:
        # Load sample dataset if available
        sample_path = SAMPLE_DATA_DIR / "supermarket_sales.csv"
        if sample_path.exists():
            active_session.load_file(str(sample_path), "supermarket_sales.csv")

    if active_session.profile is None:
        raise HTTPException(status_code=404, detail="No active dataset loaded.")
    return active_session.profile

@app.post("/api/upload")
async def upload_dataset(file: UploadFile = File(...)):
    start_time = time.time()
    filename = file.filename or "uploaded_data.csv"
    ext = Path(filename).suffix.lower()

    if ext not in [".csv", ".xlsx", ".xls"]:
        raise HTTPException(status_code=400, detail="Only .csv and .xlsx/.xls files are supported.")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds maximum allowed size of {MAX_UPLOAD_MB} MB.")

    saved_path = UPLOADS_DIR / f"{uuid.uuid4().hex[:8]}_{filename}"
    with open(saved_path, "wb") as f:
        f.write(content)

    try:
        profile = active_session.load_file(str(saved_path), filename)
        duration_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "success": True,
            "profile": profile,
            "upload_time_ms": duration_ms,
            "message": f"Successfully loaded {filename} ({profile['total_rows']} rows, {profile['total_columns']} columns)",
        }
    except Exception as e:
        logger.error(f"Error loading dataset {filename}: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to parse dataset: {str(e)}")

@app.post("/api/query", response_model=QueryResponse)
async def execute_typed_query(req: QueryRequest):
    start_time = time.time()
    query_text = req.query.strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    lang = req.language or GNANI_DEFAULT_LANGUAGE
    voice = req.voice or GNANI_DEFAULT_VOICE

    # Execute deterministic pandas analytics
    result = QuestionPlanner.execute_query(query_text, language=lang)
    answer_text = result["answer"]

    # Generate voice output using Gnani Timbre
    tts_res = speech_service.synthesize(answer_text, voice=voice, language=lang)
    audio_url = tts_res.get("audio_url")

    duration_ms = round((time.time() - start_time) * 1000, 2)

    return QueryResponse(
        query=query_text,
        transcript=None,
        answer=answer_text,
        intent=result["intent"],
        data=result["data"],
        chart_json=result["chart_json"],
        audio_url=audio_url,
        audio_type="wav",
        language=lang,
        execution_time_ms=duration_ms,
        metrics_summary=result["metrics_summary"],
    )

@app.post("/api/voice-query", response_model=QueryResponse)
async def execute_voice_query(
    audio: UploadFile = File(...),
    language: Optional[str] = Form("hi-IN"),
    voice: Optional[str] = Form(None),
):
    start_time = time.time()
    lang = language or GNANI_DEFAULT_LANGUAGE
    chosen_voice = voice or GNANI_DEFAULT_VOICE

    # Save audio upload
    temp_id = uuid.uuid4().hex[:8]
    incoming_ext = Path(audio.filename or "recording.webm").suffix.lower()
    raw_path = UPLOADS_DIR / f"raw_voice_{temp_id}{incoming_ext}"
    wav_path = UPLOADS_DIR / f"proc_voice_{temp_id}.wav"

    audio_bytes = await audio.read()
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty audio recording received.")

    with open(raw_path, "wb") as f:
        f.write(audio_bytes)

    # Convert to 16 kHz mono WAV
    try:
        convert_to_wav(raw_path, wav_path, sample_rate=16000)
    except Exception as e:
        logger.error(f"Audio conversion failed: {e}")
        # If conversion failed, try using raw file if it's already wav
        if raw_path.suffix.lower() == ".wav":
            wav_path = raw_path
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Audio format conversion failed: {str(e)}. Please install FFmpeg or record in WAV.",
            )

    # Transcribe via Gnani Prisma STT
    stt_res = speech_service.transcribe(wav_path, language_code=lang)
    transcript = stt_res.get("transcript", "").strip()

    if not transcript:
        # Check if error message returned
        err = stt_res.get("error", "No speech detected in audio recording.")
        return QueryResponse(
            query="[Voice Query]",
            transcript="[No speech detected or STT offline]",
            answer=f"आवाज़ पहचानी नहीं जा सकी: {err}",
            intent="STT_ERROR",
            data=None,
            chart_json=None,
            audio_url=None,
            language=lang,
            execution_time_ms=round((time.time() - start_time) * 1000, 2),
            metrics_summary=None,
        )

    # Execute analytics on the transcript
    result = QuestionPlanner.execute_query(transcript, language=lang)
    answer_text = result["answer"]

    # Synthesize answer back via Gnani Timbre TTS
    tts_res = speech_service.synthesize(answer_text, voice=chosen_voice, language=lang)
    audio_url = tts_res.get("audio_url")

    duration_ms = round((time.time() - start_time) * 1000, 2)

    return QueryResponse(
        query=transcript,
        transcript=transcript,
        answer=answer_text,
        intent=result["intent"],
        data=result["data"],
        chart_json=result["chart_json"],
        audio_url=audio_url,
        audio_type="wav",
        language=lang,
        execution_time_ms=duration_ms,
        metrics_summary=result["metrics_summary"],
    )

@app.get("/api/audio/{filename}")
async def get_audio_file(filename: str):
    file_path = OUTPUTS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found.")
    return FileResponse(file_path, media_type="audio/wav")

@app.get("/api/download-zip")
async def download_project_zip():
    zip_path = BASE_DIR.parent / "vaani-bi.zip"
    if not zip_path.exists():
        zip_path = BASE_DIR / "vaani-bi.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="ZIP archive not found.")
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename="vaani-bi.zip",
    )
