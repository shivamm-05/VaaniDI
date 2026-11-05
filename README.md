# VaaniBI — Voice-powered Data Intelligence

VaaniBI is an MVP web app for asking questions about uploaded CSV/Excel data. It uses:
- **Gnani Prisma** through the `gnani/gnani` Transformers adapter (and `gnani-vachana` SDK) for speech-to-text.
- **Gnani Timbre** through the same adapter for text-to-speech.
- Pandas for actual calculations (the app never executes arbitrary LLM-generated Python/SQL).
- Plotly for interactive charts.
- FastAPI for the backend and vanilla HTML/CSS/JS for the frontend.

## 1. Requirements

- Python 3.10, 3.11, or newer.
- FFmpeg installed and available on PATH (browser audio is recorded as WebM/WAV and converted to 16 kHz mono WAV before transcription; the web client also features native in-browser 16 kHz mono PCM WAV recording).
- A Gnani API key created in your Gnani dashboard.
- Internet access for Gnani hosted inference and the Plotly CDN.

## 2. Setup on Windows (VS Code)

Open the project folder in VS Code. In the terminal:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Install FFmpeg and make sure `ffmpeg -version` works in a NEW terminal. Then:
```powershell
copy .env.example .env
```
Open `.env` and replace `GNANI_API_KEY` with your real key. Never share or commit this file.

## 3. Run

From the project root:
```powershell
uvicorn backend.main:app --reload
```
Open http://127.0.0.1:8000

Upload a CSV or Excel file. You can use your supermarket sales dataset or any tidy dataset. Ask typed questions first, then test the microphone. First Gnani model initialization may take a little longer.

## 4. Gnani configuration

The code follows Gnani's currently published `gnani/gnani` adapter usage:
```python
from transformers import pipeline
stt = pipeline("automatic-speech-recognition", model="gnani/gnani", trust_remote_code=True)
result = stt("audio.wav", language_code="hi-IN")

tts = pipeline("text-to-speech", model="gnani/gnani", trust_remote_code=True)
result = tts("नमस्ते", voice="Nalini", model="timbre-v2.5",
             language="hi-IN", tts_mode="rest", container="wav")
```
If your programme dashboard exposes a newer/different API model version or a voice name different from the configured defaults, update `.env` accordingly. The voice IDs shown in the dashboard must match the model version used by the SDK. The playground selection alone does not automatically configure API credentials.

Official references:
- Gnani model integration: https://huggingface.co/gnani/gnani
- Gnani API docs: https://docs.gnani.ai/api/introduction/introduction
- Prisma v3 overview: https://www.gnani.ai/resources/prisma-v3

## 5. Supported question patterns in this MVP

The built-in analytics engine handles common data questions such as:
- Which product/category/branch has the highest sales?
- Compare sales by category or branch.
- What is the average quantity/price/sales by group?
- Show monthly sales trend (when a date column exists).
- How many rows are in the dataset?

Column detection uses common English/Hindi labels. For other datasets, edit `ALIASES` in `backend/analytics.py` or improve the question planner.

## 6. Current MVP limitations (be transparent in the demo)

- The analytics question parser is rule-based, not a general LLM. It handles common aggregation/comparison/trend questions and may need column aliases for unfamiliar datasets.
- The app keeps uploaded data in process memory. Restarting the server clears sessions. Do not deploy this as a multi-user production service without authentication, persistent storage, quotas, and privacy controls.
- No arbitrary Python or SQL is generated/executed from user prompts.
- Language options are displayed from Gnani's published supported-language set; verify exact current STT and TTS support and the matching voice before claiming each language works end-to-end.
- Speech recognition needs FFmpeg to convert browser WebM recordings to 16 kHz mono WAV (with client-side PCM WAV fallback).
- Timbre may be beta or have plan-specific limits. If it fails, typed analysis still works.

## 7. Next improvements

1. Add a schema-aware LLM planner that returns a strict JSON plan (operation, metric, group-by, filters); validate every column/operation before Pandas executes it.
2. Add date-range filters, sorting, correlation, outlier detection and forecast modules.
3. Add export to PDF/CSV and saved reports.
4. Add authentication, persistent dataset storage, deletion controls and upload scanning before public deployment.
5. Add tests for numeric results against hand-calculated expected values.

## 8. Challenge demo flow

1. Upload a dataset.
2. Show automatic profile (rows, columns, missing values, duplicates).
3. Ask a voice question in Hindi/English.
4. Show Prisma transcript.
5. Show the Pandas-derived answer and chart.
6. Play Timbre spoken output.
7. Ask a second question to demonstrate that results are dynamic.

Never show your API key in screen recordings or GitHub.
