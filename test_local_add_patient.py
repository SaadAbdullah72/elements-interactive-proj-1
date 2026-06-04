import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

# Mock pymongo before importing doctor_auth and main
mock_client = MagicMock()
mock_db = MagicMock()
mock_patients_col = MagicMock()

# Setup mock database actions
inserted_docs = []

def mock_insert_one(doc):
    inserted_docs.append(doc)
    # Mock inserted_id
    mock_result = MagicMock()
    mock_result.inserted_id = "mock_id_123"
    return mock_result

mock_patients_col.insert_one = mock_insert_one
mock_patients_col.find_one.return_value = None  # No duplicates

# Wire up the mock client hierarchy
mock_client.__getitem__.return_value = mock_db
mock_db.__getitem__.side_effect = lambda name: mock_patients_col if name == "patients" else MagicMock()

# Patch MongoClient in the modules
with patch('pymongo.MongoClient', return_value=mock_client):
    from doctor_auth import router as doctor_router
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(doctor_router)

# Run the test
client = TestClient(app)

payload = {
    "pname": "Local Test Patient",
    "patient_email": "localtest@example.com",
    "phone_number": "03001234567",
    "dob": "1990",
    "age": 36,
    "gender": "Male",
    "disease": "Diabetes",
    "medication": "Metformin"
}

print("1. Sending patient add request via local TestClient...")
response = client.post("/api/doctor/patient/add", json=payload)
print("Response Status Code:", response.status_code)
print("Response JSON:", response.json())

print("\n2. Checking if phone_number was saved in the mock database...")
if len(inserted_docs) > 0:
    saved_doc = inserted_docs[0]
    print("Saved Document in Database:")
    for k, v in saved_doc.items():
        print(f"  {k}: {v}")
    
    # Assert check
    if saved_doc.get("phone_number") == "03001234567":
        print("\n[OK] SUCCESS: The phone number was saved correctly in the database document!")
    else:
        print("\n[FAIL] FAILURE: Phone number was NOT saved correctly.")
else:
    print("\n[FAIL] FAILURE: No document was inserted.")
