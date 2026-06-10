"""
ADA 2026 Clinical Decision Support Engine

This module provides a deterministic wrapper around guideline content
to generate ADA-compliant prompts for the AI model. It enforces strict
traceability, zero-hallucination constraints, and a structured response
format so downstream consumers can rely on guideline-backed advice.
"""

from typing import Dict, Any, Optional, List
import json
import os
from datetime import datetime
import re

class ADAGuidelinesEngine:
    """
    Enforces strict ADA 2026 guideline compliance in AI responses.
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
        self.total_recommendations = 0
        self.sample_cases = 0
        self.loaded_sources = 0

    def auto_load_from_directory(self, directory_path: str) -> Dict[str, Any]:
        """
        Automatically loads all PDF files from a given directory as guidelines.
        """
        loaded_count = 0
        errors = []
        if not os.path.exists(directory_path):
            os.makedirs(directory_path, exist_ok=True)
            return {"loaded": 0, "total_recommendations": 0, "sample_cases": 0, "errors": [f"Directory not found: {directory_path}"]}

        for filename in os.listdir(directory_path):
            if filename.lower().endswith(".pdf"):
                filepath = os.path.join(directory_path, filename)
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(filepath)
                    text = "".join([page.extract_text() or "" for page in reader.pages])
                    source_name = os.path.splitext(filename)[0]
                    self.add_guideline_source(source_name, text, "pdf_guideline")
                    loaded_count += 1
                except Exception as e:
                    errors.append(f"Failed to load {filename}: {e}")
        
        # Recalculate stats after batch load
        self.loaded_sources = len(self.guideline_sources)

        return {
            "loaded": loaded_count,
            "total_recommendations": self.total_recommendations,
            "sample_cases": self.sample_cases,
            "errors": errors
        }

    def set_guideline_content(self, content: str, source_name: str = "ADA_PRIMARY"):
        """
        Sets the primary guideline content, replacing any existing primary content.
        """
        self.guideline_content = content
        if source_name not in self.guideline_sources:
            self.guideline_sources.append(source_name)
        
        # Estimate recommendations and cases
        recs = len(re.findall(r'Rec\.\s*\d+\.\d+', content))
        cases = len(re.findall(r'Case\s*\d+', content))
        
        self.total_recommendations += recs
        self.sample_cases += cases
        self.loaded_sources = len(self.guideline_sources)

    def add_guideline_source(self, source_name: str, content: str, source_type: str = "guideline") -> Dict[str, Any]:
        """
        Add a new guideline source.
        """
        self.additional_guidelines[source_name] = {
            "content": content,
            "type": source_type,
            "added_at": datetime.utcnow().isoformat(),
            "word_count": len(content.split()),
            "char_count": len(content)
        }
        if source_name not in self.guideline_sources:
            self.guideline_sources.append(source_name)
        
        self.loaded_sources = len(self.guideline_sources)
        
        # Enhanced detection for recommendations
        recs = len(re.findall(r'Rec\.\s*\d+\.\d+|Recommendation\s*\d+', content))
        cases = len(re.findall(r'Case\s*\d+', content))
        
        self.total_recommendations += recs
        self.sample_cases += cases

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

    def get_guideline_stats(self) -> Dict[str, Any]:
        """
        Returns statistics about the loaded guidelines.
        """
        return {
            "guideline_loaded": self.loaded_sources > 0,
            "total_sources_loaded": self.loaded_sources,
            "total_recommendations": self.total_recommendations,
            "sample_cases_loaded": self.sample_cases,
            "sources": self.get_all_guideline_sources()
        }

    def _get_base_system_prompt(self) -> str:
        """
        Returns the core ADA 2026 system prompt.
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
  - The exact official source (e.g., ADA 2026) supporting it.
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
"""
    
    def build_ada_prompt(self, patient_data: Dict[str, Any], clinical_question: str) -> tuple[str, Dict[str, Any]]:
        """
        Build a complete ADA-compliant prompt.
        """
        guideline_section = self._format_all_guidelines()
        usage_metadata = self._get_guideline_usage_metadata()
        
        prompt = f"""{self.system_prompt_template}

--------------------------------------------------
📚 COMPREHENSIVE GUIDELINE KNOWLEDGE BASE
--------------------------------------------------

ACTIVE GUIDELINE SOURCES:
{self._format_guideline_sources_summary()}

DETAILED GUIDELINES:
{guideline_section}

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

You MUST integrate insights from ALL available guideline sources above.
When generating recommendations:
1. Cross-reference ALL guideline sources.
2. Flag divergent recommendations (when sources differ).
3. Prioritize based on evidence hierarchy (Grade A > Grade B > etc.)

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
            
        return summary if summary else "No guideline sources loaded."
    
    def _format_all_guidelines(self) -> str:
        """Format all guideline sources for prompt insertion"""
        all_content = ""
        
        if self.guideline_content:
            all_content += f"\nSource: ADA_PRIMARY\nType: primary\n{self._truncate_content(self.guideline_content, 5000)}\n"
        
        for source_name, source_data in self.additional_guidelines.items():
            source_type = source_data.get("type", "guideline").replace("_", " ").title()
            all_content += f"\nSource: {source_name} ({source_type})\n{self._truncate_content(source_data['content'], 4000)}\n"
        
        return all_content if all_content else "NO GUIDELINE CONTENT LOADED."

    def _truncate_content(self, content: str, max_chars: int) -> str:
        if len(content) <= max_chars:
            return content
        return content[:max_chars] + "... [TRUNCATED]"

    def _format_patient_data(self, data: Dict[str, Any]) -> str:
        return json.dumps(data, indent=2)

    def _get_guideline_usage_metadata(self) -> Dict[str, Any]:
        return {
            "guideline_loaded": self.loaded_sources > 0,
            "sources_count": self.loaded_sources,
            "recommendations_estimate": self.total_recommendations
        }

def get_ada_engine():
    if not hasattr(get_ada_engine, "_instance"):
        get_ada_engine._instance = ADAGuidelinesEngine()
    return get_ada_engine._instance