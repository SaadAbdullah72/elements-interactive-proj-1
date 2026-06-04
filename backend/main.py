"""
Advanced AI Clinical System with Image & PDF Analysis
Independent analysis for each query based on uploaded data
"""

import os
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from groq import Groq
from pypdf import PdfReader  # Pure Python PDF reader
import io
import base64
from datetime import datetime

# Import routers
from doctor_auth import router as doctor_router
from auth import router as auth_router
from profile import router as profile_router

# Import services
from email_service import send_diagnosis_email
from ada_guidelines_engine import get_ada_engine

load_dotenv()

# NOTE: This module is the main FastAPI application for IntelliHealth.
# It wires together routers, AI client initialization, and file-upload
# helpers. Keep this file focused on high-level wiring; business logic
# lives in the imported modules (auth, doctor_auth, profile, etc.).
#
# Security note: do not print secrets or full connection strings to logs.
app = FastAPI(title="IntelliHealth AI Clinical System")

# -------------------------
# CORS Middleware Setup
# -------------------------
# Using allow_credentials=False so allow_origins=["*"] works
# Frontend sends JWT via Authorization header, not cookies
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://health-zeta-three.vercel.app",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
# -------------------------
# Groq API Client Setup
# -------------------------
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    print("Warning: GROQ_API_KEY not found. AI features will not work.")
    groq_client = None
else:
    groq_client = Groq(api_key=groq_api_key)
# Allow overriding the default Groq model via environment (e.g. MEDGEMMA)
groq_model = os.getenv("GROQ_MODEL", "google/gemma-3-27b-it")
print(f"Using GROQ model: {groq_model}")

# -------------------------
# MongoDB Setup with DB Connection Logging
# -------------------------
mongodburl = os.getenv(
    "MONGODB_URL", os.getenv("LOCAL_MONGODB_URL", "mongodb://localhost:27017/")
)
db_name = os.getenv("MONGODB_LOCAL_DB", "local_data")

is_live = "mongodb+srv" in mongodburl

print("\n" + "=" * 60)
if is_live:
    print("  DATABASE MODE : LIVE ATLAS (Cloud)")
else:
    print("  DATABASE MODE : LOCAL MongoDB")
print(f"  Database Name : {db_name}")
print(f"  URL Type      : {'mongodb+srv (Atlas)' if is_live else 'localhost (Local)'}")
if mongodburl:
    print("  MongoDB URL   : (configured)")
else:
    print("  MongoDB URL   : NOT SET")
print("=" * 60 + "\n")

