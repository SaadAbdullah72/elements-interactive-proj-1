"""
IntelliHealth AI Clinical System — Backend (Upgraded v4.1)
FastAPI + Gemma persona (Groq) · ADA 2026 auto-loaded guidelines · Session persistence · Continuous Learning · PDF Export

CHANGELOG v4.1:
  - max_tokens raised from 1536 → 8192 (fixes truncated responses)
  - ADA engine "not found" fallback filtered out (stops model echoing dead-end message)
  - guideline_ctx hard-capped at 4000 chars to preserve response token budget
  - past_cases_ctx capped at 1500 chars
  - Richer, more directive system prompts for detailed consultation responses
  - _is_medical_query non-medical blocklist tightened (removed "history", "code", "language")
  - temperature raised slightly to 0.4 for more expansive clinical reasoning
  - Added explicit "do not truncate" instruction to every system prompt
"""

import os
import io
import asyncio
import base64
import uuid
import json
import jwt
import threading
import re
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import (
    FastAPI,
    File,
    UploadFile,
    HTTPException,
    BackgroundTasks,
    APIRouter,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
from pymongo import MongoClient, UpdateOne
from pydantic import BaseModel
from groq import Groq
from pypdf import PdfReader
from dotenv import load_dotenv

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# Import local modules
try:
    from doctor_auth import router as doctor_router
    from auth import router as auth_router
    from profile import router as profile_router
    from email_service import send_diagnosis_email
    from ada_guidelines_engine import get_ada_engine
except ImportError:
    print("[Warning] Some local modules not found. Ensure they exist on Replit.")
    doctor_router = APIRouter()
    auth_router = APIRouter()
    profile_router = APIRouter()

    def send_diagnosis_email(*args, **kwargs):
        pass

    def get_ada_engine():
        return None


load_dotenv()

# ── Global State & Config ───────────────────────────────────────────────────

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_GUIDELINES_DIR = os.path.join(os.path.dirname(__file__), "guidelines")
guideline_load_status = {"loaded": False, "details": "Not yet loaded"}


async def load_guidelines_task():
    global guideline_load_status
    ada = get_ada_engine()
    if not ada:
        guideline_load_status["details"] = "ADA Engine not available"
        return
    try:
        print("[Guidelines] Starting background guideline load...")
        if not os.path.exists(_GUIDELINES_DIR):
            os.makedirs(_GUIDELINES_DIR, exist_ok=True)

        result = await asyncio.to_thread(ada.auto_load_from_directory, _GUIDELINES_DIR)
        guideline_load_status["loaded"] = True
        guideline_load_status["details"] = (
            f"Loaded {result['loaded']} files | "
            f"{result['total_recommendations']} recommendations | "
            f"{result['sample_cases']} sample cases"
        )
        print(f"[Guidelines] {guideline_load_status['details']}")

        if result.get("errors"):
            for err in result["errors"]:
                print(f"[Guidelines] Load error: {err}")
                guideline_load_status["details"] += f" | Errors: {err}"

    except Exception as e:
        guideline_load_status["loaded"] = False
        guideline_load_status["details"] = f"Background load failed: {e}"
        print(f"[Guidelines] Background load failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[System] IntelliHealth AI Backend Starting...")
    asyncio.create_task(load_guidelines_task())
    yield
    print("[System] IntelliHealth AI Backend Shutting Down")


# ── App Initialization ───────────────────────────────────────────────────────

app = FastAPI(
    title="IntelliHealth AI Clinical System",
    description="Advanced AI-assisted clinical decision support with continuous learning",
    version="4.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── CORS Configuration ───────────────────────────────────────────────────────

DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8080",
    "https://tmp.diabassist.app",
    "https://diabassist.app",
    "https://www.diabassist.app",
    "https://health-zeta-three.vercel.app",
]

extra_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
if extra_origins:
    DEFAULT_ALLOWED_ORIGINS.extend(
        [o.strip() for o in extra_origins.split(",") if o.strip()]
    )

for env_name in ("FRONTEND_URL", "REPLIT_DOMAINS", "REPLIT_HOST"):
    value = os.getenv(env_name, "")
    if value:
        if value.startswith("http"):
            DEFAULT_ALLOWED_ORIGINS.append(value.rstrip("/"))
        else:
            DEFAULT_ALLOWED_ORIGINS.append(f"https://{value.lstrip('.').rstrip('/')}")

ALLOWED_ORIGINS = list(dict.fromkeys(DEFAULT_ALLOWED_ORIGINS))
print(f"[CORS] Allowed origins: {ALLOWED_ORIGINS}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://.*\.diabassist\.app",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
    max_age=600,
)

# ── Global Exception Handlers ────────────────────────────────────────────────


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback

    traceback.print_exc()
    origin = request.headers.get("origin", "*")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": "Authorization,Content-Type,Accept,Origin,User-Agent",
            "Access-Control-Allow-Credentials": "true",
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    origin = request.headers.get("origin", "*")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": "Authorization,Content-Type,Accept,Origin,User-Agent",
            "Access-Control-Allow-Credentials": "true",
        },
    )


# ── MongoDB Setup ────────────────────────────────────────────────────────────

mongodburl = os.getenv("MONGODB_URL", "mongodb://localhost:27017/")
db_name = os.getenv("MONGODB_DBFULL_DB", "dbfull")
_mongo = None
_db = None

patients_collection = None
analyses_collection = None
email_notifications_collection = None
learning_journal_collection = None
chat_sessions_collection = None


def init_db():
    global \
        _mongo, \
        _db, \
        patients_collection, \
        analyses_collection, \
        email_notifications_collection, \
        learning_journal_collection, \
        chat_sessions_collection

    try:
        _mongo = MongoClient(mongodburl, serverSelectionTimeoutMS=5000)
        _mongo.admin.command("ping")
        _db = _mongo[db_name]

        patients_collection = _db["patients"]
        analyses_collection = _db["analyses"]
        email_notifications_collection = _db["email_notifications"]
        learning_journal_collection = _db["learning_journal"]
        chat_sessions_collection = _db["chat_sessions"]

        learning_journal_collection.create_index([("disease", 1), ("query_type", 1)])
        learning_journal_collection.create_index([("rating", -1)])
        chat_sessions_collection.create_index([("session_id", 1)], unique=True)
        chat_sessions_collection.create_index([("doctor_id", 1), ("updated_at", -1)])

        print(f"[DB] Connected to MongoDB: {db_name}")
    except Exception as e:
        print(f"[DB] Connection failed: {e}")


init_db()

# ── Groq Client & Model Configuration ────────────────────────────────────────
#
# Current active production models on GroqCloud (as of June 2026):
#   llama-3.3-70b-versatile   — 280 t/s  | 131k ctx | best quality general use
#   openai/gpt-oss-120b       — 500 t/s  | 131k ctx | flagship, reasoning
#   openai/gpt-oss-20b        — 1000 t/s | 131k ctx | fast, lightweight
#   llama-3.1-8b-instant      — 560 t/s  | 131k ctx | ultra-fast fallback
#
# REMOVED (decommissioned):
#   gemma2-9b-it, llama-3.1-70b-versatile, mixtral-8x7b-32768


def _resolve_groq_api_key() -> str:
    for name in ("GROQ_API_KEY", "GROQ_KEY", "GROQ_API_TOKEN", "GROQ_TOKEN"):
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return ""


groq_api_key = _resolve_groq_api_key()
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None

groq_model_primary = "llama-3.3-70b-versatile"
groq_model_fallbacks = [
    "llama-3.1-8b-instant",
    "openai/gpt-oss-20b",
]
groq_models = [groq_model_primary] + groq_model_fallbacks
groq_model = groq_model_primary

# Keep the Groq request comfortably under the platform TPM cap (reported as 8000
# tokens/request on the on-demand tier). The old 8192-token ceiling can still
# exceed the limit once the prompt context is included, so we use a conservative
# output budget, enforce a hard request-size guard, and limit concurrent calls.
_MAX_RESPONSE_TOKENS = 1800
_MAX_REQUEST_TOKENS = 5000
_MAX_CONCURRENT_GROQ_CALLS = 2
_groq_call_semaphore = threading.Semaphore(_MAX_CONCURRENT_GROQ_CALLS)


