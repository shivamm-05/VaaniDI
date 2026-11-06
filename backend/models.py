from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class DatasetProfile(BaseModel):
    filename: str
    total_rows: int
    total_columns: int
    columns: List[str]
    column_types: Dict[str, str]
    missing_count: int
    missing_pct: float
    duplicate_rows: int
    memory_kb: float
    numeric_columns: List[str]
    categorical_columns: List[str]
    date_columns: List[str]
    sample_data: List[Dict[str, Any]]
    suggested_questions: Optional[List[Dict[str, Any]]] = None

class QueryRequest(BaseModel):
    query: str = Field(..., description="The user's analytical question")
    language: Optional[str] = Field("hi-IN", description="Language code e.g. hi-IN, en-IN")
    voice: Optional[str] = Field(None, description="Voice ID for speech synthesis")

class QueryResponse(BaseModel):
    query: str
    transcript: Optional[str] = None
    answer: str
    intent: str
    data: Optional[List[Dict[str, Any]]] = None
    chart_json: Optional[str] = None
    audio_url: Optional[str] = None
    audio_type: Optional[str] = "wav"
    language: str
    execution_time_ms: float
    metrics_summary: Optional[Dict[str, Any]] = None

class HealthResponse(BaseModel):
    status: str
    gnani_configured: bool
    ffmpeg_available: bool
    active_dataset: Optional[str] = None
    supported_languages: List[Dict[str, str]]
