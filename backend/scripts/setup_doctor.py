from pymongo import MongoClient
from datetime import datetime
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

mongodburl = os.getenv('MONGODB_URL', os.getenv('LOCAL_MONGODB_URL', 'mongodb://localhost:27017/'))
db_name = os.getenv('MONGODB_DBFULL_DB', 'dbfull')
client = MongoClient(mongodburl)
db = client[db_name]
doctors = db.doctors

# Remove existing
doctors.delete_one({"name": "aliejaz"})

# Create doctor
doctor = {
    "name": "aliejaz",
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

result = doctors.insert_one(doctor)
print(f"Doctor created! ID: {result.inserted_id}")
print(f"Name: aliejaz")
print(f"Password: 1122334455")