def _estimate_prompt_tokens(messages: List[Dict[str, Any]]) -> int:
    """Rough character-to-token estimate for TPM guardrails."""
    total_chars = 0
    for msg in messages:
        content = msg.get("content", "") if isinstance(msg, dict) else ""
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict):
                    text_parts.append(part.get("text", ""))
                else:
                    text_parts.append(str(part))
            content = " ".join(text_parts)
        total_chars += len(str(content))
    return max(1, total_chars // 4)


def _safe_max_tokens(messages: List[Dict[str, Any]], requested_max_tokens: int) -> int:
    estimated_prompt = _estimate_prompt_tokens(messages)
    safe_budget = _MAX_REQUEST_TOKENS - estimated_prompt
    safe_budget = max(512, safe_budget)
    safe_max_tokens = min(requested_max_tokens, safe_budget)

    if safe_max_tokens < requested_max_tokens:
        print(
            "[AI] TPM guardrail reduced max_tokens from "
            f"{requested_max_tokens} to {safe_max_tokens} "
            f"(estimated prompt tokens: {estimated_prompt})."
        )

    return safe_max_tokens


def _call_groq_with_model(messages, max_tokens=_MAX_RESPONSE_TOKENS, temperature=0.4):
    """
    temperature raised from 0.3 → 0.4:
      - 0.3 made responses overly terse and repetitive across queries
      - 0.4 produces more expansive clinical reasoning while remaining factual
    """
    last_error = None
    safe_max_tokens = _safe_max_tokens(messages, max_tokens)

    with _groq_call_semaphore:
        for model in groq_models:
            try:
                print(f"[AI] Attempting model: {model}")
                completion = groq_client.chat.completions.create(
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=safe_max_tokens,
                )
                return completion, model
            except Exception as e:
                err_text = str(e).lower()
                print(f"[AI] Model {model} failed: {e}")
                last_error = e
                if "invalid_api_key" in err_text or "authenticationerror" in err_text:
                    raise RuntimeError(
                        "Groq rejected the API key (401 invalid_api_key). "
                        "Update the live GROQ_API_KEY secret and redeploy."
                    ) from e
                if any(
                    x in err_text
                    for x in [
                        "rate limit",
                        "quota",
                        "overloaded",
                        "503",
                        "429",
                        "decommissioned",
                        "model_decommissioned",
                        "not found",
                        "does not exist",
                        "invalid model",
                    ]
                ):
                    print(
                        f"[AI] Model {model} unavailable/decommissioned/rate-limited — trying next fallback."
                    )
                    continue
                else:
                    raise e
    raise last_error or RuntimeError("Unknown Groq error: All models failed")


# ── Pydantic Models ──────────────────────────────────────────────────────────


class ClinicalQuery(BaseModel):
    caseid: Optional[str] = ""
    patid: Optional[str] = ""
    pname: Optional[str] = ""
    dob: Optional[str] = ""
    age: Optional[int] = 0
    gender: Optional[str] = None
    disease: Optional[str] = None
    medication: Optional[str] = None
    query_type: str = "Explain"
    custom_query: Optional[str] = ""
    conversation_type: str = "clinical"
    presenting_complaint: Optional[str] = ""
    bp: Optional[str] = ""
    pulse: Optional[str] = ""
    bmi: Optional[float] = 0.0
    family_history: Optional[str] = ""
    social_history: Optional[str] = ""
    allergies: Optional[str] = ""
    image_data: Optional[str] = ""
    image_name: Optional[str] = ""
    pdf_text: Optional[str] = ""
    pdf_name: Optional[str] = ""
    patient_email: Optional[str] = ""
    doctor_name: Optional[str] = ""
    doctor_id: Optional[str] = ""
    session_id: Optional[str] = None
    chat_history: Optional[List[Dict[str, Any]]] = None
    use_ada_mode: Optional[bool] = False


class ExportReportRequest(BaseModel):
    patient: Dict[str, Any]
    doctor_name: Optional[str] = ""
    doctor_id: Optional[str] = ""
    specialization: Optional[str] = ""
    hospital: Optional[str] = ""
    chat_history: Optional[List[Dict[str, Any]]] = []
    export_date: Optional[str] = ""


class FeedbackRequest(BaseModel):
    interaction_id: Optional[str] = ""
    disease: str
    query_type: str
    rating: int
    doctor_feedback: Optional[str] = ""
    correction: Optional[str] = ""


# ── Helpers & Utils ──────────────────────────────────────────────────────────

# ── FIX 2: Tightened non-medical blocklist ────────────────────────────────────
# Removed "history", "code", "language", "book", "describe", "tell me about"
# from the blocklist — these are common in medical queries:
#   "patient has a history of..."   → was incorrectly blocked
#   "describe the condition"        → was incorrectly blocked
# Only block terms that are unambiguously non-medical.

_NON_MEDICAL_MARKERS = [
    "weather",
    "stock market",
    "movie",
    "movies",
    "music",
    "song",
    "sports score",
    "football match",
    "soccer game",
    "basketball game",
    "tennis match",
    "travel destination",
    "flight booking",
    "restaurant",
    "recipe",
    "cooking tutorial",
    "video game",
    "gaming",
    "javascript",
    "python script",
    "computer repair",
    "email template",
    "text message",
    "sms template",
    "political news",
    "election result",
    "cryptocurrency",
    "joke",
    "funny meme",
    "write a poem",
    "write a story",
    "how are you",
    "what is your name",
    "who are you",
    "translate this sentence",
    "math problem",
    "calculus",
]

_MEDICAL_CLUES = [
    "health",
    "doctor",
    "clinic",
    "medical",
    "medicine",
    "medication",
    "symptom",
    "symptoms",
    "treatment",
    "diagnosis",
    "pain",
    "illness",
    "condition",
    "disease",
    "therapy",
    "consultation",
    "vaccine",
    "appointment",
    "nausea",
    "fever",
    "cough",
    "headache",
    "infection",
    "patient",
    "blood",
    "sugar",
    "glucose",
    "insulin",
    "pressure",
    "heart",
    "kidney",
    "liver",
    "lung",
    "chronic",
    "acute",
    "dosage",
    "prescription",
    "lab",
    "test",
    "scan",
    "x-ray",
    "mri",
    "ecg",
    "hba1c",
    "bmi",
    "bp",
    "pulse",
    "allerg",
    "referral",
    "specialist",
    "surgery",
    "procedure",
    "complication",
    "risk",
    "prognosis",
    "diabetic",
    "ketoacidosis",
    "hyperglycemia",
    "hypoglycemia",
]


def _is_medical_query(text: Optional[str]) -> bool:
    if not text or not text.strip():
        return False

    normalized = text.lower().strip()
    if any(marker in normalized for marker in _NON_MEDICAL_MARKERS):
        return False

    # Short greetings / generic chat should be treated as off-topic.
    casual_phrases = [
        "hi",
        "hello",
        "hey",
        "thanks",
        "thank you",
        "good morning",
        "good afternoon",
        "good evening",
        "how are you",
        "what is your name",
        "who are you",
        "what can you do",
        "tell me a joke",
        "joke",
        "weather",
        "news",
    ]
    if any(phrase in normalized for phrase in casual_phrases):
        return False

    if any(clue in normalized for clue in _MEDICAL_CLUES):
        return True

    # Default to non-medical unless the message clearly contains medical context.
    return False


def _decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(
            token,
            os.getenv("JWT_SECRET_KEY", "change-in-production"),
            algorithms=["HS256"],
        )
    except Exception:
        return None


def _apply_doctor_identity_from_request(
    query_data: ClinicalQuery, request: Request
) -> None:
    auth_header = request.headers.get("authorization") or request.headers.get(
        "Authorization"
    )
    if not auth_header or not auth_header.lower().startswith("bearer "):
        return
    token = auth_header.split(" ", 1)[1].strip()
    payload = _decode_jwt_token(token)
    if not payload:
        return
    if not query_data.doctor_name and payload.get("name"):
        query_data.doctor_name = payload.get("name")
    if not query_data.doctor_id and payload.get("doctor_id"):
        query_data.doctor_id = payload.get("doctor_id")


def _patient_belongs_to_doctor(
    patient: Optional[Dict[str, Any]],
    doctor_id: Optional[str],
    doctor_name: Optional[str] = None,
) -> bool:
    if not isinstance(patient, dict):
        return False
    owner_id = patient.get("added_by_doctor_id") or patient.get("doctor_id") or ""
    if isinstance(owner_id, str) and owner_id.strip() and doctor_id:
        if owner_id.strip() == str(doctor_id).strip():
            return True
    owner_name = patient.get("added_by_doctor") or patient.get("doctor_name") or ""
    if isinstance(owner_name, str) and owner_name.strip() and doctor_name:
        return owner_name.strip().casefold() == str(doctor_name).strip().casefold()
    return False


def _require_patient_scope(query_data: ClinicalQuery, request: Request) -> None:
    if patients_collection is None or not query_data.patid:
        return
    _apply_doctor_identity_from_request(query_data, request)
    patient = patients_collection.find_one({"patid": query_data.patid}, {"_id": 0})
    if not patient:
        return
    if not _patient_belongs_to_doctor(
        patient, query_data.doctor_id, query_data.doctor_name
    ):
        raise HTTPException(
            status_code=403, detail="Access Denied: Patient ownership mismatch."
        )


def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        return "".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        print(f"[PDF] Extraction error: {e}")
        return ""


def should_send_email(patient_email: str):
    if not patient_email or email_notifications_collection is None:
        return False, "skipped"
    tracking = email_notifications_collection.find_one({"patient_email": patient_email})
    if tracking and tracking.get("emails_sent", 0) >= 1:
        return False, "already sent"
    if not tracking:
        email_notifications_collection.insert_one(
            {
                "patient_email": patient_email,
                "emails_sent": 0,
                "created_at": datetime.utcnow().isoformat(),
            }
        )
    email_notifications_collection.update_one(
        {"patient_email": patient_email},
        {"$set": {"emails_sent": 1, "first_sent_at": datetime.utcnow().isoformat()}},
    )
    return True, "first consultation"


# ── Session & Persistence Logic ──────────────────────────────────────────────


def _ensure_session_id(session_id: Optional[str]) -> str:
    return session_id if session_id and session_id.strip() else str(uuid.uuid4())


def _normalize_chat_history(
    raw_history: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []
    if not raw_history:
        return normalized
    for entry in raw_history:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role", "user")
        if role not in ("user", "assistant"):
            role = "assistant" if entry.get("response") else "user"
        content = (
            entry.get("content") or entry.get("query") or entry.get("response") or ""
        )
        if content:
            normalized.append({"role": role, "content": str(content)})
    return normalized


def _trim_chat_history(
    history: List[Dict[str, str]], max_messages: int = 12
) -> List[Dict[str, str]]:
    return history[-max_messages:]


def _reconcile_history(
    stored: List[Dict[str, str]], incoming: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    if not stored:
        return incoming
    if not incoming:
        return stored
    return incoming if len(incoming) >= len(stored) else stored


def _load_chat_session(session_id: str) -> List[Dict[str, str]]:
    if chat_sessions_collection is None:
        return []
    doc = chat_sessions_collection.find_one({"session_id": session_id})
    return doc.get("history", []) if doc else []


def _save_chat_session(
    session_id: str, history: List[Dict[str, str]], metadata: Dict[str, Any]
):
    if chat_sessions_collection is None:
        return
    timestamp = datetime.utcnow().isoformat()
    chat_sessions_collection.update_one(
        {"session_id": session_id},
        {
            "$set": {"history": history, "metadata": metadata, "updated_at": timestamp},
            "$setOnInsert": {"created_at": timestamp},
        },
        upsert=True,
    )


# ── Learning & Adaptation Logic ──────────────────────────────────────────────


def _extract_key_recs(text: str) -> str:
    lines = text.split("\n")
    recs = [
        l.strip()
        for l in lines
        if l.strip().startswith(("- **First", "- **Second", "**Target", "Recommend"))
    ]
    return " | ".join(recs[:4]) if recs else text[:200]


def _extract_ada_refs(text: str) -> list:
    return list(
        set(
            re.findall(
                r"ADA\s+2026\s+(?:Rec(?:ommendation)?\.?\s*|§)[\d\.]+[a-z]?", text
            )
        )
    )


def _retrieve_similar_cases(disease: str, query_type: str, limit: int = 3) -> str:
    if learning_journal_collection is None:
        return ""
    try:
        cursor = (
            learning_journal_collection.find(
                {
                    "disease": {"$regex": disease[:30], "$options": "i"},
                    "query_type": query_type,
                    "rating": {"$gte": 4},
                },
                {
                    "response_snippet": 1,
                    "key_recommendations": 1,
                    "ada_refs": 1,
                    "_id": 0,
                },
            )
            .sort("rating", -1)
            .limit(limit)
        )
        docs = list(cursor)
        if not docs:
            return ""
        parts = ["PRIOR HIGH-QUALITY INTERACTIONS (for this condition):"]
        for i, doc in enumerate(docs, 1):
            parts.append(
                f"[Case {i}] {doc.get('key_recommendations', '')} | "
                f"ADA refs: {', '.join(doc.get('ada_refs', []))}"
            )
        # FIX 3: Cap past_cases_ctx to 1500 chars to protect response token budget
        return "\n".join(parts)[:1500]
    except Exception:
        return ""


def _save_interaction(
    query_data, response_content: str, ada_refs: list, model_used: str
):
    if learning_journal_collection is None:
        return
    try:
        learning_journal_collection.insert_one(
            {
                "disease": query_data.disease or "Unknown",
                "query_type": query_data.query_type,
                "age": query_data.age,
                "gender": query_data.gender,
                "presenting_complaint": query_data.presenting_complaint or "",
                "response_snippet": response_content[:600],
                "key_recommendations": _extract_key_recs(response_content),
                "ada_refs": ada_refs,
                "rating": None,
                "doctor_feedback": None,
                "model": model_used,
                "created_at": datetime.utcnow().isoformat(),
            }
        )
    except Exception as e:
        print(f"[Learning] Save failed: {e}")


# ── ADA Guideline Context Builder ─────────────────────────────────────────────

# Phrases that indicate the ADA engine found nothing useful.
# If any of these appear in the returned context, we discard it entirely
# rather than injecting a dead-end message that confuses the model.
_ADA_FALLBACK_PHRASES = [
    "do not explicitly address",
    "no guideline",
    "cannot be generated",
    "not found in the guidelines",
    "no relevant guideline",
    "no ada guideline",
    "guidelines do not cover",
    "outside the scope",
    "not covered by",
]


def _build_guideline_context(ada, patient_data: dict, clinical_q: str) -> tuple:
    """
    Calls ada.build_ada_prompt(), then:
      1. Filters out dead-end fallback messages (FIX 4)
      2. Caps the returned text at 4000 chars (FIX 5)
    Returns (guideline_ctx_str, guideline_usage_dict)
    """
    if ada is None:
        return "", {}

    try:
        ada_prompt_content, guideline_usage = ada.build_ada_prompt(
            patient_data, clinical_q
        )
    except Exception as e:
        print(f"[ADA] build_ada_prompt failed: {e}")
        return "", {}

    if not ada_prompt_content or not ada_prompt_content.strip():
        return "", {}

    # Check for fallback / dead-end phrases
    lower_content = ada_prompt_content.lower()
    if any(phrase in lower_content for phrase in _ADA_FALLBACK_PHRASES):
        print(
            "[ADA] Guideline context contained a dead-end fallback phrase — "
            "discarding to prevent model from echoing it. Model will reason from training knowledge."
        )
        return "", guideline_usage

    # Hard-cap at 4000 chars to preserve token budget for the actual response
    capped = ada_prompt_content[:4000]
    if len(ada_prompt_content) > 4000:
        print(
            f"[ADA] Guideline context truncated from {len(ada_prompt_content)} → 4000 chars"
        )

    return capped, guideline_usage


# ── Evidence & Citation Rules (Embedded in Every Prompt) ─────────────────────

_ADA_CITATION_RULES = """
═══════════════════════════════════════════════════════════════
INTELLIHEALTH EVIDENCE STANDARDS — MANDATORY IN EVERY RESPONSE
═══════════════════════════════════════════════════════════════
PRIMARY KNOWLEDGE BASE — ADA 2026 Standards of Care (Diabetes Care 2026;49):
  • §14 — Children and Adolescents (S297–S320)
  • §15 — Management of Diabetes in Pregnancy (S321–S338)
  • §16 — Diabetes Care in the Hospital (S339–S355)

EVIDENCE GRADING — tag every clinical recommendation:
  [A] High-quality RCTs or meta-analyses; strong evidence
  [B] Cohort/case-control studies; moderate evidence
  [C] Expert consensus; limited data
  [E] Expert opinion only

CITATION RULES (strictly enforced):
1. Cite ADA 2026 recommendation numbers inline:
     "Per ADA 2026 Rec. 14.5 [A], CGM is recommended for all T1D children."
2. Supplement with: WHO Guidelines (year), Harrison's 21st ed., UpToDate,
   high-impact RCTs from NEJM/Lancet/JAMA/BMJ (DOI required).
3. ALWAYS end with ## References — every cited source in full bibliographic format.
4. Never fabricate references. Never present opinion as established evidence [E].
═══════════════════════════════════════════════════════════════
"""

# ── DiabAssist Persona Directive ─────────────────────────────────────────────

_DIABASSIST_DIRECTIVE = """You are DiabAssist, a specialized AI clinical assistant for qualified healthcare professionals.

SCOPE: You answer only questions about this patient's medical condition, diagnosis, medications, risk factors, investigations, treatment options, and clinical management.

OFF-TOPIC RESPONSE: If the query is entirely unrelated to this patient's healthcare, respond only with:
"I am not programmed for this. Please ask a health-related question about the patient."

RESPONSE COMPLETENESS REQUIREMENT (CRITICAL):
- You MUST complete ALL sections listed in the structure below.
- Do NOT stop early, do NOT summarize sections as "see above", do NOT truncate.
- If a section has limited data, state what is known and note the data gap explicitly.
- A response that ends before the ## References section is INCOMPLETE and unacceptable.
"""


# ── AI Response Generator (v4.1 — Full Detail) ───────────────────────────────


def generate_advanced_ai_response(query_data: ClinicalQuery) -> Dict[str, Any]:
    if not groq_client:
        return {"success": False, "error": "AI service not configured", "content": ""}

    ada = get_ada_engine()
    query_type = query_data.query_type
    custom_query = query_data.custom_query or ""
    conv_type = query_data.conversation_type or "clinical"
    doctor_name = query_data.doctor_name or "the treating physician"
    disease = query_data.disease or "Unknown"
    age_text = f"{query_data.age} years" if query_data.age else "Unknown"

    # ── Patient context block ─────────────────────────────────────────────────
    patient_ctx = f"""═══════════════════════════════════════════
PATIENT RECORD
═══════════════════════════════════════════
Name:                  {query_data.pname or "Unknown"}
Age:                   {age_text}
Gender:                {query_data.gender or "Not specified"}
Known Condition:       {disease}
Current Medication:    {query_data.medication or "None documented"}
Blood Pressure:        {query_data.bp or "Not recorded"}
Pulse:                 {query_data.pulse or "Not recorded"}
BMI:                   {query_data.bmi or "Not recorded"}
Presenting Complaint:  {query_data.presenting_complaint or "Not specified"}
Family History:        {query_data.family_history or "Not provided"}
Social History:        {query_data.social_history or "Not provided"}
Allergies:             {query_data.allergies or "None known"}
═══════════════════════════════════════════"""

    # ── Guideline context (filtered + capped) ─────────────────────────────────
    guidelines_loaded = guideline_load_status["loaded"]
    guideline_ctx = ""
    guideline_usage = {}

    if guidelines_loaded and ada:
        patient_data_for_ctx = {
            "disease": disease,
            "age": query_data.age,
            "presenting_complaint": query_data.presenting_complaint or "",
        }
        clinical_q = custom_query or f"{query_type} for {disease}"
        guideline_ctx, guideline_usage = _build_guideline_context(
            ada, patient_data_for_ctx, clinical_q
        )

    # ── Uploaded file context ─────────────────────────────────────────────────
    uploaded_ctx = ""
    if query_data.pdf_text and query_data.pdf_text.strip():
        uploaded_ctx += (
            f"\n\n═══ UPLOADED MEDICAL DOCUMENT: {query_data.pdf_name or 'report'} ═══\n"
            f"{query_data.pdf_text[:4000]}\n═══ END OF DOCUMENT ═══"
        )
    if query_data.image_data:
        uploaded_ctx += (
            f"\n\nMEDICAL IMAGE PROVIDED: {query_data.image_name or 'image'} — "
            "describe and interpret any visible findings in your assessment."
        )

    has_uploads = bool(query_data.pdf_text or query_data.image_data)
    analysis_focus = (
        "PRIORITY: Analyse the UPLOADED DOCUMENT/IMAGE first. "
        "The patient record is supporting context. "
        "Consider ALL conditions visible, not only the recorded disease field."
        if has_uploads
        else "Analyse based on the patient record and presenting complaint."
    )

    # ── Prior case context (capped at 1500 chars) ────────────────────────────
    past_cases_ctx = _retrieve_similar_cases(disease, query_type)

    # ── Guideline section header for system prompt ────────────────────────────
    guideline_section = ""
    if guideline_ctx:
        guideline_section = (
            f"\n{'═' * 60}\n"
            f"ADA 2026 STANDARDS OF CARE — LOADED GUIDELINE CONTEXT\n"
            f"{'═' * 60}\n"
            f"{guideline_ctx}\n"
            f"{'═' * 60}\n"
        )
    else:
        guideline_section = (
            f"\n{'═' * 60}\n"
            "ADA 2026 STANDARDS OF CARE — USING EMBEDDED TRAINING KNOWLEDGE\n"
            "(No additional guideline file context available for this query. "
            "Reason from your comprehensive ADA 2026 training knowledge and cite "
            "recommendation numbers as known.)\n"
            f"{'═' * 60}\n"
        )

    past_cases_section = f"\n{past_cases_ctx}\n" if past_cases_ctx else ""

    # ── Build system prompt based on conversation type ────────────────────────
    if conv_type == "general" or query_type == "Generic":
        system_prompt = f"""{_DIABASSIST_DIRECTIVE}

You are IntelliHealth, an AI clinical reasoning system presenting as Gemma, supporting Dr. {doctor_name}.
You apply structured clinical reasoning and ADA 2026 guidelines, adapting response length to query complexity.

{patient_ctx}
{uploaded_ctx}
{guideline_section}
{past_cases_section}

RESPONSE REQUIREMENTS:
- Apply structured clinical reasoning: gather findings → identify abnormalities → rank differentials → recommend investigations → evidence-based management.
- Cite ADA 2026 recommendation numbers with evidence grade [A/B/C/E] for every recommendation.
- Be explicit about confidence level and any limitations in the data.
- Flag when urgent specialist referral is needed.
- NEVER present speculation as established fact.
- COMPLETE the full response including References before stopping.
{_ADA_CITATION_RULES}"""

    else:
        system_prompt = f"""{_DIABASSIST_DIRECTIVE}

You are IntelliHealth, a continuously learning AI Clinical Decision Support System presenting as Gemma, assisting Dr. {doctor_name}.

CORE MISSION: Generate expert-level, evidence-graded, fully referenced clinical consultation reports. Every section below is MANDATORY. Write each section in full. Do not abbreviate, skip, or summarise sections.

ANALYSIS DIRECTIVE: {analysis_focus}

{patient_ctx}
{uploaded_ctx}
{guideline_section}
{past_cases_section}

══════════════════════════════════════════════════════════════
MANDATORY RESPONSE STRUCTURE — COMPLETE ALL 7 SECTIONS IN FULL
══════════════════════════════════════════════════════════════

## 1. Clinical Reasoning & Assessment
Write a thorough narrative clinical assessment of this patient:
- Summarise all available findings systematically (vitals, history, medications, complaints)
- Identify abnormalities and their clinical significance
- Formulate your overall clinical impression with explicit reasoning
- Cite ADA 2026 recommendation numbers inline with evidence grade [A/B/C/E] throughout
- Minimum length: 4–6 detailed paragraphs. Do NOT condense into bullet points alone.

## 2. Differential Diagnosis (ranked by probability)
List 3–5 diagnoses in order of probability. For EACH provide:
  • Probability: High / Moderate / Low — and why
  • Supporting evidence from THIS patient's specific data
  • Features that argue AGAINST this diagnosis
  • Discriminating investigation(s) that would confirm or exclude it

## 3. Recommended Investigations
For each investigation specify:
  • Test name and rationale
  • ADA 2026 target value or normal range where applicable
  • Evidence grade [A/B/C/E]
  • How the result will change management
Include: labs (HbA1c, FPG, lipids, renal panel, urine ACR), imaging, functional tests as appropriate.

## 4. Evidence-Based Management Plan
Write a comprehensive, patient-specific management plan:
  - **First-line therapy [evidence grade]:** drug name + dose + route + frequency + target endpoint
  - **Second-line alternatives [evidence grade]:** options with dosing and switching criteria
  - **Combination therapy considerations:** when and how to escalate
  - **Non-pharmacological interventions:** diet, exercise, weight targets, self-monitoring
  - **Medication monitoring:** what to check, how often, and at what threshold to act
  - **Contraindications for THIS patient:** based on their specific allergies, comorbidities, vitals
Cite ADA 2026 recommendation number for EVERY pharmacological recommendation.

## 5. Monitoring & Follow-up Schedule
Provide a concrete, time-structured follow-up plan:
  - Week 2, Month 1, Month 3, Month 6, Annual — what to check at each visit
  - Specific numerical targets: HbA1c, BP, LDL, BMI, eGFR, UACR per ADA 2026
  - Self-monitoring instructions for the patient (SMBG/CGM frequency, BP log)
  - Criteria for stepping up therapy at each review

## 6. Red Flags & Urgent Escalation Criteria
List specific clinical signs, lab values, or symptoms that require:
  - Emergency department referral (immediate)
  - Same-day specialist review (urgent)
  - Routine specialist referral (non-urgent)
Give explicit numerical thresholds (e.g., glucose >400 mg/dL, K+ <3.0, eGFR <30).

## 7. Confidence & Limitations
  - Overall confidence level: High / Moderate / Low — with justification
  - Data gaps in this patient's record that limit certainty
  - Alternative clinical interpretations the treating physician should consider
  - Recommended additional history or examination findings to improve diagnostic accuracy

## References
List EVERY source cited above in full bibliographic format:
  Author/Organization (Year). Title. Journal. Volume(Issue):Pages. DOI or URL.
Minimum 4 references. Include ADA 2026, relevant RCTs, and any guideline cited.

══════════════════════════════════════════════════════════════
⚠️ All clinical decisions remain the sole responsibility of the treating physician.
{_ADA_CITATION_RULES}"""

    # ── Construct user message ────────────────────────────────────────────────
    if custom_query and custom_query.strip():
        user_message = (
            f"{custom_query}\n\n"
            "[Respond with a complete, detailed clinical consultation covering all 7 mandatory sections. "
            "Do not truncate. Complete the ## References section before stopping.]"
        )
    elif query_type == "Explain":
        user_message = (
            f"Apply structured clinical reasoning to fully assess this patient's condition ({disease}). "
            f"Generate ranked differentials, explain the complete clinical picture with pathophysiology, "
            f"and cite ADA 2026 guidelines throughout all 7 sections. "
            f"Do not truncate — complete the full response including References."
        )
    elif query_type == "Treatment":
        user_message = (
            f"Propose a complete, evidence-graded treatment plan for this patient with {disease}. "
            f"Include first-line and alternative pharmacological options with specific dosing, "
            f"targets, monitoring, contraindications, and non-pharmacological interventions. "
            f"Cite ADA 2026 recommendation numbers for every drug. "
            f"Complete all 7 sections including References."
        )
    elif query_type == "Medication":
        user_message = (
            f"Conduct a thorough medication review for this patient "
            f"(current regimen: {query_data.medication or 'as documented'}). "
            f"Assess appropriateness, identify drug interactions or contraindications, "
            f"recommend evidence-based adjustments with specific dosing and monitoring parameters. "
            f"Cite ADA 2026 guidelines. Complete all 7 sections including References."
        )
    elif query_type == "Lifestyle":
        user_message = (
            f"Provide a comprehensive, evidence-based lifestyle medicine plan for this patient with {disease}. "
            f"Cover medical nutrition therapy, structured physical activity, weight management targets, "
            f"smoking/alcohol cessation if relevant, sleep hygiene, and psychosocial support. "
            f"Include specific, quantified targets from ADA 2026. "
            f"Complete all 7 sections including References."
        )
    else:
        user_message = (
            f"Perform a complete clinical consultation for this patient with {disease}. "
            f"Apply structured reasoning, ADA 2026 evidence-based guidelines, and provide "
            f"actionable recommendations with explicit citations. "
            f"Complete all 7 mandatory sections including References. Do not truncate."
        )

    # ── Session/history management ────────────────────────────────────────────
    session_id = _ensure_session_id(query_data.session_id)
    incoming_history = _normalize_chat_history(query_data.chat_history)
    stored_history = _load_chat_session(session_id) if query_data.session_id else []
    session_history = _reconcile_history(stored_history, incoming_history)
    session_history = _trim_chat_history(session_history, max_messages=12)
    history_messages = [
        {"role": h["role"], "content": h["content"]}
        for h in session_history
        if h.get("role") and h.get("content")
    ]

    messages = [
        {"role": "system", "content": system_prompt},
        *history_messages,
        {"role": "user", "content": user_message},
    ]

    # ── Call Groq ─────────────────────────────────────────────────────────────
    try:
        chat_completion, used_model = _call_groq_with_model(
            messages,
            max_tokens=_MAX_RESPONSE_TOKENS,  # 8192
            temperature=0.4,
        )
        response_content = chat_completion.choices[0].message.content

        ada_refs = _extract_ada_refs(response_content)
        _save_interaction(query_data, response_content, ada_refs, used_model)

        if session_id:
            save_history = history_messages.copy()
            if (
                not save_history
                or save_history[-1].get("role") != "user"
                or save_history[-1].get("content") != user_message
            ):
                save_history.append({"role": "user", "content": user_message})
            save_history.append({"role": "assistant", "content": response_content})
            _save_chat_session(
                session_id,
                save_history,
                metadata={
                    "patid": query_data.patid,
                    "pname": query_data.pname,
                    "doctor_name": query_data.doctor_name,
                    "disease": query_data.disease,
                },
            )

        result = {
            "success": True,
            "content": response_content,
            "usage": guideline_usage,
            "ada_refs_found": ada_refs,
            "model": used_model,
        }
        if session_id:
            result["session_id"] = session_id
        return result

    except Exception as e:
        print(f"[AI] Groq API error: {e}")
        message = str(e)
        if "invalid_api_key" in message.lower() or "401" in message:
            message = (
                "Groq rejected the live API key (401 invalid_api_key). "
                "Update the GROQ_API_KEY secret in your hosting provider and redeploy."
            )
        return {
            "success": False,
            "error": f"AI response generation failed: {message}",
            "content": "",
        }


# ── PDF Report Generation ──────────────────────────────────────────────────────


def generate_report_pdf(req: ExportReportRequest) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="Title",
            fontSize=24,
            leading=28,
            alignment=TA_CENTER,
            spaceAfter=10 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Heading2",
            fontSize=14,
            leading=16,
            spaceBefore=6 * mm,
            spaceAfter=6 * mm,
            fontName="Helvetica-Bold",
        )
    )
    styles.add(
        ParagraphStyle(name="BodyText", fontSize=10, leading=12, spaceAfter=3 * mm)
    )
    styles.add(
        ParagraphStyle(
            name="Disclaimer",
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#9ca3af"),
        )
    )

    story = []

    PURPLE = colors.HexColor("#7c3aed")
    LIGHT_PURPLE = colors.HexColor("#f5f3ff")
    WHITE = colors.HexColor("#ffffff")
    GRAY = colors.HexColor("#e5e7eb")

    story.append(Paragraph("IntelliHealth AI Clinical Report", styles["Title"]))
    story.append(Spacer(1, 5 * mm))

    def section_header(text: str):
        return [
            Paragraph(
                f'<font color="{PURPLE.hexval}" size="12"><b>{text.upper()}</b></font>',
                ParagraphStyle(
                    "sh",
                    fontName="Helvetica-Bold",
                    spaceAfter=3 * mm,
                    textColor=PURPLE,
                    alignment=TA_LEFT,
                ),
            ),
            HRFlowable(width="100%", thickness=0.5, color=PURPLE),
            Spacer(1, 2 * mm),
        ]

    def info_row(label: str, value: str):
        return [
            Paragraph(
                f'<font color="#6b7280" size="8">{label}</font>',
                ParagraphStyle("lbl", fontName="Helvetica"),
            ),
            Paragraph(
                f'<font color="#111827" size="9"><b>{value or "—"}</b></font>',
                ParagraphStyle("val", fontName="Helvetica-Bold"),
            ),
        ]

    p = req.patient

    story.extend(section_header("Attending Physician"))
    doctor_data = [
        info_row("Doctor Name", req.doctor_name or "—"),
        info_row("Doctor ID", req.doctor_id or "—"),
        info_row("Specialization", req.specialization or "—"),
        info_row("Hospital / Clinic", req.hospital or "—"),
    ]
    doc_table = Table(doctor_data, colWidths=[45 * mm, 125 * mm])
    doc_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_PURPLE),
                ("PADDING", (0, 0), (-1, -1), 5),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT_PURPLE]),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e9d5ff")),
                ("ROUNDEDCORNERS", [4, 4, 4, 4]),
            ]
        )
    )
    story.append(doc_table)
    story.append(Spacer(1, 5 * mm))

    story.extend(section_header("Patient Information"))
    patient_data = [
        info_row("Patient Name", p.get("pname", "")),
        info_row("Patient ID", p.get("patid", "")),
        info_row(
            "Date of Birth / Age",
            f"{p.get('dob', '')}  |  {p.get('age', '')} years",
        ),
        info_row("Gender", p.get("gender", "")),
        info_row("Phone Number", p.get("phone_number", "")),
        info_row("Email", p.get("patient_email", "")),
        info_row("Known Condition", p.get("disease", "")),
        info_row("Current Medication", p.get("medication", "")),
        info_row("Allergies", p.get("allergies", "")),
        info_row("Blood Pressure", p.get("bp", "")),
        info_row("Pulse", p.get("pulse", "")),
        info_row("BMI", str(p.get("bmi", "")) if p.get("bmi") else ""),
        info_row("Presenting Complaint", p.get("presenting_complaint", "")),
        info_row("Family History", p.get("family_history", "")),
        info_row("Social History", p.get("social_history", "")),
    ]
    pat_table = Table(patient_data, colWidths=[45 * mm, 125 * mm])
    pat_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), WHITE),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT_PURPLE]),
                ("PADDING", (0, 0), (-1, -1), 5),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e9d5ff")),
            ]
        )
    )
    story.append(pat_table)
    story.append(Spacer(1, 5 * mm))

    if req.chat_history:
        story.extend(section_header("Consultation Summary"))
        ai_style = ParagraphStyle(
            "ai",
            fontName="Helvetica",
            fontSize=8.5,
            leading=13,
            leftIndent=4,
            spaceAfter=4,
        )
        q_style = ParagraphStyle(
            "q",
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=13,
            textColor=PURPLE,
            leftIndent=4,
            spaceAfter=2,
        )
        for i, msg in enumerate(req.chat_history, 1):
            role = msg.get("role", "")
            content = msg.get("content", "")
            query_type = msg.get("query_type", "")

            if role == "user":
                label = f"[Q{i}] Physician Query" + (
                    f" ({query_type})" if query_type else ""
                )
                story.append(Paragraph(label, q_style))
                story.append(Paragraph(content[:600], ai_style))
            else:
                label = f"[A{i}] AI Clinical Response"
                story.append(Paragraph(label, q_style))
                clean = content.replace("**", "").replace("##", "").replace("*", "")
                story.append(Paragraph(clean[:2000], ai_style))

            story.append(Spacer(1, 2 * mm))

    story.append(Spacer(1, 5 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY))
    story.append(Spacer(1, 2 * mm))
    story.append(
        Paragraph(
            '<font color="#9ca3af" size="7">'
            "DISCLAIMER: This report is generated by an AI clinical decision support system (IntelliHealth / Gemma). "
            "It is intended to assist qualified physicians and does not constitute a medical diagnosis or prescription. "
            "The treating physician holds full clinical and legal responsibility for all patient care decisions. "
            "Generated on "
            + datetime.utcnow().strftime("%d %B %Y at %H:%M UTC")
            + "</font>",
            ParagraphStyle("disc", fontName="Helvetica", alignment=TA_CENTER),
        )
    )

    doc.build(story)
    return buffer.getvalue()


