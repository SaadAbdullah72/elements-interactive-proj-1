# main.py
from fastapi import FastAPI, File, UploadFile, HTTPException, Response, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pymongo import MongoClient
from typing import List, Optional, Dict, Any
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from groq import Groq
import base64
import requests
from datetime import datetime
import re
import json
import csv
import pandas as pd
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
import hashlib
from email_service import send_registration_email
from auth import get_current_user

load_dotenv()

app = FastAPI(title="Medical Prescription Checker")

# -------------------------
# CORS Middleware Setup
# -------------------------
origins = [
    "http://localhost:3000",  # Default React port
    "http://localhost:5173",  # Default Vite port
    "http://localhost:8000",  # Backend server
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8000",
    "http://localhost:*",  # Allow all localhost ports for development
    "http://127.0.0.1:*",
    "*",  # Allow all origins (for development only - restrict in production)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Groq API Client Setup
# -------------------------
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    print("Warning: GROQ_API_KEY not found in .env file. Photo analysis will not work.")
    groq_client = None
else:
    groq_client = Groq(api_key=groq_api_key)

# -------------------------
# MongoDB Setup
# -------------------------
mongodburl = os.getenv('MONGODB_URL', os.getenv('LOCAL_MONGODB_URL', 'mongodb://localhost:27017/'))
db_name = os.getenv('MONGODB_LOCAL_DB', 'local')
client = MongoClient(mongodburl)
db = client[db_name]  # Replace "local" with your DB name

# -------------------------
# Import and Include Auth Router
# -------------------------
from auth import router as auth_router
app.include_router(auth_router)

# -------------------------
# Pydantic model for input
# -------------------------
class PatientData(BaseModel):
    description: Optional[str] = ""
    disease: str
    medication: str  # Can be comma-separated for multiple medications
    age: Optional[int] = None
    gender: Optional[str] = None
    symptoms: Optional[List[str]] = None  # For symptom-based prediction

class PDFReportRequest(BaseModel):
    """Request model for PDF report generation."""
    user_email: str
    patient_name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    disease: str
    medications: List[str]
    final_decision: str
    risk_level: str
    risk_score: Optional[Dict] = None
    explanation: Optional[str] = None
    drug_interactions: Optional[List[Dict]] = None
    possible_reactions: Optional[List[str]] = None

class SaveAnalysisRequest(BaseModel):
    """Request model for saving analysis."""
    user_email: str  # Changed from user_id to match frontend
    disease: str
    medication: str
    final_decision: str
    risk_level: Optional[str] = None  # Made optional
    risk_score: Optional[Dict] = None
    explanation: Optional[str] = None
    drug_interactions: Optional[List[Dict]] = None
    session_id: Optional[str] = None  # Session identifier for grouping consultations

class SessionRequest(BaseModel):
    """Request model for creating a new session."""
    patient_name: str
    patient_email: Optional[str] = None
    session_notes: Optional[str] = None

class ChatbotRequest(BaseModel):
    """Request model for chatbot analysis."""
    symptoms: str
    patient_name: Optional[str] = None

# -------------------------
# Agents
# -------------------------
class DiseaseAgent:
    def extract_symptoms(self, description: str) -> List[str]:
        # Simple split, can replace with NLP model
        return [sym.strip() for sym in description.lower().replace("with", ",").split(",") if sym]

class DrugVerificationAgent:
    def __init__(self, db):
        self.db = db
        # Common, well-established medication-disease pairs that should ALWAYS be SAFE
        self.established_pairs = {
            # Fever/Pain
            ("fever", "paracetamol"): True,
            ("fever", "acetaminophen"): True,
            ("fever", "ibuprofen"): True,
            ("fever", "aspirin"): True,
            ("pain", "paracetamol"): True,
            ("pain", "acetaminophen"): True,
            ("pain", "ibuprofen"): True,
            ("pain", "aspirin"): True,
            ("headache", "paracetamol"): True,
            ("headache", "ibuprofen"): True,
            ("headache", "aspirin"): True,
            # Hypertension
            ("hypertension", "amlodipine"): True,
            ("hypertension", "lisinopril"): True,
            ("hypertension", "losartan"): True,
            ("hypertension", "metoprolol"): True,
            ("hypertension", "hydrochlorothiazide"): True,
            # Diabetes
            ("diabetes", "metformin"): True,
            ("diabetes", "insulin"): True,
            ("diabetes", "glipizide"): True,
            ("diabetes", "sitagliptin"): True,
            # Infections
            ("bacterial infection", "amoxicillin"): True,
            ("infection", "amoxicillin"): True,
            ("infection", "azithromycin"): True,
            ("infection", "ciprofloxacin"): True,
            # Respiratory
            ("asthma", "albuterol"): True,
            ("asthma", "budesonide"): True,
            ("copd", "albuterol"): True,
            ("copd", "tiotropium"): True,
            # GI
            ("acid reflux", "omeprazole"): True,
            ("gerd", "omeprazole"): True,
            ("gastritis", "omeprazole"): True,
            ("nausea", "ondansetron"): True,
            # Mental Health
            ("depression", "sertraline"): True,
            ("depression", "fluoxetine"): True,
            ("anxiety", "sertraline"): True,
            ("anxiety", "lorazepam"): True,
            # Allergies
            ("allergies", "cetirizine"): True,
            ("allergies", "loratadine"): True,
            ("allergies", "diphenhydramine"): True,
            # Thyroid
            ("hypothyroidism", "levothyroxine"): True,
            # Cholesterol
            ("high cholesterol", "atorvastatin"): True,
            ("hyperlipidemia", "atorvastatin"): True,
            ("high cholesterol", "simvastatin"): True,
        }

    def verify(self, disease: str, drug: str) -> str:
        """
        Universal verification system for ANY disease-medication pair.
        Uses multi-stage verification: database -> established pairs -> advanced AI.
        """
        disease_lower = disease.lower().strip()
        drug_lower = drug.lower().strip()

        # PRIORITY 1: Check established medication-disease pairs (EXACT matches first)
        if (disease_lower, drug_lower) in self.established_pairs:
            return "SAFE"

        # PRIORITY 2: Check database for EXACT matches
        found = self.db.drug_disease_map.find_one({
            "disease": disease_lower,
            "drug_name": drug_lower
        })
        if found:
            return "SAFE"

        # PRIORITY 3: Check database with similarity (brand names vs generic)
        db_matches = list(self.db.drug_disease_map.find({
            "disease": disease_lower
        }))
        
        for db_record in db_matches:
            db_drug_name = db_record.get("drug_name", "").lower().strip()
            drug_similarity = self._drug_similarity(drug_lower, db_drug_name)
            if drug_similarity >= 0.8:
                return "SAFE"

        # PRIORITY 4: Check for STRONG partial disease matches
        for (db_disease, db_drug), is_safe in self.established_pairs.items():
            disease_similarity = self._disease_similarity(disease_lower, db_disease)
            drug_similarity = self._drug_similarity(drug_lower, db_drug)
            if disease_similarity >= 0.7 and drug_similarity >= 0.8:
                return "SAFE"

        # PRIORITY 5: Use advanced AI-powered verification for unknown pairs
        if groq_client:
            return self._verify_with_advanced_ai(disease, drug)

        # Default: If not in database, use cautious approach
        return "WARNING"

    def _verify_with_advanced_ai(self, disease: str, drug: str) -> str:
        """
        Advanced multi-stage AI verification using comprehensive clinical knowledge.
        Accurately assesses any disease-medication pair through intelligent prompting.
        """
        try:
            # STAGE 1: Clinical Classification
            clinical_prompt = f"""You are a world-class clinical pharmacist with extensive expertise in pharmacology and drug-disease interactions.

TASK: Classify the appropriateness of this medication for the given condition.

Condition: {disease}
Medication: {drug}

Analyze comprehensively:
1. Is this a first-line/gold standard treatment?
2. Is this a well-established alternative (second-line, adjunctive)?
3. Can this be used off-label appropriately?
4. Would this medication harm the condition?
5. Is there any direct contraindication?

CLASSIFICATIONS:
- FIRST_LINE: Standard first-choice medication for this condition
- ESTABLISHED: Well-documented, commonly used alternative
- APPROPRIATE: Can be used appropriately (off-label, older med, specialty use)
- CONCERNING: Not standard, requires caution
- CONTRAINDICATED: Should NOT be used for this condition

RESPOND WITH ONLY the classification word, nothing else."""

            response1 = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": clinical_prompt}],
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                max_tokens=20,
                temperature=0.2
            )
            
            classification = response1.choices[0].message.content.strip().upper()

            # STAGE 2: Safety verification check
            if classification in ["FIRST_LINE", "ESTABLISHED", "APPROPRIATE"]:
                safety_prompt = f"""Is {drug} known to be dangerous, contraindicated, or harmful for {disease}? 
Answer with either: DANGEROUS or SAFE
Only respond with one word."""

                response2 = groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": safety_prompt}],
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    max_tokens=5,
                    temperature=0.1
                )
                
                safety_verdict = response2.choices[0].message.content.strip().upper()
                
                if "DANGEROUS" in safety_verdict:
                    return "WARNING"
                
                return "SAFE"
            else:
                # CONCERNING or CONTRAINDICATED = WARNING
                return "WARNING"

        except Exception as e:
            print(f"AI verification error: {e}")
            return "WARNING"

    def _disease_similarity(self, disease1: str, disease2: str) -> float:
        """Calculate similarity between two disease names (0.0 to 1.0)."""
        # Exact match
        if disease1 == disease2:
            return 1.0
        # Check if one contains the other (but require significant overlap)
        if disease1 in disease2 or disease2 in disease1:
            # Require at least 70% length match
            min_len = min(len(disease1), len(disease2))
            max_len = max(len(disease1), len(disease2))
            return min_len / max_len
        # Check for common word overlap
        words1 = set(disease1.split())
        words2 = set(disease2.split())
        if len(words1) > 0 and len(words2) > 0:
            overlap = len(words1 & words2)
            total = len(words1 | words2)
            return overlap / total if total > 0 else 0.0
        return 0.0

class ReactionAgent:
    def __init__(self, db):
        self.db = db

    def get_reactions(self, drug: str) -> List[str]:
        reactions = list(self.db.drug_reaction_map.find({"drug_name": drug.lower()}, {"reaction": 1, "_id": 0}))
        return [r["reaction"] for r in reactions]

