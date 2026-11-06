import os
import uuid
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union

from backend.config import (
    GNANI_API_KEY,
    GNANI_STT_MODEL,
    GNANI_TTS_MODEL,
    GNANI_TTS_VERSION,
    GNANI_DEFAULT_LANGUAGE,
    GNANI_DEFAULT_VOICE,
    OUTPUTS_DIR,
)
from backend.audio import create_beep_wav

logger = logging.getLogger("vaanibi.speech")

class SpeechManager:
    """
    Manages speech-to-text (Gnani Prisma) and text-to-speech (Gnani Timbre).
    Supports both the native Gnani SDK (gnani-vachana) and Transformers pipeline adapter,
    with graceful fallback when offline or during demo test without credentials.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        stt_model: Optional[str] = None,
        tts_model: Optional[str] = None,
        tts_version: Optional[str] = None,
    ):
        self.api_key = (api_key or GNANI_API_KEY or "").strip()
        self.stt_model_name = stt_model or GNANI_STT_MODEL
        self.tts_model_name = tts_model or GNANI_TTS_MODEL
        self.tts_version = tts_version or GNANI_TTS_VERSION

        self.stt_client = None
        self.tts_client = None
        self._init_clients()

    def _init_clients(self):
        """Initialize Gnani clients."""
        if not self.api_key:
            logger.warning("No GNANI_API_KEY provided. Speech features will run in mock/fallback mode.")
            return

        os.environ["GNANI_API_KEY"] = self.api_key

        try:
            from gnani.stt import GnaniSTTClient
            from gnani.tts import GnaniTTSClient

            self.stt_client = GnaniSTTClient(api_key=self.api_key)
            self.tts_client = GnaniTTSClient(api_key=self.api_key)
            logger.info("Gnani SDK (gnani-vachana) initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Gnani SDK clients: {e}")

    def is_configured(self) -> bool:
        """Check if a real API key is configured."""
        return bool(self.api_key and self.api_key != "replace_with_your_gnani_api_key")

    def transcribe(self, audio_path: Union[str, Path], language_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe an audio file using Gnani Prisma STT.
        """
        audio_path = Path(audio_path)
        lang = language_code or GNANI_DEFAULT_LANGUAGE

        if not audio_path.exists():
            return {
                "success": False,
                "transcript": "",
                "error": f"Audio file not found: {audio_path}",
                "engine": "none",
            }

        # 1. Try Gnani SDK Client (Primary production method)
        if self.stt_client:
            try:
                res = self.stt_client.transcribe(
                    audio=audio_path,
                    language_code=lang,
                    format="transcribe" if lang in ("hi-IN", "en-IN") else "verbatim",
                )
                transcript = res.get("transcript", "").strip()
                detected_lang = res.get("detected_language_code", lang)
                return {
                    "success": True,
                    "transcript": transcript,
                    "language": detected_lang,
                    "engine": "gnani-prisma-sdk",
                    "raw": res,
                }
            except Exception as e:
                logger.warning(f"Gnani SDK transcribe failed: {e}")
                err_str = str(e).lower()
                if "connection" in err_str or "nameresolution" in err_str or "timeout" in err_str:
                    return {
                        "success": False,
                        "transcript": "",
                        "error": "Cannot reach Gnani speech services. Please verify internet access and GNANI_API_KEY.",
                        "engine": "fallback",
                    }

        # 2. Transformers pipeline fallback (if pre-cached)
        try:
            from transformers import pipeline
            stt_pipe = pipeline("automatic-speech-recognition", model=self.stt_model_name, trust_remote_code=True)
            result = stt_pipe(str(audio_path), language_code=lang)
            text = result.get("text") or result.get("transcript") or "" if isinstance(result, dict) else str(result)
            return {
                "success": True,
                "transcript": text.strip(),
                "language": lang,
                "engine": "transformers-pipeline",
            }
        except Exception as e:
            logger.debug(f"Transformers pipeline STT omitted/failed: {e}")

        return {
            "success": False,
            "transcript": "",
            "error": "STT transcription could not be completed with Gnani Prisma. Please ensure GNANI_API_KEY is valid and internet access is active.",
            "engine": "fallback",
        }

    def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        language: Optional[str] = None,
        output_filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Synthesize text to speech using Gnani Timbre.
        Returns a dictionary with audio file path, relative URL, and metadata.
        """
        voice = voice or GNANI_DEFAULT_VOICE
        lang = language or GNANI_DEFAULT_LANGUAGE
        filename = output_filename or f"speech_{uuid.uuid4().hex[:10]}.wav"
        output_path = OUTPUTS_DIR / filename

        clean_text = text.strip()
        if not clean_text:
            create_beep_wav(output_path, duration_sec=0.2)
            return {
                "success": True,
                "audio_path": str(output_path),
                "audio_url": f"/api/audio/{filename}",
                "engine": "silent-wav",
            }

        # 1. Try Gnani SDK Client
        if self.tts_client:
            try:
                audio_bytes = self.tts_client.synthesize(
                    text=clean_text,
                    voice=voice,
                    model=self.tts_version,
                    language=lang,
                )
                if audio_bytes and len(audio_bytes) > 0:
                    with open(output_path, "wb") as f:
                        f.write(audio_bytes)
                    return {
                        "success": True,
                        "audio_path": str(output_path),
                        "audio_url": f"/api/audio/{filename}",
                        "voice": voice,
                        "language": lang,
                        "engine": "gnani-timbre-sdk",
                    }
            except Exception as e:
                logger.warning(f"Gnani SDK TTS synthesize failed: {e}")
                err_str = str(e).lower()
                if "connection" in err_str or "nameresolution" in err_str or "timeout" in err_str:
                    create_beep_wav(output_path, duration_sec=0.4, freq=520.0)
                    return {
                        "success": False,
                        "audio_path": str(output_path),
                        "audio_url": f"/api/audio/{filename}",
                        "error": "Gnani Timbre offline or unreachable.",
                        "engine": "fallback-tone",
                    }

        # 2. Fallback tone so audio player always receives a valid playable WAV
        try:
            create_beep_wav(output_path, duration_sec=0.4, freq=520.0)
            return {
                "success": False,
                "audio_path": str(output_path),
                "audio_url": f"/api/audio/{filename}",
                "error": "Gnani Timbre synthesis not available or quota limit reached.",
                "engine": "fallback-tone",
            }
        except Exception as e:
            return {
                "success": False,
                "audio_path": None,
                "audio_url": None,
                "error": str(e),
                "engine": "none",
            }

speech_service = SpeechManager()
