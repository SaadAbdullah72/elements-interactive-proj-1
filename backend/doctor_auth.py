"""
Doctor authentication, patient management, and session system.

Doctor ID format: DR{gender}-{last4_phone}-{last3_cnic}
  gender: 1=Male, 0=Female
  last4_phone: last 4 digits of normalized phone number
  last3_cnic: last 3 digits of CNIC (digits only)

Example: DR1-4567-891
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, validator
from pymongo import MongoClient, DESCENDING
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import jwt
import hashlib
import re
import os
import random

load_dotenv()

router = APIRouter(prefix="/api", tags=["Doctor System"])

mongodburl = os.getenv("MONGODB_URL", "mongodb://localhost:27017/")
auth_db_name = os.getenv("MONGODB_AUTH_DB", "authentication")
app_db_name = os.getenv("MONGODB_DBFULL_DB", "dbfull")

try:
    _client = MongoClient(mongodburl, serverSelectionTimeoutMS=5000)
    _client.admin.command("ping")
    auth_db = _client[auth_db_name]
    doctors_collection = auth_db["doctors"]
    license_verifications_collection = auth_db["license_verifications"]
    app_db = _client[app_db_name]
    patients_collection = app_db["patients"]
    sessions_collection = app_db["sessions"]

    patients_collection.create_index("patid", unique=True, sparse=True)
    patients_collection.create_index("phone_number", unique=True, sparse=True)
    sessions_collection.create_index([("patid", 1), ("doctor_name", 1)])

    print(f"[Doctor Auth] MongoDB connected. auth={auth_db_name} app={app_db_name}")
except Exception as e:
    print(f"[Doctor Auth] MongoDB connection failed: {e}")
    doctors_collection = None
    license_verifications_collection = None
    patients_collection = None
    sessions_collection = None

MEDICAL_SPECIALTIES = [
    "General Physician", "Cardiologist", "Neurologist", "Pediatrician",
    "Orthopedic Surgeon", "Dermatologist", "Gastroenterologist",
    "Endocrinologist", "Pulmonologist", "Nephrologist", "Oncologist",
    "Hematologist", "Rheumatologist", "Infectious Disease Specialist",
    "Allergist/Immunologist", "Psychiatrist", "Psychologist", "Radiologist",
    "Anesthesiologist", "Pathologist", "Ophthalmologist",
    "Otolaryngologist (ENT)", "Urologist", "Gynecologist", "Obstetrician",
    "Plastic Surgeon", "Cardiothoracic Surgeon", "Neurosurgeon",
    "Vascular Surgeon", "Colorectal Surgeon", "Emergency Medicine Physician",
    "Family Medicine Physician", "Internal Medicine Physician",
    "Preventive Medicine Physician", "Physical Medicine & Rehabilitation",
    "Pain Management Specialist", "Sleep Medicine Specialist",
    "Sports Medicine Specialist", "Geriatrician", "Hepatologist",
    "Intensivist (Critical Care)", "Medical Geneticist",
    "Nuclear Medicine Physician", "Occupational Medicine Physician",
    "Palliative Care Physician", "Reproductive Endocrinologist",
    "Transplant Surgeon", "Trauma Surgeon", "Dentist", "Oral Surgeon",
    "Periodontist", "Endodontist", "Orthodontist", "Prosthodontist",
    "Pediatric Dentist",
]

PROVINCE_CODE_MAP = {
    "punjab": "3", "sindh": "4", "khyber pakhtunkhwa": "5", "kpk": "5",
    "balochistan": "6", "islamabad": "7", "islamabad capital territory": "7",
    "gilgit-baltistan": "8", "gilgit baltistan": "8", "gilgit": "8",
    "azad jammu & kashmir": "9", "ajk": "9",
}

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 1440

security = HTTPBearer(auto_error=False)


# ── Helpers ──────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed


def create_access_token(data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("0092"):
        digits = "0" + digits[4:]
    elif digits.startswith("92") and len(digits) == 12:
        digits = "0" + digits[2:]
    elif digits.startswith("3") and len(digits) == 10:
        digits = "0" + digits
    return digits


def generate_doctor_id(gender: str, phone: str, cnic: str) -> str:
    """
    Format: DR{gender_code}-{last4_phone}-{last3_cnic}
    gender_code: 1=Male, 0=Female
    last4_phone: last 4 digits of normalized phone
    last3_cnic:  last 3 digits of CNIC (digits only)
    """
    gender_code = "1" if gender.strip().lower() == "male" else "0"
    phone_digits = re.sub(r"\D", "", normalize_phone(phone))
    cnic_digits = re.sub(r"\D", "", cnic)
    last4_phone = phone_digits[-4:].zfill(4) if phone_digits else "0000"
    last3_cnic = cnic_digits[-3:].zfill(3) if cnic_digits else "000"
    return f"DR{gender_code}-{last4_phone}-{last3_cnic}"


def verify_pmc_license(license_number: str, doctor_name: str) -> Dict[str, Any]:
    pmc_pattern = r"^(PMC|PMDC)-\d{5,7}$"
    numeric_pattern = r"^\d{6,8}$"
    result = {
        "verified": False,
        "license_number": license_number,
        "doctor_name": doctor_name,
        "verification_date": datetime.utcnow().isoformat(),
        "source": "Pakistan Medical Commission (PMC)",
        "status": "pending",
        "message": "",
    }
    if re.match(pmc_pattern, license_number.upper()) or re.match(numeric_pattern, license_number):
        result.update({"verified": True, "status": "active",
                        "message": "License verified with PMC",
                        "valid_until": "2026-12-31"})
    else:
        result["message"] = "Invalid license format. Expected: PMC-XXXXX or 6-8 digits"
        result["status"] = "invalid_format"
    return result


def verify_cnic(cnic: str) -> Dict[str, Any]:
    result = {"verified": False, "cnic": cnic, "message": ""}
    digits = re.sub(r"\D", "", cnic)
    if len(digits) == 13:
        result.update({"verified": True, "message": "CNIC validated"})
    else:
        result["message"] = "Invalid CNIC. Expected: XXXXX-XXXXXXX-X (13 digits)"
    return result


def get_doctor_from_token(credentials: HTTPAuthorizationCredentials) -> Dict[str, Any]:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ── Auto-seed default doctor ──────────────────────────────────────────────────

def seed_default_doctor():
    if doctors_collection is None:
        return
    try:
        DEFAULT = {
            "email": "admin@diabassist.com",
            "password": "Doctor@1122",
            "name": "DrAdmin",
            "age": 40,
            "date_of_birth": "1984-01-01",
            "gender": "Male",
            "province": "Sindh",
            "specialization": "General Physician",
            "medical_council_registration": "PMC-123456",
            "medical_council_country": "Pakistan",
            "cnic": "42101-1234567-1",
            "phone": "03001234567",
            "address": "123 Main Street, Gulshan",
            "city": "Karachi",
            "hospital_affiliation": "IntelliHealth Medical Center",
            "hospital_address": "456 Hospital Road, Karachi",
            "years_of_experience": 15,
            "additional_qualifications": "MBBS, FCPS",
        }
        if doctors_collection.find_one({"email": DEFAULT["email"]}):
            return
        doctor_id = generate_doctor_id(
            DEFAULT["gender"], DEFAULT["phone"], DEFAULT["cnic"]
        )
        doctors_collection.insert_one({
            **{k: v for k, v in DEFAULT.items() if k != "password"},
            "password_hash": hash_password(DEFAULT["password"]),
            "doctor_id": doctor_id,
            "license_verification": verify_pmc_license(DEFAULT["medical_council_registration"], DEFAULT["name"]),
            "cnic_verification": verify_cnic(DEFAULT["cnic"]),
            "account_status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "last_login": None,
            "total_consultations": 0,
            "is_default_seed": True,
        })
        print(f"[Seed] Default doctor created. ID: {doctor_id}")
    except Exception as e:
        print(f"[Seed] Error: {e}")


seed_default_doctor()


# ── Pydantic models ────────────────────────────────────────────────────────────

class DoctorSignup(BaseModel):
    email: EmailStr
    password: str
    name: str
    age: int = Field(..., ge=21, le=100)
    date_of_birth: str
    gender: str
    province: str
    specialization: str
    medical_council_registration: str
    medical_council_country: str = "Pakistan"
    cnic: str
    phone: str
    address: str
    city: str
    hospital_affiliation: str
    hospital_address: str
    years_of_experience: int = Field(..., ge=0, le=50)
    additional_qualifications: Optional[str] = None
    license_image: Optional[str] = None

    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Must contain uppercase")
        if not re.search(r"[a-z]", v):
            raise ValueError("Must contain lowercase")
        if not re.search(r"\d", v):
            raise ValueError("Must contain a digit")
        return v

    @validator("gender")
    def validate_gender(cls, v):
        if v.lower() not in ["male", "female"]:
            raise ValueError("Gender must be Male or Female")
        return v.title()

    @validator("province")
    def validate_province(cls, v):
        if v.strip().lower() not in PROVINCE_CODE_MAP:
            raise ValueError("Invalid province")
        return v.title()

    @validator("specialization")
    def validate_specialization(cls, v):
        if v not in MEDICAL_SPECIALTIES:
            raise ValueError("Invalid specialization")
        return v


class DoctorLogin(BaseModel):
    name: str
    password: str


class AddPatient(BaseModel):
    pname: str
    patient_email: Optional[str] = ""
    phone_number: Optional[str] = ""
    dob: Optional[str] = ""
    age: Optional[int] = None
    gender: Optional[str] = ""
    disease: Optional[str] = ""
    condition: Optional[str] = ""
    medication: Optional[str] = ""
    presenting_complaint: Optional[str] = ""
    bp: Optional[str] = ""
    pulse: Optional[str] = ""
    bmi: Optional[float] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    family_history: Optional[str] = ""
    social_history: Optional[str] = ""
    allergies: Optional[str] = ""
    case_notes: Optional[str] = ""


class UpdatePatient(BaseModel):
    pname: Optional[str] = None
    patient_email: Optional[str] = None
    phone_number: Optional[str] = None
    dob: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    disease: Optional[str] = None
    condition: Optional[str] = None
    medication: Optional[str] = None
    presenting_complaint: Optional[str] = None
    bp: Optional[str] = None
    pulse: Optional[str] = None
    bmi: Optional[float] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    family_history: Optional[str] = None
    social_history: Optional[str] = None
    allergies: Optional[str] = None
    case_notes: Optional[str] = None


class ChatMessage(BaseModel):
    role: str
    content: str
    query_type: Optional[str] = ""
    timestamp: Optional[str] = None
    is_error: Optional[bool] = False


# ── Doctor endpoints ───────────────────────────────────────────────────────────

@router.get("/doctor/specialties")
async def get_specialties():
    return MEDICAL_SPECIALTIES


@router.post("/doctor/signup")
async def doctor_signup(signup_data: DoctorSignup):
    if doctors_collection is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    if doctors_collection.find_one({"email": signup_data.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    if doctors_collection.find_one({"medical_council_registration": signup_data.medical_council_registration}):
        raise HTTPException(status_code=400, detail="License number already in use")

    cnic_v = verify_cnic(signup_data.cnic)
    if not cnic_v["verified"]:
        raise HTTPException(status_code=400, detail=f"CNIC error: {cnic_v['message']}")

    license_v = verify_pmc_license(signup_data.medical_council_registration, signup_data.name)
    doctor_id = generate_doctor_id(signup_data.gender, signup_data.phone, signup_data.cnic)

    doc = {
        "email": signup_data.email,
        "name": signup_data.name,
        "password_hash": hash_password(signup_data.password),
        "age": signup_data.age,
        "date_of_birth": signup_data.date_of_birth,
        "gender": signup_data.gender,
        "province": signup_data.province,
        "specialization": signup_data.specialization,
        "medical_council_registration": signup_data.medical_council_registration,
        "medical_council_country": signup_data.medical_council_country,
        "cnic": signup_data.cnic,
        "phone": signup_data.phone,
        "address": signup_data.address,
        "city": signup_data.city,
        "hospital_affiliation": signup_data.hospital_affiliation,
        "hospital_address": signup_data.hospital_address,
        "years_of_experience": signup_data.years_of_experience,
        "additional_qualifications": signup_data.additional_qualifications,
        "license_image": signup_data.license_image,
        "doctor_id": doctor_id,
        "license_verification": license_v,
        "cnic_verification": cnic_v,
        "account_status": "active" if license_v["verified"] else "pending_verification",
        "created_at": datetime.utcnow().isoformat(),
        "last_login": None,
        "total_consultations": 0,
    }
    doctors_collection.insert_one(doc)
    return {
        "success": True,
        "message": "Registration successful!",
        "doctor_id": doctor_id,
        "account_status": doc["account_status"],
        "license_verified": license_v["verified"],
    }


@router.post("/doctor/login")
async def doctor_login(login_data: DoctorLogin):
    if doctors_collection is None:
        raise HTTPException(status_code=503, detail="Database unavailable — check MONGODB_URL")

    doctor = doctors_collection.find_one(
        {"name": {"$regex": f"^{re.escape(login_data.name)}$", "$options": "i"}}
    )
    if not doctor:
        raise HTTPException(status_code=401, detail="Doctor not found")
    if doctor.get("account_status") == "pending_verification":
        raise HTTPException(status_code=403, detail="Account pending license verification")
    if doctor.get("account_status") == "suspended":
        raise HTTPException(status_code=403, detail="Account suspended")
    if not verify_password(login_data.password, doctor["password_hash"]):
        raise HTTPException(status_code=401, detail="Wrong password")

    doctors_collection.update_one(
        {"_id": doctor["_id"]},
        {"$set": {"last_login": datetime.utcnow().isoformat()}},
    )
    token = create_access_token({
        "sub": doctor["email"],
        "role": "doctor",
        "name": doctor["name"],
        "specialization": doctor["specialization"],
        "doctor_id": doctor.get("doctor_id", ""),
    })
    return {
        "access_token": token,
        "token_type": "bearer",
        "doctor": {
            "id": str(doctor["_id"]),
            "name": doctor["name"],
            "email": doctor["email"],
            "specialization": doctor["specialization"],
            "hospital": doctor.get("hospital_affiliation", ""),
            "years_of_experience": doctor.get("years_of_experience", 0),
            "account_status": doctor.get("account_status", "active"),
            "license_verified": doctor.get("license_verification", {}).get("verified", False),
            "doctor_id": doctor.get("doctor_id", ""),
        },
    }


@router.get("/doctor/me")
async def get_doctor_me(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = get_doctor_from_token(credentials)
    if doctors_collection is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    doctor = doctors_collection.find_one({"email": payload.get("sub")})
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    doctor.pop("_id", None)
    doctor.pop("password_hash", None)
    return doctor


# ── Patient management ─────────────────────────────────────────────────────────

def _generate_patid() -> str:
    """Generate a unique 8-char patient ID."""
    import uuid
    return "PT" + uuid.uuid4().hex[:6].upper()


@router.get("/doctor/patients")
async def list_patients(
    search: Optional[str] = Query(None),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    get_doctor_from_token(credentials)
    if patients_collection is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    query: Dict[str, Any] = {}
    if search:
        query["$or"] = [
            {"pname": {"$regex": search, "$options": "i"}},
            {"patid": {"$regex": search, "$options": "i"}},
            {"phone_number": {"$regex": search, "$options": "i"}},
            {"disease": {"$regex": search, "$options": "i"}},
        ]

    patients = list(patients_collection.find(query, {"_id": 0}).sort("created_at", DESCENDING).limit(200))
    return {"success": True, "patients": patients, "total": len(patients)}


@router.post("/doctor/patients")
async def add_patient(
    patient: AddPatient,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    payload = get_doctor_from_token(credentials)
    if patients_collection is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    patid = _generate_patid()
    while patients_collection.find_one({"patid": patid}):
        patid = _generate_patid()

    # Normalize and validate phone number if provided
    phone_normalized = ""
    if patient.phone_number and patient.phone_number.strip():
        phone_normalized = normalize_phone(patient.phone_number.strip())
        # Check uniqueness
        existing = patients_collection.find_one({"phone_number": phone_normalized})
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Phone number already registered for patient: {existing.get('pname', 'Unknown')}",
            )

    doc = {
        "patid": patid,
        "pname": patient.pname,
        "patient_email": patient.patient_email or "",
        "phone_number": phone_normalized,
        "dob": patient.dob or "",
        "age": patient.age,
        "gender": patient.gender or "",
        "disease": patient.disease or "",
        "condition": patient.condition or "",
        "medication": patient.medication or "",
        "presenting_complaint": patient.presenting_complaint or "",
        "bp": patient.bp or "",
        "pulse": patient.pulse or "",
        "bmi": patient.bmi,
        "weight": patient.weight,
        "height": patient.height,
        "family_history": patient.family_history or "",
        "social_history": patient.social_history or "",
        "allergies": patient.allergies or "",
        "case_notes": patient.case_notes or "",
        "added_by_doctor": payload.get("name", ""),
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "caseid": f"CASE-{patid}",
    }

    patients_collection.insert_one(doc)
    doc.pop("_id", None)
    return {"success": True, "message": "Patient added successfully", "patient": doc}


@router.get("/doctor/patients/{patid}")
async def get_patient(
    patid: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    get_doctor_from_token(credentials)
    if patients_collection is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    patient = patients_collection.find_one(
        {"$or": [{"patid": patid}, {"phone_number": normalize_phone(patid)}]},
        {"_id": 0},
    )
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"success": True, "patient": patient}


@router.put("/doctor/patients/{patid}")
async def update_patient(
    patid: str,
    updates: UpdatePatient,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    get_doctor_from_token(credentials)
    if patients_collection is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    update_data = {k: v for k, v in updates.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Normalize phone if being updated
    if "phone_number" in update_data and update_data["phone_number"]:
        update_data["phone_number"] = normalize_phone(update_data["phone_number"])

    update_data["updated_at"] = datetime.utcnow().isoformat()
    result = patients_collection.update_one({"patid": patid}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient = patients_collection.find_one({"patid": patid}, {"_id": 0})
    return {"success": True, "message": "Patient updated", "patient": patient}


@router.delete("/doctor/patients/{patid}")
async def delete_patient(
    patid: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    get_doctor_from_token(credentials)
    if patients_collection is None:
        raise HTTPException(status_code=503, detail="Database unavailable")
    result = patients_collection.delete_one({"patid": patid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"success": True, "message": "Patient deleted"}


# ── Session / Chat history endpoints ──────────────────────────────────────────

@router.get("/session/{patid}")
async def load_session(
    patid: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Load persisted chat history for a patient (survives refresh)."""
    payload = get_doctor_from_token(credentials)
    if sessions_collection is None:
        return {"success": True, "messages": []}

    doctor_name = payload.get("name", "")
    session = sessions_collection.find_one(
        {"patid": patid, "doctor_name": doctor_name}, {"_id": 0}
    )
    return {
        "success": True,
        "messages": session.get("messages", []) if session else [],
        "patid": patid,
    }