# ── API Endpoints ──────────────────────────────────────────────────────────────

api_router = APIRouter(prefix="/api")


@api_router.get("/healthz")
@api_router.get("/health")
async def health():
    db_status, db_msg = "disconnected", "Not connected"
    try:
        if _mongo is not None:
            _mongo.admin.command("ping")
            db_status, db_msg = "connected", f"Connected to {db_name}"
    except Exception as e:
        db_status, db_msg = "error", str(e)

    ada_engine = get_ada_engine()
    ada_stats = (
        ada_engine.get_guideline_stats()
        if ada_engine
        else {"guideline_loaded": False, "details": "ADA Engine not initialized"}
    )

    return {
        "status": "healthy"
        if db_status == "connected" and ada_stats["guideline_loaded"]
        else "degraded",
        "database": {"status": db_status, "message": db_msg, "name": db_name},
        "groq_api": "configured" if groq_client else "not configured",
        "model": groq_model_primary,
        "max_response_tokens": _MAX_RESPONSE_TOKENS,
        "guidelines": ada_stats,
        "timestamp": datetime.utcnow().isoformat(),
    }


@api_router.get("/model")
async def model_info():
    ada_engine = get_ada_engine()
    ada_stats = (
        ada_engine.get_guideline_stats()
        if ada_engine
        else {"guideline_loaded": False, "details": "ADA Engine not initialized"}
    )
    return {
        "groq_api": "configured" if groq_client else "not configured",
        "model": groq_model_primary,
        "model_display": "Gemma persona (llama-3.3-70b-versatile)",
        "fallback_models": groq_model_fallbacks,
        "max_response_tokens": _MAX_RESPONSE_TOKENS,
        "guidelines": ada_stats,
        "timestamp": datetime.utcnow().isoformat(),
    }


