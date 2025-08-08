#!/usr/bin/env python3
"""
Test script to verify OVH API integration and model configuration
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.ollama_client import OllamaClient
from app.services.ovh_client import OVHClient
from app.models.document import SupportedLanguage

async def test_ovh_connection():
    """Test OVH API connection"""
    print("\n📡 Testing OVH API Connection...")
    print("-" * 50)
    
    ovh_client = OVHClient()
    
    # Check if token is configured
    if not os.getenv("OVH_AI_ENDPOINTS_ACCESS_TOKEN"):
        print("⚠️  OVH_AI_ENDPOINTS_ACCESS_TOKEN not set in environment")
        print("   Please add your token to the .env file")
        return False
    
    # Test connection
    connected = await ovh_client.check_connection()
    if connected:
        print("✅ OVH API connection successful!")
        print(f"   Model: {ovh_client.model}")
        print(f"   Endpoint: {ovh_client.base_url}")
    else:
        print("❌ OVH API connection failed")
        print("   Please check your token and network connection")
    
    return connected

async def test_ollama_models():
    """Test local Ollama models"""
    print("\n🖥️  Testing Local Ollama Models...")
    print("-" * 50)
    
    ollama_client = OllamaClient(use_ovh_for_main=False)  # Test without OVH first
    
    # Check connection
    connected = await ollama_client.check_connection()
    if not connected:
        print("❌ Ollama not connected. Make sure Ollama is running.")
        return False
    
    print("✅ Ollama connected")
    
    # List available models
    models = await ollama_client.list_models()
    print(f"\n📋 Available models: {len(models)}")
    for model in models:
        print(f"   • {model}")
    
    # Check required models
    required_models = [
        os.getenv("OLLAMA_PREPROCESSING_MODEL", "gpt-oss:20b"),
        os.getenv("OLLAMA_TRANSLATION_MODEL", "zongwei/gemma3-translator:4b")
    ]
    
    print(f"\n🔍 Checking required models:")
    for model in required_models:
        if model in models:
            print(f"   ✅ {model} - Available")
        else:
            print(f"   ❌ {model} - NOT FOUND")
            print(f"      Please install with: ollama pull {model}")
    
    return True

async def test_preprocessing():
    """Test preprocessing with local gpt-oss:20b on GPU"""
    print("\n🔧 Testing Preprocessing with gpt-oss:20b (GPU)...")
    print("-" * 50)
    
    ollama_client = OllamaClient(use_ovh_for_main=False)
    
    test_text = """
    Sehr geehrte Frau Dr. Müller,
    
    Patient: Max Mustermann, geb. 15.03.1970
    
    Diagnose: Hypertonie (ICD-10: I10.90)
    Der Patient zeigt erhöhte Blutdruckwerte von 150/95 mmHg.
    
    Therapie: ACE-Hemmer verordnet.
    
    Mit freundlichen Grüßen
    Dr. Schmidt
    """
    
    try:
        # Test preprocessing
        cleaned_text = await ollama_client._ai_preprocess_text(test_text)
        
        if cleaned_text and len(cleaned_text) > 10:
            print("✅ Preprocessing successful!")
            print(f"   Original length: {len(test_text)} chars")
            print(f"   Cleaned length: {len(cleaned_text)} chars")
            print("\n   Preview of cleaned text:")
            print("   " + cleaned_text[:200].replace("\n", "\n   "))
        else:
            print("❌ Preprocessing failed or returned empty text")
        
        return True
    except Exception as e:
        print(f"❌ Preprocessing error: {e}")
        return False

async def test_ovh_processing():
    """Test main processing with OVH API"""
    print("\n🚀 Testing Main Processing with OVH API...")
    print("-" * 50)
    
    if not os.getenv("OVH_AI_ENDPOINTS_ACCESS_TOKEN"):
        print("⚠️  Skipping OVH test - token not configured")
        return False
    
    ovh_client = OVHClient()
    
    test_text = """
    Diagnose: Hypertonie (ICD-10: I10.90)
    Blutdruck: 150/95 mmHg
    Therapie: ACE-Hemmer 5mg täglich
    """
    
    try:
        result = await ovh_client.process_medical_text(
            text=test_text,
            instruction="Translate this medical text into simple patient-friendly language in German",
            temperature=0.3,
            max_tokens=500
        )
        
        if result and len(result) > 10:
            print("✅ OVH processing successful!")
            print(f"   Result length: {len(result)} chars")
            print("\n   Preview:")
            print("   " + result[:300].replace("\n", "\n   "))
        else:
            print("❌ OVH processing failed or returned empty")
        
        return True
    except Exception as e:
        print(f"❌ OVH processing error: {e}")
        return False

async def test_language_translation():
    """Test language translation with gemma3-translator"""
    print("\n🌐 Testing Language Translation with gemma3-translator...")
    print("-" * 50)
    
    ollama_client = OllamaClient(use_ovh_for_main=False)
    
    test_text = """
    # 📋 Ihre medizinische Dokumentation
    
    ## 🎯 Das Wichtigste zuerst
    Sie haben Bluthochdruck.
    
    ## 💊 Behandlung
    • ACE-Hemmer täglich einnehmen
    """
    
    try:
        # Test translation to English
        result, confidence = await ollama_client.translate_to_language(
            simplified_text=test_text,
            target_language=SupportedLanguage.ENGLISH
        )
        
        if result and len(result) > 10:
            print("✅ Language translation successful!")
            print(f"   Target: English")
            print(f"   Confidence: {confidence:.2f}")
            print(f"   Result length: {len(result)} chars")
            print("\n   Preview:")
            print("   " + result[:200].replace("\n", "\n   "))
        else:
            print("❌ Language translation failed")
        
        return True
    except Exception as e:
        print(f"❌ Language translation error: {e}")
        return False

async def test_full_pipeline():
    """Test the complete processing pipeline"""
    print("\n🔄 Testing Complete Pipeline...")
    print("-" * 50)
    
    # Initialize with OVH enabled
    ollama_client = OllamaClient(use_ovh_for_main=True)
    
    test_document = """
    Entlassungsbrief
    
    Patient: [Name entfernt]
    Diagnose: Arterielle Hypertonie (ICD-10: I10.90)
    
    Befund:
    - Blutdruck: 155/98 mmHg
    - Puls: 78/min
    - Labor: Kreatinin 1.2 mg/dl, GFR 68 ml/min
    
    Therapie:
    - Ramipril 5mg 1-0-0
    - Hydrochlorothiazid 12.5mg 1-0-0
    
    Empfehlung:
    Regelmäßige Blutdruckkontrolle beim Hausarzt.
    Salzarme Ernährung empfohlen.
    """
    
    try:
        print("Step 1: Medical text translation...")
        result = await ollama_client.translate_medical_text(test_document)
        translated_text, doc_type, confidence, cleaned_text = result
        
        if translated_text and len(translated_text) > 100:
            print(f"✅ Medical translation successful!")
            print(f"   Document type: {doc_type}")
            print(f"   Confidence: {confidence:.2f}")
            print(f"   Length: {len(translated_text)} chars")
            
            # Test language translation
            print("\nStep 2: Language translation to English...")
            lang_result, lang_confidence = await ollama_client.translate_to_language(
                simplified_text=translated_text,
                target_language=SupportedLanguage.ENGLISH
            )
            
            if lang_result and len(lang_result) > 50:
                print(f"✅ Language translation successful!")
                print(f"   Confidence: {lang_confidence:.2f}")
                print(f"   Length: {len(lang_result)} chars")
            else:
                print("❌ Language translation failed")
        else:
            print("❌ Medical translation failed")
        
        return True
    except Exception as e:
        print(f"❌ Pipeline error: {e}")
        return False

async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("🧪 DOCTRANSLATOR CONFIGURATION TEST")
    print("=" * 60)
    
    # Load environment variables
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded .env from: {env_path}")
    else:
        print(f"⚠️  No .env file found at: {env_path}")
    
    # Display configuration
    print("\n📋 Current Configuration:")
    print("-" * 50)
    print(f"OLLAMA_PREPROCESSING_MODEL: {os.getenv('OLLAMA_PREPROCESSING_MODEL', 'gpt-oss:20b')}")
    print(f"OLLAMA_TRANSLATION_MODEL: {os.getenv('OLLAMA_TRANSLATION_MODEL', 'zongwei/gemma3-translator:4b')}")
    print(f"OVH_AI_MODEL: {os.getenv('OVH_AI_MODEL', 'Meta-Llama-3_3-70B-Instruct')}")
    print(f"OVH_AI_BASE_URL: {os.getenv('OVH_AI_BASE_URL', 'https://oai.endpoints.kepler.ai.cloud.ovh.net/v1')}")
    token = os.getenv('OVH_AI_ENDPOINTS_ACCESS_TOKEN', '')
    print(f"OVH_AI_ENDPOINTS_ACCESS_TOKEN: {'***' + token[-4:] if len(token) > 4 else 'NOT SET'}")
    
    # Run tests
    tests = [
        ("OVH Connection", test_ovh_connection),
        ("Ollama Models", test_ollama_models),
        ("Preprocessing", test_preprocessing),
        ("OVH Processing", test_ovh_processing),
        ("Language Translation", test_language_translation),
        ("Full Pipeline", test_full_pipeline)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = await test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
    
    passed = sum(1 for _, s in results if s)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Configuration is ready.")
    else:
        print("\n⚠️  Some tests failed. Please check the configuration above.")

if __name__ == "__main__":
    asyncio.run(main())