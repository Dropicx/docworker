import os
import httpx
import logging
from typing import Optional, Dict, Any, AsyncGenerator
from openai import AsyncOpenAI
import json

# Setup logger
logger = logging.getLogger(__name__)

class OVHClient:
    """
    Client for OVH AI Endpoints using Meta-Llama-3.3-70B-Instruct
    """
    
    def __init__(self):
        self.access_token = os.getenv("OVH_AI_ENDPOINTS_ACCESS_TOKEN")
        self.base_url = os.getenv("OVH_AI_BASE_URL", "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1")
        self.model = os.getenv("OVH_AI_MODEL", "Meta-Llama-3_3-70B-Instruct")
        
        if not self.access_token:
            logger.warning("⚠️ OVH_AI_ENDPOINTS_ACCESS_TOKEN not set in environment")
        
        # Initialize OpenAI client for OVH
        self.client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.access_token or "dummy-key"  # Use dummy key if not set
        )
        
        # Alternative HTTP client for direct API calls
        self.timeout = 300  # 5 minutes timeout
        
    async def check_connection(self) -> bool:
        """Check connection to OVH AI Endpoints"""
        if not self.access_token:
            logger.error("❌ OVH API token not configured")
            return False
            
        try:
            # Try a simple completion to test connection
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=10,
                temperature=0
            )
            logger.info("✅ OVH AI Endpoints connection successful")
            return True
        except Exception as e:
            logger.error(f"❌ OVH AI Endpoints connection failed: {e}")
            return False
    
    async def process_medical_text(
        self, 
        text: str,
        instruction: str = "Process this medical text",
        temperature: float = 0.3,
        max_tokens: int = 4000
    ) -> str:
        """
        Process medical text using Meta-Llama-3.3-70B-Instruct
        
        Args:
            text: The medical text to process
            instruction: Processing instruction
            temperature: Model temperature (0-1)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Processed text from the model
        """
        if not self.access_token:
            logger.error("❌ OVH API token not configured")
            return "Error: OVH API token not configured. Please set OVH_AI_ENDPOINTS_ACCESS_TOKEN in .env"
        
        try:
            logger.info(f"🚀 Processing with OVH {self.model}")
            
            # Prepare the message
            messages = [
                {
                    "role": "system",
                    "content": "You are a highly specialized medical text processor. Follow the instructions precisely."
                },
                {
                    "role": "user",
                    "content": f"{instruction}\n\nText to process:\n{text}"
                }
            ]
            
            # Make the API call using OpenAI client
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=0.9
            )
            
            result = response.choices[0].message.content
            logger.info(f"✅ OVH processing successful")
            return result.strip()
            
        except Exception as e:
            logger.error(f"❌ OVH API error: {e}")
            return f"Error processing with OVH API: {str(e)}"
    
    async def process_medical_text_direct(
        self,
        text: str,
        instruction: str = "Process this medical text",
        temperature: float = 0.3,
        max_tokens: int = 4000
    ) -> str:
        """
        Process medical text using direct HTTP calls (alternative method)
        """
        if not self.access_token:
            return "Error: OVH API token not configured"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a highly specialized medical text processor."
                        },
                        {
                            "role": "user",
                            "content": f"{instruction}\n\nText:\n{text}"
                        }
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "top_p": 0.9
                }
                
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.access_token}"
                }
                
                logger.info(f"🌐 Direct API call to OVH {self.model}")
                
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    result = response_data["choices"][0]["message"]["content"]
                    logger.info("✅ Direct OVH API call successful")
                    return result.strip()
                else:
                    logger.error(f"❌ OVH API error: {response.status_code} - {response.text}")
                    return f"Error: OVH API returned {response.status_code}"
                    
        except Exception as e:
            logger.error(f"❌ Direct OVH API call failed: {e}")
            return f"Error with direct API call: {str(e)}"
    
    async def generate_streaming(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 4000
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming response from OVH API
        """
        if not self.access_token:
            yield "Error: OVH API token not configured"
            return
        
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"❌ OVH streaming error: {e}")
            yield f"Streaming error: {str(e)}"
    
    async def translate_medical_document(
        self,
        text: str,
        document_type: str = "universal"
    ) -> tuple[str, str, float, str]:
        """
        Main processing using OVH Meta-Llama-3.3-70B for medical document translation
        
        Returns:
            tuple[str, str, float, str]: (translated_text, doc_type, confidence, cleaned_original)
        """
        try:
            logger.info("🏥 Starting medical document processing with OVH AI")
            
            # Create the comprehensive instruction for medical translation
            instruction = self._get_medical_translation_instruction()
            
            # Process with OVH API
            translated_text = await self.process_medical_text(
                text=text,
                instruction=instruction,
                temperature=0.3,
                max_tokens=4000
            )
            
            # Evaluate quality
            confidence = self._evaluate_translation_quality(text, translated_text)
            
            return translated_text, document_type, confidence, text
            
        except Exception as e:
            logger.error(f"❌ OVH translation failed: {e}")
            return f"Translation error: {str(e)}", "error", 0.0, text
    
    def _get_medical_translation_instruction(self) -> str:
        """Get the comprehensive medical translation instruction"""
        return """You are a highly specialized medical translator. Your task is to translate medical documents into patient-friendly language.

CRITICAL ANTI-HALLUCINATION RULES:
⛔ ADD NOTHING that is not explicitly in the document
⛔ NO guesses, assumptions, or "could be" statements
⛔ NO general medical advice not in the text
⛔ NO additional explanations except direct translation of technical terms
⛔ DO NOT invent additional information
✅ Translate ONLY what is literally in the document
✅ Do not omit any medical information
✅ Explain technical terms briefly in parentheses (definition only)
✅ Address the patient DIRECTLY (use "You", "Your")
✅ For uncertainties: mark with [unclear] instead of interpreting

LANGUAGE GUIDELINES:
- Use short main sentences (maximum 15-20 words)
- Active formulations ("The doctor examines" not "It is examined")
- Concrete terms ("measure blood pressure" not "perform blood pressure control")
- Everyday language ("heart" in addition to "cardiac")
- Comparisons from everyday life (e.g., "size of a walnut")
- Direct address ("You were", "Your blood pressure", "You should")

FORMAT:
# 📋 Your Medical Documentation - Simply Explained

## 🎯 The Most Important First
[The central information in one clear sentence]

## 📊 Summary
### What was done?
• [Examination/treatment in simple language]
• [Period/date if available]

### What was found?
• [Main finding 1 in simple language]
  → Meaning: [What does this mean for you?]
• [Main finding 2 in simple language]
  → Meaning: [What does this mean for you?]

## 🏥 Your Diagnoses
• [Diagnosis in everyday language]
  → Medical term: [Technical term]
  → ICD code if available: [Code with explanation]
  → Explanation: [What exactly is this?]

## 💊 Treatment & Medications
• [Medication/treatment]
  → Purpose: [Why]
  → Intake: [How and when]
  → Important: [Special notes/side effects]

## ✅ Your Next Steps
• [What you should do in simple language]
• [Upcoming appointments]
• [What to watch for in simple language]

## 📖 Understanding Medical Terms
• **[Term 1]**: [Simple explanation]
• **[Term 2]**: [Simple explanation]

## ⚠️ Important Notes
This translation helps you understand your documents
Discuss all questions with your doctor
In emergencies: Call emergency services"""
    
    def _evaluate_translation_quality(self, original: str, translated: str) -> float:
        """Evaluate the quality of the translation"""
        if not translated or translated.startswith("Error"):
            return 0.0
        
        confidence = 0.6  # Base confidence for OVH model
        
        # Length check
        if len(translated) > 100:
            confidence += 0.1
        if len(translated) > 500:
            confidence += 0.1
        
        # Ratio check
        length_ratio = len(translated) / max(len(original), 1)
        if 0.5 <= length_ratio <= 2.0:
            confidence += 0.1
        
        # Simple language indicators
        simple_indicators = [
            "this means", "simply put", "in other words",
            "das bedeutet", "einfach gesagt", "mit anderen worten"
        ]
        translated_lower = translated.lower()
        found_indicators = sum(1 for indicator in simple_indicators if indicator in translated_lower)
        confidence += min(found_indicators * 0.05, 0.1)
        
        return min(confidence, 1.0)