class RiskAgent:
    def __init__(self, db):
        self.db = db

    def assess_risk(self, age: Optional[int], gender: Optional[str], drug: str, disease: str,
                   symptoms: Optional[List[str]] = None, description: str = "") -> str:
        """
        Risk assessment - calibrated to avoid over-caution.
        Most common medications for common conditions in healthy adults = LOW risk.
        """
        risk_score = 0  # Start at 0, only add for REAL risks
        risk_factors = []  # Initialize risk factors list

        # Common, low-risk medications that should NOT trigger high risk scores
        low_risk_meds = ["paracetamol", "acetaminophen", "ibuprofen", "aspirin",
                        "cetirizine", "loratadine", "omeprazole", "metformin",
                        "amlodipine", "lisinopril", "levothyroxine", "sertraline"]

        is_low_risk_med = drug.lower() in low_risk_meds

        # 1. Age-based risk (only for extremes)
        if age is not None:
            if age < 2 or age > 85:
                risk_score += 3  # Reduced from 4
                risk_factors.append("extreme_age")
            elif age < 6 or age > 80:
                risk_score += 1  # Mild caution
            # Adults 18-65 = no additional risk (normal)

        # 2. FAERS adverse events (only for very high counts)
        faers_count = self.db.faers_clean_dataset.count_documents({
            "drug_name": drug.lower()
        })
        if faers_count > 5000:  # Increased threshold
            risk_score += 2
        elif faers_count > 3000:
            risk_score += 1

        # 3. Drug-disease mapping (don't penalize if not in database)
        drug_disease_match = self.db.drug_disease_map.find_one({
            "disease": disease.lower(),
            "drug_name": drug.lower()
        })
        if not drug_disease_match:
            # Don't add risk score - Groq already verified it's appropriate
            pass  # Removed: risk_score += 4

        # 4. Gender-specific considerations (only for REAL contraindications)
        if gender:
            gender_lower = gender.lower()
            drug_lower = drug.lower()

            # Isotretinoin/Accutane - pregnancy risk (REAL danger)
            if drug_lower in ["isotretinoin", "accutane", "methotrexate"] and gender_lower == "female":
                if age is not None and 15 <= age <= 45:
                    risk_score += 3
                    risk_factors.append("pregnancy_risk")

        # 5. High-risk medications (narrow therapeutic index only)
        high_risk_drugs = ["warfarin", "digoxin", "lithium", "methotrexate",
                          "clozapine", "insulin", "morphine", "fentanyl"]
        if drug.lower() in high_risk_drugs:
            risk_score += 2  # Reduced from higher values
            risk_factors.append("narrow_therapeutic_index")
        elif not is_low_risk_med:
            # Unknown medication = mild caution, not high risk
            risk_score += 1
        high_risk_drugs = ["warfarin", "digoxin", "lithium", "methotrexate", "clozapine",
                          "insulin", "morphine", "fentanyl", "prednisone"]
        if drug.lower() in high_risk_drugs:
            risk_score += 2
            risk_factors.append("narrow_therapeutic_index")

        # 6. Symptom-drug mismatch detection
        if symptoms:
            symptoms_lower = [s.lower().strip() for s in symptoms]
            # Check if symptoms suggest a different condition
            if any(s in symptoms_lower for s in ["pregnant", "pregnancy"]):
                if drug.lower() in ["isotretinoin", "accutane", "methotrexate", "warfarin"]:
                    risk_score += 4
                    risk_factors.append("contraindicated_in_pregnancy")

        # 7. Description-based risk (keyword analysis)
        if description:
            desc_lower = description.lower()
            high_risk_keywords = ["severe", "allergic", "anaphylaxis", "emergency", "critical", 
                                 "unconscious", "bleeding", "chest pain", "difficulty breathing"]
            if any(keyword in desc_lower for keyword in high_risk_keywords):
                risk_score += 2
                risk_factors.append("severe_presentation")

        # Convert score to risk level
        if risk_score >= 8:
            return "CRITICAL"
        elif risk_score >= 5:
            return "HIGH"
        elif risk_score >= 2:
            return "MEDIUM"
        else:
            return "LOW"

class FinalDecisionAgent:
    def decide(self, verification_status: str, risk_level: str) -> str:
        """
        CLINICAL DECISION MATRIX - Doctor-Level Final Verdict
        
        Rules:
        1. HARMFUL/WRONG drug → UNSAFE
        2. WARNING verification + elevated risk → UNSAFE
        3. CRITICAL/VERY HIGH risk → UNSAFE
        4. WARNING verification alone → CAUTION
        5. HIGH risk → CAUTION
        6. SAFE verification + LOW risk → SAFE
        """
        # Rule 1 & 2: WARNING verification with elevated risk = UNSAFE
        if verification_status == "WARNING" and risk_level in ["CRITICAL", "VERY HIGH", "HIGH"]:
            return "UNSAFE"
        
        # Rule 3: CRITICAL or VERY HIGH risk = UNSAFE (dangerous medication)
        if risk_level in ["CRITICAL", "VERY HIGH"]:
            return "UNSAFE"
        
        # Rule 4: WARNING verification alone = CAUTION (needs review)
        if verification_status == "WARNING":
            return "CAUTION"
        
        # Rule 5: HIGH risk = CAUTION (monitor closely)
        if risk_level == "HIGH":
            return "CAUTION"
        
        # Rule 6: SAFE verification + acceptable risk = SAFE
        if verification_status == "SAFE" and risk_level in ["LOW", "VERY LOW", "MODERATE"]:
            return "SAFE"
        
        # Default: When in doubt, caution
        return "CAUTION"