# Initialize MongoDB with error handling
try:
    client = MongoClient(mongodburl, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db = client[db_name]
    patients_collection = db["patients"]
    analyses_collection = db["analyses"]
    email_notifications_collection = db["email_notifications"]
    print("MongoDB connection successful!")
except Exception as e:
    print(f"MongoDB connection failed: {e}")
    print("Some features will not work until MongoDB is configured")
    db = None
    patients_collection = None
    analyses_collection = None
    email_notifications_collection = None

# -------------------------
# Include Routers
# -------------------------
app.include_router(doctor_router)
app.include_router(auth_router)
app.include_router(profile_router)

# -------------------------
# Main API Router (prefix /api for all main routes)
# -------------------------
api_router = APIRouter(prefix="/api")


# -------------------------
# Pydantic Models
# -------------------------
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
    use_ada_mode: Optional[bool] = False


# -------------------------
# Email Notification Tracking
# -------------------------
def should_send_email(patient_email: str):
    if not patient_email:
        return False, "No patient email provided"
    if email_notifications_collection is None:
        return False, "Database not connected"

    tracking = email_notifications_collection.find_one({"patient_email": patient_email})

    if tracking and tracking.get("emails_sent", 0) >= 1:
        return False, f"Email already sent to {patient_email} on first query — skipping"

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

    print(f"First query for {patient_email} — sending email now")
    return True, f"First consultation detected for {patient_email} — sending email"


# -------------------------
# Helper Functions
# -------------------------
def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        print(f"PDF extraction error: {e}")
        return ""


def encode_image_to_base64(file_bytes: bytes) -> str:
    return base64.b64encode(file_bytes).decode("utf-8")


# -------------------------
# Advanced AI Response Generator
# -------------------------
def generate_advanced_ai_response(query_data: ClinicalQuery) -> Dict[str, Any]:
    if not groq_client:
        return {"error": "AI service unavailable"}

    query_type = query_data.query_type
    custom_query = query_data.custom_query or ""
    conversation_type = query_data.conversation_type or "clinical"

    print(f"\n{'=' * 70}")
    print(f"STARTING AI CLINICAL ANALYSIS")
    print(f"   - Patient: {query_data.pname} (ID: {query_data.patid})")
    print(f"   - Query: {query_type} | Conversation: {conversation_type}")
    print(f"   - ADA Mode: {'ENABLED' if query_data.use_ada_mode else 'DISABLED'}")
    print(f"{'=' * 70}")

    if query_data.use_ada_mode:
        ada_engine = get_ada_engine()
        stats = ada_engine.get_guideline_stats()

        if not stats["guideline_loaded"]:
            return {
                "success": False,
                "error": "ADA mode requested but no guidelines loaded",
                "message": "Please upload ADA 2026 guideline PDF via /api/upload-guideline endpoint first",
                "status": "GUIDELINE NOT LOADED",
            }

        patient_data_for_ada = {
            "age": query_data.age,
            "gender": query_data.gender or "Not specified",
            "A1C": query_data.disease or "Not measured",
            "FPG": "See patient notes",
            "BMI": query_data.bmi or "Not recorded",
            "conditions": [query_data.disease] if query_data.disease else [],
            "risk_factors": [query_data.medication] if query_data.medication else [],
            "family_history": query_data.family_history or "Not provided",
            "allergies": query_data.allergies or "None known",
        }

        ada_prompt, guideline_usage = ada_engine.build_ada_prompt(
            patient_data=patient_data_for_ada,
            clinical_question=query_data.custom_query
            or f"{query_data.query_type}: Provide guideline-based analysis for {query_data.pname}",
        )

        try:
            response = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": ada_prompt},
                    {
                        "role": "user",
                        "content": f"Patient: {query_data.pname}, Age: {query_data.age}\n\nAnalyze based STRICTLY on ALL guideline sources provided.",
                    },
                ],
                model="google/gemma-3-27b-it",
                max_tokens=3000,
                temperature=0.3,
            )

            ai_content = response.choices[0].message.content.strip()
            validation = ada_engine.validate_response(ai_content)

            return {
                "success": True,
                "content": ai_content,
                "query_type": query_type,
                "conversation_type": "ADA_2026_COMPLIANT",
                "mode": "ADA 2026 GUIDELINE-COMPLIANT",
                "analyzed_uploaded_data": bool(
                    query_data.pdf_text or query_data.image_data
                ),
                "guideline_usage": {
                    "total_sources_used": guideline_usage["active_guideline_sources"],
                    "sources_list": guideline_usage["sources"],
                    "total_words_in_context": guideline_usage["total_content_words"],
                },
                "guideline_stats": stats,
                "validation": validation,
                "model_used": groq_model,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            print(f"ADA mode error: {e}")
            return {
                "success": False,
                "error": str(e),
                "mode": "ADA 2026",
                "message": "Error generating ADA-compliant response",
            }

    # ===== STANDARD MODE =====
    age_text = f"{query_data.age} years" if query_data.age else "Unknown age"
    bmi_text = f"{query_data.bmi}" if query_data.bmi else "Not recorded"
    patient_db_context = f"""
PATIENT DATABASE RECORD:
- Name: {query_data.pname or 'Unknown patient'}
- Age: {age_text}
- Gender: {query_data.gender or 'Not specified'}
- Known Disease/Condition: {query_data.disease or 'Not specified'}
- Current Medication: {query_data.medication or 'Not specified'}
- Blood Pressure: {query_data.bp or 'Not recorded'}
- BMI: {bmi_text}
- Family History: {query_data.family_history or 'Not provided'}
- Allergies: {query_data.allergies or 'None known'}
"""

    uploaded_data_context = ""
    if query_data.pdf_text and query_data.pdf_text.strip():
        uploaded_data_context += f"""
UPLOADED PDF REPORT ({query_data.pdf_name or "Unnamed"}):
{query_data.pdf_text[:3000]}
"""

    if query_data.image_data:
        uploaded_data_context += f"""
UPLOADED MEDICAL IMAGE ({query_data.image_name or "Unnamed"}):
Image has been uploaded for analysis. Analyze this image for abnormalities and clinical findings.
"""

    has_uploaded_data = bool(query_data.pdf_text or query_data.image_data)

    if has_uploaded_data:
        analysis_focus = """
IMPORTANT: Base analysis PRIMARILY on UPLOADED DATA. Patient database is context only.
A patient can have MULTIPLE conditions. Do NOT limit analysis to only the known disease.
"""
    else:
        analysis_focus = "Base your analysis on the patient's database record and clinical presentation."

    custom_query_instruction = ""
    if custom_query and custom_query.strip():
        custom_query_instruction = f"""
USER'S SPECIFIC QUESTION: "{custom_query}"
Address this specific question comprehensively and in detail.
"""

    doctor_identity = query_data.doctor_name or "Doctor"

    # Build system prompt based on query type
    if query_type == "Generic":
        system_prompt = f"""You are a knowledgeable clinical assistant assisting {doctor_identity} in reviewing patient records for {query_data.pname}.
PATIENT CONTEXT:\n{patient_db_context}\n{uploaded_data_context}\n{custom_query_instruction}
Provide helpful, evidence-based clinical information. Always recommend professional consultation."""
    elif conversation_type == "general":
        system_prompt = f"""You are a knowledgeable healthcare advisor providing general health information.
Use simple language. Explicitly state when professional consultation is needed.
PATIENT CONTEXT:\n{patient_db_context}\n{custom_query_instruction}"""
    else:
        system_prompt = f"""You are an advanced AI clinical decision support system assisting {doctor_identity}.
{analysis_focus}
PATIENT CONTEXT:\n{patient_db_context}\n{uploaded_data_context}\n{custom_query_instruction}
Provide comprehensive, evidence-based clinical analysis. All recommendations require physician review."""

    try:
        messages = [{"role": "system", "content": system_prompt}]

        if query_data.image_data and conversation_type != "general":
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{query_data.image_data}"
                            },
                        },
                        {
                            "type": "text",
                            "text": f"Analyze this medical image for {query_data.pname}, age {query_data.age}. {custom_query or 'Provide comprehensive analysis.'}",
                        },
                    ],
                }
            )
        else:
            messages.append(
                {
                    "role": "user",
                    "content": f"Provide {query_type.lower()} analysis for {query_data.pname}, age {query_data.age}. {custom_query or ''}",
                }
            )

        response = groq_client.chat.completions.create(
            messages=messages,
            model=groq_model,
            max_tokens=2000,
            temperature=0.7,
        )

        ai_content = response.choices[0].message.content.strip()

        return {
            "success": True,
            "content": ai_content,
            "query_type": query_type,
            "conversation_type": conversation_type,
            "analyzed_uploaded_data": has_uploaded_data,
            "model_used": groq_model,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        print(f"AI generation error: {e}")
        import traceback

        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
                "message": "Error generating AI response",
                "model_used": groq_model,
        }


