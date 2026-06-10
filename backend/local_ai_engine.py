"""Local AI compatibility layer for the backend.

This module provides a lightweight engine that can:
1. use Google Generative AI when the dependency and API key are available, or
2. fall back to a deterministic response path if the external service is not
   configured.

The fallback keeps the backend importable and prevents deployment-time crashes
when the AI provider is unavailable.
"""

import os
from typing import Any, Dict, List, Optional


class LocalAIEngine:
    """Small compatibility wrapper around a local/remote AI model."""

    def __init__(self, model_name: str = "gemini-3-flash-preview"):
        self.model_name = model_name
        self._client = None
        self._client_error = None

        try:
            import google.generativeai as genai  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            self._client_error = f"google-generativeai unavailable: {exc}"
            return

        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            self._client_error = "No Google/Gemini API key configured"
            return

        try:
            genai.configure(api_key=api_key)
            self._client = genai
        except Exception as exc:  # pragma: no cover - runtime configuration issue
            self._client_error = f"Failed to configure Gemini client: {exc}"

    def generate_response(
        self,
        system_prompt: str,
        user_query: str,
        chat_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Generate a response using the configured provider or a safe fallback."""

        if self._client is not None:
            try:
                model = self._client.GenerativeModel(self.model_name)

                history = []
                for item in chat_history or []:
                    role = item.get("role", "user")
                    if role == "assistant":
                        history.append({"role": "model", "parts": [item.get("content", "")]})
                    else:
                        history.append({"role": "user", "parts": [item.get("content", "")]})

                prompt = f"{system_prompt}\n\nUSER QUERY:\n{user_query}"

                if history:
                    chat = model.start_chat(history=history)
                    response = chat.send_message(prompt)
                else:
                    response = model.generate_content(prompt)

                text = getattr(response, "text", None)
                if not text and hasattr(response, "parts"):
                    text = "\n".join(str(part) for part in response.parts)

                if not text:
                    raise ValueError("Empty response from Gemini model")

                return {
                    "success": True,
                    "content": text,
                    "model_used": self.model_name,
                }
            except Exception as exc:
                return {
                    "success": False,
                    "error": f"Gemini generation failed: {exc}",
                    "model_used": self.model_name,
                }

        # Safe fallback path (used in local/dev or when no API key is set).
        fallback_text = (
            "I am operating in fallback mode because the AI service is not configured. "
            "This response is a placeholder and should be verified by the treating physician. "
            f"The request received was: {user_query[:200]}"
        )

        return {
            "success": True,
            "content": fallback_text,
            "model_used": self.model_name,
            "fallback": True,
        }