# -------------------------
# NEW: Drug Interaction Detection Agent
# -------------------------
class DrugInteractionAgent:
    def __init__(self, db):
        self.db = db
        self.interactions = self._load_interactions()
    
    def _load_interactions(self) -> Dict:
        """Load drug interactions from CSV file."""
        interactions = {}
        try:
            with open('drug_interactions.csv', 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    drug1 = row['drug1'].lower().strip()
                    drug2 = row['drug2'].lower().strip()
                    severity = row['severity']
                    description = row['description']
                    # Store both directions
                    interactions[(drug1, drug2)] = {'severity': severity, 'description': description}
                    interactions[(drug2, drug1)] = {'severity': severity, 'description': description}
        except Exception as e:
            print(f"Error loading drug interactions: {e}")
        return interactions
    
    def check_interactions(self, medications: List[str]) -> List[Dict]:
        """Check for interactions between multiple medications."""
        interactions_found = []
        for i, drug1 in enumerate(medications):
            for drug2 in medications[i+1:]:
                key = (drug1.lower().strip(), drug2.lower().strip())
                if key in self.interactions:
                    interactions_found.append({
                        'drug1': drug1,
                        'drug2': drug2,
                        'severity': self.interactions[key]['severity'],
                        'description': self.interactions[key]['description']
                    })
        return interactions_found

# -------------------------
# NEW: Symptom → Disease Prediction Agent
# -------------------------
class SymptomPredictionAgent:
    def __init__(self, db):
        self.db = db
        self.symptom_map = self._load_symptom_map()
        # Common medical conditions that should NOT be treated as symptoms
        self.known_conditions = {
            'fever', 'migraine', 'hypertension', 'diabetes', 'asthma', 'arthritis',
            'depression', 'anxiety', 'epilepsy', 'cancer', 'pneumonia', 'bronchitis',
            'influenza', 'common cold', 'covid-19', 'malaria', 'typhoid', 'jaundice',
            'tuberculosis', 'hiv', 'aids', 'hepatitis', 'cirrhosis', 'kidney failure',
            'heart disease', 'stroke', 'anemia', 'thyroid', 'hypothyroidism', 'hyperthyroidism',
            'copd', 'emphysema', 'allergies', 'eczema', 'psoriasis', 'acne',
            'obesity', 'malnutrition', 'insomnia', 'sleep apnea', 'dementia',
            'alzheimers', 'parkinsons', 'multiple sclerosis', 'fibromyalgia',
            'chronic fatigue syndrome', 'ibs', 'crohns disease', 'ulcerative colitis',
            'gerd', 'gallstones', 'kidney stones', 'uti', 'std', 'herpes', 'hpv',
            'malaria', 'dengue', 'chikungunya', 'zika', 'ebola', 'measles', 'mumps',
            'rubella', 'chickenpox', 'shingles', 'mononucleosis', 'lyme disease',
            'sepsis', 'meningitis', 'encephalitis', 'osteoporosis', 'gout',
            'lupus', 'rheumatoid arthritis', 'osteoarthritis', 'tendinitis', 'bursitis',
            'carpal tunnel', 'sciatica', 'herniated disc', 'scoliosis', 'flat feet',
            'glaucoma', 'cataracts', 'macular degeneration', 'retinal detachment',
            'hearing loss', 'tinnitus', 'vertigo', 'menieres disease',
            'endometriosis', 'pcos', 'fibroids', 'ovarian cysts', 'prostatitis',
            'erectile dysfunction', 'infertility', 'pregnancy', 'miscarriage',
            'ectopic pregnancy', 'preeclampsia', 'gestational diabetes',
            'autism', 'adhd', 'dyslexia', 'down syndrome', 'cerebral palsy',
            'cleft lip', 'cleft palate', 'spina bifida', 'hydrocephalus'
        }

    def _load_symptom_map(self) -> Dict:
        """Load symptom to disease mapping from CSV."""
        symptom_map = {}
        try:
            with open('symptom_disease_map.csv', 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    symptoms = [s.strip().lower() for s in row['symptoms'].split(';')]
                    disease = row['diseases']
                    confidence = row['confidence']
                    symptom_key = tuple(sorted(symptoms))
                    symptom_map[symptom_key] = {'disease': disease, 'confidence': confidence}
        except Exception as e:
            print(f"Error loading symptom map: {e}")
        return symptom_map

    def predict_diseases(self, symptoms: List[str]) -> List[Dict]:
        """Predict possible diseases from symptoms."""
        predictions = []
        symptoms_lower = [s.lower().strip() for s in symptoms]
        
        # Check if input looks like a condition/disease rather than symptoms
        # If so, return it directly as the predicted condition
        for symptom in symptoms_lower:
            if symptom in self.known_conditions:
                return [{
                    'disease': symptom.title(),
                    'confidence': 'HIGH',
                    'matched_symptoms': [symptom],
                    'note': 'Recognized as a medical condition'
                }]

        # Direct match with symptom map
        for symptom_key, disease_info in self.symptom_map.items():
            match_count = len(set(symptoms_lower) & set(symptom_key))
            if match_count >= min(len(symptom_key), len(symptoms_lower)):
                predictions.append({
                    'disease': disease_info['disease'],
                    'confidence': disease_info['confidence'],
                    'matched_symptoms': list(set(symptoms_lower) & set(symptom_key))
                })

        # Also check database for partial matches
        if not predictions:
            # Use Groq for AI-based prediction
            if groq_client:
                try:
                    prompt = f"""Given these symptoms: {', '.join(symptoms)}, list 3-5 possible medical conditions (one per line, just the condition name).
Important: Only return actual medical conditions/diseases, NOT symptoms or treatments.
Format: One condition name per line."""
                    response = groq_client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model="meta-llama/llama-4-scout-17b-16e-instruct",
                        max_tokens=100
                    )
                    diseases = response.choices[0].message.content.strip().split('\n')
                    for disease in diseases[:5]:
                        disease_clean = disease.strip()
                        # Filter out non-condition responses
                        if disease_clean and not any(word in disease_clean.lower() for word in ['symptom', 'treatment', 'medication', 'drug', 'pill']):
                            predictions.append({
                                'disease': disease_clean,
                                'confidence': 'MEDIUM',
                                'matched_symptoms': symptoms_lower
                            })
                except Exception:
                    pass

        return predictions[:5]  # Return top 5 predictions

# -------------------------
# NEW: Enhanced Risk Score Agent (Doctor Prescription Accuracy Based)
# -------------------------
class PersonalRiskScoreAgent:
    def __init__(self, db):
        self.db = db
        # Gold Standard medications - first-line, best-in-class for common conditions
        self.gold_standard_pairs = {
            ("fever", "paracetamol"), ("fever", "acetaminophen"), ("fever", "ibuprofen"),
            ("pain", "paracetamol"), ("pain", "ibuprofen"), ("pain", "acetaminophen"),
            ("headache", "paracetamol"), ("headache", "ibuprofen"),
            ("hypertension", "amlodipine"), ("hypertension", "lisinopril"), ("hypertension", "losartan"),
            ("diabetes", "metformin"), ("diabetes", "insulin"),
            ("bacterial infection", "amoxicillin"), ("infection", "amoxicillin"),
            ("asthma", "albuterol"), ("copd", "albuterol"),
            ("acid reflux", "omeprazole"), ("gerd", "omeprazole"),
            ("depression", "sertraline"), ("depression", "fluoxetine"),
            ("anxiety", "sertraline"), ("allergies", "cetirizine"), ("allergies", "loratadine"),
            ("hypothyroidism", "levothyroxine"),
            ("high cholesterol", "atorvastatin"), ("hyperlipidemia", "atorvastatin"),
        }
        # Harmful/Contraindicated medications - can worsen condition
        self.harmful_pairs = {
            ("fever", "aspirin"): "Risk of Reye's syndrome in children",
            ("hypertension", "prednisone"): "Steroids increase blood pressure",
            ("diabetes", "prednisone"): "Steroids increase blood sugar",
            ("asthma", "propranolol"): "Beta-blockers can trigger bronchospasm",
            ("depression", "prednisone"): "Can worsen mood disorders",
        }

        # Enhanced scoring weights based on clinical evidence
        self.scoring_weights = {
            "gold_standard_match": 35,  # First-line treatment
            "appropriate_match": 25,    # Established treatment
            "database_match": 20,       # Evidence-based match
            "ai_verified_safe": 15,     # AI-verified appropriateness
            "age_appropriate": 10,      # Age-appropriate dosing
            "gender_appropriate": 8,    # Gender considerations
            "no_interactions": 12,      # No drug interactions
            "low_risk_medication": 10,  # Low-risk medication class
            "single_medication": 8,     # Simpler regimen
            "evidence_based": 5,        # Evidence-based practice
            # Penalties
            "harmful_medication": -50,  # Contraindicated
            "wrong_drug": -30,          # Not for this condition
            "high_interactions": -25,   # Severe interactions
            "high_risk_medication": -15,# Narrow therapeutic index
            "polypharmacy": -10,        # Multiple medications
            "age_risk": -12,            # Age-related risks
            "pregnancy_risk": -40,      # Pregnancy contraindication
            "severe_symptoms": -8,      # Severe presentation
        }

    def _get_ai_confidence_score(self, disease: str, medications: List[str], verification_status: str) -> Dict:
        """
        Use AI to verify confidence in the prescription assessment.
        Works for ANY disease-medication combination.
        Returns confidence metrics and refined accuracy score.
        """
        if not groq_client:
            return {"confidence_level": "UNKNOWN", "confidence_score": 50, "explanation": "AI unavailable"}
        
        try:
            meds_str = ", ".join(medications)
            prompt = f"""As a clinical expert, rate your confidence in this assessment:

Condition: {disease}
Medications: {meds_str}
Initial Assessment: {verification_status}

Questions to consider:
1. How well-established is this medication for this condition?
2. Are there better alternatives?
3. What's the evidence level (strong, moderate, weak)?
4. Any special considerations needed?

Rate confidence from 1-100, where:
- 85-100: High confidence, well-established
- 70-84: Good confidence, established treatment
- 55-69: Moderate confidence, reasonable choice
- 40-54: Lower confidence, acceptable but not ideal
- 25-39: Low confidence, needs caution
- 0-24: Very low confidence, concerning

Respond with ONLY the number (e.g., 87)"""

            response = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                max_tokens=5,
                temperature=0.3
            )
            
            score_text = response.choices[0].message.content.strip()
            confidence_score = int(score_text) if score_text.isdigit() else 50
            confidence_score = max(0, min(100, confidence_score))
            
            if confidence_score >= 85:
                level = "VERY HIGH"
            elif confidence_score >= 70:
                level = "HIGH"
            elif confidence_score >= 55:
                level = "MODERATE"
            elif confidence_score >= 40:
                level = "LOWER"
            else:
                level = "LOW"
            
            return {
                "confidence_level": level,
                "confidence_score": confidence_score,
                "explanation": f"AI validation score: {confidence_score}/100"
            }
        
        except Exception as e:
            print(f"Error calculating AI confidence: {e}")
            return {"confidence_level": "UNKNOWN", "confidence_score": 50, "explanation": "Error in AI validation"}

    def _generate_ai_commentary(self, disease: str, medications: List[str], risk_level: str, 
                                verification_status: str, age: Optional[int] = None, 
                                gender: Optional[str] = None) -> str:
        """
        Generate accurate, personalized medical commentary for ANY prescription.
        Provides detailed explanation of the assessment.
        """
        if not groq_client:
            return "Medical assessment completed. Please consult with a healthcare provider for detailed guidance."
        
        try:
            meds_str = ", ".join(medications)
            age_context = f"Patient age: {age} years old. " if age else ""
            gender_context = f"Patient gender: {gender}. " if gender else ""
            
            prompt = f"""You are a clinical pharmacist providing patient-friendly but medically accurate commentary.

{age_context}{gender_context}
Condition: {disease}
Prescribed Medications: {meds_str}
Risk Level: {risk_level}
Verification: {verification_status}

Provide a 2-3 sentence professional explanation covering:
1. Is this medication appropriate for this condition?
2. Any important considerations the patient should know?
3. Recommendation about the prescription

Be accurate, evidence-based, and patient-friendly. Avoid medical jargon."""

            response = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                max_tokens=150,
                temperature=0.5
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            print(f"Error generating commentary: {e}")
            return "Medical assessment completed. Consult with healthcare provider for detailed guidance."

    def calculate_risk_score(self, age: Optional[int], gender: Optional[str],
                            medications: List[str], disease: str,
                            adverse_reactions: Optional[List[str]] = None,
                            symptom_severity: str = "moderate",
                            verification_status: str = "SAFE",
                            final_decision: str = "SAFE",
                            drug_interactions: Optional[List[Dict]] = None,
                            symptoms: Optional[List[str]] = None,
                            description: str = "") -> Dict:
        """
        ENHANCED CLINICAL SCORING SYSTEM - Doctor-Level Prescription Accuracy Assessment
        Uses weighted scoring based on clinical evidence and best practices.
        """
        risk_factors_detail = []
        disease_lower = disease.lower().strip()
        total_score = 50  # Start at neutral score

        # ==========================================
        # STEP 1: DISEASE-MEDICATION MATCH QUALITY (Most Important - 40% weight)
        # ==========================================
        match_quality_score = 0
        is_gold_standard = False
        is_appropriate = False
        is_harmful = False
        is_wrong_drug = False

        for med in medications:
            med_lower = med.lower().strip()

            # Check for HARMFUL medications first (immediate fail)
            if (disease_lower, med_lower) in self.harmful_pairs:
                reason = self.harmful_pairs[(disease_lower, med_lower)]
                risk_factors_detail.append(f"🚨 HARMFUL: {med} can worsen {disease} - {reason}")
                match_quality_score += self.scoring_weights["harmful_medication"]
                is_harmful = True
                continue

            # Check gold standard (first-line treatments)
            if (disease_lower, med_lower) in self.gold_standard_pairs:
                match_quality_score += self.scoring_weights["gold_standard_match"]
                is_gold_standard = True
                is_appropriate = True
                risk_factors_detail.append(f"🏆 GOLD STANDARD: {med} is first-line treatment for {disease}")
                continue

            # Check database match
            db_match = self.db.drug_disease_map.find_one({
                "disease": disease_lower,
                "drug_name": med_lower
            })

            if db_match:
                confidence = db_match.get("confidence", "").lower()
                if confidence == "high":
                    match_quality_score += self.scoring_weights["database_match"] + 5
                    risk_factors_detail.append(f"✅ HIGH CONFIDENCE: {med} is well-established for {disease}")
                elif confidence == "medium":
                    match_quality_score += self.scoring_weights["database_match"]
                    risk_factors_detail.append(f"✓ MODERATE: {med} is commonly used for {disease}")
                else:
                    match_quality_score += self.scoring_weights["database_match"] - 5
                    risk_factors_detail.append(f"ℹ️ LIMITED EVIDENCE: {med} has been used for {disease}")
                is_appropriate = True
            else:
                # Not in database - check AI verification
                if verification_status == "SAFE":
                    match_quality_score += self.scoring_weights["ai_verified_safe"]
                    is_appropriate = True
                    risk_factors_detail.append(f"✓ AI-VERIFIED: {med} is appropriate for {disease}")
                else:
                    match_quality_score += self.scoring_weights["wrong_drug"]
                    is_wrong_drug = True
                    risk_factors_detail.append(f"⚠️ NOT ESTABLISHED: {med} is not standard for {disease}")

        total_score += match_quality_score

        # ==========================================
        # STEP 2: DRUG INTERACTIONS & POLYPHARMACY (15% weight)
        # ==========================================
        interaction_score = 0
        if drug_interactions and len(drug_interactions) > 0:
            high_severity_count = sum(1 for i in drug_interactions if i.get('severity') == 'HIGH')
            medium_severity_count = sum(1 for i in drug_interactions if i.get('severity') == 'MEDIUM')

            if high_severity_count > 0:
                interaction_score += self.scoring_weights["high_interactions"]
                risk_factors_detail.append(f"🔴 {high_severity_count} HIGH-SEVERITY drug interaction(s)")
            elif medium_severity_count > 0:
                interaction_score += self.scoring_weights["high_interactions"] // 2
                risk_factors_detail.append(f"🟠 {medium_severity_count} MEDIUM-SEVERITY drug interaction(s)")
            else:
                interaction_score += 5  # Minor interactions
                risk_factors_detail.append("🟡 Minor drug interaction(s) present")
        else:
            interaction_score += self.scoring_weights["no_interactions"]
            risk_factors_detail.append("✅ No drug interactions detected")

        # Polypharmacy penalty
        if len(medications) > 5:
            interaction_score += self.scoring_weights["polypharmacy"]
            risk_factors_detail.append(f"💊 Polypharmacy risk ({len(medications)} medications)")
        elif len(medications) == 1:
            interaction_score += self.scoring_weights["single_medication"]
            risk_factors_detail.append("✓ Single medication: Lower complexity")

        total_score += interaction_score

        # ==========================================
        # STEP 3: PATIENT-SPECIFIC FACTORS (20% weight)
        # ==========================================
        patient_score = 0

        # Age considerations
        if age is not None:
            if age < 2:
                patient_score += self.scoring_weights["age_risk"] * 2
                risk_factors_detail.append("👶 Infant: Extreme caution required")
            elif age < 12:
                patient_score += self.scoring_weights["age_risk"]
                risk_factors_detail.append("🧒 Pediatric: Dosing adjustments needed")
            elif age > 75:
                patient_score += self.scoring_weights["age_risk"]
                risk_factors_detail.append("👴 Elderly: Reduced clearance risk")
            elif 18 <= age <= 65:
                patient_score += self.scoring_weights["age_appropriate"]
                risk_factors_detail.append("✓ Adult: Standard dosing appropriate")
            else:
                patient_score += 5  # Mild adjustment needed

        # Gender considerations
        if gender and gender.lower() == "female" and age and 15 <= age <= 45:
            pregnancy_risk_meds = ["isotretinoin", "accutane", "methotrexate", "warfarin",
                                 "lisinopril", "valsartan", "topiramate", "valproic acid"]
            for med in medications:
                if med.lower() in pregnancy_risk_meds:
                    patient_score += self.scoring_weights["pregnancy_risk"]
                    risk_factors_detail.append(f"🚫 PREGNANCY RISK: {med} is teratogenic")
                    break
            else:
                patient_score += self.scoring_weights["gender_appropriate"]
                risk_factors_detail.append("✓ Reproductive age female: No pregnancy risks identified")

        # ==========================================
        # STEP 4: MEDICATION RISK CLASS (15% weight)
        # ==========================================
        medication_score = 0
        high_risk_drugs = ["warfarin", "digoxin", "lithium", "methotrexate", "clozapine",
                          "insulin", "morphine", "fentanyl", "prednisone"]
        low_risk_drugs = ["paracetamol", "acetaminophen", "ibuprofen", "aspirin",
                         "cetirizine", "loratadine", "omeprazole", "metformin"]

        for med in medications:
            med_lower = med.lower()
            if med_lower in high_risk_drugs:
                medication_score += self.scoring_weights["high_risk_medication"]
                risk_factors_detail.append(f"⚠️ HIGH-RISK: {med} requires monitoring")
            elif med_lower in low_risk_drugs:
                medication_score += self.scoring_weights["low_risk_medication"]
                risk_factors_detail.append(f"✓ LOW-RISK: {med} has favorable safety profile")

        total_score += medication_score + patient_score

        # ==========================================
        # STEP 5: SYMPTOM CORRELATION (10% weight)
        # ==========================================
        symptom_score = 0
        if symptoms:
            # Check if symptoms suggest comorbidities (not penalties)
            skin_symptoms = ["rash", "itchy skin", "hives", "eczema", "dermatitis"]
            if any(sym in " ".join(symptoms).lower() for sym in skin_symptoms):
                symptom_score += 0  # Neutral - separate condition
                risk_factors_detail.append("ℹ️ Note: Skin symptoms may indicate separate dermatological condition")

            # Check for contraindications
            contraindication_symptoms = {
                "pregnant": ["isotretinoin", "accutane", "methotrexate", "warfarin"],
                "pregnancy": ["isotretinoin", "accutane", "methotrexate", "warfarin"],
            }

            for symptom, contraindicated_meds in contraindication_symptoms.items():
                if any(symptom in s.lower() for s in symptoms):
                    for med in medications:
                        if med.lower() in contraindicated_meds:
                            symptom_score += self.scoring_weights["pregnancy_risk"] // 2
                            risk_factors_detail.append(f"🚫 CONTRAINDICATION: {med} unsafe with {symptom}")

        # Symptom severity consideration
        if symptom_severity == "severe":
            symptom_score += self.scoring_weights["severe_symptoms"]
            risk_factors_detail.append("🚨 Severe symptoms: Requires urgent attention")

        total_score += symptom_score

        # ==========================================
        # STEP 6: EVIDENCE-BASED PRACTICE BONUS (Minor)
        # ==========================================
        if is_gold_standard or (is_appropriate and not is_wrong_drug):
            total_score += self.scoring_weights["evidence_based"]
            risk_factors_detail.append("📚 Evidence-based practice followed")

        # ==========================================
        # FINAL SCORE CALCULATION & CATEGORIZATION
        # ==========================================
        final_score = max(0, min(100, total_score))

        # Enhanced categorization based on clinical significance
        if is_harmful or final_score < 20:
            risk_level = "CRITICAL"
            safety_category = "UNSAFE - DO NOT PRESCRIBE"
        elif final_score >= 85:
            risk_level = "VERY LOW"
            safety_category = "GOLD STANDARD"
        elif final_score >= 70:
            risk_level = "LOW"
            safety_category = "EXCELLENT"
        elif final_score >= 55:
            risk_level = "MODERATE"
            safety_category = "GOOD"
        elif final_score >= 40:
            risk_level = "HIGH"
            safety_category = "ACCEPTABLE - MONITOR"
        elif final_score >= 25:
            risk_level = "VERY HIGH"
            safety_category = "CONCERNING - REVIEW"
        else:
            risk_level = "CRITICAL"
            safety_category = "UNSAFE - DO NOT USE"

        # ==========================================
        # AI CONFIDENCE VALIDATION & COMMENTARY
        # ==========================================
        ai_confidence = self._get_ai_confidence_score(disease, medications, verification_status)
        ai_commentary = self._generate_ai_commentary(disease, medications, risk_level, 
                                                     verification_status, age, gender)
        
        # Adjust final score slightly based on AI confidence if high confidence
        if ai_confidence["confidence_score"] >= 85:
            final_score = min(100, final_score + 3)  # Small boost for high confidence
        elif ai_confidence["confidence_score"] <= 40:
            final_score = max(0, final_score - 5)  # Small penalty for low confidence

        return {
            "score": final_score,
            "level": risk_level,
            "safety_category": safety_category,
            "factors": risk_factors_detail,
            "ai_confidence": ai_confidence,
            "ai_commentary": ai_commentary,
            "breakdown": {
                "match_quality_score": match_quality_score,
                "interaction_score": interaction_score,
                "patient_score": patient_score,
                "medication_score": medication_score,
                "symptom_score": symptom_score,
                "final_decision": final_decision,
                "verification_status": verification_status,
                "is_gold_standard": is_gold_standard,
                "is_appropriate": is_appropriate,
                "is_harmful": is_harmful,
                "is_wrong_drug": is_wrong_drug,
                "medication_count": len(medications),
                "interaction_count": len(drug_interactions) if drug_interactions else 0,
                "age_provided": age is not None,
                "gender_provided": gender is not None
            }
        }