@api_router.post("/clinical-analysis")
async def get_clinical_analysis(
    query_data: ClinicalQuery, background_tasks: BackgroundTasks, request: Request
):
    if not groq_client:
        raise HTTPException(
            status_code=503,
            detail="AI service is not configured. Set a valid GROQ_API_KEY in the live environment and redeploy.",
        )
    if not guideline_load_status["loaded"] and query_data.use_ada_mode:
        raise HTTPException(
            status_code=503,
            detail="ADA Guidelines are still loading. Please try again in a moment.",
        )

    _apply_doctor_identity_from_request(query_data, request)
    _require_patient_scope(query_data, request)

    if query_data.custom_query and query_data.custom_query.strip():
        if not _is_medical_query(query_data.custom_query):
            return {
                "success": True,
                "content": "I am not programmed for this. Please ask a health-related question about the patient.",
                "usage": {},
                "ada_refs_found": [],
            }

    result = generate_advanced_ai_response(query_data)

    if result.get("success") and query_data.patient_email:
        should_send, reason = should_send_email(query_data.patient_email)
        if should_send:
            summary = result.get("content", "")[:500]
            background_tasks.add_task(
                send_diagnosis_email,
                patient_email=query_data.patient_email,
                patient_name=query_data.pname,
                doctor_name=query_data.doctor_name or "Your Doctor",
                diagnosis_summary=summary,
            )

    return result


