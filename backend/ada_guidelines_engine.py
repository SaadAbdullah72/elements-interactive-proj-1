"""
ADA 2026 Clinical Decision Support Engine with Multi-Guideline Support

This module provides a deterministic wrapper around guideline content
to generate ADA-compliant prompts for the AI model. It enforces strict
traceability, zero-hallucination constraints, and a structured response
format so downstream consumers can rely on guideline-backed advice.

Design notes:
 - Store uploaded guidelines as text and track metadata (word/char counts)
 - Build a single system prompt that includes all active guideline sources
 - Validate AI outputs for required sections and hallucination indicators
"""

from typing import Dict, Any, Optional, List
import json
import os
from datetime import datetime

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None
    
try:
    import openpyxl
except ImportError:
    openpyxl = None


class PDFPageSearcher:
    """
    Splits local PDFs page-by-page, extracts text, and builds a lightweight keyword index.
    """
    def __init__(self):
        self.pages = []  # List of dicts: {"source": str, "page_num": int, "text": str, "keywords": set}
        
    def load_pdf(self, file_path: str, source_name: str):
        if not PdfReader:
            print("Warning: PdfReader is not installed. PDF search will not be active.")
            return
        if not os.path.exists(file_path):
            print(f"Warning: PDF file not found: {file_path}")
            return
        try:
            reader = PdfReader(file_path)
            for idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    # Extract keywords (lowercase, alphanumeric, length > 3)
                    words = set(
                        w.strip(",.?!()[]{}:;\"'").lower() 
                        for w in text.split() 
                        if w.strip(",.?!()[]{}:;\"'").isalnum() and len(w.strip(",.?!()[]{}:;\"'")) > 3
                    )
                    self.pages.append({
                        "source": source_name,
                        "page_num": idx + 1,
                        "text": text,
                        "keywords": words
                    })
            print(f"Loaded {len(reader.pages)} pages from {source_name}")
        except Exception as e:
            print(f"Error loading PDF {file_path}: {e}")
            
    def search(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        # Normalize query words
        query_words = set(
            w.strip(",.?!()[]{}:;\"'").lower() 
            for w in query.split() 
            if w.strip(",.?!()[]{}:;\"'").isalnum() and len(w.strip(",.?!()[]{}:;\"'")) > 3
        )
        if not query_words:
            return []
            
        scored_pages = []
        for p in self.pages:
            score = len(query_words.intersection(p["keywords"]))
            if score > 0:
                scored_pages.append((score, p))
                
        # Sort by score descending, then page number ascending
        scored_pages.sort(key=lambda x: (-x[0], x[1]["page_num"]))
        return [p for score, p in scored_pages[:limit]]


class ExcelCaseMatcher:
    """
    Parses Complete Sample Cases by Scenario.xlsx and searches for matching clinical scenarios.
    """
    def __init__(self):
        self.cases = []  # List of dicts
        
    def load_excel(self, file_path: str):
        if not openpyxl:
            print("Warning: openpyxl is not installed. Excel case matching will not be active.")
            return
        if not os.path.exists(file_path):
            print(f"Warning: Excel file not found: {file_path}")
            return
        try:
            wb = openpyxl.load_workbook(file_path)
            sheet = wb.active
            
            # Row 3 contains column headers
            headers = []
            for cell in sheet[3]:
                headers.append(cell.value)
                
            for row in sheet.iter_rows(min_row=4, values_only=True):
                if not row or row[0] is None:
                    continue
                # If row looks like section header or is invalid, skip
                if str(row[1]).lower().startswith('scenario') or str(row[0]).startswith('#'):
                    continue
                    
                case_dict = {}
                for idx, val in enumerate(row):
                    if idx < len(headers) and headers[idx]:
                        case_dict[headers[idx].lower().replace(' ', '_')] = val
                if case_dict.get('sample_case_id'):
                    self.cases.append(case_dict)
            print(f"Loaded {len(self.cases)} reference cases from Excel.")
        except Exception as e:
            print(f"Error loading Excel {file_path}: {e}")
            
    def find_relevant_cases(self, patient_data: Dict[str, Any], query: str, limit: int = 2) -> List[Dict[str, Any]]:
        # Collect search terms from patient parameters
        search_terms = []
        if patient_data.get("conditions"):
            search_terms.extend(patient_data["conditions"])
        if patient_data.get("risk_factors"):
            search_terms.extend(patient_data["risk_factors"])
        if patient_data.get("gender") and patient_data["gender"] != "Not specified":
            search_terms.append(patient_data["gender"])
        if patient_data.get("age"):
            search_terms.append(str(patient_data["age"]))
        if patient_data.get("disease") and patient_data["disease"] != "Not specified":
            search_terms.append(patient_data["disease"])
            
        search_terms.extend(query.split())
        
        query_words = set(
            w.strip(",.?!()[]{}:;\"'").lower() 
            for w in search_terms 
            if w.strip(",.?!()[]{}:;\"'").isalnum() and len(w.strip(",.?!()[]{}:;\"'")) > 3
        )
        if not query_words:
            return []
            
        scored_cases = []
        for c in self.cases:
            # Combine all text fields in the case to form standard search document
            case_text = f"{c.get('scenario', '')} {c.get('demographics', '')} {c.get('key_labs', '')} {c.get('current_meds', '')} {c.get('intervention', '')}"
            case_words = set(
                w.strip(",.?!()[]{}:;\"'").lower() 
                for w in case_text.split() 
                if w.strip(",.?!()[]{}:;\"'").isalnum() and len(w.strip(",.?!()[]{}:;\"'")) > 3
            )
            score = len(query_words.intersection(case_words))
            if score > 0:
                scored_cases.append((score, c))
                
        # Sort by score descending
        scored_cases.sort(key=lambda x: x[0], reverse=True)
        return [c for score, c in scored_cases[:limit]]


class ADAGuidelinesEngine:
    """
    Enforces strict ADA 2026 guideline compliance in AI responses.
    Supports multiple guideline PDFs for comprehensive clinical decision-making.
    Acts as a wrapper to ensure deterministic, guideline-driven outputs.
    """
    
    def __init__(self, guideline_content: Optional[str] = None):
        """
        Initialize the engine with optional guideline content.
        
        Args:
            guideline_content: Extracted PDF or text content of ADA guidelines
        """
        self.guideline_content = guideline_content or ""
        self.additional_guidelines: Dict[str, Dict[str, Any]] = {}
        self.guideline_sources: List[str] = []
        self.system_prompt_template = self._get_base_system_prompt()
        
        # Initialize searchers
        self.pdf_searcher = PDFPageSearcher()
        self.excel_matcher = ExcelCaseMatcher()
        
        # Load default guidelines if available
        self._load_local_data()
        
    def _load_local_data(self):
        paths_to_try = [
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            os.path.dirname(os.path.abspath(__file__)),
            os.getcwd()
        ]
        
        def find_file(filename):
            for p in paths_to_try:
                full_path = os.path.join(p, filename)
                if os.path.exists(full_path):
                    return full_path
            return None

        # Load PDFs
        pdf_files = {
            "14. Children and Adolescents": "14. Children and Adolescents.pdf",
            "15. Management of Diabetes in Pregnancy": "15. Management of Diabetes in Pregnancy.pdf",
            "16. Diabetes Care in the Hospital": "16. Diabetes Care in the Hospital.pdf"
        }
        for name, filename in pdf_files.items():
            path = find_file(filename)
            if path:
                self.pdf_searcher.load_pdf(path, name)
                
        # Load Excel Cases
        excel_filename = "Complete Sample Cases by Scenario.xlsx"
        excel_path = find_file(excel_filename)
        if excel_path:
            self.excel_matcher.load_excel(excel_path)
    
    def add_guideline_source(self, source_name: str, content: str, source_type: str = "guideline") -> Dict[str, Any]:
        """
        Add a new guideline source (can be ADA, other standards, best practices, etc.)
        
        Args:
            source_name: Name/identifier for the guideline (e.g., "ADA_2026", "WHO_Guidelines", "Clinical_Best_Practices")
            content: Extracted text from the PDF
            source_type: Type of guideline (e.g., "guideline", "standard", "protocol", "best_practice")
            
        Returns:
            Confirmation with source details
        """
        self.additional_guidelines[source_name] = {
            "content": content,
            "type": source_type,
            "added_at": datetime.utcnow().isoformat(),
            "word_count": len(content.split()),
            "char_count": len(content)
        }
        self.guideline_sources.append(source_name)
        
        return {
            "success": True,
            "source_name": source_name,
            "source_type": source_type,
            "word_count": len(content.split()),
            "message": f"Guideline source '{source_name}' added successfully"
        }
    
    def get_all_guideline_sources(self) -> Dict[str, Any]:
        """Get all loaded guideline sources with metadata"""
        all_sources = {}
        
        if self.guideline_content:
            all_sources["ADA_PRIMARY"] = {
                "type": "primary",
                "content_length": len(self.guideline_content),
                "word_count": len(self.guideline_content.split()),
                "status": "active"
            }
        
        for source_name, source_data in self.additional_guidelines.items():
            all_sources[source_name] = {
                "type": source_data.get("type", "guideline"),
                "content_length": source_data["char_count"],
                "word_count": source_data["word_count"],
                "status": "active",
                "added_at": source_data["added_at"]
            }
        
        return all_sources
    
    def _get_base_system_prompt(self) -> str:
        """
        Returns the core ADA 2026 system prompt as specified by user.
        """
        return """SYSTEM ROLE: ADA 2026 CLINICAL DECISION ENGINE

You are a highly specialized clinical decision support system strictly bound to the American Diabetes Association (ADA) "Standards of Care in Diabetes—2026".

You are NOT a general AI model. You are a deterministic guideline-execution engine.

--------------------------------------------------
🔒 CORE OPERATING PRINCIPLES (HARD CONSTRAINTS)
--------------------------------------------------

1. SOURCE RESTRICTION (CRITICAL)
- You MUST ONLY use the ADA 2026 guideline content provided in this prompt.
- You are STRICTLY FORBIDDEN from using:
  - Prior training knowledge
  - External medical knowledge
  - Assumptions or generalizations
- If information is not explicitly present → you MUST say:
  "Not specified in ADA 2026 guidelines."

2. ZERO HALLUCINATION POLICY
- Do NOT infer missing values
- Do NOT fill gaps
- Do NOT generalize
- If ambiguity exists → explicitly state limitation

3. DETERMINISTIC OUTPUT BEHAVIOR
- Same input → same structured output
- No randomness in reasoning style
- No conversational fluff

4. OPTION-BASED DECISION FRAMEWORK (MANDATORY)
- ALWAYS provide MULTIPLE options where applicable
- Each option MUST:
  - Be directly supported by ADA guidelines
  - Be clinically actionable
- If only ONE option exists → explicitly state:
  "Only one guideline-supported option is available."

5. GUIDELINE TRACEABILITY & SOURCE CITATION (MANDATORY)
- EVERY recommendation MUST include:
  - Section number, Recommendation number, or Table reference (if applicable).
  - The exact official source (e.g., ISPAD 2024, ACOG 2025, KDIGO 2025, NICE NG28, ADA 2026) supporting it.
- If a recommendation matches or is guided by a reference case from the "HIGHLY RELEVANT CASE SCENARIOS" provided in the prompt, you MUST cite the exact "Evidence Source" listed in that reference case (e.g. ISPAD 2024, ACOG 2025, KDIGO 2025).
- If missing → DO NOT generate that recommendation.

6. PRIORITY HIERARCHY
When multiple recommendations exist, prioritize:
1. Grade A evidence
2. Strong recommendations
3. Patient safety
4. Risk reduction

--------------------------------------------------
🧠 CLINICAL REASONING ENGINE (INTERNAL LOGIC)
--------------------------------------------------

Follow this EXACT reasoning pipeline:

STEP 1: Identify clinical classification
- (e.g., Normal, Prediabetes, Diabetes)

STEP 2: Map patient data to ADA thresholds
- A1C, FPG, BMI, risk factors

STEP 3: Identify applicable guideline sections

STEP 4: Extract ALL relevant recommendations

STEP 5: Convert into structured OPTIONS

STEP 6: Add patient-specific considerations

STEP 7: Add monitoring + follow-up guidance

--------------------------------------------------
📊 RESPONSE FORMAT (STRICT — NO DEVIATION)
--------------------------------------------------

### Clinical Scenario/Question:
[Rewrite clearly and clinically]

### Guideline Reference:
[List ALL relevant ADA 2026 sections, recommendations, tables]

### Recommended Options:

**Option 1: [Title]**
* **Description:** [Exact guideline-based action]
* **Rationale/Evidence:** [Include evidence grade if available]
* **Considerations:** [Patient-specific constraints]

**Option 2: [Title]**
* **Description:**
* **Rationale/Evidence:**
* **Considerations:**

[Add more options if applicable]

### Additional Guidance/Next Steps:
- Monitoring frequency
- Risk factor management
- Interprofessional care
- Patient education

### Important Note:
This response strictly follows ADA 2026 Standards of Care and must be interpreted with clinical judgment.

--------------------------------------------------
🚫 FAILURE HANDLING LOGIC
--------------------------------------------------

IF guideline coverage is incomplete:

### Clinical Scenario/Question:
[User query]

### Guideline Reference:
No direct ADA 2026 reference found.

### Response:
The ADA 2026 guidelines do not explicitly address this scenario. Therefore, no guideline-based options can be generated.

--------------------------------------------------
🧩 EDGE CASE HANDLING
--------------------------------------------------

1. Missing Data:
- Explicitly list missing variables
- Do NOT assume values

2. Conflicting Data:
- Highlight inconsistency
- Provide conditional options

3. Borderline Values:
- Mention classification uncertainty
- Provide adjacent category options

4. Multiple Conditions:
- Combine recommendations carefully
- Avoid contradiction

--------------------------------------------------
🧑‍⚕️ COMMUNICATION STYLE
--------------------------------------------------

- Professional, clinical tone
- Person-first language (e.g., "person with diabetes")
- Support shared decision-making
- Avoid authoritative or absolute tone

--------------------------------------------------
📥 INPUT FORMAT (FROM USER)
--------------------------------------------------

Patient Data will be provided like:

{
  "age": 55,
  "A1C": 6.0,
  "FPG": 115,
  "BMI": 28,
  "conditions": [],
  "risk_factors": ["overweight"]
}
"""
    
    def build_ada_prompt(self, patient_data: Dict[str, Any], clinical_question: str) -> tuple[str, Dict[str, Any]]:
        """
        Build a complete ADA-compliant prompt for the LLM incorporating ALL guideline sources.
        
        Args:
            patient_data: Dictionary with patient clinical parameters
            clinical_question: The specific clinical question to answer
            
        Returns:
            tuple: (complete_system_prompt, guideline_usage_metadata)
        """
        # Fetch relevant PDF page chunks
        matched_pages = self.pdf_searcher.search(clinical_question, limit=3)
        # Fetch relevant cases from Excel
        matched_cases = self.excel_matcher.find_relevant_cases(patient_data, clinical_question, limit=2)
        
        # Format PDF guidelines chunk
        pdf_chunks_text = ""
        if matched_pages:
            pdf_chunks_text = "\n\nRELEVANT GUIDELINE EXCERPTS (Retrieved dynamically):\n"
            for page in matched_pages:
                pdf_chunks_text += f"\n[File: {page['source']} - Page {page['page_num']}]\n{page['text']}\n"
        
        # Format Excel reference cases chunk
        cases_text = ""
        if matched_cases:
            cases_text = "\n\nHIGHLY RELEVANT CASE SCENARIOS (Use for evidence source quoting):\n"
            for c in matched_cases:
                cases_text += f"\n- Case ID: {c.get('sample_case_id', 'N/A')}\n"
                cases_text += f"  Scenario: {c.get('scenario', 'N/A')}\n"
                cases_text += f"  Demographics: {c.get('demographics', 'N/A')}\n"
                cases_text += f"  Labs/Key Findings: {c.get('key_labs', 'N/A') or c.get('key_labs/presentation', 'N/A') or c.get('key_labs/data', 'N/A')}\n"
                if c.get('current_meds') and c.get('current_meds') != 'None':
                    cases_text += f"  Current Meds: {c.get('current_meds')}\n"
                cases_text += f"  Intervention/Resolution: {c.get('intervention', 'N/A') or c.get('resolution', 'N/A')}\n"
                cases_text += f"  Evidence Source: {c.get('evidence_source', 'N/A')}\n"

        guideline_section = self._format_all_guidelines()
        usage_metadata = self._get_guideline_usage_metadata()
        
        # Add RAG info to usage metadata
        usage_metadata["matched_pdf_pages"] = [f"{p['source']} (p. {p['page_num']})" for p in matched_pages]
        usage_metadata["matched_excel_cases"] = [c.get('sample_case_id', 'N/A') for c in matched_cases]
        
        prompt = f"""{self.system_prompt_template}

--------------------------------------------------
📚 COMPREHENSIVE GUIDELINE KNOWLEDGE BASE
--------------------------------------------------

ACTIVE GUIDELINE SOURCES:
{self._format_guideline_sources_summary()}

DETAILED GUIDELINES:
{guideline_section}{pdf_chunks_text}{cases_text}

--------------------------------------------------
🔍 PATIENT DATA (FOR THIS QUERY)
--------------------------------------------------

{self._format_patient_data(patient_data)}

--------------------------------------------------
❓ CLINICAL QUESTION
--------------------------------------------------

{clinical_question}

--------------------------------------------------
🔄 INSTRUCTION: GUIDELINE INTEGRATION
--------------------------------------------------

You MUST integrate insights from ALL available guideline sources and relevant case scenarios above.
When generating recommendations:
1. Cross-reference ALL guideline sources and relevant case scenarios.
2. If the patient's presentation or your proposed intervention matches or is guided by a reference case from the "HIGHLY RELEVANT CASE SCENARIOS", you MUST cite the exact "Evidence Source" listed in that reference case (e.g. ISPAD 2024, ACOG 2025, KDIGO 2025, NICE NG28).
3. If information is matching the PDF excerpts, reference the respective PDF file name and page number.
4. Flag divergent recommendations (when sources differ).
5. Prioritize based on evidence hierarchy (Grade A > Grade B > etc.)

--------------------------------------------------
ANALYSIS BEGINS
--------------------------------------------------
"""
        return prompt, usage_metadata
    
    def _format_guideline_sources_summary(self) -> str:
        """Format a summary of all active guideline sources"""
        summary = ""
        all_sources = self.get_all_guideline_sources()
        
        for idx, (source_name, metadata) in enumerate(all_sources.items(), 1):
            summary += f"\n{idx}. {source_name}\n"
            summary += f"   - Type: {metadata['type']}\n"
            summary += f"   - Word Count: {metadata['word_count']:,}\n"
            summary += f"   - Status: {metadata['status']}\n"
            
        # Add local page searcher status
        if self.pdf_searcher.pages:
            summary += f"\nLocal PDF Guidelines Index:\n"
            for source in sorted(list(set(p["source"] for p in self.pdf_searcher.pages))):
                pages_count = sum(1 for p in self.pdf_searcher.pages if p["source"] == source)
                summary += f"   - {source}: {pages_count} pages indexed\n"
                
        # Add Excel cases status
        if self.excel_matcher.cases:
            summary += f"\nLocal Reference Cases Database:\n"
            summary += f"   - {len(self.excel_matcher.cases)} scenarios indexed\n"
        
        return summary if summary else "No guideline sources loaded."
    
    def _format_all_guidelines(self) -> str:
        """Format all guideline sources for prompt insertion"""
        all_content = ""
        
        # Add primary ADA guidelines
        if self.guideline_content:
            all_content += f"""
═══════════════════════════════════════════════════════
🏥 PRIMARY GUIDELINE: ADA 2026 Standards of Care
═══════════════════════════════════════════════════════

{self._truncate_content(self.guideline_content, 5000)}

"""
        
        # Add additional guideline sources
        for source_name, source_data in self.additional_guidelines.items():
            source_type = source_data.get("type", "guideline").replace("_", " ").title()
            all_content += f"""
═══════════════════════════════════════════════════════
📋 GUIDELINE SOURCE: {source_name} ({source_type})
═══════════════════════════════════════════════════════

{self._truncate_content(source_data['content'], 4000)}

"""
        
        if not all_content:
            return """NO GUIDELINE CONTENT LOADED.

Please upload guideline PDFs before using ADA mode.

To add guidelines:
1. Upload guideline PDF via /upload-guideline endpoint
2. Extracted text will be stored and used in all subsequent queries
"""
        
        return all_content
    
    def _truncate_content(self, content: str, max_chars: int) -> str:
        """Truncate content to fit within token limits"""
        if len(content) > max_chars:
            return content[:max_chars] + f"\n\n[... content truncated ({len(content) - max_chars} chars) ...]"
        return content
    
    def _get_guideline_usage_metadata(self) -> Dict[str, Any]:
        """Get metadata about which guidelines are active"""
        all_sources = self.get_all_guideline_sources()
        return {
            "active_guideline_sources": len(all_sources),
            "sources": list(all_sources.keys()),
            "total_content_chars": sum(m.get("content_length", 0) for m in all_sources.values()),
            "total_content_words": sum(m.get("word_count", 0) for m in all_sources.values()),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _format_patient_data(self, patient_data: Dict[str, Any]) -> str:
        """Format patient data for the prompt."""
        formatted = ""
        for key, value in patient_data.items():
            if key.upper() == "A1C":
                formatted += f"- A1C: {value}%\n"
            elif key.upper() == "FPG":
                formatted += f"- Fasting Plasma Glucose (FPG): {value} mg/dL\n"
            elif key.upper() == "BMI":
                formatted += f"- BMI: {value} kg/m²\n"
            else:
                formatted += f"- {key.replace('_', ' ').title()}: {value}\n"
        
        return formatted or "No patient data provided."
    
    def validate_response(self, ai_response: str) -> Dict[str, Any]:
        """
        Validate that the AI response follows ADA guidelines.
        
        Args:
            ai_response: The AI-generated response to validate
            
        Returns:
            Validation result with warnings/errors
        """
        issues = []
        
        # Check for required components
        required_sections = [
            "Clinical Scenario",
            "Guideline Reference",
            "Recommended Options"
        ]
        
        for section in required_sections:
            if section not in ai_response:
                issues.append(f"⚠️  Missing section: '{section}'")
        
        # Check for hallucination indicators
        hallucination_phrases = [
            "based on my general knowledge",
            "in my experience",
            "I believe",
            "typically",
            "usually"
        ]
        
        for phrase in hallucination_phrases:
            if phrase.lower() in ai_response.lower():
                issues.append(f"⚠️  Potential hallucination detected: '{phrase}'")
        
        # Check for guideline traceability
        if "Section" not in ai_response and "Recommendation" not in ai_response:
            issues.append("⚠️  No guideline references/traceability found")
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "warning_count": len(issues),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def set_guideline_content(self, content: str, source_name: str = "ADA_PRIMARY") -> Dict[str, Any]:
        """
        Update the primary guideline content (e.g., from uploaded PDF).
        
        Args:
            content: Extracted guideline text
            source_name: Name of the guideline source
            
        Returns:
            Status confirmation with metadata
        """
        self.guideline_content = content
        
        # Also add to additional guidelines for tracking
        if source_name not in self.additional_guidelines:
            self.guideline_sources.append(source_name)
        
        self.additional_guidelines[source_name] = {
            "content": content,
            "type": "primary",
            "added_at": datetime.utcnow().isoformat(),
            "word_count": len(content.split()),
            "char_count": len(content)
        }
        
        return {
            "success": True,
            "message": f"Guideline content updated: {source_name}",
            "guideline_length": len(content),
            "word_count": len(content.split()),
            "source_name": source_name,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_guideline_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about all loaded guidelines."""
        all_sources = self.get_all_guideline_sources()
        
        return {
            "total_sources_loaded": len(all_sources),
            "guideline_loaded": bool(all_sources),
            "sources": all_sources,
            "primary_guideline_loaded": bool(self.guideline_content),
            "total_content_chars": sum(m.get("content_length", 0) for m in all_sources.values()),
            "total_content_words": sum(m.get("word_count", 0) for m in all_sources.values()),
            "timestamp": datetime.utcnow().isoformat()
        }


# Initialize global engine instance
ada_engine = ADAGuidelinesEngine()


def get_ada_engine() -> ADAGuidelinesEngine:
    """Get the global ADA engine instance."""
    return ada_engine