# -------------------------
# NEW: Medical Knowledge Graph Agent
# -------------------------
class KnowledgeGraphAgent:
    def __init__(self):
        self.graph = self._load_knowledge_graph()
    
    def _load_knowledge_graph(self) -> Dict:
        """Load medical knowledge graph from JSON."""
        try:
            with open('medical_knowledge_graph.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading knowledge graph: {e}")
            return {"diseases": {}, "medications": {}, "symptoms": {}, "reactions": {}}
    
    def get_disease_info(self, disease: str) -> Optional[Dict]:
        """Get disease information from knowledge graph."""
        disease_lower = disease.lower()
        for key, value in self.graph.get("diseases", {}).items():
            if disease_lower in key.lower() or key.lower() in disease_lower:
                return value
        return None
    
    def get_medication_info(self, medication: str) -> Optional[Dict]:
        """Get medication information from knowledge graph."""
        med_lower = medication.lower()
        for key, value in self.graph.get("medications", {}).items():
            if med_lower in key.lower() or key.lower() in med_lower:
                return value
        return None
    
    def get_graph_for_response(self, disease: str, medications: List[str]) -> Dict:
        """Get relevant knowledge graph data for response."""
        disease_info = self.get_disease_info(disease)
        medication_infos = []
        for med in medications:
            med_info = self.get_medication_info(med)
            if med_info:
                medication_infos.append(med_info)
        
        # NEW: Get alternative medications
        alternative_medications = []
        if disease_info and disease_info.get('medications'):
            current_meds_lower = [m.lower() for m in medications]
            all_alternatives = disease_info['medications']
            
            # Filter out current medications and sort by score
            alternatives = [
                alt for alt in all_alternatives 
                if alt['name'].lower() not in current_meds_lower
            ]
            alternatives.sort(key=lambda x: x.get('suggestion_score', 0), reverse=True)
            alternative_medications = alternatives[:3] # Return top 3

        return {
            "disease": disease_info,
            "medications": medication_infos,
            "alternative_medications": alternative_medications,
            "nodes": self._create_graph_nodes(disease_info, medication_infos),
            "edges": self._create_graph_edges(disease_info, medication_infos)
        }
    
    def _create_graph_nodes(self, disease_info: Optional[Dict], medication_infos: List[Dict]) -> List[Dict]:
        """Create nodes for graph visualization."""
        nodes = []
        if disease_info:
            nodes.append({
                "id": disease_info.get("name", "Unknown"),
                "type": "disease",
                "label": disease_info.get("name", "Unknown")
            })
            for symptom in disease_info.get("symptoms", [])[:5]:
                nodes.append({"id": symptom, "type": "symptom", "label": symptom})
        for med_info in medication_infos:
            nodes.append({
                "id": med_info.get("name", "Unknown"),
                "type": "medication",
                "label": med_info.get("name", "Unknown")
            })
        return nodes
    
    def _create_graph_edges(self, disease_info: Optional[Dict], medication_infos: List[Dict]) -> List[Dict]:
        """Create edges for graph visualization."""
        edges = []
        if disease_info:
            for symptom in disease_info.get("symptoms", [])[:5]:
                edges.append({
                    "source": disease_info.get("name", "Unknown"),
                    "target": symptom,
                    "type": "has_symptom"
                })
            for med_info in medication_infos:
                edges.append({
                    "source": disease_info.get("name", "Unknown"),
                    "target": med_info.get("name", "Unknown"),
                    "type": "treated_by"
                })
        return edges

# -------------------------
# Orchestrator
# -------------------------
class Orchestrator:
    def __init__(self, db):
        self.disease_agent = DiseaseAgent()
        self.drug_agent = DrugVerificationAgent(db)
        self.reaction_agent = ReactionAgent(db)
        self.risk_agent = RiskAgent(db)
        self.final_agent = FinalDecisionAgent()
        self.interaction_agent = DrugInteractionAgent(db)
        self.symptom_agent = SymptomPredictionAgent(db)
        self.risk_score_agent = PersonalRiskScoreAgent(db)
        self.knowledge_graph_agent = KnowledgeGraphAgent()

    def process(self, data: PatientData) -> dict:
        """Enhanced processing with better error handling and edge case management"""
        try:
            # Enhanced input sanitization
            data.disease = data.disease.strip().lower() if data.disease else ""
            data.medication = data.medication.strip() if data.medication else ""
            data.description = data.description.strip() if data.description else ""
            if data.symptoms:
                data.symptoms = [s.strip().lower() for s in data.symptoms if s.strip()]

            # Parse medications (support multiple comma-separated) and remove duplicates
            medications = list(dict.fromkeys([med.strip() for med in data.medication.split(',') if med.strip()]))

            if not medications:
                return {
                    "error": "No valid medications provided",
                    "medications": [],
                    "verification_status": "ERROR",
                    "final_decision": "ERROR",
                    "explanation": "Please provide at least one medication to analyze."
                }

            # Step 1: Extract symptoms with better handling
            symptoms = self.disease_agent.extract_symptoms(data.description) if data.description else []

            # If symptoms provided separately, merge them
            if data.symptoms:
                symptoms.extend(data.symptoms)
                symptoms = list(set(symptoms))  # Remove duplicates

            # Step 2: Verify drug for disease (database + AI) with error handling
            verification_results = []
            for med in medications:
                try:
                    verification = self.drug_agent.verify(data.disease, med)
                    verification_results.append({
                        "medication": med,
                        "status": verification,
                        "error": None
                    })
                except Exception as e:
                    verification_results.append({
                        "medication": med,
                        "status": "WARNING",  # Default to warning on error
                        "error": str(e)
                    })

            # Determine overall verification status
            verification_status = "SAFE"
            if any(v["status"] == "WARNING" for v in verification_results):
                verification_status = "WARNING"

            # Step 3: Get possible reactions for all medications
            all_reactions = []
            for med in medications:
                try:
                    reactions = self.reaction_agent.get_reactions(med)
                    all_reactions.extend(reactions)
                except Exception as e:
                    print(f"Error getting reactions for {med}: {e}")

            reactions = list(set(all_reactions))[:10]  # Remove duplicates, limit to 10

            # Step 4: Check drug interactions with error handling
            try:
                drug_interactions = self.interaction_agent.check_interactions(medications)
            except Exception as e:
                print(f"Error checking drug interactions: {e}")
                drug_interactions = []

            # Step 5: Enhanced risk assessment
            try:
                risk_level = self.risk_agent.assess_risk(
                    age=data.age,
                    gender=data.gender,
                    drug=data.medication,  # Use original string for compatibility
                    disease=data.disease,
                    symptoms=symptoms,
                    description=data.description
                )
            except Exception as e:
                print(f"Error in risk assessment: {e}")
                risk_level = "MEDIUM"  # Default fallback

            # Step 6: Final decision with interaction consideration
            final_decision = self.final_agent.decide(verification_status, risk_level)

            # Adjust final decision based on drug interactions
            if drug_interactions:
                high_severity_interactions = [i for i in drug_interactions if i.get('severity') == 'HIGH']
                if high_severity_interactions:
                    final_decision = "UNSAFE"
                elif final_decision == "SAFE":
                    final_decision = "CAUTION"

            # Step 7: Calculate comprehensive personal risk score
            try:
                risk_score = self.risk_score_agent.calculate_risk_score(
                    age=data.age,
                    gender=data.gender,
                    medications=medications,
                    disease=data.disease,
                    adverse_reactions=reactions[:3],
                    symptom_severity="moderate",
                    verification_status=verification_status,
                    final_decision=final_decision,
                    drug_interactions=drug_interactions,
                    symptoms=symptoms if symptoms else None,
                    description=data.description or ""
                )
            except Exception as e:
                print(f"Error calculating risk score: {e}")
                risk_score = None

            # Step 8: Generate intelligent explanation
            try:
                explanation = self._generate_explanation(
                    data, verification_status, risk_level, final_decision,
                    reactions[:5], drug_interactions, medications, risk_score
                )
            except Exception as e:
                print(f"Error generating explanation: {e}")
                explanation = f"Analysis completed with final decision: {final_decision}. Please consult healthcare provider for detailed advice."

            # Step 9: Get knowledge graph data
            try:
                knowledge_graph = self.knowledge_graph_agent.get_graph_for_response(data.disease, medications)
            except Exception as e:
                print(f"Error getting knowledge graph: {e}")
                knowledge_graph = {"disease": None, "medications": [], "alternative_medications": []}

            return {
                "symptoms": symptoms,
                "verification_status": verification_status,
                "verification_details": verification_results,  # NEW: Detailed verification per medication
                "possible_reactions": reactions[:5],
                "risk_level": risk_level,
                "risk_score": risk_score,
                "final_decision": final_decision,
                "explanation": explanation,
                "drug_interactions": drug_interactions,
                "medications": medications,
                "knowledge_graph": knowledge_graph,
                "processing_status": "success"
            }

        except Exception as e:
            print(f"Critical error in orchestrator process: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")

            return {
                "error": "Processing failed",
                "message": "An unexpected error occurred during analysis. Please try again.",
                "final_decision": "ERROR",
                "processing_status": "failed"
            }
    
    def _generate_explanation(self, data: PatientData, verification_status: str, risk_level: str, final_decision: str, reactions: List[str], drug_interactions: List[Dict], medications: List[str], risk_score: Optional[Dict] = None) -> str:
        """
        ENHANCED CLINICAL ANALYSIS - Structured, patient-friendly response format
        Provides comprehensive yet clear analysis tailored to user inputs
        """
        if not groq_client:
            return self._generate_fallback_explanation(data, verification_status, risk_level, final_decision, reactions, drug_interactions, medications, risk_score)

        # Build structured patient profile
        patient_profile = self._build_patient_profile(data)

        # Get risk score insights
        risk_insights = ""
        if risk_score:
            score = risk_score.get('score', 0)
            category = risk_score.get('safety_category', 'UNKNOWN')
            risk_insights = f"Risk Score: {score}/100 ({category})"

        # Build medication analysis context
        medication_context = self._build_medication_context(medications, data.disease, verification_status)

        # Build interaction context
        interaction_context = self._build_interaction_context(drug_interactions)

        # Create the enhanced AI prompt for structured response
        prompt = f"""You are a compassionate, expert clinical pharmacist providing a comprehensive medication review.

PATIENT PROFILE:
{patient_profile}

PRESCRIBED MEDICATIONS: {', '.join(medications)}
DIAGNOSED CONDITION: {data.disease}
VERIFICATION STATUS: {verification_status}
FINAL DECISION: {final_decision}
{risk_insights}

{medication_context}

{interaction_context}

Provide a structured analysis in this exact format:

## 📋 CLINICAL ASSESSMENT

### 🎯 OVERALL RECOMMENDATION
[2-3 sentences summarizing if this prescription is appropriate, safe, and effective for this specific patient]

### 💊 MEDICATION ANALYSIS
[For each medication, analyze:]
- **Drug Name**: [Brief explanation of appropriateness for the condition]
- **Expected Benefits**: [What symptoms/improvements to expect]
- **Key Concerns**: [Any specific risks for this patient]

### ⚠️ SAFETY CONSIDERATIONS
[List 3-5 specific safety factors for this patient, including age/gender considerations]

### 💡 SUGGESTIONS FOR IMPROVEMENT
[2-4 actionable recommendations to optimize this prescription or suggest alternatives if needed]

### 📝 PATIENT COUNSELING
[3-5 specific instructions for the patient about how to take the medication safely]

### 🚨 WHEN TO SEEK HELP
[2-3 clear warning signs that require immediate medical attention]

Be specific to this patient's age, gender, condition, and medications. Use clear, non-technical language. Focus on what matters most for this individual case."""

        try:
            response = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                max_tokens=1200,
                temperature=0.4
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"AI explanation error: {e}")
            return self._generate_fallback_explanation(data, verification_status, risk_level, final_decision, reactions, drug_interactions, medications, risk_score)

    def _build_patient_profile(self, data: PatientData) -> str:
        """Build a structured patient profile for AI analysis"""
        profile_parts = []
        if data.age:
            profile_parts.append(f"Age: {data.age} years")
        if data.gender:
            profile_parts.append(f"Gender: {data.gender}")
        if data.symptoms:
            profile_parts.append(f"Symptoms: {', '.join(data.symptoms)}")
        if data.description:
            profile_parts.append(f"Description: {data.description}")

        return " | ".join(profile_parts) if profile_parts else "Limited patient information provided"

    def _build_medication_context(self, medications: List[str], disease: str, verification_status: str) -> str:
        """Build medication analysis context"""
        context = f"MEDICATION CONTEXT:\n"
        context += f"- Condition: {disease}\n"
        context += f"- Medications: {', '.join(medications)}\n"
        context += f"- Verification: {verification_status}\n"

        # Add specific guidance based on verification status
        if verification_status == "WARNING":
            context += "- CAUTION: These medications may not be the best choice for this condition\n"
        elif verification_status == "SAFE":
            context += "- CONFIRMED: These medications are appropriate for the diagnosed condition\n"

        return context

    def _build_interaction_context(self, drug_interactions: List[Dict]) -> str:
        """Build drug interaction context"""
        if not drug_interactions:
            return "DRUG INTERACTIONS: None detected"

        context = "DRUG INTERACTIONS DETECTED:\n"
        for interaction in drug_interactions[:3]:  # Limit to top 3
            severity = interaction.get('severity', 'UNKNOWN')
            context += f"- {interaction['drug1']} + {interaction['drug2']}: {severity} severity - {interaction['description'][:100]}...\n"

        return context

    def _generate_fallback_explanation(self, data: PatientData, verification_status: str, risk_level: str, final_decision: str, reactions: List[str], drug_interactions: List[Dict], medications: List[str], risk_score: Optional[Dict] = None) -> str:
        """Fallback explanation when AI is unavailable"""
        explanation = "## 📋 CLINICAL ASSESSMENT\n\n"

        # Overall recommendation
        explanation += "### 🎯 OVERALL RECOMMENDATION\n"
        if final_decision == "SAFE":
            explanation += "This prescription appears appropriate for your condition. The medications selected are generally considered safe and effective.\n\n"
        elif final_decision == "CAUTION":
            explanation += "This prescription may be acceptable but requires careful monitoring. Some aspects need additional consideration.\n\n"
        else:
            explanation += "This prescription raises significant concerns and may not be the best choice for your condition.\n\n"

        # Medication analysis
        explanation += "### 💊 MEDICATION ANALYSIS\n"
        for med in medications:
            explanation += f"**{med.title()}**: {'Appropriate' if verification_status == 'SAFE' else 'Requires review'} for {data.disease}\n"

        # Safety considerations
        explanation += "\n### ⚠️ SAFETY CONSIDERATIONS\n"
        if data.age:
            if data.age < 12:
                explanation += f"- Pediatric patient ({data.age} years): Dosing adjustments may be needed\n"
            elif data.age > 65:
                explanation += f"- Elderly patient ({data.age} years): Increased monitoring for side effects\n"

        if drug_interactions:
            explanation += f"- Drug interactions detected: {len(drug_interactions)} interaction(s) require attention\n"

        # Suggestions
        explanation += "\n### 💡 SUGGESTIONS FOR IMPROVEMENT\n"
        explanation += "- Consult with your healthcare provider for personalized advice\n"
        explanation += "- Report any side effects promptly\n"
        if final_decision != "SAFE":
            explanation += "- Consider discussing alternative treatment options\n"

        return explanation


