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
from datetime import datetime

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

5. GUIDELINE TRACEABILITY (MANDATORY)
- EVERY recommendation MUST include:
  - Section number
  - Recommendation number
  - Table reference (if applicable)
- If missing → DO NOT generate that recommendation

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
1. Cross-reference ALL guideline sources
2. Identify convergent recommendations (when multiple sources agree)
3. Flag divergent recommendations (when sources differ)
4. Prioritize based on evidence hierarchy (Grade A > Grade B > etc.)
5. Explicitly cite which guideline source supports each recommendation

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
