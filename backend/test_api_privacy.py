#!/usr/bin/env python3
"""
Test-Skript für Privacy Filter über die API
Kann lokal oder gegen Railway getestet werden
"""

import httpx
import asyncio
import json
import sys

# Konfiguration
LOCAL_URL = "http://localhost:8000"
RAILWAY_URL = "https://doctranslator-production.up.railway.app"  # Ersetze mit deiner Railway URL

# Wähle die URL (kann als Argument übergeben werden)
API_URL = sys.argv[1] if len(sys.argv) > 1 else LOCAL_URL

async def test_privacy_filter():
    """Testet den Privacy Filter über die API"""
    
    print(f"🔬 Teste Privacy Filter auf: {API_URL}")
    print("=" * 60)
    
    # Test-Dokument mit vielen verschiedenen Namen
    test_document = """
    Universitätsklinikum München
    Abteilung für Innere Medizin
    
    Sehr geehrte Frau Dr. med. Sabine Müller-Schmidt,
    
    wir berichten über Ihren Patienten Herrn Wolfgang von Grafenstein,
    geboren am 15.03.1965 in München.
    
    Anamnese:
    Der Patient wurde erstmals von Dr. Alexander Zimmermann untersucht.
    Die Ehefrau des Patienten, Frau Elisabeth von Grafenstein, berichtet
    über folgende Symptome.
    
    Befunde:
    - Morbus Crohn (diagnostiziert von Prof. Dr. Hartmann)
    - Baker-Zyste am rechten Knie
    - Parkinson-Syndrom im Frühstadium
    - Frank-Starling-Kurve zeigt normale kardiale Funktion
    
    Laborwerte:
    - Hämoglobin: 14.2 g/dl (Norm: 13-17)
    - Leukozyten: 7.8 /nl (Norm: 4-10)
    - CRP: 12 mg/l (erhöht)
    - HbA1c: 6.8% (leicht erhöht)
    - TSH: 2.1 mU/l (normal)
    - BMI: 28 kg/m²
    
    Medikation:
    - Mesalazin 500mg 1-0-1 (für Morbus Crohn)
    - L-Dopa 100mg 1-1-1 (für Parkinson)
    - Ramipril 5mg 1-0-0
    
    Weitere behandelnde Ärzte:
    - Hausarzt: Dr. med. Friedrich Wilhelm Schulze
    - Neurologe: Prof. Dr. Dr. h.c. Jean-Baptiste Dubois
    - Gastroenterologe: Dr. med. Anastasia Petrov-Romanova
    
    Kontakt:
    Patient wohnhaft: Leopoldstraße 234, 80802 München
    Tel: 089-12345678
    Email: w.grafenstein@email.de
    
    Mit freundlichen Grüßen
    
    Prof. Dr. med. Hans-Joachim von Reichenberg
    Chefarzt Innere Medizin
    """
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Teste den translate Endpoint
            print("\n📤 Sende Dokument zur Übersetzung...")
            
            response = await client.post(
                f"{API_URL}/api/translate",
                json={
                    "text": test_document,
                    "document_type": "arztbrief"
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                
                print("\n✅ Übersetzung erfolgreich!")
                print(f"   Dokumenttyp: {result.get('document_type', 'N/A')}")
                print(f"   Konfidenz: {result.get('confidence', 0):.2%}")
                
                translated_text = result.get('translated_text', '')
                
                print("\n📋 Überprüfe PII-Entfernung:")
                print("-" * 40)
                
                # Namen die entfernt sein sollten
                names_to_check = [
                    "Sabine Müller-Schmidt",
                    "Wolfgang von Grafenstein",
                    "Elisabeth von Grafenstein",
                    "Alexander Zimmermann",
                    "Friedrich Wilhelm Schulze",
                    "Jean-Baptiste Dubois",
                    "Anastasia Petrov-Romanova",
                    "Hans-Joachim von Reichenberg"
                ]
                
                removed_count = 0
                for name in names_to_check:
                    if name not in translated_text:
                        print(f"  ✓ '{name}' wurde entfernt")
                        removed_count += 1
                    else:
                        print(f"  ✗ '{name}' ist NOCH VORHANDEN!")
                
                print(f"\n  → {removed_count}/{len(names_to_check)} Namen entfernt")
                
                # Medizinische Begriffe die erhalten bleiben sollten
                print("\n📋 Überprüfe medizinische Begriffe:")
                print("-" * 40)
                
                medical_terms = [
                    "Morbus Crohn",
                    "Baker-Zyste",
                    "Parkinson",
                    "Frank-Starling",
                    "Hämoglobin",
                    "Leukozyten",
                    "HbA1c",
                    "BMI",
                    "Mesalazin",
                    "L-Dopa",
                    "Ramipril"
                ]
                
                preserved_count = 0
                for term in medical_terms:
                    if term in translated_text or term.lower() in translated_text.lower():
                        print(f"  ✓ '{term}' wurde erhalten")
                        preserved_count += 1
                    else:
                        print(f"  ✗ '{term}' FEHLT!")
                
                print(f"\n  → {preserved_count}/{len(medical_terms)} medizinische Begriffe erhalten")
                
                # Andere PII
                print("\n📋 Überprüfe andere sensible Daten:")
                print("-" * 40)
                
                sensitive_data = [
                    ("15.03.1965", "Geburtsdatum"),
                    ("Leopoldstraße 234", "Adresse"),
                    ("80802", "PLZ"),
                    ("089-12345678", "Telefon"),
                    ("w.grafenstein@email.de", "Email")
                ]
                
                removed_sensitive = 0
                for data, dtype in sensitive_data:
                    if data not in translated_text:
                        print(f"  ✓ {dtype} wurde entfernt")
                        removed_sensitive += 1
                    else:
                        print(f"  ✗ {dtype} ({data}) ist NOCH VORHANDEN!")
                
                print(f"\n  → {removed_sensitive}/{len(sensitive_data)} sensible Daten entfernt")
                
                # Zeige einen Ausschnitt
                print("\n📄 Ausschnitt des bereinigten Texts:")
                print("-" * 40)
                print(translated_text[:500] + "..." if len(translated_text) > 500 else translated_text)
                
                # Gesamtbewertung
                total_removed = removed_count + removed_sensitive
                total_should_remove = len(names_to_check) + len(sensitive_data)
                removal_rate = total_removed / total_should_remove if total_should_remove > 0 else 0
                
                preservation_rate = preserved_count / len(medical_terms) if len(medical_terms) > 0 else 0
                
                print("\n" + "=" * 60)
                print("📊 GESAMTBEWERTUNG:")
                print(f"   PII-Entfernung: {removal_rate:.1%} ({total_removed}/{total_should_remove})")
                print(f"   Medizinische Daten erhalten: {preservation_rate:.1%} ({preserved_count}/{len(medical_terms)})")
                
                if removal_rate >= 0.8 and preservation_rate >= 0.8:
                    print("\n   ✅ Privacy Filter funktioniert GUT!")
                elif removal_rate >= 0.6 and preservation_rate >= 0.6:
                    print("\n   ⚠️ Privacy Filter funktioniert TEILWEISE")
                else:
                    print("\n   ❌ Privacy Filter muss verbessert werden")
                
            else:
                print(f"\n❌ API Fehler: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"\n❌ Fehler beim API-Aufruf: {e}")

async def main():
    """Hauptfunktion"""
    print("🚀 Privacy Filter API Test")
    print("=" * 60)
    
    # Teste Verbindung
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(f"{API_URL}/health")
            if response.status_code == 200:
                print(f"✅ API ist erreichbar auf {API_URL}")
            else:
                print(f"⚠️ API antwortet mit Status {response.status_code}")
        except:
            print(f"❌ Kann keine Verbindung zu {API_URL} herstellen")
            print("\nVersuche mit:")
            print(f"  python {sys.argv[0]} {LOCAL_URL}  # für lokal")
            print(f"  python {sys.argv[0]} <RAILWAY_URL>  # für Railway")
            return
    
    await test_privacy_filter()

if __name__ == "__main__":
    print("\nUsage:")
    print(f"  python {sys.argv[0]}                    # Test lokal")
    print(f"  python {sys.argv[0]} <API_URL>          # Test gegen spezifische URL")
    print()
    
    asyncio.run(main())