# -------------------------
# Initialize Orchestrator
# -------------------------
orchestrator = Orchestrator(db)

# -------------------------
# Photo Upload Endpoint
# -------------------------
@app.post("/scan-face")
async def scan_face(file: UploadFile = File(...), patient_name: str = None, patient_email: str = None):
    try:
        contents = await file.read()
        # Generate a unique ID based on the image content hash
        hasher = hashlib.sha256()
        hasher.update(contents)
        user_id = hasher.hexdigest()[:16] # Use first 16 chars for a shorter ID

        # Check for duplicate patient name or email
        if patient_name:
            # Build query based on whether email is provided
            if patient_email:
                existing_patient = db.patients.find_one({
                    "$or": [
                        {"patient_name": {"$regex": patient_name, "$options": "i"}},
                        {"patient_email": patient_email}
                    ]
                })
            else:
                existing_patient = db.patients.find_one({
                    "patient_name": {"$regex": patient_name, "$options": "i"}
                })

            if existing_patient:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "type": "duplicate_patient",
                        "message": f"Patient already exists with name '{existing_patient['patient_name']}' or email. Registration date: {existing_patient.get('created_at', 'Unknown')}"
                    }
                )

        # Store patient info in database if name provided
        if patient_name:
            patient_data = {
                "patient_name": patient_name,
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat(),
                "total_consultations": 0,
                "last_diagnosis": None,
                "risk_level": None
            }
            if patient_email:
                patient_data["patient_email"] = patient_email

            db.patients.insert_one(patient_data)

            # Send email notification (if email provided)
            if patient_email and groq_client:
                try:
                    # Send notification email
                    send_registration_email(patient_email, patient_name, user_id)
                except Exception as email_error:
                    print(f"Failed to send email: {email_error}")

        return {"user_id": user_id, "patient_name": patient_name, "patient_email": patient_email}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process image: {str(e)}")

@app.post("/upload-photo")
async def upload_photo(file: UploadFile = File(...)):
    if not groq_client:
        raise HTTPException(status_code=500, detail="Groq API client is not configured. Please set GROQ_API_KEY.")

    try:
        contents = await file.read()
        base64_image = base64.b64encode(contents).decode("utf-8")

        image_url = f"data:{file.content_type};base64,{base64_image}"

        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analyze the medical condition in this image. Describe the visual symptoms in detail (e.g., color, shape, texture of any visible condition like a rash or swelling). Based on these visual cues, create a comprehensive patient description that includes what they might be suffering from. For example: 'The patient presents with a red, bumpy rash on their forearm, which could be indicative of contact dermatitis or an allergic reaction.'",
                        },
                        {
                            "type": "image_url",
                            "image_url": { "url": image_url },
                        },
                    ],
                }
            ],
            model="meta-llama/llama-4-scout-17b-16e-instruct",
        )

        description = chat_completion.choices[0].message.content
        return {"description": description}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze image: {str(e)}")