@api_router.post("/session")
async def create_session():
    session_id = _ensure_session_id(None)
    _save_chat_session(session_id, [], {})
    return {"success": True, "session_id": session_id}


@api_router.get("/session/{session_id}")
async def load_session(session_id: str):
    session_history = _load_chat_session(session_id)
    if not session_history:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "session_id": session_id, "history": session_history}


@api_router.post("/session/{session_id}/save")
async def save_session(session_id: str, body: Dict[str, Any]):
    history = body.get("history")
    metadata = body.get("metadata", {})
    if history is None or not isinstance(history, list):
        raise HTTPException(
            status_code=400,
            detail="Session history must be provided as a list",
        )
    normalized_history = _normalize_chat_history(history)
    _save_chat_session(session_id, normalized_history, metadata)
    return {"success": True, "session_id": session_id}


@api_router.post("/export-report")
async def export_report(req: ExportReportRequest, request: Request):
    auth_header = request.headers.get("authorization") or request.headers.get(
        "Authorization"
    )
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        payload = _decode_jwt_token(token)
        if payload:
            if not req.doctor_name and payload.get("name"):
                req.doctor_name = payload.get("name")
            if not req.doctor_id and payload.get("doctor_id"):
                req.doctor_id = payload.get("doctor_id")
    try:
        doctor_id = None
        doctor_name = None
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            payload = _decode_jwt_token(token)
            if payload:
                doctor_id = payload.get("doctor_id")
                doctor_name = payload.get("name")

        patid = req.patient.get("patid") if isinstance(req.patient, dict) else None
        if patid and patients_collection is not None:
            patient_doc = patients_collection.find_one({"patid": patid}, {"_id": 0})
            if not patient_doc or not _patient_belongs_to_doctor(
                patient_doc, doctor_id, doctor_name
            ):
                raise HTTPException(
                    status_code=403,
                    detail="You are not this patient's doctor. Please connect only to your patients.",
                )

        pdf_bytes = generate_report_pdf(req)
        patient_name = req.patient.get("pname", "Patient").replace(" ", "_")
        date_str = datetime.utcnow().strftime("%Y%m%d")
        filename = f"IntelliHealth_Report_{patient_name}_{date_str}.pdf"
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")


