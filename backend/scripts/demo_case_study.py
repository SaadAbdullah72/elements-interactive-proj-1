"""
Demo Case Study - Live API Call to IntelliHealth AI Clinical System
"""
import requests
import json

API_URL = "http://localhost:8000"

# Demo Patient Data (from database)
# Using query types that match the backend: "Explain", "Diagnosis", "Treatment", "Side Effects"
patient_data = {
    "caseid": "CASE-2024-00025",
    "patid": "PAT-000025",
    "pname": "Ahmed Mansour",
    "dob": "2003-03-18",
    "age": 38,
    "gender": "Female",
    "disease": "Hypertension",
    "medication": "Lisinopril",
    "bp": "150/95",
    "pulse": "88",
    "bmi": 28.5,
    "presenting_complaint": "Headache and dizziness",
    "family_history": "Father had stroke at 60",
    "social_history": "Non-smoker",
    "allergies": "None",
    "query_type": "Diagnosis",  # Must match backend: Explain, Diagnosis, Treatment, Side Effects
    "custom_query": ""
}

print("=" * 80)
print("🏥 INTELLIHEALTH AI CLINICAL SYSTEM - DEMO CASE STUDY")
print("=" * 80)

print("\n📋 PATIENT INPUT DATA:")
print("-" * 50)
for key, value in patient_data.items():
    if value:
        print(f"  {key.replace('_', ' ').title()}: {value}")

print("\n\n🔄 Sending request to AI...")
print("-" * 50)

try:
    response = requests.post(
        f"{API_URL}/clinical-query",
        json=patient_data,
        timeout=120
    )
    
    if response.status_code == 200:
        result = response.json()
        
        print("\n\n✅ AI RESPONSE RECEIVED!")
        print("=" * 80)
        print("\n📝 RAW API RESPONSE:")
        print("-" * 80)
        print(json.dumps(result, indent=2))
        
        print("\n\n📝 AI CLINICAL ANALYSIS OUTPUT:")
        print("-" * 80)
        
        # Print the response nicely
        ai_response = result.get('content', result.get('response', 'No response'))
        print(ai_response)
        
        print("\n" + "=" * 80)
        print("📊 METADATA:")
        print("-" * 80)
        print(f"  Status Code: {response.status_code}")
        print(f"  Response Time: {response.elapsed.total_seconds():.2f} seconds")
        
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(f"  Response: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("\n❌ Connection Error: Could not connect to the backend server.")
    print("   Make sure main.py is running on http://localhost:8000")
except requests.exceptions.Timeout:
    print("\n⏱️ Timeout: The AI took too long to respond.")
except Exception as e:
    print(f"\n❌ Error: {str(e)}")

print("\n" + "=" * 80)
