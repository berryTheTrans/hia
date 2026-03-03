import groq
import streamlit as st
from enum import Enum
import logging
import time
from openai import OpenAI

logger = logging.getLogger(__name__)

class ModelTier(Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary" 
    TERTIARY = "tertiary"
    FALLBACK = "fallback"

class ModelManager:
    """
    Manages AI model selection, fallback, and rate limits.
    Implements an agent-based approach for model management.
    """
    
    MODEL_CONFIG = {
        ModelTier.PRIMARY: {
            "provider": "groq",
            "model": "meta-llama/llama-4-maverick-17b-128e-instruct",
            "max_tokens": 2000,
            "temperature": 0.7
        },
        ModelTier.SECONDARY: {
            "provider": "groq", 
            "model": "llama-3.3-70b-versatile",
            "max_tokens": 2000,
            "temperature": 0.7
        },
        ModelTier.TERTIARY: {
            "provider": "groq",
            "model": "llama-3.1-8b-instant",
            "max_tokens": 2000, 
            "temperature": 0.7
        },
        ModelTier.FALLBACK: {
            "provider": "groq",
            "model": "llama3-70b-8192",
            "max_tokens": 2000,
            "temperature": 0.7
        }
    }
    
    def __init__(self):
        self.clients = {}
        self._initialize_clients()

    def _initialize_clients(self):
        try:
            self.clients["groq"] = groq.Groq(api_key=st.secrets["GROQ_API_KEY"])
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {str(e)}")
        try:
            self.clients["deepseek"] = OpenAI(api_key=st.secrets["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")
        except Exception as e:
            logger.error(f"Failed to initialize DeepSeek client: {str(e)}")

    def generate_analysis(self, data, system_prompt, retry_count=0):
        """
        Generate analysis using the best available model with automatic fallback.
        Implements agent-based decision making for model selection.
        """
        if retry_count > 3:
            return {"success": False, "error": "All models failed after multiple retries"}

        # Determine which model tier to use based on retry count
        if retry_count == 0:
            tier = ModelTier.PRIMARY
        elif retry_count == 1:
            tier = ModelTier.SECONDARY
        elif retry_count == 2:
            tier = ModelTier.TERTIARY
        else:
            tier = ModelTier.FALLBACK
            
        model_config = self.MODEL_CONFIG[tier]
        provider = model_config["provider"]
        model = model_config["model"]
        if "deepseek" in self.clients:
            provider = "deepseek"
            if tier == ModelTier.PRIMARY:
                model = "deepseek-chat"
            elif tier == ModelTier.SECONDARY:
                model = "deepseek-reasoner"
            else:
                model = "deepseek-chat"
        
        if provider not in self.clients or not self.clients.get(provider):
            fallback = self._local_fallback_analysis(data, system_prompt)
            return fallback
            
        try:
            client = self.clients[provider]
            logger.info(f"Attempting generation with {provider} model: {model}")
            
            if provider == "groq":
                completion = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": str(data)}
                    ],
                    temperature=model_config["temperature"],
                    max_tokens=model_config["max_tokens"]
                )
                
                return {
                    "success": True,
                    "content": completion.choices[0].message.content,
                    "model_used": f"{provider}/{model}"
                }
            if provider == "deepseek":
                completion = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": str(data)}
                    ],
                    temperature=model_config["temperature"],
                    max_tokens=model_config["max_tokens"]
                )
                return {
                    "success": True,
                    "content": completion.choices[0].message.content,
                    "model_used": f"{provider}/{model}"
                }
                
        except Exception as e:
            error_message = str(e).lower()
            logger.warning(f"Model {model} failed: {error_message}")
            
            # Check for rate limit errors
            if "rate limit" in error_message or "quota" in error_message:
                # Wait briefly before retrying with a different model
                time.sleep(2)
            
            # Try next model in hierarchy
            if retry_count < 3:
                return self.generate_analysis(data, system_prompt, retry_count + 1)
            return self._local_fallback_analysis(data, system_prompt)
            
        return {"success": False, "error": "Analysis failed with all available models"}

    def _local_fallback_analysis(self, data, system_prompt):
        try:
            report = ""
            name = ""
            age = ""
            gender = ""
            if isinstance(data, dict):
                report = str(data.get("report", "")).strip()
                name = str(data.get("patient_name", "")).strip()
                age = str(data.get("age", "")).strip()
                gender = str(data.get("gender", "")).strip()
            header = "Preliminary, offline summary (no AI service reachable)."
            patient = f"Patient: {name or 'N/A'}, Age: {age or 'N/A'}, Gender: {gender or 'N/A'}"
            length = len(report)
            indicators = []
            for k in ["hemoglobin", "glucose", "cholesterol", "triglycerides", "hdl", "ldl", "wbc", "rbc", "platelet", "creatinine"]:
                if k in report.lower():
                    indicators.append(k)
            inds = ", ".join(indicators) if indicators else "No common indicators detected"
            content = (
                f"{header}\n\n"
                f"{patient}\n\n"
                f"Report length: {length} characters.\n"
                f"Detected keywords: {inds}.\n\n"
                "Notes:\n"
                "- Provide clearer report text or check network/API key for full analysis.\n"
                "- This is a template summary using simple heuristics."
            )
            return {"success": True, "content": content, "model_used": "local/fallback"}
        except Exception:
            return {"success": False, "error": "All models failed after multiple retries"}
