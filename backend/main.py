"""
IntelliHealth AI Clinical System — Backend
FastAPI + Gemma 2 (Groq) · ADA 2026 auto-loaded guidelines · Session persistence · PDF export
"""

import os
import io
import asyncio
import base64
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, Dict, Any, List
import threading

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
from fastapi.responses import HTMLResponse, StreamingResponse
from pymongo import MongoClient
from pydantic import BaseModel
from groq import Groq
from pypdf import PdfReader
from dotenv import load_dotenv

from doctor_auth import router as doctor_router
from auth import router as auth_router
from profile import router as profile_router
from email_service import send_diagnosis_email
from ada_guidelines_engine import get_ada_engine

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

load_dotenv()

# ── Auto-load guidelines at startup ───────────────────────────────────────────

_GUIDELINES_DIR = os.path.join(os.path.dirname(__file__), "guidelines")

# Global variable to store guideline loading status and results
guideline_load_status = {"loaded": False, "details": "Not yet loaded"}


async def load_guidelines_task():
    global guideline_load_status
    ada = get_ada_engine()
    try:
        print("[Guidelines] Starting background guideline load...")
        # This synchronous call will run in a separate thread thanks to asyncio.to_thread
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
    print("[Guidelines] Server starting... scheduling heavy load for fast boot")
    # Schedule the guideline loading as a background task
    asyncio.create_task(load_guidelines_task())

    # 🚀 IMPORTANT: allow server to start immediately
    yield

    print("[Guidelines] Server shutting down")


# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="IntelliHealth AI Clinical System",
    description="Advanced AI-assisted clinical decision support powered by Gemma 2 (Groq)",
    version="3.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Groq client ────────────────────────────────────────────────────────────────
groq_api_key = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=groq_api_key) if groq_api_key else None
groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
print(
    f"[AI] Model: {groq_model} | Client: {'ready' if groq_client else 'NOT configured'}"
)

# ── MongoDB ────────────────────────────────────────────────────────────────────
mongodburl = os.getenv("MONGODB_URL", "mongodb://localhost:27017/")
db_name = os.getenv("MONGODB_DBFULL_DB", "dbfull")
try:
    _mongo = MongoClient(mongodburl, serverSelectionTimeoutMS=5000)
    _mongo.admin.command("ping")
    _db = _mongo[db_name]
    patients_collection = _db["patients"]
    analyses_collection = _db["analyses"]
    email_notifications_collection = _db["email_notifications"]
    learning_journal_collection = _db["learning_journal"]
    learning_journal_collection.create_index([("disease", 1), ("query_type", 1)])
    learning_journal_collection.create_index([("rating", 1)])
    print(f"[DB] Connected to {db_name}")
except Exception as e:
    print(f"[DB] Connection failed: {e}")
    _mongo = None
    _db = None
    patients_collection = None
    analyses_collection = None
    email_notifications_collection = None
    learning_journal_collection = None

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(doctor_router)
app.include_router(auth_router)
app.include_router(profile_router)

api_router = APIRouter(prefix="/api")


# ── Pydantic models ────────────────────────────────────────────────────────────


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


class ExportReportRequest(BaseModel):
    patient: Dict[str, Any]
    doctor_name: Optional[str] = ""
    doctor_id: Optional[str] = ""
    specialization: Optional[str] = ""
    hospital: Optional[str] = ""
    chat_history: Optional[List[Dict[str, Any]]] = []
    export_date: Optional[str] = ""


# ── Helpers ────────────────────────────────────────────────────────────────────


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


# ── AI response generator ──────────────────────────────────────────────────────

