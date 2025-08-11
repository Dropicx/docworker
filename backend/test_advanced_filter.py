#!/usr/bin/env python3
"""
Test-Skript für den Advanced Privacy Filter mit NER
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.privacy_filter_advanced import AdvancedPrivacyFilter

def test_advanced_filter():
    """Testet die erweiterte Privacy Filter Funktionalität"""
    
    # Initialisiere Filter
    filter = AdvancedPrivacyFilter()
    
    print("=" * 60)
    print("🧪 ADVANCED PRIVACY FILTER TEST")
    print("=" * 60)
    
    # Test 1: Unbekannte Namen (nicht in statischer Liste)
    test_text_1 = """
    Sehr geehrte Frau Sabine Zimmermann-Huber,
    
    wir berichten über Herrn Maximilian von Grafenstein, geboren am 15.03.1965.
    Der Patient wurde von Dr. Johanna Schreiber-Klein untersucht.
    
    Befund:
    Hämoglobin: 12.5 g/dl (Norm: 12-16)
    Die kardiale Funktion ist unauffällig.
    """
    
    result_1 = filter.remove_pii(test_text_1)
    print("\n📝 TEST 1 - Unbekannte Namen:")
    print("Original:")
    print(test_text_1)
    print("\nBereinigt:")
    print(result_1)
    print("-" * 50)
    
    # Test 2: Medizinische Begriffe die wie Namen aussehen
    test_text_2 = """
    Patient: Unbekannt
    
    Die Untersuchung wurde in der Abteilung Innere Medizin durchgeführt.
    Prof. Dr. med. Alexander Hartmann, Chefarzt Kardiologie
    
    Diagnose: 
    - Morbus Crohn (chronisch entzündliche Darmerkrankung)
    - Morbus Basedow (Autoimmunerkrankung der Schilddrüse)
    - Baker-Zyste (Knie)
    
    Medikation:
    - Mesalazin 500mg (Morbus Crohn)
    - Thiamazol 10mg (Morbus Basedow)
    """
    
    result_2 = filter.remove_pii(test_text_2)
    print("\n📝 TEST 2 - Medizinische Eponyme vs. echte Namen:")
    print("Original:")
    print(test_text_2)
    print("\nBereinigt:")
    print(result_2)
    
    # Prüfe ob medizinische Eponyme erhalten bleiben
    medical_eponyms = ['Morbus Crohn', 'Morbus Basedow', 'Baker-Zyste']
    print("\n✅ Erhaltene medizinische Eponyme:")
    for eponym in medical_eponyms:
        if eponym in result_2:
            print(f"  ✓ {eponym}")
        else:
            print(f"  ✗ {eponym} FEHLT!")
    
    # Prüfe ob echte Namen entfernt wurden
    real_names = ['Alexander Hartmann', 'Sabine Zimmermann-Huber', 'Maximilian von Grafenstein']
    print("\n🔒 Sollten entfernt sein:")
    for name in real_names:
        if name not in result_2:
            print(f"  ✓ {name} entfernt")
        else:
            print(f"  ✗ {name} NOCH VORHANDEN!")
    
    print("-" * 50)
    
    # Test 3: Verschiedene Namensformate
    test_text_3 = """
    Universitätsklinikum Berlin
    Abteilung für Gastroenterologie
    
    Patientenbericht:
    
    Frau Dr. rer. nat. Lisa-Marie Schulze-Böhm
    Herrn Dipl.-Ing. Hans-Jürgen Müller-Lüdenscheid
    Familie von und zu Guttenberg
    
    Untersucht von:
    OA Dr. med. habil. Friedrich Wilhelm von Preußen
    AA Dr. med. Anne-Sophie Charlotte Elisabeth von Habsburg
    
    Befund: Die hepatische Funktion zeigt keine Auffälligkeiten.
    Die Patientin Anna klagt über abdominale Schmerzen.
    Patient Max zeigt Zeichen einer Gastritis.
    """
    
    result_3 = filter.remove_pii(test_text_3)
    print("\n📝 TEST 3 - Komplexe Namensformate:")
    print("Original (gekürzt):")
    print(test_text_3[:300] + "...")
    print("\nBereinigt (gekürzt):")
    print(result_3[:300] + "...")
    print("-" * 50)
    
    # Test 4: Kontext-sensitive Erkennung
    test_text_4 = """
    Der Patient Frank wurde in der Frank-Starling-Kurve untersucht.
    Die Weber-Fechner-Regel wurde angewendet.
    Herr Weber wurde von Dr. Fechner behandelt.
    
    Die Parkinson-Krankheit wurde diagnostiziert.
    Herrn Parkinson geht es heute besser.
    
    BMI aktuell: 28
    Patient Klaus hat einen BMI von 28.
    """
    
    result_4 = filter.remove_pii(test_text_4)
    print("\n📝 TEST 4 - Kontext-sensitive Erkennung:")
    print("Original:")
    print(test_text_4)
    print("\nBereinigt:")
    print(result_4)
    
    # Prüfe Erhaltung medizinischer Begriffe
    print("\n✅ Medizinische Begriffe (sollten erhalten bleiben):")
    medical = ['Frank-Starling-Kurve', 'Weber-Fechner-Regel', 'Parkinson-Krankheit', 'BMI']
    for term in medical:
        if term in result_4:
            print(f"  ✓ {term}")
        else:
            print(f"  ✗ {term} FEHLT!")
    
    print("-" * 50)
    
    # Test 5: Großer realistischer Text
    test_text_5 = """
    Klinikum Großhadern München
    Zentrum für Innere Medizin
    
    Sehr geehrte Frau Kollegin Dr. med. Angelika Bauer-Schmidt,
    
    wir berichten über Ihre Patientin Frau Gertrud Elfriede Müller-Meier, 
    geb. Schneider, geboren am 12.05.1958 in München-Schwabing.
    
    Anamnese:
    Die Patientin stellte sich erstmals am 15.01.2024 in unserer Notaufnahme vor.
    Sie wurde begleitet von ihrem Ehemann Wolfgang Müller-Meier und ihrer 
    Tochter Christina Müller-Meier.
    
    Hauptdiagnosen:
    1. Diabetes mellitus Typ 2 (ICD E11.9)
       - Erstdiagnose durch Dr. Konstantin Alexandropoulos im Jahr 2015
       - HbA1c aktuell: 7.8%
    
    2. Arterielle Hypertonie (ICD I10.90)
       - Bekannt seit 2010
       - RR-Werte: 145/90 mmHg unter Therapie
    
    3. Hashimoto-Thyreoiditis (ICD E06.3)
       - Diagnose durch Prof. Takahashi 2018
       - TSH: 2.5 mU/l unter L-Thyroxin
    
    Aktuelle Medikation (verordnet durch Dr. Bernhard Hoffmann-Rüdiger):
    - Metformin 1000mg 1-0-1
    - Ramipril 5mg 1-0-0
    - L-Thyroxin 75µg 1-0-0
    
    Allergien: 
    Penicillin-Allergie (dokumentiert von Dr. Elisabeth von Trapp 2019)
    
    Sozialanamnese:
    Verheiratet mit Wolfgang Müller-Meier (Rentner)
    2 Kinder: Christina (32) und Maximilian (28)
    Wohnhaft: Leopoldstraße 234a, 80802 München
    Tel: 089-123456789
    Email: gertrud.mueller@email.de
    
    Behandelnde Ärzte:
    - Hausarzt: Dr. med. Friedrich-Wilhelm Schulze-Delitzsch
    - Diabetologe: Dr. med. Anastasia Romanova-Petrov
    - Kardiologe: Prof. Dr. Dr. h.c. mult. Jean-Baptiste Dubois
    
    Mit kollegialen Grüßen
    
    Prof. Dr. med. Hans-Joachim Freiherr von und zu Löwenstein
    Chefarzt Innere Medizin
    
    Dr. med. Marie-Antoinette de la Rochefoucauld
    Oberärztin Endokrinologie
    """
    
    result_5 = filter.remove_pii(test_text_5)
    print("\n📝 TEST 5 - Realistischer komplexer Arztbrief:")
    print(f"Original: {len(test_text_5)} Zeichen")
    print(f"Bereinigt: {len(result_5)} Zeichen")
    
    # Prüfe wichtige medizinische Informationen
    print("\n✅ Erhaltene medizinische Informationen:")
    medical_info = [
        'Diabetes mellitus Typ 2', 'ICD E11.9', 'HbA1c', '7.8%',
        'Arterielle Hypertonie', 'ICD I10.90', '145/90 mmHg',
        'Hashimoto-Thyreoiditis', 'ICD E06.3', 'TSH', '2.5 mU/l',
        'Metformin 1000mg', 'Ramipril 5mg', 'L-Thyroxin 75µg',
        'Penicillin-Allergie'
    ]
    
    preserved = 0
    for info in medical_info:
        if info in result_5:
            preserved += 1
    
    print(f"  {preserved}/{len(medical_info)} medizinische Informationen erhalten")
    
    # Prüfe Entfernung von Namen
    print("\n🔒 Entfernte Personendaten:")
    names_to_remove = [
        'Gertrud Elfriede Müller-Meier', 'Wolfgang Müller-Meier',
        'Christina Müller-Meier', 'Angelika Bauer-Schmidt',
        'Konstantin Alexandropoulos', 'Bernhard Hoffmann-Rüdiger',
        'Friedrich-Wilhelm Schulze-Delitzsch', 'Anastasia Romanova-Petrov',
        'Hans-Joachim Freiherr von und zu Löwenstein'
    ]
    
    removed = 0
    for name in names_to_remove:
        if name not in result_5:
            removed += 1
    
    print(f"  {removed}/{len(names_to_remove)} Namen erfolgreich entfernt")
    
    # Zeige einen Ausschnitt des bereinigten Texts
    print("\n📄 Ausschnitt des bereinigten Texts:")
    print(result_5[:500] + "...")

if __name__ == "__main__":
    print("🔬 Teste Advanced Privacy Filter mit NER...")
    try:
        test_advanced_filter()
        print("\n✅ Alle Tests abgeschlossen!")
    except Exception as e:
        print(f"\n❌ Fehler: {e}")
        import traceback
        traceback.print_exc()