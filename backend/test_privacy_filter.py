#!/usr/bin/env python3
"""
Test-Skript für den Privacy Filter
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.privacy_filter import PrivacyFilter

def test_privacy_filter():
    """Testet die Privacy Filter Funktionalität"""
    
    # Initialisiere Filter
    filter = PrivacyFilter()
    
    # Test 1: Entfernung von Namen
    test_text_1 = """
    Sehr geehrte Frau Maria Müller,
    geboren am 15.03.1965
    
    Befund vom 10.01.2024:
    Hämoglobin: 12.5 g/dl (Norm: 12-16)
    Leukozyten: 6.8 /nl (Norm: 4.0-10.0)
    
    Mit freundlichen Grüßen
    Dr. Hans Schmidt
    """
    
    result_1 = filter.remove_pii(test_text_1)
    print("TEST 1 - Namen und Geburtsdaten:")
    print("Original:")
    print(test_text_1)
    print("\nBereinigt:")
    print(result_1)
    print("-" * 50)
    
    # Test 2: Entfernung von Adressen
    test_text_2 = """
    Patient: Max Mustermann
    Adresse: Hauptstraße 42
    12345 Berlin
    Tel: 030-1234567
    Email: max.mustermann@email.de
    
    Diagnose: Hypertonie ICD I10.90
    Medikation: Ramipril 5mg 1-0-0
    """
    
    result_2 = filter.remove_pii(test_text_2)
    print("\nTEST 2 - Adressen und Kontaktdaten:")
    print("Original:")
    print(test_text_2)
    print("\nBereinigt:")
    print(result_2)
    print("-" * 50)
    
    # Test 3: Erhaltung medizinischer Daten
    test_text_3 = """
    Geschlecht: männlich
    Versicherungsnr: 123456789
    
    Laborwerte vom 15.10.2024:
    - Glucose: 95 mg/dl (Norm: 70-100)
    - HbA1c: 5.8% (Norm: <6.5%)
    - Kreatinin: 0.9 mg/dl (Norm: 0.7-1.2)
    
    siehe Anhang: Weitere Laborwerte
    
    ANHANG - Laborwerte:
    TSH: 2.1 mU/l (Norm: 0.4-4.0)
    fT4: 1.3 ng/dl (Norm: 0.9-1.7)
    """
    
    result_3 = filter.remove_pii(test_text_3)
    print("\nTEST 3 - Medizinische Daten erhalten:")
    print("Original:")
    print(test_text_3)
    print("\nBereinigt:")
    print(result_3)
    print("-" * 50)
    
    # Test 4: Validierung
    validation = filter.validate_medical_content_preserved(test_text_3, result_3)
    print(f"\nValidierung: Medizinische Inhalte erhalten? {validation}")
    
    # Test 5: Komplexer medizinischer Text
    test_text_4 = """
    Universitätsklinikum München
    Abteilung für Innere Medizin
    
    Sehr geehrte Frau Dr. Andrea Weber,
    
    wir berichten über Ihren Patienten Herrn Klaus Fischer, geb. 12.05.1958,
    wohnhaft in der Bergstraße 15, 80333 München.
    
    Aufnahmedatum: 01.12.2024
    Entlassdatum: 05.12.2024
    
    Hauptdiagnose: 
    - Akutes Koronarsyndrom ICD I20.0
    - Diabetes mellitus Typ 2 ICD E11.9
    
    Durchgeführte Untersuchungen:
    1. Herzkatheteruntersuchung OPS 1-275.0
       → LAD-Stenose 80%, RCA 50%
    2. Echokardiographie
       → EF 45%, keine regionalen Wandbewegungsstörungen
    
    Laborwerte bei Aufnahme:
    - Troponin T: 0.8 ng/ml (erhöht, Norm: <0.014)
    - CK-MB: 45 U/l (erhöht, Norm: <25)
    - Cholesterin gesamt: 280 mg/dl (erhöht, Norm: <200)
    - LDL: 180 mg/dl (erhöht, Norm: <100)
    - HDL: 35 mg/dl (erniedrigt, Norm: >40)
    
    Therapie:
    - PCI mit Stent-Implantation LAD
    - ASS 100mg 1-0-0
    - Clopidogrel 75mg 1-0-0
    - Atorvastatin 40mg 0-0-1
    - Metoprolol 47,5mg 1-0-1
    - Ramipril 5mg 1-0-0
    
    Empfehlungen:
    - Kardiale Rehabilitation
    - Gewichtsreduktion (BMI aktuell 32)
    - Nikotinkarenz
    - Kontrolle in 3 Monaten
    
    Mit kollegialen Grüßen
    Prof. Dr. med. Thomas Bauer
    Chefarzt Kardiologie
    """
    
    result_4 = filter.remove_pii(test_text_4)
    print("\nTEST 4 - Komplexer Arztbrief:")
    print("Original (gekürzt):")
    print(test_text_4[:500] + "...")
    print("\nBereinigt (gekürzt):")
    print(result_4[:500] + "...")
    
    # Prüfe ob wichtige medizinische Informationen erhalten sind
    important_terms = ['ICD I20.0', 'ICD E11.9', 'OPS 1-275.0', 'Troponin', 
                      'Stent-Implantation', 'ASS 100mg', 'BMI']
    
    print("\n✅ Erhaltene medizinische Begriffe:")
    for term in important_terms:
        if term in result_4:
            print(f"  ✓ {term}")
        else:
            print(f"  ✗ {term} FEHLT!")
    
    # Prüfe ob PII entfernt wurde
    pii_terms = ['Klaus Fischer', 'Andrea Weber', 'Bergstraße 15', '80333', 
                 '12.05.1958', 'Thomas Bauer']
    
    print("\n🔒 Entfernte persönliche Daten:")
    for term in pii_terms:
        if term not in result_4:
            print(f"  ✓ {term} entfernt")
        else:
            print(f"  ✗ {term} NOCH VORHANDEN!")

if __name__ == "__main__":
    print("🔬 Teste Privacy Filter...")
    print("=" * 60)
    test_privacy_filter()
    print("\n✅ Tests abgeschlossen!")