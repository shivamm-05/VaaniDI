import os
import shutil
import subprocess
import wave
import struct
from pathlib import Path

def is_ffmpeg_available() -> bool:
    """Check if ffmpeg is available on the system PATH."""
    return shutil.which("ffmpeg") is not None

def is_wav_file(file_path: Path) -> bool:
    """Check whether the file is a standard RIFF/WAVE audio file."""
    try:
        with open(file_path, "rb") as f:
            header = f.read(12)
            return header[:4] == b"RIFF" and header[8:12] == b"WAVE"
    except Exception:
        return False

def convert_to_wav(input_path: Path, output_path: Path, sample_rate: int = 16000) -> Path:
    """
    Convert an audio file (WebM, OGG, MP3, or WAV) to 16 kHz mono 16-bit PCM WAV.
    Uses ffmpeg if installed. If ffmpeg is absent and input is already WAV,
    verifies/copies the WAV file directly.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if is_ffmpeg_available():
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(input_path),
            "-ar", str(sample_rate),
            "-ac", "1",
            "-c:a", "pcm_s16le",
            str(output_path),
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg conversion failed: {res.stderr.decode('utf-8', errors='ignore')}")
        return output_path
    else:
        # Check if already a valid WAV
        if is_wav_file(input_path):
            if input_path.resolve() != output_path.resolve():
                shutil.copyfile(input_path, output_path)
            return output_path
        else:
            raise RuntimeError(
                "FFmpeg is not installed on PATH to convert browser WebM audio to WAV. "
                "Please install FFmpeg or use a browser that records in WAV directly."
            )

def create_beep_wav(output_path: Path, duration_sec: float = 0.5, freq: float = 440.0, sample_rate: int = 16000) -> Path:
    """Generate a clean synthetic beep/wav for audio test or fallback audio."""
    import math
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    num_samples = int(duration_sec * sample_rate)
    with wave.open(str(output_path), "w") as wav_file:
        wav_file.setnchannels(1)      # mono
        wav_file.setsampwidth(2)      # 16-bit
        wav_file.setframerate(sample_rate)
        for i in range(num_samples):
            # smooth envelope
            envelope = math.sin(math.pi * i / num_samples)
            sample = int(10000.0 * envelope * math.sin(2.0 * math.pi * freq * i / sample_rate))
            wav_file.writeframes(struct.pack("<h", sample))
    return output_path
