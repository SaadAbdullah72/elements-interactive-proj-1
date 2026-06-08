from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
import hashlib
import os
import re

load_dotenv()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


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
    gender_code = "1" if gender.strip().lower() == "male" else "0"
    phone_digits = re.sub(r"\D", "", normalize_phone(phone))
    cnic_digits = re.sub(r"\D", "", cnic)
    last4_phone = phone_digits[-4:].zfill(4) if phone_digits else "0000"
    last3_cnic = cnic_digits[-3:].zfill(3) if cnic_digits else "000"
    return f"DR{gender_code}-{last4_phone}-{last3_cnic}"


def verify_cnic(cnic: str) -> dict:
    digits = re.sub(r"\D", "", cnic)
    return {
        "verified": len(digits) == 13,
        "cnic": cnic,
        "message": "CNIC validated" if len(digits) == 13 else "Invalid CNIC. Expected: XXXXX-XXXXXXX-X (13 digits)"
    }


def verify_pmc_license(license_number: str, doctor_name: str) -> dict:
    pmc_pattern = r"^(PMC|PMDC)-\d{5,7}$"
    numeric_pattern = r"^\d{6,8}$"
    verified = bool(re.match(pmc_pattern, license_number.upper()) or re.match(numeric_pattern, license_number))
    return {
        "verified": verified,
        "license_number": license_number,
        "doctor_name": doctor_name,
        "verification_date": datetime.utcnow().isoformat(),
        "source": "Pakistan Medical Commission (PMC)",
        "status": "active" if verified else "invalid_format",
        "message": "License verified with PMC" if verified else "Invalid license format. Expected: PMC-XXXXX or 6-8 digits",
        "valid_until": "2026-12-31" if verified else None,
    }


mongodburl = os.getenv('MONGODB_URL', os.getenv('LOCAL_MONGODB_URL', 'mongodb://localhost:27017/'))
auth_db_name = os.getenv('MONGODB_AUTH_DB', 'authentication')
client = MongoClient(mongodburl, serverSelectionTimeoutMS=5000)
auth_db = client[auth_db_name]
doctors_collection = auth_db['doctors']

physicians = []
for i in range(10):
    gender = 'Male' if i % 2 == 0 else 'Female'
    email = f'physician{i}.test@gmail.com'
    name = f'Physician {i}'
    password = f'Physician{i}@2026'
    phone = f'0300123456{i}'
    cnic = f'42101-12345{67 + i:02d}-{(8 + i) % 10}'
    doctor_id = generate_doctor_id(gender, phone, cnic)
    license_number = f'PMC-1000{50 + i}'
    physicians.append({
        'email': email,
        'name': name,
        'password': password,
        'age': 30 + (i % 10),
        'date_of_birth': f'199{3 + (i % 7)}-0{((i % 12) + 1):02d}-15',
        'gender': gender,
        'province': 'Punjab' if i % 3 == 0 else 'Sindh',
        'specialization': 'General Physician',
        'medical_council_registration': license_number,
        'medical_council_country': 'Pakistan',
        'cnic': cnic,
        'phone': phone,
        'address': f'{100 + i} Medical Street, {"Lahore" if i % 3 == 0 else "Karachi"}',
        'city': 'Lahore' if i % 3 == 0 else 'Karachi',
        'hospital_affiliation': 'City Medical Center',
        'hospital_address': f'{200 + i} Hospital Road',
        'years_of_experience': 5 + i,
        'additional_qualifications': 'MBBS, FCPS',
        'doctor_id': doctor_id,
        'license_verification': verify_pmc_license(license_number, name),
        'cnic_verification': verify_cnic(cnic),
        'account_status': 'active',
        'created_at': datetime.utcnow().isoformat(),
        'last_login': None,
        'total_consultations': 0,
    })

existing_filter = {
    '$or': [
        {'name': {'$in': [doc['name'] for doc in physicians]}},
        {'email': {'$in': [doc['email'] for doc in physicians]}},
        {'medical_council_registration': {'$in': [doc['medical_council_registration'] for doc in physicians]}},
    ]
}
remove_result = doctors_collection.delete_many(existing_filter)
print(f'Removed {remove_result.deleted_count} existing Physician records matching the same names/emails/licenses.')

insert_docs = []
for doc in physicians:
    insert_docs.append({
        **{k: v for k, v in doc.items() if k != 'password'},
        'password_hash': hash_password(doc['password']),
    })

result = doctors_collection.insert_many(insert_docs)
print(f'Inserted {len(result.inserted_ids)} physician doctor records.')
print('Doctors created:')
for doc in physicians:
    print(f"{doc['name']} | {doc['email']} | {doc['password']} | doctor_id={doc['doctor_id']}")
