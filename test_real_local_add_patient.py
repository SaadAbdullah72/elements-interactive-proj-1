import requests
import random
from pymongo import MongoClient

# 1. Add patient via local API on port 8080
url_add = "http://localhost:8080/api/doctor/patient/add"
phone = f"0300{random.randint(1000000, 9999999)}"
payload = {
    "pname": "Local Real Database Test",
    "patient_email": "realtest@example.com",
    "phone_number": phone,
    "dob": "1990",
    "age": 36,
    "gender": "Male",
    "disease": "Diabetes",
    "medication": "Metformin",
    "presenting_complaint": "Fatigue"
}

print(f"1. Sending request to local backend: {url_add}")
print("Payload:", payload)

try:
    response = requests.post(url_add, json=payload, timeout=10)
    print("Status Code:", response.status_code)
    resp_data = response.json()
    print("Response JSON:", resp_data)
    
    if response.status_code == 200 and resp_data.get("success"):
        patid = resp_data["patient"]["patid"]
        print(f"\n[OK] Patient added successfully! Generated Patient ID: {patid}")
        
        # 2. Directly verify from MongoDB Atlas using the connection string
        print("\n2. Connecting directly to MongoDB Atlas to check the database document...")
        uri = "mongodb+srv://hima21517_db_user:64nGo0W9xSCUpPwb@mitdb.xrxuxql.mongodb.net/?appName=MITDBcv"
        client = MongoClient(uri)
        db = client["dbfull"]
        patient_doc = db["patients"].find_one({"patid": patid})
        
        if patient_doc:
            print("Found Patient Document in MongoDB Atlas:")
            for k, v in patient_doc.items():
                print(f"  {k}: {v}")
            
            # Verify the phone_number field is saved in Atlas database
            if "phone_number" in patient_doc and patient_doc["phone_number"] == phone:
                print(f"\n[OK] SUCCESS: 'phone_number' is saved in MongoDB Atlas as '{patient_doc['phone_number']}'!")
            else:
                print("\n[FAIL] FAILURE: 'phone_number' field is missing or mismatch in database document.")
        else:
            print("\n[FAIL] FAILURE: Patient document not found in MongoDB Atlas.")
    else:
        print("\n❌ FAILURE: Backend failed to add patient.")
        
except Exception as e:
    print("Test failed with error:", e)