# -------------------------
# API Endpoints (all prefixed with /api)
# -------------------------


@api_router.get("/healthz")
@api_router.get("/health")
async def health():
    db_status = "unknown"
    db_message = "Database status unknown"

    try:
        if client is not None:
            client.admin.command("ping")
            db_status = "connected"
            db_message = f"Connected to {db_name} database"
        else:
            db_status = "disconnected"
            db_message = "Database client not initialized"
    except Exception as e:
        db_status = "error"
        db_message = f"Database connection error: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "database": {"status": db_status, "message": db_message, "name": db_name},
        "groq_api": "configured" if groq_client else "not configured",
        "timestamp": datetime.utcnow().isoformat(),
    }


@api_router.get("/model")
async def model_info():
    """Return the active Groq model and client status."""
    return {
        "groq_api": "configured" if groq_client else "not configured",
        "model": groq_model,
        "timestamp": datetime.utcnow().isoformat(),
    }


@api_router.post("/clinical-analysis")
async def get_clinical_analysis(
    query_data: ClinicalQuery, background_tasks: BackgroundTasks
):
    if not groq_client:
        raise HTTPException(
            status_code=503,
            detail="AI service (Groq) not configured. Check GROQ_API_KEY.",
        )

    result = generate_advanced_ai_response(query_data)

    if result.get("success") and query_data.patient_email:
        send_email, reason = should_send_email(query_data.patient_email)
        print(f"Email decision: {reason}")

        if send_email:
            ai_summary = result.get("content", "")[:500]
            background_tasks.add_task(
                send_diagnosis_email,
                patient_email=query_data.patient_email,
                patient_name=query_data.pname,
                doctor_name=query_data.doctor_name or "Your Doctor",
                diagnosis_summary=ai_summary,
            )

    return result


@api_router.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    file_bytes = await file.read()
    extracted_text = extract_text_from_pdf(file_bytes)

    if not extracted_text.strip():
        raise HTTPException(
            status_code=400, detail="Could not extract text from the PDF"
        )

    return {
        "success": True,
        "filename": file.filename,
        "text": extracted_text,
        "character_count": len(extracted_text),
        "word_count": len(extracted_text.split()),
    }


@api_router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400, detail=f"Image type {file.content_type} not supported"
        )

    file_bytes = await file.read()
    image_base64 = encode_image_to_base64(file_bytes)

    return {
        "success": True,
        "filename": file.filename,
        "image_data": image_base64,
        "file_size": len(file_bytes),
    }


