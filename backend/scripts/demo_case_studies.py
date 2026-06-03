"""
Complete Demo Case Studies - IntelliHealth AI Clinical System
Shows real AI responses for different clinical scenarios
"""
import requests
import json
from datetime import datetime

API_URL = "http://localhost:8000"

# ============================================================================
# CASE STUDY 1: Diagnosis Query - Hypertension Patient
# ============================================================================
case1 = {
    "title": "CASE STUDY 1: Hypertension - Diagnostic Analysis",
    "patient": {
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
        "query_type": "Diagnosis",
        "custom_query": ""
    }
}

# ============================================================================
# CASE STUDY 2: Treatment Plan - Type 2 Diabetes
# ============================================================================
case2 = {
    "title": "CASE STUDY 2: Type 2 Diabetes - Treatment Plan",
    "patient": {
        "caseid": "CASE-2024-00041",
        "patid": "PAT-000041",
        "pname": "Tariq Hassan",
        "dob": "1958-09-30",
        "age": 47,
        "gender": "Male",
        "disease": "Type 2 Diabetes Mellitus",
        "medication": "Metformin",
        "bp": "135/85",
        "pulse": "76",
        "bmi": 32.1,
        "presenting_complaint": "Increased thirst and frequent urination",
        "family_history": "Mother has diabetes and hypertension",
        "social_history": "Sedentary lifestyle, occasional alcohol",
        "allergies": "Penicillin",
        "query_type": "Treatment",
        "custom_query": ""
    }
}

# ============================================================================
# CASE STUDY 3: Side Effects Analysis - Multiple Medications
# ============================================================================
case3 = {
    "title": "CASE STUDY 3: Anxiety Disorder - Side Effects Analysis",
    "patient": {
        "caseid": "CASE-2024-00039",
        "patid": "PAT-000039",
        "pname": "Badra Qasim",
        "dob": "2002-04-12",
        "age": 44,
        "gender": "Female",
        "disease": "Anxiety Disorder",
        "medication": "Alprazolam",
        "bp": "120/80",
        "pulse": "92",
        "bmi": 24.5,
        "presenting_complaint": "Excessive worry and restlessness",
        "family_history": "Sister has anxiety disorder",
        "social_history": "Works from home, limited social interaction",
        "allergies": "None",
        "query_type": "Side Effects",
        "custom_query": ""
    }
}

# ============================================================================
# CASE STUDY 4: Explain Condition - COPD Patient
# ============================================================================
case4 = {
    "title": "CASE STUDY 4: COPD - Condition Explanation",
    "patient": {
        "caseid": "CASE-2024-00004",
        "patid": "PAT-000004",
        "pname": "Sarah Ramadan",
        "dob": "1962-05-19",
        "age": 53,
        "gender": "Male",
        "disease": "COPD",
        "medication": "Albuterol inhaler",
        "bp": "140/90",
        "pulse": "85",
        "bmi": 26.8,
        "presenting_complaint": "Fatigue and weakness",
        "family_history": "Father was a smoker, had emphysema",
        "social_history": "Former smoker (20 pack-years), quit 5 years ago",
        "allergies": "Dust mites",
        "query_type": "Explain",
        "custom_query": ""
    }
}

def run_case_study(case_data):
    """Run a single case study and return the result"""
    print("\n" + "=" * 80)
    print(f"📋 {case_data['title']}")
    print("=" * 80)
    
    patient = case_data['patient']
    
    print("\n👤 PATIENT INFORMATION:")
    print("-" * 50)
    print(f"  Name: {patient['pname']}")
    print(f"  Age: {patient['age']} | Gender: {patient['gender']}")
    print(f"  Condition: {patient['disease']}")
    print(f"  Medication: {patient['medication']}")
    print(f"  BP: {patient['bp']} | Pulse: {patient['pulse']} | BMI: {patient['bmi']}")
    print(f"  Presenting Complaint: {patient['presenting_complaint']}")
    print(f"  Family History: {patient['family_history']}")
    print(f"  Query Type: {patient['query_type']}")
    
    print("\n🔄 Sending to AI for analysis...")
    
    try:
        start_time = datetime.now()
        response = requests.post(
            f"{API_URL}/clinical-query",
            json=patient,
            timeout=120
        )
        end_time = datetime.now()
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result.get('content', 'No response')
            
            print("\n✅ AI ANALYSIS COMPLETE!")
            print("-" * 80)
            print(f"⏱️ Response Time: {(end_time - start_time).total_seconds():.2f} seconds")
            print("\n📝 AI RESPONSE:")
            print("-" * 80)
            print(ai_response)
            
            return {
                "success": True,
                "patient_name": patient['pname'],
                "query_type": patient['query_type'],
                "response_time": (end_time - start_time).total_seconds(),
                "ai_response": ai_response
            }
        else:
            print(f"\n❌ API Error: {response.status_code}")
            return {"success": False, "error": f"Status {response.status_code}"}
            
    except requests.exceptions.Timeout:
        print("\n⏱️ Timeout: AI took too long to respond")
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return {"success": False, "error": str(e)}

def save_results(results):
    """Save all results to a file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"demo_results_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved to: {filename}")

def main():
    """Run all case studies"""
    print("\n" + "╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "INTELLIHEALTH AI CLINICAL SYSTEM" + " " * 26 + "║")
    print("║" + " " * 25 + "DEMO CASE STUDIES" + " " * 36 + "║")
    print("╚" + "=" * 78 + "╝")
    
    all_cases = [case1, case2, case3, case4]
    results = []
    
    for i, case in enumerate(all_cases, 1):
        print(f"\n\n{'='*80}")
        print(f"RUNNING CASE {i} OF {len(all_cases)}")
        print('='*80)
        
        result = run_case_study(case)
        results.append(result)
        
        # Small delay between requests
        if i < len(all_cases):
            print("\n⏳ Waiting 2 seconds before next case...")
            import time
            time.sleep(2)
    
    # Summary
    print("\n\n" + "=" * 80)
    print("📊 DEMO SUMMARY")
    print("=" * 80)
    
    successful = sum(1 for r in results if r.get('success'))
    print(f"\n✅ Successful: {successful}/{len(results)}")
    
    for r in results:
        if r.get('success'):
            print(f"  ✓ {r['patient_name']} - {r['query_type']} ({r['response_time']:.1f}s)")
        else:
            print(f"  ✗ Failed: {r.get('error', 'Unknown error')}")
    
    # Save results
    save_choice = input("\n💾 Save detailed results to file? (y/n): ").lower()
    if save_choice == 'y':
        save_results(results)
    
    print("\n" + "=" * 80)
    print("DEMO COMPLETE!")
    print("=" * 80)

if __name__ == "__main__":
    main()