_ADA_CITATION_RULES = """

═══════════════════════════════════════════════════════════════
INTELLIHEALTH EVIDENCE STANDARDS — MANDATORY IN EVERY RESPONSE
═══════════════════════════════════════════════════════════════
PRIMARY KNOWLEDGE BASE — ADA 2026 Standards of Care (Diabetes Care 2026;49):
  • §14 — Children and Adolescents (S297–S320)
  • §15 — Management of Diabetes in Pregnancy (S321–S338)
  • §16 — Diabetes Care in the Hospital (S339–S355)

EVIDENCE GRADING — tag every clinical recommendation with its grade:
  [A] — High-quality RCTs or meta-analyses; strong evidence
  [B] — Cohort/case-control studies; moderate evidence
  [C] — Expert consensus; limited data
  [E] — Expert opinion only

CITATION RULES (strictly enforced):
1. Cite ADA 2026 recommendation numbers inline:
     "Per ADA 2026 Rec. 14.5 [A], CGM is recommended for all T1D children."
     "ADA 2026 §16.5b [B] targets 100–180 mg/dL for non-critically ill inpatients."
2. Supplement with peer-reviewed sources when ADA does not cover the topic:
     - WHO Clinical Guidelines (with year)
     - Harrison's Principles of Internal Medicine (21st ed., 2022)
     - UpToDate (most recent version)
     - High-impact RCTs/meta-analyses: NEJM, Lancet, JAMA, BMJ (DOI required)
3. ALWAYS end with a ## References section — every cited source in full:
     Format: Author/Organization (Year). Title. Journal/Publisher. DOI.
4. Never fabricate references. Only cite real, verifiable literature.
5. Never present expert opinion as established evidence — always label [E].
6. If a recommendation number appears in the guideline context above, cite it.
═══════════════════════════════════════════════════════════════"""


# ── Learning journal helpers ───────────────────────────────────────────────────

def _retrieve_similar_cases(disease: str, query_type: str, limit: int = 3) -> str:
    """Pull high-rated past interactions for the same condition to enrich context."""
    if learning_journal_collection is None:
        return ""
    try:
        cursor = learning_journal_collection.find(
            {
                "disease": {"$regex": disease[:30], "$options": "i"},
                "query_type": query_type,
                "rating": {"$gte": 4},
            },
            {"response_snippet": 1, "key_recommendations": 1, "ada_refs": 1, "_id": 0},
        ).sort("rating", -1).limit(limit)
        docs = list(cursor)
        if not docs:
            return ""
        parts = ["PRIOR HIGH-QUALITY INTERACTIONS (for this condition):"]
        for i, doc in enumerate(docs, 1):
            parts.append(
                f"[Case {i}] {doc.get('key_recommendations', '')} | "
                f"ADA refs: {', '.join(doc.get('ada_refs', []))}"
            )
        return "\n".join(parts)
    except Exception:
        return ""


def _save_interaction(query_data, response_content: str, ada_refs: list):
    """Persist an AI interaction to the learning journal for future adaptation."""
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
                "model": groq_model,
                "created_at": datetime.utcnow().isoformat(),
            }
        )
    except Exception as e:
        print(f"[Learning] Save failed: {e}")


def _extract_key_recs(text: str) -> str:
    """Extract a compact summary of management recommendations from AI response."""
    lines = text.split("\n")
    recs = [l.strip() for l in lines if l.strip().startswith(("- **First", "- **Second", "**Target", "Recommend"))]
    return " | ".join(recs[:4]) if recs else text[:200]