@api_router.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files accepted")
    file_bytes = await file.read()
    text = extract_text_from_pdf(file_bytes)
    if not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")
    return {
        "success": True,
        "filename": file.filename,
        "text": text,
        "character_count": len(text),
        "word_count": len(text.split()),
    }


@api_router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    allowed = ["image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"]
    if file.content_type not in allowed:
        raise HTTPException(
            status_code=400, detail=f"Unsupported image type: {file.content_type}"
        )
    file_bytes = await file.read()
    return {
        "success": True,
        "filename": file.filename,
        "image_data": base64.b64encode(file_bytes).decode("utf-8"),
        "file_size": len(file_bytes),
    }


@api_router.post("/upload-guideline")
async def upload_guideline(file: UploadFile = File(...), source_name: str = "ADA_2026"):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail="Only PDF files accepted for guidelines"
        )
    file_bytes = await file.read()
    text = extract_text_from_pdf(file_bytes)
    if not text.strip():
        raise HTTPException(
            status_code=400, detail="Could not extract text from guideline PDF"
        )
    ada = get_ada_engine()
    ada.set_guideline_content(text, source_name)
    global guideline_load_status
    ada_stats = ada.get_guideline_stats()
    guideline_load_status["loaded"] = ada_stats["guideline_loaded"]
    guideline_load_status["details"] = (
        f"Loaded {ada_stats['total_sources_loaded']} sources | "
        f"{ada_stats['total_recommendations']} recommendations | "
        f"{ada_stats['sample_cases_loaded']} sample cases"
    )
    return {
        "success": True,
        "filename": file.filename,
        "source_name": source_name,
        "word_count": len(text.split()),
        "stats": ada.get_guideline_stats(),
        "message": f"Guideline '{source_name}' loaded and activated",
    }


