import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Gnani API & Voice Engine Configurations
GNANI_API_KEY = os.getenv("GNANI_API_KEY", "").strip()
GNANI_STT_MODEL = os.getenv("GNANI_STT_MODEL", "gnani/gnani")
GNANI_TTS_MODEL = os.getenv("GNANI_TTS_MODEL", "gnani/gnani")
GNANI_TTS_VERSION = os.getenv("GNANI_TTS_VERSION", "timbre-v2.5")
GNANI_DEFAULT_LANGUAGE = os.getenv("GNANI_DEFAULT_LANGUAGE", "hi-IN")
GNANI_DEFAULT_VOICE = os.getenv("GNANI_DEFAULT_VOICE", "Nalini")

# Storage & Upload limits
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"
FRONTEND_DIR = BASE_DIR / "frontend"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# Supported Languages for Gnani STT & TTS
SUPPORTED_LANGUAGES = [
    {"code": "hi-IN", "label": "Hindi (हिंदी)"},
    {"code": "en-IN", "label": "English (India)"},
    {"code": "ta-IN", "label": "Tamil (தமிழ்)"},
    {"code": "te-IN", "label": "Telugu (తెలుగు)"},
    {"code": "kn-IN", "label": "Kannada (ಕನ್ನಡ)"},
    {"code": "mr-IN", "label": "Marathi (मराठी)"},
    {"code": "bn-IN", "label": "Bengali (বাংলা)"},
    {"code": "gu-IN", "label": "Gujarati (ગુજરાતી)"},
    {"code": "ml-IN", "label": "Malayalam (മലയാളം)"},
]

# Supported voices per language
SUPPORTED_VOICES = {
    "hi-IN": ["Nalini", "Pranav", "Maya", "Amol"],
    "en-IN": ["Nalini", "Pranav", "Maya", "Amol"],
    "ta-IN": ["Vani", "Anbu"],
    "te-IN": ["Kavya", "Venkat"],
    "kn-IN": ["Soumya", "Ravi"],
    "mr-IN": ["Radha", "Kunal"],
    "bn-IN": ["Pooja", "Arjun"],
    "gu-IN": ["Diya", "Jay"],
    "ml-IN": ["Asha", "Anoop"],
}