@api_router.post("/upload-guideline")
async def upload_guideline(file: UploadFile = File(...), source_name: str = "ADA_2026"):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail="Only PDF files are accepted for guidelines"
        )

    file_bytes = await file.read()
    extracted_text = extract_text_from_pdf(file_bytes)

    if not extracted_text.strip():
        raise HTTPException(
            status_code=400, detail="Could not extract text from guideline PDF"
        )

    ada_engine = get_ada_engine()
    result = ada_engine.set_guideline_content(extracted_text, source_name)
    stats = ada_engine.get_guideline_stats()

    return {
        "success": True,
        "filename": file.filename,
        "source_name": source_name,
        "guideline_length": len(extracted_text),
        "word_count": len(extracted_text.split()),
        "stats": stats,
        "message": f"Guideline '{source_name}' uploaded and activated for ADA mode",
    }


@api_router.post("/upload-additional-guideline")
async def upload_additional_guideline(
    file: UploadFile = File(...),
    source_name: str = "Additional_Guideline",
    source_type: str = "guideline",
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    file_bytes = await file.read()
    extracted_text = extract_text_from_pdf(file_bytes)

    if not extracted_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")

    ada_engine = get_ada_engine()
    result = ada_engine.add_guideline_source(source_name, extracted_text, source_type)
    stats = ada_engine.get_guideline_stats()

    return {
        "success": True,
        "filename": file.filename,
        "result": result,
        "total_sources": stats["total_sources_loaded"],
    }


@api_router.post("/list-guidelines")
@api_router.get("/list-guidelines")
async def list_guidelines():
    ada_engine = get_ada_engine()
    stats = ada_engine.get_guideline_stats()
    return {
        "success": True,
        "stats": stats,
        "message": f"{stats['total_sources_loaded']} guideline source(s) loaded",
    }


@api_router.post("/demo-cases")
async def list_demo_cases(request: dict):
    patient_data = request.get("patient_data", {})
    disease = patient_data.get("disease", "General Condition")

    demo_cases = [
        {
            "id": "explain",
            "title": f"Explain {disease}",
            "description": "Comprehensive explanation of the condition",
            "query_type": "Explain",
        },
        {
            "id": "treatment",
            "title": "Treatment Plan",
            "description": "Evidence-based treatment recommendations",
            "query_type": "Treatment",
        },
        {
            "id": "medication",
            "title": "Medication Review",
            "description": "Analysis of current medications",
            "query_type": "Medication",
        },
        {
            "id": "lifestyle",
            "title": "Lifestyle Guidance",
            "description": "Lifestyle modification recommendations",
            "query_type": "Lifestyle",
        },
    ]
    return {"success": True, "demo_cases": demo_cases}


@api_router.post("/demo-case/run")
async def run_demo_case(demo_request: dict):
    import time

    patient_data = demo_request.get("patient_data", {})
    query_type = demo_request.get("query_type", "Explain")

    full_query = {
        "caseid": patient_data.get("caseid", "DEMO"),
        "patid": patient_data.get("patid", "DEMO"),
        "pname": patient_data.get("pname", "Demo Patient"),
        "dob": "",
        "age": int(patient_data.get("age", 30)),
        "gender": patient_data.get("gender", "Male"),
        "disease": patient_data.get("disease", "Unknown"),
        "medication": patient_data.get("medication", "None"),
        "bp": patient_data.get("bp", "120/80"),
        "pulse": patient_data.get("pulse", "80"),
        "bmi": float(patient_data.get("bmi", 25)),
        "presenting_complaint": patient_data.get(
            "presenting_complaint", "General checkup"
        ),
        "family_history": patient_data.get("family_history", "None"),
        "social_history": patient_data.get("social_history", "None"),
        "allergies": patient_data.get("allergies", "None"),
        "query_type": query_type,
        "custom_query": "",
    }

    query = ClinicalQuery(**full_query)

    start_time = time.time()
    result = generate_advanced_ai_response(query)
    response_time = round(time.time() - start_time, 2)

    return {
        "success": True,
        "title": f"{patient_data.get('disease', 'Condition')} - {query_type} Analysis",
        "patient_info": {
            "name": patient_data.get("pname", "Demo Patient"),
            "age": patient_data.get("age", 30),
            "condition": patient_data.get("disease", "Unknown"),
        },
        "query_type": query_type,
        "ai_analysis": result.get("content", ""),
        "analysis_metadata": {
            "response_time_seconds": response_time,
            "ai_model": groq_model,
        },
    }


@api_router.get("/")
async def root():
    return {
        "message": "IntelliHealth AI Clinical System API",
        "status": "running",
        "version": "2.0",
        "endpoints": {
            "health": "GET /api/health",
            "clinical_analysis": "POST /api/clinical-analysis",
            "upload_pdf": "POST /api/upload-pdf",
            "upload_image": "POST /api/upload-image",
            "auth": "/api/auth/*",
            "doctor": "/api/doctor/*",
            "profile": "/api/profile/*",
        },
    }


# Register the main api_router
app.include_router(api_router)


# Root health check for the proxy
@app.get("/")
async def root_redirect():
    return {"message": "IntelliHealth AI Clinical System", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