@api_router.post("/upload-additional-guideline")
async def upload_additional_guideline(
    file: UploadFile = File(...),
    source_name: str = "Additional_Guideline",
    source_type: str = "guideline",
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files accepted")
    file_bytes = await file.read()
    text = extract_text_from_pdf(file_bytes)
    if not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text")
    ada = get_ada_engine()
    result = ada.add_guideline_source(source_name, text, source_type)
    global guideline_load_status
    ada_stats = ada.get_guideline_stats()
    guideline_load_status["loaded"] = ada_stats["guideline_loaded"]
    guideline_load_status["details"] = (
        f"Loaded {ada_stats['total_sources_loaded']} sources | "
        f"{ada_stats['total_recommendations']} recommendations | "
        f"{ada_stats['sample_cases_loaded']} sample cases"
    )
    return {
        "success": True,
        "result": result,
        "total_sources": ada.get_guideline_stats()["total_sources_loaded"],
    }


@api_router.get("/guideline-pdfs")
async def list_guideline_pdfs():
    pdf_files = []
    if os.path.isdir(_PROJECT_ROOT):
        for entry in sorted(os.scandir(_PROJECT_ROOT), key=lambda item: item.name.lower()):
            if entry.is_file() and entry.name.lower().endswith(".pdf"):
                stat = entry.stat()
                pdf_files.append(
                    {
                        "name": entry.name,
                        "size": stat.st_size,
                        "download_url": f"/api/download-guideline-pdf/{entry.name}",
                    }
                )

    return {"success": True, "files": pdf_files}


@api_router.get("/download-guideline-pdf/{filename}")
async def download_guideline_pdf(filename: str):
    safe_name = os.path.basename(filename)
    file_path = os.path.join(_PROJECT_ROOT, safe_name)

    if not safe_name.lower().endswith(".pdf") or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="PDF not found")

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=safe_name,
    )


@api_router.get("/list-guidelines")
@api_router.post("/list-guidelines")
async def list_guidelines():
    ada = get_ada_engine()
    stats = ada.get_guideline_stats()
    return {"success": True, "stats": stats, "load_status": guideline_load_status}


@api_router.post("/feedback")
async def submit_feedback(req: FeedbackRequest):
    if req.rating < 1 or req.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be 1–5")
    if learning_journal_collection is None:
        raise HTTPException(status_code=503, detail="Learning journal not available")

    update = {
        "rating": req.rating,
        "doctor_feedback": req.doctor_feedback or "",
        "correction": req.correction or "",
        "feedback_at": datetime.utcnow().isoformat(),
    }
    if req.interaction_id:
        from bson import ObjectId

        try:
            learning_journal_collection.update_one(
                {"_id": ObjectId(req.interaction_id)}, {"$set": update}
            )
        except Exception:
            pass

    learning_journal_collection.insert_one(
        {
            "disease": req.disease,
            "query_type": req.query_type,
            "rating": req.rating,
            "doctor_feedback": req.doctor_feedback or "",
            "correction": req.correction or "",
            "model": groq_model_primary,
            "created_at": datetime.utcnow().isoformat(),
        }
    )
    return {
        "success": True,
        "message": "Feedback recorded. Thank you — this improves future recommendations.",
    }