# -------------------------
# FastAPI Endpoint with Enhanced Validation
# -------------------------
@app.post("/check-prescription")
def check_prescription(patient_data: PatientData):
    """Enhanced prescription checking with comprehensive validation and error handling"""
    try:
        # Input validation
        validation_errors = []

        if not patient_data.disease or not patient_data.disease.strip():
            validation_errors.append("Disease/condition is required")

        if not patient_data.medication or not patient_data.medication.strip():
            validation_errors.append("Medication is required")

        if patient_data.age is not None and (patient_data.age < 0 or patient_data.age > 150):
            validation_errors.append("Age must be between 0 and 150 years")

        if patient_data.gender and patient_data.gender.lower() not in ['male', 'female', 'other', 'm', 'f', 'o']:
            validation_errors.append("Gender must be 'male', 'female', or 'other'")

        if validation_errors:
            raise HTTPException(
                status_code=400,
                detail={
                    "type": "validation_error",
                    "message": "Input validation failed",
                    "errors": validation_errors
                }
            )

        # Process the request
        result = orchestrator.process(patient_data)

        # Add metadata to response
        result["metadata"] = {
            "processed_at": datetime.utcnow().isoformat(),
            "api_version": "2.0",
            "input_validation": "passed",
            "processing_time_seconds": None  # Could be added with timing
        }

        return result

    except HTTPException:
        raise
    except Exception as e:
        # Log the error for debugging
        print(f"Prescription check error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

        raise HTTPException(
            status_code=500,
            detail={
                "type": "processing_error",
                "message": "An error occurred while processing your request. Please try again.",
                "error_id": str(datetime.utcnow().timestamp())
            }
        )

# -------------------------
# NEW: Symptom Prediction Endpoint
# -------------------------
@app.post("/predict-disease")
def predict_disease(symptoms: List[str]):
    """Predict possible diseases from symptoms."""
    predictions = orchestrator.symptom_agent.predict_diseases(symptoms)
    return {"predictions": predictions}

# -------------------------
# NEW: Patient Timeline Endpoint (Save Analysis)
# -------------------------
@app.post("/save-analysis")
def save_analysis(request: SaveAnalysisRequest):
    """Save analysis to patient timeline in MongoDB and update patient stats."""
    try:
        analysis_record = {
            "id": str(datetime.utcnow().timestamp()),
            "date": datetime.utcnow().isoformat(),
            "disease": request.disease,
            "medication": request.medication,
            "final_decision": request.final_decision,
            "risk_level": request.risk_level or "UNKNOWN",
            "risk_score": request.risk_score,
            "explanation": request.explanation or "",
            "drug_interactions": request.drug_interactions or [],
            "session_id": request.session_id or ""  # Add session_id
        }

        # Save to patient_reports collection
        db.patient_reports.insert_one({
            "user_email": request.user_email,
            **analysis_record
        })

        # Update patient stats in patients collection (analytics still sum up ALL sessions)
        db.patients.update_one(
            {"patient_name": request.user_email},
            {
                "$inc": {"total_consultations": 1},
                "$set": {
                    "last_diagnosis": request.disease,
                    "last_consultation_date": datetime.utcnow().isoformat(),
                    "last_risk_level": request.risk_level or "UNKNOWN"
                }
            },
            upsert=False
        )

        # Update session consultation count if session_id provided
        if request.session_id:
            db.sessions.update_one(
                {"session_id": request.session_id},
                {"$inc": {"consultation_count": 1}}
            )

        return {"message": "Analysis saved successfully", "analysis": analysis_record}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save analysis: {str(e)}")

# -------------------------
# NEW: Get Patient Timeline Endpoint
# -------------------------
@app.get("/patient-timeline/{user_email}")
def get_patient_timeline(user_email: str, session_id: Optional[str] = None):
    """Get patient's analysis history."""
    try:
        # Build query - filter by session_id if provided
        query = {"user_email": {"$regex": user_email, "$options": "i"}}
        if session_id:
            query["session_id"] = session_id

        analyses_cursor = db.patient_reports.find(query).sort("date", -1).limit(50)

        # Convert to JSON-serializable format
        analyses = []
        for analysis in analyses_cursor:
            analysis_dict = {
                "id": str(analysis["_id"]),  # Convert ObjectId to string
                "date": analysis.get("date", ""),
                "disease": analysis.get("disease", ""),
                "medication": analysis.get("medication", ""),
                "final_decision": analysis.get("final_decision", ""),
                "risk_level": analysis.get("risk_level", "UNKNOWN"),
                "risk_score": analysis.get("risk_score"),
                "explanation": analysis.get("explanation", ""),
                "drug_interactions": analysis.get("drug_interactions", []),
                "session_id": analysis.get("session_id", "")
            }
            analyses.append(analysis_dict)

        return {"analyses": analyses}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get timeline: {str(e)}")

# -------------------------
# NEW: Session Management Endpoints
# -------------------------
@app.post("/create-session")
def create_session(request: SessionRequest):
    """Create a new consultation session for a patient."""
    try:
        session_id = f"session_{datetime.utcnow().timestamp()}"

        session_record = {
            "session_id": session_id,
            "patient_name": request.patient_name,
            "patient_email": request.patient_email,
            "session_notes": request.session_notes or "",
            "created_at": datetime.utcnow().isoformat(),
            "consultation_count": 0,
            "status": "active"
        }

        # Save session to database
        db.sessions.insert_one(session_record)

        return {
            "message": "Session created successfully",
            "session_id": session_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")

@app.get("/patient-sessions/{patient_name}")
def get_patient_sessions(patient_name: str):
    """Get all sessions for a patient."""
    try:
        sessions_cursor = db.sessions.find({
            "$or": [
                {"patient_name": {"$regex": patient_name, "$options": "i"}},
                {"patient_email": {"$regex": patient_name, "$options": "i"}}
            ]
        }, {
            "_id": 0  # Exclude MongoDB _id
        }).sort("created_at", -1)

        sessions = []
        for session in sessions_cursor:
            # Get consultation count for this session
            consultation_count = db.patient_reports.count_documents({
                "user_email": {"$regex": patient_name, "$options": "i"},
                "session_id": session.get("session_id", "")
            })

            session_dict = {
                "session_id": session.get("session_id", ""),
                "created_at": session.get("created_at", ""),
                "session_notes": session.get("session_notes", ""),
                "consultation_count": consultation_count,
                "status": session.get("status", "active")
            }
            sessions.append(session_dict)

        return {"sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sessions: {str(e)}")

@app.get("/active-session/{patient_name}")
def get_active_session(patient_name: str):
    """Get the most recent active session for a patient."""
    try:
        session = db.sessions.find_one({
            "$or": [
                {"patient_name": {"$regex": patient_name, "$options": "i"}},
                {"patient_email": {"$regex": patient_name, "$options": "i"}}
            ],
            "status": "active"
        }, {
            "_id": 0  # Exclude MongoDB _id
        }, sort=[("created_at", -1)])

        if not session:
            return {"session_id": None, "message": "No active session found"}

        return {
            "session_id": session.get("session_id", ""),
            "created_at": session.get("created_at", ""),
            "session_notes": session.get("session_notes", "")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get active session: {str(e)}")

@app.post("/close-session/{session_id}")
def close_session(session_id: str):
    """Close a session (mark as inactive)."""
    try:
        result = db.sessions.update_one(
            {"session_id": session_id},
            {"$set": {"status": "closed", "closed_at": datetime.utcnow().isoformat()}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"message": "Session closed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to close session: {str(e)}")


# -------------------------
# NEW: Admin Endpoints (Doctor Panel)
# -------------------------

async def verify_doctor_role(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Verify that the current user is a doctor."""
    if current_user.get("role") != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only doctors can access this resource."
        )
    return current_user

@app.get("/api/admin/patients")
async def get_all_patients(
    current_user: Dict[str, Any] = Depends(verify_doctor_role),
    page: int = 1,
    per_page: int = 5
):
    """
    Get all patients registered in the system (from patient_reports collection).
    Only accessible to doctors.
    Returns: user_email, id, date, disease, medication, final_decision
    Supports pagination (default: 5 patients per page).
    """
    try:
        # Get total count of unique patients
        total_docs = db.patient_reports.count_documents({})
        
        # Get total count of unique patients
        unique_emails = db.patient_reports.distinct("user_email")
        total_count = len(unique_emails)
        
        # Calculate skip for pagination
        skip = (page - 1) * per_page
        
        # Get unique patients with their latest report using aggregation
        pipeline = [
            {
                "$sort": {"date": -1}
            },
            {
                "$group": {
                    "_id": "$user_email",
                    "latest_report": {"$first": "$$ROOT"}
                }
            },
            {
                "$sort": {"latest_report.date": -1}
            },
            {
                "$skip": skip
            },
            {
                "$limit": per_page
            }
        ]

        patients_aggregated = list(db.patient_reports.aggregate(pipeline))

        patients = []
        for patient_doc in patients_aggregated:
            latest = patient_doc.get("latest_report", {})
            patients.append({
                "user_email": latest.get("user_email", ""),
                "id": str(latest.get("_id", "")),
                "date": latest.get("date", ""),
                "disease": latest.get("disease", ""),
                "medication": latest.get("medication", ""),
                "final_decision": latest.get("final_decision", "")
            })
        
        return {
            "patients": patients,
            "total_count": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": (total_count + per_page - 1) // per_page
        }
    except Exception as e:
        print(f"Error fetching patients: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch patients: {str(e)}")

@app.get("/api/admin/patient/{patient_email}/details")
async def get_patient_details(patient_email: str, current_user: Dict[str, Any] = Depends(verify_doctor_role)):
    """
    Get detailed information for a specific patient including all consultations.
    Only accessible to doctors.
    Data is fetched from patient_reports collection.
    """
    try:
        # Get all consultations/reports for this patient from patient_reports
        reports_cursor = db.patient_reports.find({
            "user_email": {"$regex": f"^{patient_email}$", "$options": "i"}
        }).sort("date", -1)

        consultations = []
        patient_email_found = ""
        for report in reports_cursor:
            if not patient_email_found:
                patient_email_found = report.get("user_email", "")
            consultations.append({
                "id": str(report.get("_id", "")),
                "date": report.get("date", ""),
                "disease": report.get("disease", ""),
                "medication": report.get("medication", ""),
                "final_decision": report.get("final_decision", ""),
                "risk_level": report.get("risk_level", ""),
                "risk_score": report.get("risk_score"),
                "explanation": report.get("explanation", ""),
                "drug_interactions": report.get("drug_interactions", [])
            })

        if len(consultations) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Patient '{patient_email}' not found"
            )

        return {
            "patient_info": {
                "patient_email": patient_email_found,
                "patient_id": str(consultations[0]["id"]),
                "created_at": consultations[-1].get("date", "") if consultations else "",
                "total_consultations": len(consultations),
                "last_diagnosis": consultations[0].get("disease", ""),
                "last_risk_level": consultations[0].get("risk_level", "")
            },
            "consultations": consultations,
            "total_records": len(consultations)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching patient details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch patient details: {str(e)}")

@app.delete("/api/admin/patient/{patient_email}")
async def delete_patient(patient_email: str, current_user: Dict[str, Any] = Depends(verify_doctor_role)):
    """
    Delete all data for a specific patient.
    Only accessible to doctors.
    Deletes from patient_reports collection and users collection.
    """
    try:
        # Check if patient exists in patient_reports
        patient_report = db.patient_reports.find_one({
            "user_email": {"$regex": f"^{patient_email}$", "$options": "i"}
        })

        if not patient_report:
            raise HTTPException(
                status_code=404,
                detail=f"Patient '{patient_email}' not found"
            )

        # Delete from users collection (patient users only)
        result_users = db.users.delete_many({
            "email": {"$regex": f"^{patient_email}$", "$options": "i"},
            "role": "patient"
        })

        # Delete from patient_reports collection by email
        result_reports = db.patient_reports.delete_many({
            "user_email": {"$regex": f"^{patient_email}$", "$options": "i"}
        })

        return {
            "message": f"Patient '{patient_email}' and all associated records have been deleted successfully",
            "deleted_user_records": result_users.deleted_count,
            "deleted_consultations": result_reports.deleted_count
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete patient: {str(e)}")


# -------------------------
# NEW: Get Patient Dashboard Endpoint
# -------------------------
@app.get("/patient-dashboard/{patient_name}")
def get_patient_dashboard(patient_name: str):
    """Get comprehensive patient dashboard data."""
    try:
        # Get patient info - search by patient_name (case-insensitive regex)
        patient = db.patients.find_one({"patient_name": {"$regex": patient_name, "$options": "i"}})

        # If not found by patient_name, try searching by patient_email
        if not patient:
            patient = db.patients.find_one({"patient_email": {"$regex": patient_name, "$options": "i"}})

        # If still not found, check if there are any reports with this user_email
        if not patient:
            # Check if there are reports with this email/patient name
            existing_reports = db.patient_reports.find_one({"user_email": {"$regex": patient_name, "$options": "i"}})
            if existing_reports:
                # Create a patient record on the fly
                patient = {
                    "patient_name": patient_name,
                    "patient_email": patient_name,
                    "user_id": "auto-generated",
                    "created_at": datetime.utcnow().isoformat(),
                    "total_consultations": 0,
                    "last_diagnosis": None,
                    "risk_level": None
                }

        if not patient:
            raise HTTPException(status_code=404, detail=f"Patient '{patient_name}' not found. Please register the patient first.")

        # Get recent consultations - search by user_email (case-insensitive)
        consultations_cursor = db.patient_reports.find(
            {"user_email": {"$regex": patient_name, "$options": "i"}}
        ).sort("date", -1).limit(10)

        # Convert consultations to JSON-serializable format
        consultations = []
        for consultation in consultations_cursor:
            consultation_dict = {
                "id": str(consultation["_id"]),
                "date": consultation.get("date", ""),
                "disease": consultation.get("disease", ""),
                "medication": consultation.get("medication", ""),
                "final_decision": consultation.get("final_decision", ""),
                "risk_level": consultation.get("risk_level", "UNKNOWN"),
                "risk_score": consultation.get("risk_score"),
                "explanation": consultation.get("explanation", ""),
                "drug_interactions": consultation.get("drug_interactions", [])
            }
            consultations.append(consultation_dict)

        # Calculate statistics
        total_consultations = len(consultations)

        # Get risk distribution
        risk_distribution = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0, "UNKNOWN": 0}
        for consultation in consultations:
            risk = consultation.get("risk_level", "UNKNOWN")
            if risk in risk_distribution:
                risk_distribution[risk] += 1

        # Determine overall risk level
        if risk_distribution.get("CRITICAL", 0) > 0:
            overall_risk = "CRITICAL"
        elif risk_distribution.get("HIGH", 0) > 0:
            overall_risk = "HIGH"
        elif risk_distribution.get("MEDIUM", 0) > 0:
            overall_risk = "MEDIUM"
        else:
            overall_risk = "LOW"

        # Get last diagnosis
        last_diagnosis = consultations[0].get("disease", "N/A") if consultations else "N/A"

        # Get decision distribution
        decision_distribution = {"SAFE": 0, "CAUTION": 0, "UNSAFE": 0}
        for consultation in consultations:
            decision = consultation.get("final_decision", "")
            if decision in decision_distribution:
                decision_distribution[decision] += 1

        safety_rate = round((decision_distribution.get("SAFE", 0) / total_consultations * 100) if total_consultations > 0 else 0, 1)

        return {
            "patient": {
                "name": patient.get("patient_name", patient_name),
                "email": patient.get("patient_email", patient_name),
                "user_id": str(patient.get("user_id", "unknown")),  # Ensure string
                "created_at": patient.get("created_at"),
                "total_consultations": patient.get("total_consultations", total_consultations),
                "last_diagnosis": patient.get("last_diagnosis", last_diagnosis),
                "risk_level": patient.get("risk_level", overall_risk)
            },
            "statistics": {
                "totalConsultations": total_consultations,
                "safetyRate": safety_rate,
                "riskDistribution": risk_distribution,
                "decisionDistribution": decision_distribution,
                "overallRiskLevel": overall_risk
            },
            "recentConsultations": consultations[:5]
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Dashboard Error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard: {str(e)}")

# -------------------------
# NEW: Generate PDF Report Endpoint
# -------------------------
@app.post("/generate-pdf")
def generate_pdf_report(request: PDFReportRequest):
    """Generate professional PDF report."""
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=colors.HexColor('#581c87'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#7e22ce'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        )

        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=8,
            alignment=TA_JUSTIFY,
            leading=14
        )

        # Title
        elements.append(Paragraph("🏥 Medical Prescription Analysis Report", title_style))
        elements.append(Spacer(1, 0.15*inch))

        # Patient Information Table with better word wrapping
        patient_info = [
            ["Patient Name:", request.patient_name],
            ["Age:", str(request.age) if request.age else "N/A"],
            ["Gender:", request.gender or "N/A"],
            ["Report Date:", datetime.utcnow().strftime("%B %d, %Y")]
        ]
        patient_table = Table(patient_info, colWidths=[1.8*inch, 4.2*inch])
        patient_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#fefce8')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('WORDWRAP', (0, 0), (-1, -1), 1)
        ]))
        elements.append(patient_table)
        elements.append(Spacer(1, 0.2*inch))

        # Clinical Summary
        elements.append(Paragraph("Clinical Summary", heading_style))
        elements.append(Paragraph(f"<b>Diagnosis/Condition:</b> {request.disease}", normal_style))
        elements.append(Paragraph(f"<b>Prescribed Medications:</b> {', '.join(request.medications)}", normal_style))
        elements.append(Spacer(1, 0.2*inch))

        # Risk Assessment
        elements.append(Paragraph("Risk Assessment", heading_style))
        risk_color = '#27ae60' if request.final_decision == "SAFE" else ('#f39c12' if request.final_decision == "CAUTION" else '#e74c3c')
        elements.append(Paragraph(f"<b>Overall Assessment:</b> <font color='{risk_color}' size='14'><b>{request.final_decision}</b></font>", normal_style))
        elements.append(Paragraph(f"<b>Risk Level:</b> {request.risk_level}", normal_style))

        if request.risk_score:
            score = request.risk_score.get('score', 0)
            score_color = '#27ae60' if score >= 65 else ('#f39c12' if score >= 40 else '#e74c3c')
            elements.append(Paragraph(f"<b>Personal Risk Score:</b> <font color='{score_color}'><b>{score}/100</b></font>", normal_style))
            if request.risk_score.get('level'):
                elements.append(Paragraph(f"<b>Risk Category:</b> {request.risk_score.get('level')}", normal_style))
        elements.append(Spacer(1, 0.2*inch))

        # AI Analysis with colored warning if not appropriate
        if request.explanation:
            elements.append(Paragraph("AI Clinical Analysis", heading_style))
            # Check if explanation contains warning keywords
            explanation_lower = request.explanation.lower()
            is_warning = any(word in explanation_lower for word in ['not appropriate', 'warning', 'unsafe', 'review', 'caution', 'avoid', 'contraindicated'])
            if is_warning:
                warning_style = ParagraphStyle(
                    'WarningStyle',
                    parent=normal_style,
                    textColor=colors.HexColor('#e74c3c'),
                    backColor=colors.HexColor('#fadbd8'),
                    borderWidth=1,
                    borderColor=colors.HexColor('#e74c3c'),
                    borderPadding=10
                )
                elements.append(Paragraph(request.explanation.replace('\n', '<br/>'), warning_style))
            else:
                elements.append(Paragraph(request.explanation.replace('\n', '<br/>'), normal_style))
            elements.append(Spacer(1, 0.2*inch))

        # Drug Interactions with better word wrapping
        if request.drug_interactions and len(request.drug_interactions) > 0:
            elements.append(Paragraph("⚠️ Drug Interactions Detected", heading_style))
            interaction_data = [["Drug 1", "Drug 2", "Severity", "Description"]]
            for interaction in request.drug_interactions:
                severity_color = colors.red if interaction['severity'] == 'HIGH' else (colors.orange if interaction['severity'] == 'MEDIUM' else colors.yellow)
                interaction_data.append([
                    interaction['drug1'],
                    interaction['drug2'],
                    interaction['severity'],
                    interaction['description']
                ])

            interaction_table = Table(interaction_data, colWidths=[1.3*inch, 1.3*inch, 0.9*inch, 3*inch])
            interaction_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#9333ea')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('WORDWRAP', (0, 0), (-1, -1), 1),
                ('BACKGROUND', (2, 1), (2, -1), severity_color),
                ('TEXTCOLOR', (2, 1), (2, -1), colors.white)
            ]))
            elements.append(interaction_table)
            elements.append(Spacer(1, 0.2*inch))

        # Possible Reactions
        if request.possible_reactions and len(request.possible_reactions) > 0:
            elements.append(Paragraph("Potential Adverse Reactions", heading_style))
            for reaction in request.possible_reactions[:10]:
                elements.append(Paragraph(f"• {reaction}", normal_style))
            elements.append(Spacer(1, 0.2*inch))

        # Alternative Medication Suggestions (if CAUTION or UNSAFE)
        if request.final_decision in ["CAUTION", "UNSAFE"]:
            # Get alternative medications from knowledge graph
            try:
                disease_info = orchestrator.knowledge_graph_agent.get_disease_info(request.disease)
                if disease_info and disease_info.get('medications'):
                    current_meds = [m.lower() for m in request.medications]
                    
                    all_alternatives = disease_info['medications']
                    
                    # Filter out current medications and sort by score
                    alternatives = [
                        alt for alt in all_alternatives 
                        if alt['name'].lower() not in current_meds
                    ]
                    alternatives.sort(key=lambda x: x.get('suggestion_score', 0), reverse=True)
                    alternatives = alternatives[:5]

                    if alternatives:
                        elements.append(Paragraph("💡 Suggested Alternative Medications", heading_style))
                        alt_list_style = ParagraphStyle(
                            'AltListStyle',
                            parent=normal_style,
                            textColor=colors.HexColor('#27ae60'),
                            leftIndent=20,
                            spaceAfter=4
                        )
                        elements.append(Paragraph("Consider discussing these alternatives:", normal_style))
                        elements.append(Spacer(1, 0.1*inch))
                        for alt_med in alternatives:
                            elements.append(Paragraph(f"• <b>{alt_med['name']}</b> (Suggestion Score: {alt_med['suggestion_score']}/5)", alt_list_style))
                        elements.append(Spacer(1, 0.15*inch))
            except Exception:
                pass  # Skip if knowledge graph lookup fails

        # Footer
        elements.append(Spacer(1, 0.5*inch))
        footer_text = """
        <para alignment="center">
        <font color="grey" size="8">
        This report is generated by AI for informational purposes only.<br/>
        Always consult with a qualified healthcare professional for medical advice.
        </font>
        </para>
        """
        elements.append(Paragraph(footer_text, normal_style))

        # Build PDF
        doc.build(elements)
        buffer.seek(0)

        filename = f"medical_report_{request.patient_name.replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
        
        return Response(
            content=buffer.getvalue(),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        import traceback
        print(f"PDF Generation Error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")

# -------------------------
# NEW: Get Knowledge Graph Endpoint
# -------------------------
@app.get("/knowledge-graph")
def get_knowledge_graph(disease: Optional[str] = None, medication: Optional[str] = None):
    """Get medical knowledge graph data."""
    try:
        graph_data = orchestrator.knowledge_graph_agent.graph
        return {"knowledge_graph": graph_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get knowledge graph: {str(e)}")

# -------------------------
# NEW: Medical Analytics Endpoint
# -------------------------
@app.get("/medical-analytics/{user_email}")
def get_medical_analytics(user_email: str, range: str = "24h"):
    """Get medical analytics data for medications and diseases trends."""
    try:
        from datetime import timedelta

        # Calculate date range
        now = datetime.utcnow()
        if range == "24h":
            start_date = now - timedelta(hours=24)
            time_format = "%Y-%m-%d %H:00"  # Hourly buckets
        elif range == "1month":
            start_date = now - timedelta(days=30)
            time_format = "%Y-%m-%d"  # Daily buckets
        elif range == "1year":
            start_date = now - timedelta(days=365)
            time_format = "%Y-%m"  # Monthly buckets
        else:
            start_date = now - timedelta(hours=24)
            time_format = "%Y-%m-%d %H:00"

        # Get all analyses for the user - case-insensitive regex search
        analyses_cursor = db.patient_reports.find({
            "user_email": {"$regex": user_email, "$options": "i"}
        }).sort("date", 1)

        analyses = []
        for analysis in analyses_cursor:
            try:
                # Parse and filter by date range in Python for better compatibility
                analysis_date_str = analysis.get("date", "")
                if isinstance(analysis_date_str, str):
                    analysis_date = datetime.fromisoformat(analysis_date_str.replace("Z", "+00:00").split("+")[0])
                else:
                    analysis_date = analysis_date_str

                if analysis_date >= start_date:
                    analyses.append(analysis)
            except Exception:
                # Include analyses with unparseable dates
                analyses.append(analysis)

        if not analyses:
            return {
                "trendData": [],
                "topMedications": [],
                "topDiseases": [],
                "summary": {
                    "totalAnalyses": 0,
                    "uniqueMedications": 0,
                    "uniqueDiseases": 0,
                    "safetyRate": 0,
                    "decisionDistribution": {}
                }
            }

        # Process trend data
        trend_map = {}
        medication_counts = {}
        disease_counts = {}
        decision_counts = {"SAFE": 0, "CAUTION": 0, "UNSAFE": 0}

        for analysis in analyses:
            # Parse date and bucket it
            try:
                analysis_date_str = analysis.get("date", "")
                if isinstance(analysis_date_str, str):
                    analysis_date = datetime.fromisoformat(analysis_date_str.replace("Z", "+00:00").split("+")[0])
                else:
                    analysis_date = analysis_date_str
                time_bucket = analysis_date.strftime(time_format)
            except Exception:
                time_bucket = "Unknown"

            if time_bucket not in trend_map:
                trend_map[time_bucket] = {
                    "timestamp": time_bucket,
                    "medications": 0,
                    "diseases": 0,
                    "consultations": 0,
                    "medication_names": [],
                    "disease_names": []
                }

            # Count consultations
            trend_map[time_bucket]["consultations"] += 1

            # Count medications (comma-separated)
            meds = [m.strip() for m in analysis.get("medication", "").split(",") if m.strip()]
            trend_map[time_bucket]["medications"] += len(meds)
            trend_map[time_bucket]["medication_names"].extend(meds)
            for med in meds:
                medication_counts[med] = medication_counts.get(med, 0) + 1

            # Count diseases
            disease = analysis.get("disease", "").strip()
            if disease:
                trend_map[time_bucket]["diseases"] += 1
                trend_map[time_bucket]["disease_names"].append(disease)
                disease_counts[disease] = disease_counts.get(disease, 0) + 1

            # Count decisions
            decision = analysis.get("final_decision", "")
            if decision in decision_counts:
                decision_counts[decision] += 1

        # Convert trend map to sorted list
        trend_data = sorted(trend_map.values(), key=lambda x: x["timestamp"] if x["timestamp"] != "Unknown" else "")

        # Make names unique
        for data_point in trend_data:
            data_point["medication_names"] = list(set(data_point["medication_names"]))
            data_point["disease_names"] = list(set(data_point["disease_names"]))

        # Get top medications and diseases
        top_medications = sorted(
            [{"medication": med, "count": count} for med, count in medication_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:10]

        top_diseases = sorted(
            [{"disease": disease, "count": count} for disease, count in disease_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:10]

        # Calculate summary statistics
        total_analyses = len(analyses)
        safe_count = decision_counts.get("SAFE", 0)
        safety_rate = round((safe_count / total_analyses * 100) if total_analyses > 0 else 0, 1)

        return {
            "trendData": trend_data,
            "topMedications": top_medications,
            "topDiseases": top_diseases,
            "summary": {
                "totalAnalyses": total_analyses,
                "uniqueMedications": len(medication_counts),
                "uniqueDiseases": len(disease_counts),
                "safetyRate": safety_rate,
                "decisionDistribution": decision_counts
            }
        }
    except Exception as e:
        import traceback
        print(f"Analytics Error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")

# -------------------------
# AI Chatbot Endpoint - Enhanced Doctor-like Consultation
# -------------------------
@app.post("/chatbot-analyze")
async def chatbot_analyze(request: ChatbotRequest):
    """AI-powered symptom analysis chatbot with doctor-like consultation."""
    try:
        if not groq_client:
            return {
                "response": "Thank you for sharing your symptoms. I'm here to help you understand what might be happening and guide you on the best next steps. Based on what you've described, I recommend consulting a healthcare professional for proper evaluation and personalized care.",
                "severity": "MEDIUM",
                "recommendations": [
                    "Schedule an appointment with your doctor or healthcare provider",
                    "Monitor your symptoms and note any changes or patterns",
                    "Rest adequately and stay well-hydrated",
                    "Avoid self-medication without professional guidance"
                ],
                "explanation": "I'm listening to your concerns and want to ensure you receive the best care possible.",
                "body_explanation": "When you experience these symptoms, your body is responding to something that needs attention. The immune system may be activated, or there could be an imbalance that needs evaluation. A healthcare provider can help determine the exact cause through proper examination.",
                "next_steps": "Please consult a healthcare provider for a thorough evaluation.",
                "red_flags": [
                    "Symptoms worsen suddenly or severely",
                    "Difficulty breathing or chest pain develops",
                    "High fever that doesn't respond to medication",
                    "Confusion, severe headache, or neck stiffness"
                ],
                "possible_causes": []
            }

        # Enhanced prompt for doctor-like, empathetic, personalized consultation
        prompt = f"""You are a compassionate, experienced medical doctor conducting a real-time consultation with a patient. Your goal is to provide thoughtful, personalized, and medically sound guidance while making the patient feel heard, understood, and cared for.

PATIENT'S SYMPTOMS: "{request.symptoms}"

Your response should feel like a real doctor-patient conversation, not robotic or generic. Adapt your tone and advice specifically to what the patient has shared. Reference their exact words to show you're truly listening.

Provide your response in this EXACT JSON format:
{{
    "response": "A warm, empathetic opening (2-4 sentences) that directly acknowledges the patient's specific concerns. Start with phrases like 'I hear that you're experiencing...' or 'I understand you're worried about...' Then explain in simple terms what might be happening. Make the patient feel genuinely heard and cared for.",
    "severity": "LOW, MEDIUM, HIGH, or CRITICAL - based on symptom urgency, potential red flags, and clinical significance",
    "recommendations": [
        "4-6 specific, actionable recommendations tailored to THEIR symptoms",
        "Include home care advice that is evidence-based",
        "Lifestyle modifications specific to their situation",
        "Over-the-counter options if appropriate (mention specific medications)",
        "When and how to seek professional medical care with timelines",
        "Precautionary measures specific to their presentation"
    ],
    "explanation": "A clear, reassuring explanation of what's likely happening in their body (3-5 sentences). Use analogies and simple language. For example: 'Think of your immune system like an army - when it detects an invader like a virus, it releases chemicals that cause fever to create an environment where the invader can't survive.' Make this educational and calming.",
    "body_explanation": "A deeper physiological explanation (2-3 sentences) describing the biological mechanisms. For example: 'When you have [symptom], your body is releasing inflammatory chemicals called cytokines. These trigger your immune cells to respond, which can cause feelings of fatigue and achiness. This is actually a sign your body is fighting effectively.'",
    "next_steps": "Clear, specific, actionable guidance with exact timelines. For example: '1) Rest for the next 24-48 hours and monitor your temperature every 6 hours. 2) If your fever exceeds 102°F or doesn't improve in 2 days, see your doctor. 3) If you develop [specific warning sign], seek urgent care immediately. 4) Consider scheduling a telehealth visit tomorrow if symptoms persist.'",
    "red_flags": [
        "List 3-5 specific warning signs that would require immediate medical attention",
        "Make these specific to THEIR symptoms, not generic",
        "Include both emergency signs and urgent-but-not-emergency signs",
        "Explain briefly why each is concerning"
    ],
    "possible_causes": [
        "List 3-5 possible conditions that could explain their symptoms",
        "Order from most likely to least likely",
        "Use plain language with brief explanations, e.g., 'Viral infection (like a common cold or flu) - this is the most common cause and usually resolves on its own'",
        "Include both common benign causes and more serious possibilities to be aware of"
    ]
}}

CRITICAL GUIDELINES FOR YOUR RESPONSE:

1. EMPATHY FIRST (Most Important): 
   - Start by genuinely acknowledging their discomfort: "I can hear that you're going through a difficult time..." or "I understand why you're concerned about these symptoms..."
   - Validate their feelings: "It's completely normal to feel worried when experiencing..."
   - Show you're present with them: "Let me help you understand what's happening..."

2. DEEP PERSONALIZATION:
   - Reference their EXACT words: "You mentioned [specific symptom they said]..." or "The fact that you're experiencing [X] specifically tells me..."
   - Tailor every recommendation to THEIR situation
   - Avoid generic, textbook responses - this should feel like a conversation about THEM

3. SIMPLE, CLEAR LANGUAGE:
   - Explain medical concepts like you're talking to a friend, not a colleague
   - If you must use a medical term, immediately explain it: "This is called 'post-nasal drip' - that's when mucus from your nose drips down the back of your throat, causing irritation"
   - Use analogies and metaphors to make complex concepts relatable

4. CLINICAL REASONING (Think Like a Doctor):
   - Consider symptom duration if mentioned: "Since you said this started 3 days ago..."
   - Assess severity and impact: "Given that this is affecting your ability to sleep/work..."
   - Note associated symptoms: "The combination of fever AND body aches suggests..."
   - Weigh common vs. rare: "Most likely this is [common condition], but we should watch for..."
   - Identify red flags specific to their presentation

5. BALANCED REASSURANCE:
   - Be honest without being alarming: "While this is uncomfortable, it's usually not serious..."
   - Acknowledge uncertainty appropriately: "I can't examine you directly, but based on what you've told me..."
   - Provide realistic expectations: "Most people start feeling better within 3-5 days, but..."
   - Know when to recommend in-person care

6. ACTIONABLE, SPECIFIC ADVICE:
   - Give concrete home remedies: "Try gargling with warm salt water (1/2 teaspoon salt in a cup of warm water) 3-4 times daily"
   - Mention OTC options with dosing: "Acetaminophen 500mg every 6 hours as needed can help with fever and aches"
   - Lifestyle specifics: "Stay hydrated - aim for at least 8 glasses of water today"
   - Clear timelines: "If you don't see improvement in 48 hours, contact your doctor"

7. COMPREHENSIVE RED FLAGS:
   - Always include 3-5 warning signs specific to their symptoms
   - Explain WHY each is concerning: "Chest pain is concerning because it could indicate..."
   - Differentiate emergency (call 911) vs. urgent care vs. schedule appointment

8. AVOID ABSOLUTE DIAGNOSES:
   - Use probabilistic language: "This sounds consistent with...", "The most likely possibility is...", "It's worth considering..."
   - Never say "You definitely have X" - say "Your symptoms suggest X could be the cause"

9. REAL-TIME CONVERSATION FEEL:
   - Make it sound like you're thinking about their case in the moment
   - Use conversational connectors: "Here's what I'm thinking...", "What stands out to me is..."
   - Reference previous parts of their message to show active listening

10. COMPREHENSIVE BUT ORGANIZED:
    - Provide substantial content - patients want to feel thoroughly heard
    - Use clear structure with distinct sections
    - Prioritize the most important information first
    - End with reassurance and a clear plan

11. CULTURAL SENSITIVITY:
    - Be respectful of different health beliefs
    - Acknowledge when home remedies might complement medical care
    - Use inclusive language

12. SAFETY FIRST:
    - When in doubt, recommend professional evaluation
    - Err on the side of caution with red flags
    - Remind them this is guidance, not a replacement for in-person care

Remember: The patient is trusting you with their health concerns. Make them feel heard, cared for, and empowered with knowledge and a clear action plan."""

        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            max_tokens=1200,  # Increased for comprehensive response
            temperature=0.7
        )

        # Parse the response
        ai_response = response.choices[0].message.content.strip()

        # Try to extract JSON from response
        try:
            # Remove markdown code blocks if present
            ai_response = ai_response.replace("```json", "").replace("```", "").strip()
            result = json.loads(ai_response)
        except Exception as json_error:
            print(f"JSON parsing error: {json_error}")
            # Fallback if JSON parsing fails - create structured response from raw text
            result = {
                "response": f"Thank you for sharing your symptoms. I hear your concerns about: {request.symptoms}. Let me provide some guidance based on what you've described.",
                "severity": "MEDIUM",
                "recommendations": [
                    "Monitor your symptoms closely and note any changes",
                    "Rest adequately and maintain good hydration",
                    "Consider scheduling an appointment with your healthcare provider",
                    "Avoid activities that worsen your symptoms",
                    "Use over-the-counter pain relievers like acetaminophen if needed for discomfort"
                ],
                "explanation": ai_response[:500] + "..." if len(ai_response) > 500 else ai_response,
                "body_explanation": "When you experience these symptoms, your body is responding to something that needs attention. The immune system may be activated, or there could be an imbalance that needs evaluation. A healthcare provider can help determine the exact cause through proper examination.",
                "next_steps": "Please consult with a healthcare professional for a proper evaluation tailored to your specific situation. If symptoms worsen before you can see a doctor, seek urgent care.",
                "red_flags": [
                    "Symptoms worsen significantly or suddenly - this could indicate a progressing condition",
                    "You develop difficulty breathing or chest pain - these could be signs of a serious complication",
                    "High fever (above 102°F/39°C) that doesn't respond to medication - may indicate severe infection",
                    "Any new concerning symptoms appear - especially confusion, severe pain, or inability to keep fluids down"
                ],
                "possible_causes": [
                    "Viral infection (like a common cold or flu) - most common cause, usually resolves on its own",
                    "Bacterial infection - may require antibiotics if symptoms persist",
                    "Inflammatory response - your body's natural healing process",
                    "Environmental factors - allergies or irritants could be contributing"
                ]
            }

        return result

    except Exception as e:
        print(f"Chatbot error: {str(e)}")
        return {
            "response": "Thank you for sharing your symptoms with me. I want to give you the best possible guidance, and I recommend consulting a healthcare professional who can evaluate you thoroughly and provide personalized care.",
            "severity": "MEDIUM",
            "recommendations": [
                "Contact your doctor or healthcare provider",
                "Visit an urgent care clinic if symptoms are bothersome",
                "Call emergency services (911) if you experience severe symptoms like chest pain, difficulty breathing, or sudden weakness",
                "Keep track of your symptoms to share with your provider",
                "Rest and stay hydrated while waiting for medical evaluation"
            ],
            "explanation": "Your health is important, and getting proper medical attention ensures you receive the right care for your specific situation.",
            "body_explanation": "When experiencing symptoms, your body is signaling that something needs attention. A healthcare provider can perform a thorough examination to understand what's happening and provide appropriate treatment.",
            "next_steps": "Please reach out to a healthcare provider today if your symptoms are concerning you. If symptoms are severe, don't wait - seek immediate medical attention.",
            "red_flags": [
                "Chest pain or pressure - could indicate heart or lung problems requiring immediate attention",
                "Difficulty breathing or shortness of breath - may signal a serious respiratory or cardiac issue",
                "Sudden severe headache or confusion - could be signs of neurological emergency",
                "High fever with stiff neck - may indicate meningitis or other serious infection",
                "Sudden weakness on one side of the body - could be a sign of stroke"
            ],
            "possible_causes": [
                "Various infections (viral or bacterial) - common causes of many symptoms",
                "Inflammatory conditions - body's response to injury or illness",
                "Chronic condition flare-up - if you have existing health conditions",
                "Environmental or allergic reactions - exposure to irritants or allergens"
            ]
        }


# -------------------------
# Health Check
# -------------------------
@app.get("/")
def home():
    return {"message": "Medical Prescription Checker API is running."}

# -------------------------
# Run Server with Details
# -------------------------
if __name__ == "__main__":
    import uvicorn
    # Run on localhost, port 8000 (use 0.0.0.0 for broader accessibility)
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)