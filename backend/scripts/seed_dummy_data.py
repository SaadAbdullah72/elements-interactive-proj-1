"""
Script to seed MongoDB with dummy doctor account and 50 patient records.
Run this script once to populate the database.
"""

from pymongo import MongoClient
from datetime import datetime, timedelta
import random
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to MongoDB
mongodburl = os.getenv('MONGODB_URL', os.getenv('LOCAL_MONGODB_URL', 'mongodb://localhost:27017/'))
db_name = os.getenv('MONGODB_DBFULL_DB', 'dbfull')
client = MongoClient(mongodburl)
db = client[db_name]  # Use the database name you specified

# -------------------------
# Helper Functions
# -------------------------
def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

# -------------------------
# Create Dummy Doctor Account
# -------------------------
print("Creating dummy doctor account...")

doctors_collection = db["doctors"]

# Clear existing dummy doctor if exists
doctors_collection.delete_one({"email": "aliejaz@hospital.com"})

doctor_document = {
    "name": "Dr. Aliejaz",
    "email": "aliejaz@hospital.com",
    "password_hash": hash_password("1122334455"),
    "specialization": "General Medicine",
    "license_number": "MD123456",
    "hospital": "City Hospital",
    "email_verified": True,
    "role": "doctor",
    "created_at": datetime.utcnow().isoformat(),
    "managed_patients": []
}

result = doctors_collection.insert_one(doctor_document)
print(f"✅ Doctor account created with ID: {result.inserted_id}")

# -------------------------
# Create 50 Dummy Patient Records
# -------------------------
print("\nCreating 50 dummy patient records...")

patients_collection = db["patients"]

# Clear existing dummy patients
patients_collection.delete_many({"source": "dummy_seed"})

# Sample data for generating realistic patient records
first_names = [
    "Mohammed", "Ahmed", "Fatima", "Sarah", "Ali", "Hassan", "Maryam", "Noor",
    "Omar", "Khalid", "Aisha", "Zainab", "Ibrahim", "Yusuf", "Layla", "Samira",
    "Abdullah", "Mariam", "Hamza", "Imran", "Sana", "Tariq", "Nadia", "Bilal",
    "Rania", "Faisal", "Huda", "Kareem", "Mona", "Rashid", "Salma", "Waleed",
    "Amira", "Jameel", "Lina", "Mahmoud", "Noura", "Osman", "Reem", "Sami",
    "Yasmin", "Zuhair", "Aziz", "Badra", "Farid", "Galila", "Habib", "Jalila"
]

last_names = [
    "Ahmed", "Ali", "Hassan", "Hussein", "Ibrahim", "Khalil", "Mahmoud", "Mansour",
    "Nasser", "Omar", "Rashid", "Salem", "Tariq", "Youssef", "Zaid", "Badawi",
    "Chamoun", "Darwish", "Elmasri", "Farouk", "Ghanem", "Hamdan", "Jaber", "Kanaan",
    "Masri", "Najjar", "Osman", "Qasim", "Ramadan", "Said", "Tabba", "Wakeel"
]

diseases = [
    "Type 2 Diabetes Mellitus", "Hypertension", "Asthma", "COPD", "Coronary Artery Disease",
    "Heart Failure", "Atrial Fibrillation", "Hyperlipidemia", "Hypothyroidism", "GERD",
    "Osteoarthritis", "Rheumatoid Arthritis", "Depression", "Anxiety Disorder", "Migraine",
    "Epilepsy", "Parkinson's Disease", "Multiple Sclerosis", "Stroke", "Dementia",
    "Chronic Kidney Disease", "Liver Cirrhosis", "Peptic Ulcer Disease", "IBS",
    "Anemia", "Thrombocytopenia", "Leukemia", "Lymphoma", "Breast Cancer", "Lung Cancer",
    "Prostate Cancer", "Colorectal Cancer", "Melanoma", "Thyroid Cancer", "Ovarian Cancer"
]