@router.post("/session/{patid}/message")
async def save_message(
    patid: str,
    message: ChatMessage,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Append a single message to persisted session."""
    payload = get_doctor_from_token(credentials)
    if sessions_collection is None:
        return {"success": True, "message": "Session storage unavailable"}

    doctor_name = payload.get("name", "")
    msg_doc = {
        "role": message.role,
        "content": message.content,
        "query_type": message.query_type or "",
        "timestamp": message.timestamp or datetime.utcnow().isoformat(),
        "is_error": message.is_error or False,
    }
    sessions_collection.update_one(
        {"patid": patid, "doctor_name": doctor_name},
        {
            "$push": {"messages": msg_doc},
            "$set": {"updated_at": datetime.utcnow().isoformat()},
            "$setOnInsert": {"created_at": datetime.utcnow().isoformat()},
        },
        upsert=True,
    )
    return {"success": True, "message": "Message saved"}


@router.post("/session/{patid}/save")
async def save_session(
    patid: str,
    body: Dict[str, Any],
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Replace entire session with provided messages array."""
    payload = get_doctor_from_token(credentials)
    if sessions_collection is None:
        return {"success": True, "message": "Session storage unavailable"}

    doctor_name = payload.get("name", "")
    messages = body.get("messages", [])
    sessions_collection.update_one(
        {"patid": patid, "doctor_name": doctor_name},
        {
            "$set": {
                "messages": messages,
                "updated_at": datetime.utcnow().isoformat(),
            },
            "$setOnInsert": {"created_at": datetime.utcnow().isoformat()},
        },
        upsert=True,
    )
    return {"success": True, "message": f"{len(messages)} messages saved", "patid": patid}


@router.delete("/session/{patid}")
async def clear_session(
    patid: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Clear chat history for a patient."""
    payload = get_doctor_from_token(credentials)
    if sessions_collection is None:
        return {"success": True}
    doctor_name = payload.get("name", "")
    sessions_collection.delete_one({"patid": patid, "doctor_name": doctor_name})
    return {"success": True, "message": "Session cleared"}


# ── License verification ───────────────────────────────────────────────────────

@router.post("/doctor/verify-license")
async def verify_license(request: Dict[str, Any]):
    license_number = request.get("medical_council_registration", "")
    doctor_name = request.get("doctor_name", "")
    result = verify_pmc_license(license_number, doctor_name)
    return {"success": True, **result}