def _extract_ada_refs(text: str) -> list:
    """Pull all ADA recommendation numbers cited in a response."""
    import re
    return list(set(re.findall(r"ADA\s+2026\s+(?:Rec(?:ommendation)?\.?\s*|§)[\d\.]+[a-z]?", text)))


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

    # ── Patient context ───────────────────────────────────────────────────────
    patient_ctx = f"""PATIENT RECORD:
  Name:                {query_data.pname or "Unknown"}
  Age:                 {age_text}
  Gender:              {query_data.gender or "Not specified"}
  Known Condition:     {disease}
  Current Medication:  {query_data.medication or "None"}
  Blood Pressure:      {query_data.bp or "Not recorded"}
  Pulse:               {query_data.pulse or "Not recorded"}
  BMI:                 {query_data.bmi or "Not recorded"}
  Presenting Complaint:{query_data.presenting_complaint or "Not specified"}
  Family History:      {query_data.family_history or "Not provided"}
  Social History:      {query_data.social_history or "Not provided"}
  Allergies:           {query_data.allergies or "None known"}"""

    # ── ADA guideline context ─────────────────────────────────────────────────
    if not guideline_load_status["loaded"]:
        guidelines_loaded = False
        ada_stats = {"guideline_loaded": False, "total_recommendations": 0, "sample_cases_loaded": 0}
    else:
        ada_stats = ada.get_guideline_stats()
        guidelines_loaded = ada_stats["guideline_loaded"]

    guideline_ctx = ""
    guideline_usage = {}
    if guidelines_loaded:
        patient_data_for_ctx = {
            "disease": disease,
            "age": query_data.age,
            "presenting_complaint": query_data.presenting_complaint or "",
        }
        clinical_q = custom_query or f"{query_type} for {disease}"
        guideline_ctx = ada.build_context_for_ai(patient_data_for_ctx, clinical_q, max_text_chars=6000)
        guideline_usage = {
            "sources": list(ada.sources.keys()),
            "total_recommendations": ada_stats["total_recommendations"],
            "sample_cases": ada_stats["sample_cases_loaded"],
        }

    # ── Uploaded file context ─────────────────────────────────────────────────
    uploaded_ctx = ""
    if query_data.pdf_text and query_data.pdf_text.strip():
        uploaded_ctx += f"\n\nUPLOADED MEDICAL PDF ({query_data.pdf_name or 'report'}):\n{query_data.pdf_text[:4000]}"
    if query_data.image_data:
        uploaded_ctx += f"\n\nMEDICAL IMAGE ({query_data.image_name or 'image'}): Provided for analysis."

    has_uploads = bool(query_data.pdf_text or query_data.image_data)
    analysis_focus = (
        "Analyze PRIMARILY from the UPLOADED DATA. Patient record is supporting context only. "
        "Consider ALL conditions visible — not just the recorded disease field."
        if has_uploads
        else "Analyze based on the patient record and presenting complaint."
    )

    # ── Learning journal context (similar validated past cases) ───────────────
    past_cases_ctx = _retrieve_similar_cases(disease, query_type)

    # ── Build system prompt ───────────────────────────────────────────────────
    if conv_type == "general" or query_type == "Generic":
        system_prompt = f"""You are IntelliHealth, an AI clinical reasoning system built on Gemma 2, supporting Dr. {doctor_name}.
You operate as a continuously learning, evidence-driven assistant that applies structured clinical reasoning and ADA 2026 guidelines.

{patient_ctx}
{uploaded_ctx}

{"=" * 60}
ADA 2026 KNOWLEDGE BASE
{"=" * 60}
{guideline_ctx}
{"=" * 60}
{past_cases_ctx}

RESPONSE REQUIREMENTS:
- Apply structured clinical reasoning: gather findings → identify abnormalities → rank differentials → recommend investigations → evidence-based management.
- Cite ADA 2026 recommendation numbers with evidence grade [A/B/C/E] for every recommendation.
- Be explicit about confidence level and any limitations in the data.
- Flag when urgent specialist referral is needed.
- NEVER present speculation as established fact.
{_ADA_CITATION_RULES}"""

    else:
        system_prompt = f"""You are IntelliHealth, a continuously learning AI Clinical Decision Support System built on Gemma 2, assisting Dr. {doctor_name}.

CORE MISSION: Apply expert-level clinical reasoning to generate evidence-graded, reference-backed recommendations that improve with each interaction.

ANALYSIS DIRECTIVE: {analysis_focus}

{patient_ctx}
{uploaded_ctx}

{"=" * 60}
ADA 2026 STANDARDS OF CARE — PRIMARY EVIDENCE BASE
{"=" * 60}
{guideline_ctx}
{"=" * 60}
{past_cases_ctx}

MANDATORY RESPONSE STRUCTURE — output each section in full:

## 1. Clinical Reasoning & Assessment
Systematically gather key findings → identify abnormalities → form clinical impression.
State your reasoning chain explicitly. Cite ADA 2026 recommendation numbers inline with evidence grade [A/B/C/E].
Example: "Per ADA 2026 Rec. 14.3 [A], HbA1c target <7% is recommended for most children."

## 2. Differential Diagnosis (ranked by probability)
List 3–5 diagnoses. For each state:
  - Probability: High / Moderate / Low
  - Supporting evidence from this patient's data
  - Discriminating investigations

## 3. Recommended Investigations
Specific labs, imaging, and tests with ADA 2026 target values where applicable.
State evidence grade for each test ordered.

## 4. Evidence-Based Management Plan
- **First-line [evidence grade]:** drug/intervention + dose + target
- **Second-line alternatives [evidence grade]:**
- **Medication monitoring:**
- **Contraindications given this patient's profile:**
Cite ADA 2026 recommendation number for EVERY pharmacological recommendation.

## 5. Monitoring & Follow-up Schedule
Specific parameters, frequency, and numerical targets from ADA 2026 (HbA1c, BP, lipids, renal function).

## 6. Red Flags & Urgent Escalation Criteria
Specific signs/values requiring emergency intervention or immediate specialist referral.

## 7. Confidence & Limitations
State your confidence level (High / Moderate / Low) and identify any data gaps, uncertainties, or alternative interpretations that the treating physician should consider.

## References
Every source cited above in full bibliographic format:
Author/Organization (Year). Title. Journal. Volume(Issue):Pages. DOI.

⚠️ All clinical decisions remain the sole responsibility of the treating physician.
{_ADA_CITATION_RULES}"""

    # ── User message by query type ────────────────────────────────────────────
    if custom_query and custom_query.strip():
        user_message = custom_query
    elif query_type == "Explain":
        user_message = (
            f"Apply structured clinical reasoning to assess this patient's condition ({disease}). "
            f"Generate ranked differentials, explain the clinical picture, and cite ADA 2026 guidelines."
        )
    elif query_type == "Treatment":
        user_message = (
            f"Propose a complete evidence-graded treatment plan for this patient with {disease}. "
            f"Include first-line and alternative pharmacological options with dosing, targets, and ADA 2026 citations."
        )
    elif query_type == "Medication":
        user_message = (
            f"Review this patient's current medication ({query_data.medication or 'current regimen'}) "
            f"and recommend evidence-based adjustments with specific dosing, monitoring parameters, and ADA 2026 citations."
        )
    elif query_type == "Lifestyle":
        user_message = (
            f"Provide an evidence-based lifestyle medicine plan for this patient with {disease}. "
            f"Cover nutrition, physical activity, weight targets, and behavioural interventions with ADA 2026 citations."
        )
    else:
        user_message = f"Perform a complete clinical analysis for this patient with {disease}, applying structured reasoning and ADA 2026 evidence-based guidelines."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=messages,
            model=groq_model,
            temperature=0.3,
            max_tokens=4096,
        )
        response_content = chat_completion.choices[0].message.content

        # ── Persist to learning journal ────────────────────────────────────────
        ada_refs = _extract_ada_refs(response_content)
        _save_interaction(query_data, response_content, ada_refs)

        return {
            "success": True,
            "content": response_content,
            "usage": guideline_usage,
            "ada_refs_found": ada_refs,
            "model": groq_model,
        }
    except Exception as e:
        print(f"[AI] Groq API error: {e}")
        return {
            "success": False,
            "error": f"AI response generation failed: {e}",
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

    # Colors
    PURPLE = colors.HexColor("#7c3aed")
    LIGHT_PURPLE = colors.HexColor("#f5f3ff")
    WHITE = colors.HexColor("#ffffff")
    GRAY = colors.HexColor("#e5e7eb")

    # Title
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

    # ── Doctor info ────────────────────────────────────────────────────────────
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

    # ── Patient info ────────────────────────────────────────────────────────────
    story.extend(section_header("Patient Information"))
    patient_data = [
        info_row("Patient Name", p.get("pname", "")),
        info_row("Patient ID", p.get("patid", "")),
        info_row(
            "Date of Birth / Age", f"{p.get('dob', '')}  |  {p.get('age', '')} years"
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

    # ── Consultation history ───────────────────────────────────────────────────
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
            ts = msg.get("timestamp", "")

            if role == "user":
                label = f"[Q{i}] Physician Query" + (
                    f" ({query_type})" if query_type else ""
                )
                story.append(Paragraph(label, q_style))
                story.append(Paragraph(content[:600], ai_style))
            else:
                label = f"[A{i}] AI Clinical Response"
                story.append(Paragraph(label, q_style))
                # Strip markdown for PDF
                clean = content.replace("**", "").replace("##", "").replace("*", "")
                story.append(Paragraph(clean[:2000], ai_style))

            story.append(Spacer(1, 2 * mm))

    # ── Disclaimer ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 5 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY))
    story.append(Spacer(1, 2 * mm))
    story.append(
        Paragraph(
            '<font color="#9ca3af" size="7">'
            "DISCLAIMER: This report is generated by an AI clinical decision support system (IntelliHealth / Med-Gemma). "
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


@api_router.get("/healthz")
@api_router.get("/health")
async def health():
    db_status, db_msg = "disconnected", "Not connected"
    try:
        if _mongo:
            _mongo.admin.command("ping")
            db_status, db_msg = "connected", f"Connected to {db_name}"
    except Exception as e:
        db_status, db_msg = "error", str(e)
    return {
        "status": "healthy"
        if db_status == "connected" and guideline_load_status["loaded"]
        else "degraded",
        "database": {"status": db_status, "message": db_msg, "name": db_name},
        "groq_api": "configured" if groq_client else "not configured",
        "model": groq_model,
        "guidelines": guideline_load_status,
        "timestamp": datetime.utcnow().isoformat(),
    }


@api_router.get("/model")
async def model_info():
    return {
        "groq_api": "configured" if groq_client else "not configured",
        "model": groq_model,
        "model_display": "LLaMA 3.3 (llama-3.3-70b)",
        "guidelines": guideline_load_status,
        "timestamp": datetime.utcnow().isoformat(),
    }


@api_router.post("/clinical-analysis")
async def get_clinical_analysis(
    query_data: ClinicalQuery, background_tasks: BackgroundTasks
):
    if not groq_client:
        raise HTTPException(
            status_code=503, detail="AI service not configured. Check GROQ_API_KEY."
        )
    if not guideline_load_status["loaded"] and query_data.use_ada_mode:
        raise HTTPException(
            status_code=503,
            detail="ADA Guidelines are still loading. Please try again in a moment.",
        )

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


@api_router.post("/export-report")
async def export_report(req: ExportReportRequest):
    """Generate and download a professional PDF patient consultation report."""
    try:
        pdf_bytes = generate_report_pdf(req)
        patient_name = req.patient.get("pname", "Patient").replace(" ", "_")
        date_str = datetime.utcnow().strftime("%Y%m%d")
        filename = f"IntelliHealth_Report_{patient_name}_{date_str}.pdf"
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
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
    # Update global status after successful upload of a new guideline
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
    # Update global status after successful upload of an additional guideline
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


@api_router.get("/list-guidelines")
@api_router.post("/list-guidelines")
async def list_guidelines():
    ada = get_ada_engine()
    stats = ada.get_guideline_stats()
    return {"success": True, "stats": stats, "load_status": guideline_load_status}


class FeedbackRequest(BaseModel):
    interaction_id: Optional[str] = ""
    disease: str
    query_type: str
    rating: int
    doctor_feedback: Optional[str] = ""
    correction: Optional[str] = ""


@api_router.post("/feedback")
async def submit_feedback(req: FeedbackRequest):
    """Doctors rate AI responses 1–5 and optionally provide corrections for model learning."""
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
            "model": groq_model,
            "created_at": datetime.utcnow().isoformat(),
        }
    )
    return {"success": True, "message": "Feedback recorded. Thank you — this improves future recommendations."}


@api_router.get("/learning-stats")
async def learning_stats():
    """Return learning journal statistics showing model improvement over time."""
    if learning_journal_collection is None:
        return {"success": False, "error": "Learning journal not connected"}
    try:
        total = learning_journal_collection.count_documents({})
        rated = learning_journal_collection.count_documents({"rating": {"$ne": None}})
        pipeline = [
            {"$match": {"rating": {"$ne": None}}},
            {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}},
        ]
        avg_result = list(learning_journal_collection.aggregate(pipeline))
        avg_rating = round(avg_result[0]["avg"], 2) if avg_result else None

        by_condition = list(learning_journal_collection.aggregate([
            {"$match": {"rating": {"$gte": 4}}},
            {"$group": {"_id": "$disease", "count": {"$sum": 1}, "avg_rating": {"$avg": "$rating"}}},
            {"$sort": {"count": -1}},
            {"$limit": 10},
        ]))

        corrections = list(learning_journal_collection.find(
            {"correction": {"$ne": ""}},
            {"disease": 1, "query_type": 1, "correction": 1, "rating": 1, "_id": 0}
        ).sort("feedback_at", -1).limit(5))

        return {
            "success": True,
            "total_interactions": total,
            "rated_interactions": rated,
            "average_rating": avg_rating,
            "top_conditions": by_condition,
            "recent_corrections": corrections,
            "model": groq_model,
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
        "model": groq_model,
    }


@api_router.get("/")
async def api_root():
    return {
        "message": "IntelliHealth AI Clinical System API v3",
        "model": groq_model,
        "status": "running",
        "docs": "/api/docs",
        "admin": "/admin",
    }


# Register main router
app.include_router(api_router)


# ── Admin Dashboard ────────────────────────────────────────────────────────────


@app.get("/admin", response_class=HTMLResponse)
@app.get("/api/admin", response_class=HTMLResponse)
@app.get("/", response_class=HTMLResponse)
async def admin_dashboard():
    db_ok = False
    patient_count = 0
    doctor_count = 0
    try:
        if _mongo:
            _mongo.admin.command("ping")
            db_ok = True
            patient_count = (
                patients_collection.count_documents({}) if patients_collection else 0
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

    # Build guideline rows
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
</style>
</head>
<body>
<nav class="navbar">
  <div class="navbar-brand">Intelli<span>Health</span> <span style="font-weight:300;font-size:14px">Admin</span></div>
  <div class="navbar-right">AI Clinical System v3.0</div>
</nav>

<div class="hero">
  <h1>System Dashboard</h1>
  <p>IntelliHealth AI Clinical Backend — powered by Gemma 2 (Groq) via Groq</p>
</div>

<div class="container">
  <div class="grid">
    <div class="card">
      <div class="card-icon">🧑‍⚕️</div>
      <div class="card-value">{doctor_count}</div>
      <div class="card-label">Registered Doctors</div>
    </div>
    <div class="card">
      <div class="card-icon">🏥</div>
      <div class="card-value">{patient_count}</div>
      <div class="card-label">Total Patients</div>
    </div>
    <div class="card">
      <div class="card-icon">📚</div>
      <div class="card-value">{guideline_count}</div>
      <div class="card-label">ADA 2026 Guideline Docs</div>
    </div>
    <div class="card">
      <div class="card-icon">🔖</div>
      <div class="card-value">{rec_count}</div>
      <div class="card-label">Indexed Recommendations</div>
    </div>
    <div class="card">
      <div class="card-icon">🩺</div>
      <div class="card-value">{case_count}</div>
      <div class="card-label">Clinical Sample Cases</div>
    </div>
    <div class="card">
      <div class="card-icon">🕐</div>
      <div class="card-value" style="font-size:13px">{now}</div>
      <div class="card-label">Server Time (UTC)</div>
    </div>
  </div>

  <div class="section">
    <h2>System Status</h2>
    <div class="status-row">
      <span class="status-label">🗄️ MongoDB Database</span>
      {db_badge}
    </div>
    <div class="status-row">
      <span class="status-label">🤖 LLaMA 3.3 via Groq</span>
      {ai_badge}
    </div>
    <div class="status-row">
      <span class="status-label">📚 ADA 2026 Guidelines</span>
      {gl_badge}
    </div>
    <div class="status-row">
      <span class="status-label">📡 AI Model</span>
      <code>{groq_model}</code>
    </div>
    <div class="status-row">
      <span class="status-label">🔗 Database</span>
      <code>{db_name}</code>
    </div>
    <div class="flex-row">
      <a href="/api/docs" class="link-btn">📄 API Docs (Swagger)</a>
      <a href="/api/health" class="link-btn outline">🩺 Health Check</a>
      <a href="/api/list-guidelines" class="link-btn outline">📚 Guidelines Status</a>
    </div>
  </div>

  <div class="section">
    <h2>Loaded ADA 2026 Guidelines</h2>
    <p style="color:#6b7280;font-size:13px;margin-bottom:14px">
      These documents are auto-loaded at startup. Every AI response cites specific recommendation numbers (14.x, 15.x, 16.x) from these sources.
    </p>
    {gl_rows}
  </div>

  <div class="section">
    <h2>Key API Endpoints</h2>
    <ul class="endpoint-list">
      <li><span class="method post">POST</span><span class="path">/api/clinical-analysis</span><span class="desc">Gemma 2 clinical analysis</span></li>
      <li><span class="method post">POST</span><span class="path">/api/export-report</span><span class="desc">Download PDF report</span></li>
      <li><span class="method post">POST</span><span class="path">/api/doctor/login</span><span class="desc">Doctor authentication</span></li>
      <li><span class="method post">POST</span><span class="path">/api/doctor/signup</span><span class="desc">Doctor registration</span></li>
      <li><span class="method">GET</span><span class="path">/api/doctor/patients</span><span class="desc">List patients</span></li>
      <li><span class="method post">POST</span><span class="path">/api/doctor/patients</span><span class="desc">Add new patient</span></li>
      <li><span class="method">GET</span><span class="path">/api/session/{patid}</span><span class="desc">Load chat session</span></li>
      <li><span class="method post">POST</span><span class="path">/api/session/{patid}/save</span><span class="desc">Save chat session</span></li>
      <li><span class="method post">POST</span><span class="path">/api/upload-pdf</span><span class="desc">Upload medical PDF</span></li>
      <li><span class="method post">POST</span><span class="path">/api/upload-guideline</span><span class="desc">Upload ADA guideline</span></li>
    </ul>
  </div>

  <div class="section">
    <h2>Frontend Integration</h2>
    <p style="color:#6b7280;font-size:14px;margin-bottom:12px">
      Set <code>API_URL</code> in your frontend's <code>apiConfig.js</code> to this backend's deployed URL.
      The backend supports CORS from all origins.
    </p>
    <div class="status-row">
      <span class="status-label">Frontend (Vercel)</span>
      <code>health-zeta-three.vercel.app</code>
    </div>
    <div class="status-row">
      <span class="status-label">CORS</span>
      <span style="color:#16a34a;font-weight:600">✓ All origins allowed</span>
    </div>
  </div>
</div>

<div class="footer">
  © 2026 Elements Interactive · IntelliHealth AI Clinical System · Powered by LLaMA 3.3 via Groq
</div>
</body>
</html>"""
    return HTMLResponse(content=html)


# ── Root health for proxy ──────────────────────────────────────────────────────


@app.get("/api/healthz")
async def proxy_health():
    return {"status": "ok", "service": "IntelliHealth API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