medications = [
    "Metformin 500mg", "Metformin 1000mg", "Glimepiride 2mg", "Gliclazide 80mg",
    "Insulin Glargine", "Insulin Aspart", "Amlodipine 5mg", "Amlodipine 10mg",
    "Lisinopril 10mg", "Lisinopril 20mg", "Losartan 50mg", "Valsartan 80mg",
    "Atorvastatin 20mg", "Atorvastatin 40mg", "Simvastatin 20mg", "Rosuvastatin 10mg",
    "Aspirin 75mg", "Aspirin 150mg", "Clopidogrel 75mg", "Warfarin 5mg",
    "Levothyroxine 50mcg", "Levothyroxine 100mcg", "Omeprazole 20mg", "Pantoprazole 40mg",
    "Salbutamol Inhaler", "Budesonide Inhaler", "Tiotropium Inhaler", "Montelukast 10mg",
    "Paracetamol 500mg", "Ibuprofen 400mg", "Diclofenac 50mg", "Tramadol 50mg",
    "Sertraline 50mg", "Fluoxetine 20mg", "Alprazolam 0.5mg", "Lorazepam 1mg",
    "Gabapentin 300mg", "Pregabalin 75mg", "Carbamazepine 200mg", "Valproate 500mg"
]

presenting_complaints = [
    "Fatigue and weakness", "Chest pain", "Shortness of breath", "Dizziness",
    "Headache", "Abdominal pain", "Nausea and vomiting", "Joint pain",
    "Back pain", "Cough", "Fever", "Weight loss", "Weight gain", "Swelling of legs",
    "Palpitations", "Syncope", "Confusion", "Memory loss", "Tremors", "Seizures",
    "Numbness in extremities", "Blurred vision", "Hearing loss", "Skin rash",
    "Difficulty sleeping", "Loss of appetite", "Constipation", "Diarrhea",
    "Frequent urination", "Excessive thirst"
]

def generate_random_date(min_age, max_age):
    """Generate random date of birth based on age range"""
    today = datetime.now()
    age = random.randint(min_age, max_age)
    days_offset = random.randint(0, 365)
    dob = today - timedelta(days=(age * 365 + days_offset))
    return dob

def generate_case_id(index):
    """Generate unique case ID"""
    return f"CASE-{2024}-{str(index).zfill(5)}"

def generate_patient_id(index):
    """Generate unique patient ID"""
    return f"PAT-{str(index).zfill(6)}"

# Generate 50 patient records
patients = []
for i in range(1, 51):
    first_name = random.choice(first_names)
    last_name = random.choice(last_names)
    patient_name = f"{first_name} {last_name}"
    
    # Generate DOB and age consistently
    age = random.randint(18, 85)
    dob = generate_random_date(18, 85)
    
    patient_document = {
        "caseid": generate_case_id(i),
        "patid": generate_patient_id(i),
        "pname": patient_name,
        "dob": dob.strftime("%Y-%m-%d"),
        "age": age,
        "gender": random.choice(["Male", "Female"]),
        "disease": random.choice(diseases),
        "medication": random.choice(medications),
        "presenting_complaint": random.choice(presenting_complaints),
        "bp": f"{random.randint(110, 160)}/{random.randint(70, 100)} mmHg",
        "pulse": f"{random.randint(60, 100)}/min",
        "bmi": round(random.uniform(18, 40), 1),
        "patient_email": f"{first_name.lower()}.{last_name.lower()}@example.com",
        "doctor_email": "aliejaz@hospital.com",
        "source": "dummy_seed",
        "created_at": datetime.utcnow().isoformat(),
        "case_notes": f"Patient {patient_name} presents for routine follow-up and medication management.",
        "family_history": random.choice([
            "Father had Type 2 Diabetes",
            "Mother had Hypertension",
            "Family history of heart disease",
            "No significant family history",
            "Sibling with asthma"
        ]),
        "social_history": random.choice([
            "Non-smoker, sedentary lifestyle",
            "Former smoker, moderate activity",
            "Current smoker, sedentary lifestyle",
            "Non-smoker, active lifestyle",
            "Occasional alcohol use"
        ]),
        "allergies": random.choice([
            "No known allergies",
            "Penicillin allergy",
            "Sulfa drug allergy",
            "Aspirin sensitivity",
            "Latex allergy"
        ])
    }
    patients.append(patient_document)

# Insert all patients
result = patients_collection.insert_many(patients)
print(f"✅ {len(result.inserted_ids)} patient records created")

# Update doctor's managed_patients list
doctors_collection.update_one(
    {"email": "aliejaz@hospital.com"},
    {"$set": {"managed_patients": [p["patid"] for p in patients]}}
)

print("\n✅ Seeding completed successfully!")
print("\nDoctor Login Credentials:")
print("  Email: aliejaz@hospital.com")
print("  Password: 1122334455")
print(f"\nDatabase: dbfull")
print(f"Collections created: doctors, patients")
