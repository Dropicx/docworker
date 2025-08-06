#!/usr/bin/env python3
"""
Test-Skript für die neue Sprachübersetzungsfunktionalität
"""

import asyncio
import sys
import os

# Pfad zum Backend hinzufügen
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.ollama_client import OllamaClient
from app.models.document import SupportedLanguage, LANGUAGE_NAMES

async def test_language_translation():
    """Testet die neue Sprachübersetzungsfunktionalität"""
    
    print("🧪 Test der Sprachübersetzungsfunktionalität")
    print("=" * 50)
    
    # Ollama Client initialisieren
    client = OllamaClient()
    
    # 1. Verbindung testen
    print("\n1. Teste Ollama-Verbindung...")
    connected = await client.check_connection()
    print(f"   Verbindung: {'✅ OK' if connected else '❌ Fehler'}")
    
    if not connected:
        print("   ❌ Ollama ist nicht verfügbar. Stelle sicher, dass Ollama läuft.")
        return
    
    # 2. Verfügbare Modelle auflisten
    print("\n2. Verfügbare Modelle:")
    models = await client.list_models()
    for model in models:
        print(f"   - {model}")
    
    # 3. Teste Sprachübersetzung
    print("\n3. Teste Sprachübersetzung...")
    
    # Beispieltext in einfacher Sprache
    simplified_text = """📋 **ZUSAMMENFASSUNG**
Ihr Bluttest zeigt wichtige Informationen über Ihre Gesundheit.

🏥 **HAUPTBEFUNDE**
• Ihre Blutzuckerwerte sind normal (zwischen 70-100 mg/dl)
• Ihr Cholesterin ist leicht erhöht (220 mg/dl, normal ist unter 200)
• Alle anderen Werte sind in Ordnung

💊 **EMPFEHLUNGEN**
• Weniger fettiges Essen
• Mehr Bewegung (30 Minuten täglich)
• Kontrolle in 3 Monaten

⚠️ **WICHTIGE PUNKTE**
Das ist kein Notfall, aber Sie sollten auf Ihre Ernährung achten."""

    # Teste verschiedene Sprachen
    test_languages = [
        SupportedLanguage.ENGLISH,
        SupportedLanguage.SPANISH,
        SupportedLanguage.FRENCH
    ]
    
    for language in test_languages:
        print(f"\n   Übersetze nach {LANGUAGE_NAMES[language]} ({language.value})...")
        
        try:
            translated_text, confidence = await client.translate_to_language(
                simplified_text, 
                language,
                "mannix/llamax3-8b-alpaca:latest"
            )
            
            print(f"   ✅ Übersetzung erfolgreich (Vertrauen: {confidence:.2f})")
            print(f"   📝 Erste 100 Zeichen: {translated_text[:100]}...")
            
        except Exception as e:
            print(f"   ❌ Fehler bei {language.value}: {e}")
    
    # 4. Teste API-Endpunkte (mock)
    print("\n4. Teste neue API-Funktionen...")
    
    try:
        from app.models.document import ProcessingOptions
        
        # Teste ProcessingOptions
        options = ProcessingOptions(target_language=SupportedLanguage.ENGLISH)
        print(f"   ✅ ProcessingOptions: {options.dict()}")
        
        # Teste Language-Mapping
        print(f"   ✅ Sprachen verfügbar: {len(LANGUAGE_NAMES)}")
        print(f"   📋 Beispiel-Sprachen: {list(LANGUAGE_NAMES.keys())[:5]}")
        
    except Exception as e:
        print(f"   ❌ API-Test Fehler: {e}")
    
    print("\n🎉 Test abgeschlossen!")

if __name__ == "__main__":
    asyncio.run(test_language_translation()) 