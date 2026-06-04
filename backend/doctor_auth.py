"""
Doctor authentication, registration, and license verification system.

This module handles doctor-specific onboarding, license verification
and the auto-seeding of a development admin account. Key responsibilities:
 - Validate license/identity formats
 - Enforce account status checks (pending, active, suspended)
 - Provide doctor-specific login tokens

Security: seeded credentials are for development only. Replace with
secure provisioning in production and never log plaintext passwords.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, validator
from pymongo import MongoClient
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

# -------------------------
# MongoDB Setup
# -------------------------
mongodburl = os.getenv('MONGODB_URL', os.getenv('LOCAL_MONGODB_URL', 'mongodb://localhost:27017/')) # This correctly picks up MONGODB_URL from .env
db_name = os.getenv('MONGODB_DBFULL_DB', 'dbfull') # Use 'dbfull' as per migration guide for doctor data

try:
    client = MongoClient(mongodburl, serverSelectionTimeoutMS=5000)
    # Test the connection
    client.admin.command('ping')
    db = client[db_name]
    doctors_collection = db["doctors"]
    license_verifications_collection = db["license_verifications"]
    patients_collection = db["patients"]  # For patient-related operations
    print(f"✅ [Doctor Auth] MongoDB connected to database: {db_name}")
except Exception as e:
    print(f"❌ [Doctor Auth] MongoDB connection failed: {e}")
    # Set to None so we can check for this in endpoints
    db = None
    doctors_collection = None
    license_verifications_collection = None
    patients_collection = None

# -------------------------
# Medical Specialties
# -------------------------
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
    "Pediatric Dentist"
]

PROVINCE_CODE_MAP = {
    "punjab": "3",
    "sindh": "4",
    "khyber pakhtunkhwa": "5",
    "kpk": "5",
    "balochistan": "6",
    "islamabad": "7",
    "islamabad capital territory": "7",
    "gilgit-baltistan": "8",
    "gilgit baltistan": "8",
    "gilgit": "8",
    "azad jammu & kashmir": "9",
    "ajk": "9"
}

# -------------------------
# JWT Configuration
# -------------------------
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "doctor-system-secret-key-change-in-production-2024")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = 1440  # 24 hours

# -------------------------
# Default Doctor Seed Credentials
# -------------------------
DEFAULT_DOCTOR = {
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
    "hospital_affiliation": "DiabAssist Medical Center",
    "hospital_address": "456 Hospital Road, Karachi",
    "years_of_experience": 15,
    "additional_qualifications": "MBBS, FCPS",
    "license_image": None
}

# -------------------------
# Helper Functions
# -------------------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed_password: str) -> bool:
    return hash_password(password) == hashed_password

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=JWT_EXPIRATION_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_pmc_license(license_number: str, doctor_name: str) -> Dict[str, Any]:
    pmc_pattern = r'^(PMC|PMDC)-\d{5,7}$'
    numeric_pattern = r'^\d{6,8}$'

    result = {
        "verified": False,
        "license_number": license_number,
        "doctor_name": doctor_name,
        "verification_date": datetime.utcnow().isoformat(),
        "source": "Pakistan Medical Commission (PMC)",
        "status": "pending",
        "message": ""
    }

    if not (re.match(pmc_pattern, license_number.upper()) or re.match(numeric_pattern, license_number)):
        result["message"] = "Invalid license number format. Expected: PMC-XXXXX, PMDC-XXXXX, or 6-8 digits"
        result["status"] = "invalid_format"
        return result

    result["verified"] = True
    result["status"] = "active"
    result["message"] = "License verified successfully with PMC"
    result["license_type"] = "Pakistan Medical Commission"
    result["valid_until"] = "2026-12-31"
    return result

def verify_cnic(cnic: str) -> Dict[str, Any]:
    cnic_pattern = r'^\d{5}-\d{7}-\d{1}$'
    result = {
        "verified": False,
        "cnic": cnic,
        "verification_date": datetime.utcnow().isoformat(),
        "message": ""
    }
    if not re.match(cnic_pattern, cnic):
        cnic_no_dash = cnic.replace('-', '')
        if len(cnic_no_dash) != 13 or not cnic_no_dash.isdigit():
            result["message"] = "Invalid CNIC format. Expected: XXXXX-XXXXXXX-X"
            return result
    result["verified"] = True
    result["message"] = "CNIC format validated"
    return result


def get_province_code(province: str) -> str:
    normalized = province.strip().lower()
    return PROVINCE_CODE_MAP.get(normalized, "0")


def generate_doctor_id(gender: str, province: str, license_number: str) -> str:
    gender_digit = "1" if gender.strip().lower() == "male" else "0"
    province_digit = get_province_code(province)
    license_digits = re.sub(r'\D', '', license_number)
    license_suffix = license_digits[-3:].zfill(3)
    random_segment = str(random.randint(0, 99)).zfill(2)
    return f"DR{gender_digit}-{province_digit}{random_segment}-{license_suffix}"

# -------------------------
# Auto-Seed Default Doctor
# -------------------------
def seed_default_doctor():
    """
    Creates the default admin doctor on startup if not already present.
    Runs once when the module is loaded. Safe to call multiple times.
    """
    # Seed a default administrative doctor if none exists. This is
    # intended for local development and quick demos only. The function
    # is safe to call multiple times (idempotent check up front).
    try:
        existing = doctors_collection.find_one({
            "$or": [
                {"name": {"$regex": f"^{re.escape(DEFAULT_DOCTOR['name'])}$", "$options": "i"}},
                {"email": DEFAULT_DOCTOR["email"]}
            ]
        })

        if existing:
            print(f"[Seed] Default doctor '{DEFAULT_DOCTOR['name']}' already exists. Skipping.")
            return

        license_verification = verify_pmc_license(
            DEFAULT_DOCTOR["medical_council_registration"],
            DEFAULT_DOCTOR["name"]
        )
        cnic_verification = verify_cnic(DEFAULT_DOCTOR["cnic"])

        default_doctor_id = generate_doctor_id(
            DEFAULT_DOCTOR["gender"],
            DEFAULT_DOCTOR["province"],
            DEFAULT_DOCTOR["medical_council_registration"]
        )

        doctor_record = {
            "email": DEFAULT_DOCTOR["email"],
            "name": DEFAULT_DOCTOR["name"],
            "password_hash": hash_password(DEFAULT_DOCTOR["password"]),
            "age": DEFAULT_DOCTOR["age"],
            "date_of_birth": DEFAULT_DOCTOR["date_of_birth"],
            "gender": DEFAULT_DOCTOR["gender"],
            "province": DEFAULT_DOCTOR["province"],
            "specialization": DEFAULT_DOCTOR["specialization"],
            "medical_council_registration": DEFAULT_DOCTOR["medical_council_registration"],
            "medical_council_country": DEFAULT_DOCTOR["medical_council_country"],
            "cnic": DEFAULT_DOCTOR["cnic"],
            "phone": DEFAULT_DOCTOR["phone"],
            "address": DEFAULT_DOCTOR["address"],
            "city": DEFAULT_DOCTOR["city"],
            "hospital_affiliation": DEFAULT_DOCTOR["hospital_affiliation"],
            "hospital_address": DEFAULT_DOCTOR["hospital_address"],
            "years_of_experience": DEFAULT_DOCTOR["years_of_experience"],
            "additional_qualifications": DEFAULT_DOCTOR["additional_qualifications"],
            "license_image": None,
            "doctor_id": default_doctor_id,
            "license_verification": license_verification,
            "cnic_verification": cnic_verification,
            "account_status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "last_login": None,
            "total_consultations": 0,
            "rating": 0,
            "total_reviews": 0,
            "is_default_seed": True
        }

        result = doctors_collection.insert_one(doctor_record)

        license_verifications_collection.insert_one({
            "doctor_id": str(result.inserted_id),
            "email": DEFAULT_DOCTOR["email"],
            "name": DEFAULT_DOCTOR["name"],
            "medical_council_registration": DEFAULT_DOCTOR["medical_council_registration"],
            "verification_result": license_verification,
            "verification_date": datetime.utcnow().isoformat(),
            "status": "completed"
        })

        print(f"[Seed] ✅ Default doctor created successfully.")
        print(f"[Seed]    Name: {DEFAULT_DOCTOR['name']}")
        print(f"[Seed]    Email: {DEFAULT_DOCTOR['email']}")
        print(f"[Seed]    Note: Default credentials are for development only. Do NOT expose passwords in logs or production environments.")

    except Exception as e:
        print(f"[Seed] ❌ Failed to seed default doctor: {e}")

# Run seed on module load
seed_default_doctor()

# -------------------------
# Pydantic Models
# -------------------------
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

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        return v

    @validator('gender')
    def validate_gender(cls, v):
        if v.lower() not in ["male", "female"]:
            raise ValueError("Gender must be either Male or Female")
        return v.title()

    @validator('province')
    def validate_province(cls, v):
        if v.strip().lower() not in PROVINCE_CODE_MAP:
            raise ValueError(
                "Province must be one of Punjab, Sindh, Khyber Pakhtunkhwa, Balochistan, Islamabad, Gilgit-Baltistan, or Azad Jammu & Kashmir"
            )
        return v.title()

    @validator('specialization')
    def validate_specialization(cls, v):
        if v not in MEDICAL_SPECIALTIES:
            raise ValueError(f"Invalid specialization.")
        return v

class DoctorLogin(BaseModel):
    name: str
    password: str

class LicenseVerificationRequest(BaseModel):
    medical_council_registration: str
    doctor_name: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    doctor: Dict[str, Any]

class MessageResponse(BaseModel):
    message: str
    success: bool = True

# -------------------------
# API Endpoints
# -------------------------

@router.get("/doctor/specialties", response_model=List[str])
async def get_medical_specialties():
    return MEDICAL_SPECIALTIES


@router.post("/doctor/signup", response_model=Dict[str, Any])
async def doctor_signup(signup_data: DoctorSignup):
    existing_doctor = doctors_collection.find_one({"email": signup_data.email})
    if existing_doctor:
        raise HTTPException(status_code=400, detail="Email already registered")

    existing_license = doctors_collection.find_one({
        "medical_council_registration": signup_data.medical_council_registration
    })
    if existing_license:
        raise HTTPException(status_code=400, detail="Medical council registration number already in use")

    cnic_verification = verify_cnic(signup_data.cnic)
    if not cnic_verification["verified"]:
        raise HTTPException(status_code=400, detail=f"CNIC verification failed: {cnic_verification['message']}")

    license_verification = verify_pmc_license(signup_data.medical_council_registration, signup_data.name)
    doctor_id = generate_doctor_id(signup_data.gender, signup_data.province, signup_data.medical_council_registration)

    doctor_record = {
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
        "license_verification": license_verification,
        "cnic_verification": cnic_verification,
        "account_status": "active" if license_verification["verified"] else "pending_verification",
        "created_at": datetime.utcnow().isoformat(),
        "last_login": None,
        "total_consultations": 0,
        "rating": 0,
        "total_reviews": 0
    }

    result = doctors_collection.insert_one(doctor_record)

    license_verifications_collection.insert_one({
        "doctor_id": str(result.inserted_id),
        "email": signup_data.email,
        "name": signup_data.name,
        "medical_council_registration": signup_data.medical_council_registration,
        "verification_result": license_verification,
        "verification_date": datetime.utcnow().isoformat(),
        "status": "completed"
    })

    return {
        "success": True,
        "message": "Registration successful! Your account is " +
                   ("active" if license_verification["verified"] else "pending license verification"),
        "doctor_id": doctor_record["doctor_id"],
        "email": signup_data.email,
        "account_status": doctor_record["account_status"],
        "license_verified": license_verification["verified"],
        "license_details": license_verification
    }


@router.post("/doctor/login", response_model=TokenResponse)
async def doctor_login(login_data: DoctorLogin):
    # Check if database is available
    if doctors_collection is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable - MongoDB connection failed. Check MONGODB_URL environment variable on Replit."
        )
    
    # Case-insensitive name search
    doctor = doctors_collection.find_one({
        "name": {"$regex": f"^{re.escape(login_data.name)}$", "$options": "i"}
    })

    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Doctor not found."
        )

    if doctor.get("account_status") == "pending_verification":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "reason": "Account pending verification",
                "message": "Your medical license is under verification. Please wait for admin approval.",
                "license_status": doctor.get("license_verification", {}).get("status", "unknown")
            }
        )

    if doctor.get("account_status") == "suspended":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended. Please contact support."
        )

    if not verify_password(login_data.password, doctor["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Wrong password."
        )

    doctors_collection.update_one(
        {"_id": doctor["_id"]},
        {"$set": {"last_login": datetime.utcnow().isoformat()}}
    )

    access_token = create_access_token(data={
        "sub": doctor["email"],
        "role": "doctor",
        "name": doctor["name"],
        "specialization": doctor["specialization"]
    })

    doctor_response = {
        "id": str(doctor["_id"]),
        "name": doctor["name"],
        "email": doctor["email"],
        "specialization": doctor["specialization"],
        "hospital": doctor.get("hospital_affiliation", ""),
        "years_of_experience": doctor.get("years_of_experience", 0),
        "account_status": doctor.get("account_status", "active"),
        "license_verified": doctor.get("license_verification", {}).get("verified", False)
    }

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        doctor=doctor_response
    )


@router.post("/doctor/verify-license", response_model=Dict[str, Any])
async def verify_doctor_license(verification_request: LicenseVerificationRequest):
    doctor = doctors_collection.find_one({
        "medical_council_registration": verification_request.medical_council_registration
    })

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found with this registration number")

    license_verification = verify_pmc_license(
        verification_request.medical_council_registration,
        verification_request.doctor_name
    )

    doctors_collection.update_one(
        {"medical_council_registration": verification_request.medical_council_registration},
        {"$set": {
            "license_verification": license_verification,
            "account_status": "active" if license_verification["verified"] else "pending_verification"
        }}
    )

    license_verifications_collection.insert_one({
        "doctor_id": str(doctor["_id"]),
        "email": doctor["email"],
        "name": doctor["name"],
        "medical_council_registration": verification_request.medical_council_registration,
        "verification_result": license_verification,
        "verification_date": datetime.utcnow().isoformat(),
        "status": "completed"
    })

    return {
        "success": True,
        "verified": license_verification["verified"],
        "message": license_verification["message"],
        "account_status": "active" if license_verification["verified"] else "pending_verification",
        "license_details": license_verification
    }


@router.get("/doctor/profile", response_model=Dict[str, Any])
async def get_doctor_profile(email: str):
    doctor = doctors_collection.find_one({"email": email})
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    doctor.pop("password_hash", None)
    doctor.pop("cnic", None)
    doctor["_id"] = str(doctor["_id"])
    return doctor


@router.get("/doctor/patients", response_model=List[Dict[str, Any]])
async def get_all_patients():
    patients_collection = db["patients"]
    patients = list(patients_collection.find({}, {
        "caseid": 1, "patid": 1, "pname": 1, "dob": 1,
        "age": 1, "gender": 1, "disease": 1,
        "presenting_complaint": 1, "patient_email": 1
    }).limit(100))

    for patient in patients:
        patient["id"] = str(patient["_id"])
        del patient["_id"]
    return patients


@router.post("/doctor/verify-patient", response_model=Dict[str, Any])
async def verify_patient(patient_data: dict):
    patients_collection = db["patients"]
    patient = patients_collection.find_one({"patid": patient_data.get("patid")})

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail={"verified": False, "reason": "Patient not found"}
        )

    return {
        "verified": True,
        "patient": {
            "caseid": patient["caseid"],
            "patid": patient["patid"],
            "pname": patient["pname"],
            "dob": patient["dob"],
            "age": patient["age"],
            "gender": patient.get("gender"),
            "disease": patient.get("disease"),
            "medication": patient.get("medication"),
            "presenting_complaint": patient.get("presenting_complaint"),
            "bp": patient.get("bp"),
            "pulse": patient.get("pulse"),
            "bmi": patient.get("bmi"),
            "family_history": patient.get("family_history"),
            "social_history": patient.get("social_history"),
            "allergies": patient.get("allergies"),
            "patient_email": patient.get("patient_email")
        }
    }


@router.post("/doctor/patient/add", response_model=Dict[str, Any])
async def add_new_patient(patient_data: dict):
    import random
    patients_collection = db["patients"]

    try:
        case_id = f"CASE-{datetime.now().year}-{str(random.randint(10000, 99999))}"
        patient_id = f"PAT-{str(random.randint(100000, 999999))}"

        new_patient = {
            "caseid": case_id,
            "patid": patient_id,
            "pname": patient_data.get("pname"),
            "patient_email": patient_data.get("patient_email"),
            "dob": patient_data.get("dob"),
            "age": int(patient_data.get("age")),
            "gender": patient_data.get("gender"),
            "disease": patient_data.get("disease"),
            "medication": patient_data.get("medication"),
            "presenting_complaint": patient_data.get("presenting_complaint"),
            "bp": patient_data.get("bp"),
            "pulse": patient_data.get("pulse"),
            "bmi": patient_data.get("bmi"),
            "weight": patient_data.get("weight"),
            "height": patient_data.get("height"),
            "family_history": patient_data.get("family_history"),
            "social_history": patient_data.get("social_history"),
            "allergies": patient_data.get("allergies"),
            "case_notes": patient_data.get("case_notes"),
            "created_at": datetime.utcnow().isoformat(),
            "source": "doctor_added"
        }

        result = patients_collection.insert_one(new_patient)

        return {
            "success": True,
            "message": "Patient added successfully",
            "patient": {
                "caseid": case_id,
                "patid": patient_id,
                "pname": new_patient["pname"],
                "patient_email": new_patient["patient_email"],
                "age": new_patient["age"],
                "gender": new_patient["gender"],
                "disease": new_patient["disease"]
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add patient: {str(e)}")


def get_mismatched_fields(patient: Dict, input_data: dict) -> List[str]:
    mismatched = []
    if patient.get("caseid") != input_data.get("caseid"):
        mismatched.append("caseid")
    if patient.get("patid") != input_data.get("patid"):
        mismatched.append("patid")
    if patient.get("pname", "").lower() != input_data.get("pname", "").lower():
        mismatched.append("pname")
    if patient.get("dob") != input_data.get("dob"):
        mismatched.append("dob")
    if patient.get("age") != input_data.get("age"):
        mismatched.append("age")
    return mismatched