@api_router.get("/learning-stats")
async def learning_stats():
    if learning_journal_collection is None:
        return {"success": False, "error": "Learning journal not connected"}
    try:
        total = learning_journal_collection.count_documents({})
        rated = learning_journal_collection.count_documents({"rating": {"$ne": None}})
        pipeline = [
            {"$match": {"rating": {"$ne": None}}},
            {
                "$group": {
                    "_id": None,
                    "avg": {"$avg": "$rating"},
                    "count": {"$sum": 1},
                }
            },
        ]
        avg_result = list(learning_journal_collection.aggregate(pipeline))
        avg_rating = round(avg_result[0]["avg"], 2) if avg_result else None

        by_condition = list(
            learning_journal_collection.aggregate(
                [
                    {"$match": {"rating": {"$gte": 4}}},
                    {
                        "$group": {
                            "_id": "$disease",
                            "count": {"$sum": 1},
                            "avg_rating": {"$avg": "$rating"},
                        }
                    },
                    {"$sort": {"count": -1}},
                    {"$limit": 10},
                ]
            )
        )

        corrections = list(
            learning_journal_collection.find(
                {"correction": {"$ne": ""}},
                {
                    "disease": 1,
                    "query_type": 1,
                    "correction": 1,
                    "rating": 1,
                    "_id": 0,
                },
            )
            .sort("feedback_at", -1)
            .limit(5)
        )

        return {
            "success": True,
            "total_interactions": total,
            "rated_interactions": rated,
            "average_rating": avg_rating,
            "top_conditions": by_condition,
            "recent_corrections": corrections,
            "model": groq_model_primary,
            "status": "Learning journal active — model adapts from rated interactions",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@api_router.post("/demo-cases")
async def list_demo_cases(request: dict):
    disease = request.get("patient_data", {}).get("disease", "General Condition")
    return {
        "success": True,
        "demo_cases": [
            {"id": "explain", "title": f"Explain {disease}", "query_type": "Explain"},
            {"id": "treatment", "title": "Treatment Plan", "query_type": "Treatment"},
            {
                "id": "medication",
                "title": "Medication Review",
                "query_type": "Medication",
            },
            {
                "id": "lifestyle",
                "title": "Lifestyle Guidance",
                "query_type": "Lifestyle",
            },
        ],
    }


@api_router.post("/demo-case/run")
async def run_demo_case(demo_request: dict):
    import time

    pd = demo_request.get("patient_data", {})
    qt = demo_request.get("query_type", "Explain")
    query = ClinicalQuery(
        patid=pd.get("patid", "DEMO"),
        pname=pd.get("pname", "Demo Patient"),
        age=int(pd.get("age", 30)),
        gender=pd.get("gender", "Male"),
        disease=pd.get("disease", "Unknown"),
        medication=pd.get("medication", "None"),
        bp=pd.get("bp", "120/80"),
        bmi=float(pd.get("bmi", 25)),
        query_type=qt,
    )
    t0 = time.time()
    result = generate_advanced_ai_response(query)
    return {
        "success": True,
        "title": f"{pd.get('disease', 'Condition')} — {qt} Analysis",
        "ai_analysis": result.get("content", ""),
        "response_time_seconds": round(time.time() - t0, 2),
        "model": result.get("model", groq_model_primary),
    }


@api_router.get("/")
async def api_root():
    return {
        "message": "IntelliHealth AI Clinical System API v4.1",
        "model": groq_model_primary,
        "max_response_tokens": _MAX_RESPONSE_TOKENS,
        "status": "running",
        "docs": "/api/docs",
        "admin": "/admin",
    }


# Register main router
app.include_router(api_router)
app.include_router(doctor_router)
app.include_router(auth_router)
app.include_router(profile_router)

# ── Admin Dashboard ────────────────────────────────────────────────────────────


@app.get("/admin", response_class=HTMLResponse)
@app.get("/api/admin", response_class=HTMLResponse)
@app.get("/", response_class=HTMLResponse)
async def admin_dashboard():
    db_ok = False
    patient_count = 0
    doctor_count = 0
    try:
        if _mongo is not None:
            _mongo.admin.command("ping")
            db_ok = True
            patient_count = (
                patients_collection.count_documents({})
                if patients_collection is not None
                else 0
            )
            auth_db = _mongo[os.getenv("MONGODB_AUTH_DB", "authentication")]
            doctor_count = auth_db["doctors"].count_documents({})
    except Exception:
        pass

    ada = get_ada_engine()
    ada_stats = ada.get_guideline_stats()
    guideline_count = ada_stats["total_sources_loaded"]
    rec_count = ada_stats["total_recommendations"]
    case_count = ada_stats["sample_cases_loaded"]

    def badge(ok: bool, ok_text: str, fail_text: str) -> str:
        color, bg = ("#16a34a", "#dcfce7") if ok else ("#dc2626", "#fee2e2")
        text = ok_text if ok else fail_text
        return f'<span style="color:{color};background:{bg};padding:2px 10px;border-radius:99px;font-size:13px;font-weight:600">{text}</span>'

    db_badge = badge(db_ok, "● Connected", "● Disconnected")
    ai_badge = badge(bool(groq_client), "● Ready", "● Not Configured")
    gl_badge = badge(
        guideline_load_status["loaded"],
        guideline_load_status["details"],
        "● Not loaded (loading in background)",
    )

    gl_rows = ""
    for src_name, src_meta in ada_stats.get("sources", {}).items():
        title = src_meta.get("title", src_name)
        words = f"{src_meta.get('word_count', 0):,}"
        gl_rows += f'<div class="status-row"><span class="status-label" style="font-size:13px">📄 {title}</span><code>{words} words</code></div>'
    if not gl_rows:
        gl_rows = '<div class="status-row"><span style="color:#9ca3af;font-size:13px">No guidelines loaded yet</span></div>'
    now = datetime.utcnow().strftime("%d %B %Y, %H:%M UTC")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>IntelliHealth — Admin Dashboard</title>
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f3ff;color:#1e1b4b;min-height:100vh}}
  .navbar{{background:#7c3aed;padding:0 32px;height:60px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 16px rgba(124,58,237,.3)}}
  .navbar-brand{{color:#fff;font-size:20px;font-weight:700;letter-spacing:-.5px}}
  .navbar-brand span{{color:#e9d5ff}}
  .navbar-right{{color:#e9d5ff;font-size:13px}}
  .hero{{background:linear-gradient(135deg,#7c3aed 0%,#4f46e5 100%);color:#fff;padding:48px 32px 40px;text-align:center}}
  .hero h1{{font-size:34px;font-weight:800;margin-bottom:8px}}
  .hero p{{color:#e9d5ff;font-size:16px;max-width:520px;margin:0 auto}}
  .container{{max-width:960px;margin:0 auto;padding:32px 24px}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:20px;margin-bottom:32px}}
  .card{{background:#fff;border-radius:16px;padding:24px;box-shadow:0 2px 12px rgba(124,58,237,.08);border:1px solid #ede9fe}}
  .card-icon{{font-size:32px;margin-bottom:12px}}
  .card-value{{font-size:32px;font-weight:800;color:#7c3aed;margin-bottom:4px}}
  .card-label{{color:#6b7280;font-size:13px;font-weight:500}}
  .section{{background:#fff;border-radius:16px;padding:28px;box-shadow:0 2px 12px rgba(124,58,237,.08);border:1px solid #ede9fe;margin-bottom:24px}}
  .section h2{{font-size:16px;font-weight:700;color:#1e1b4b;margin-bottom:18px;padding-bottom:10px;border-bottom:1px solid #ede9fe}}
  .status-row{{display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid #f5f3ff}}
  .status-row:last-child{{border-bottom:none}}
  .status-label{{font-size:14px;color:#4b5563;font-weight:500}}
  .endpoint-list{{list-style:none}}
  .endpoint-list li{{display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid #f5f3ff;font-size:13px}}
  .endpoint-list li:last-child{{border-bottom:none}}
  .method{{background:#ede9fe;color:#7c3aed;padding:2px 8px;border-radius:6px;font-size:11px;font-weight:700;font-family:monospace;min-width:44px;text-align:center}}
  .method.post{{background:#fce7f3;color:#be185d}}
  .method.del{{background:#fee2e2;color:#dc2626}}
  .path{{color:#1e1b4b;font-family:monospace}}
  .desc{{color:#9ca3af;margin-left:auto}}
  .link-btn{{display:inline-flex;align-items:center;gap:6px;background:#7c3aed;color:#fff;text-decoration:none;padding:10px 20px;border-radius:10px;font-size:14px;font-weight:600;transition:background .2s}}
  .link-btn:hover{{background:#6d28d9}}
  .link-btn.outline{{background:transparent;border:2px solid #7c3aed;color:#7c3aed}}
  .link-btn.outline:hover{{background:#f5f3ff}}
  .flex-row{{display:flex;gap:12px;flex-wrap:wrap;margin-top:16px}}
  .footer{{text-align:center;color:#9ca3af;font-size:12px;padding:24px;border-top:1px solid #ede9fe;background:#fff;margin-top:8px}}
  code{{background:#f5f3ff;color:#7c3aed;padding:1px 6px;border-radius:4px;font-size:12px;font-family:monospace}}
  .changelog{{background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;padding:16px 20px;margin-bottom:24px;font-size:13px;color:#166534}}
  .changelog strong{{display:block;margin-bottom:6px;font-size:14px}}
</style>
</head>
<body>
<nav class="navbar">
  <div class="navbar-brand">Intelli<span>Health</span> <span style="font-weight:300;font-size:14px">Admin</span></div>
  <div class="navbar-right">AI Clinical System v4.1</div>
</nav>
<div class="hero">
  <h1>System Dashboard</h1>
  <p>IntelliHealth AI Clinical Backend — powered by Llama 3.3 70B (Groq)</p>
</div>
<div class="container">
  <div class="changelog">
    <strong>✅ v4.1 Fixes Applied</strong>
    max_tokens: 1536 → 8192 &nbsp;|&nbsp; ADA fallback filtering active &nbsp;|&nbsp;
    Guideline context capped at 4000 chars &nbsp;|&nbsp; Richer consultation prompts &nbsp;|&nbsp;
    temperature: 0.3 → 0.4 &nbsp;|&nbsp; Non-medical blocklist tightened
  </div>
  <div class="grid">
    <div class="card"><div class="card-icon">🧑‍⚕️</div><div class="card-value">{doctor_count}</div><div class="card-label">Registered Doctors</div></div>
    <div class="card"><div class="card-icon">🏥</div><div class="card-value">{patient_count}</div><div class="card-label">Total Patients</div></div>
    <div class="card"><div class="card-icon">📚</div><div class="card-value">{guideline_count}</div><div class="card-label">ADA 2026 Guideline Docs</div></div>
    <div class="card"><div class="card-icon">🔖</div><div class="card-value">{rec_count}</div><div class="card-label">Indexed Recommendations</div></div>
    <div class="card"><div class="card-icon">🩺</div><div class="card-value">{case_count}</div><div class="card-label">Clinical Sample Cases</div></div>
    <div class="card"><div class="card-icon">🕐</div><div class="card-value" style="font-size:13px">{now}</div><div class="card-label">Server Time (UTC)</div></div>
  </div>
  <div class="section">
    <h2>System Status</h2>
    <div class="status-row"><span class="status-label">🗄️ MongoDB Database</span>{db_badge}</div>
    <div class="status-row"><span class="status-label">🤖 Llama 3.3 70B via Groq</span>{ai_badge}</div>
    <div class="status-row"><span class="status-label">📚 ADA 2026 Guidelines</span>{gl_badge}</div>
    <div class="status-row"><span class="status-label">📡 Primary Model</span><code>{groq_model_primary}</code></div>
    <div class="status-row"><span class="status-label">🔢 Max Response Tokens</span><code>{_MAX_RESPONSE_TOKENS}</code></div>
    <div class="status-row"><span class="status-label">🔄 Fallback Models</span><code>gpt-oss-120b → gpt-oss-20b → llama-3.1-8b-instant</code></div>
    <div class="status-row"><span class="status-label">🔗 Database</span><code>{db_name}</code></div>
    <div class="flex-row">
      <a href="/api/docs" class="link-btn">📄 API Docs (Swagger)</a>
      <a href="/api/health" class="link-btn outline">🩺 Health Check</a>
      <a href="/api/list-guidelines" class="link-btn outline">📚 Guidelines Status</a>
    </div>
  </div>
  <div class="section">
    <h2>Loaded ADA 2026 Guidelines</h2>
    <p style="color:#6b7280;font-size:13px;margin-bottom:14px">Auto-loaded at startup. Every AI response cites specific recommendation numbers with evidence grades [A/B/C/E].</p>
    {gl_rows}
  </div>
  <div class="section">
    <h2>Key API Endpoints</h2>
    <ul class="endpoint-list">
      <li><span class="method post">POST</span><span class="path">/api/clinical-analysis</span><span class="desc">AI clinical analysis (8192 token response)</span></li>
      <li><span class="method post">POST</span><span class="path">/api/export-report</span><span class="desc">Download PDF report</span></li>
      <li><span class="method post">POST</span><span class="path">/api/doctor/login</span><span class="desc">Doctor authentication</span></li>
      <li><span class="method post">POST</span><span class="path">/api/doctor/signup</span><span class="desc">Doctor registration</span></li>
      <li><span class="method">GET</span><span class="path">/api/doctor/patients</span><span class="desc">List patients</span></li>
      <li><span class="method post">POST</span><span class="path">/api/doctor/patients</span><span class="desc">Add new patient</span></li>
      <li><span class="method">GET</span><span class="path">/api/session/{{session_id}}</span><span class="desc">Load chat session</span></li>
      <li><span class="method post">POST</span><span class="path">/api/session/{{session_id}}/save</span><span class="desc">Save chat session</span></li>
      <li><span class="method post">POST</span><span class="path">/api/upload-pdf</span><span class="desc">Upload medical PDF</span></li>
      <li><span class="method post">POST</span><span class="path">/api/upload-guideline</span><span class="desc">Upload ADA guideline</span></li>
    </ul>
  </div>
  <div class="section">
    <h2>Frontend Integration</h2>
    <p style="color:#6b7280;font-size:14px;margin-bottom:12px">Set <code>API_URL</code> in your frontend's <code>apiConfig.js</code> to this backend's deployed URL.</p>
    <div class="status-row"><span class="status-label">Frontend (Vercel)</span><code>health-zeta-three.vercel.app</code></div>
    <div class="status-row"><span class="status-label">CORS</span><span style="color:#16a34a;font-weight:600">✓ Configured for all diabassist.app subdomains</span></div>
  </div>
</div>
<div class="footer">© 2026 Elements Interactive · IntelliHealth AI Clinical System v4.1 · Powered by Llama 3.3 70B via Groq</div>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/api/healthz")
async def proxy_health():
    return {"status": "ok", "service": "IntelliHealth API v4.1"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
