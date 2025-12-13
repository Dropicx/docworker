#!/usr/bin/env python3
"""Privacy Filter Performance Benchmark Script.

Runs comprehensive benchmarks on the AdvancedPrivacyFilter (Issue #35 Phase 6.2):
- Processing time per document type
- Memory usage profiling
- Throughput testing (batch processing)
- Regression testing against <100ms target

Usage:
    python scripts/benchmark_privacy_filter.py
    python scripts/benchmark_privacy_filter.py --iterations 50
    python scripts/benchmark_privacy_filter.py --output benchmark_results.json
"""

import argparse
import gc
import json
import statistics
import sys
import time
import tracemalloc
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.privacy_filter_advanced import AdvancedPrivacyFilter


# ==================== SAMPLE DOCUMENTS ====================

SAMPLE_ARZTBRIEF_SHORT = """
Arztbrief
Patient: Müller, Hans
Geb.: 15.05.1965
Diagnose: Diabetes mellitus Typ 2 (E11.9)
Therapie: Metformin 1000mg
"""

SAMPLE_ARZTBRIEF_MEDIUM = """
Universitätsklinikum München
Medizinische Klinik und Poliklinik

Arztbrief

Patient: Mustermann, Max
Geb.: 22.03.1958
Adresse: Hauptstraße 42, 80331 München
Telefon: +49 89 12345678
Email: max.mustermann@email.de
Versichertennummer: A123456789

Diagnosen:
1. Diabetes mellitus Typ 2 (E11.9)
2. Arterielle Hypertonie (I10)
3. Morbus Parkinson (G20)
4. Hyperlipidämie (E78.0)

Aktuelle Medikation:
- Metformin 1000mg 1-0-1
- Ramipril 5mg 0-0-1
- Madopar 125mg 1-1-1
- Simvastatin 20mg 0-0-1

Laborwerte vom 15.01.2024:
- HbA1c: 7.2% (erhöht)
- Nüchtern-Glucose: 145 mg/dl
- Kreatinin: 1.1 mg/dl
- eGFR: 72 ml/min
- TSH: 2.1 mU/l
- Cholesterin gesamt: 220 mg/dl
- LDL: 140 mg/dl
- HDL: 45 mg/dl

Befund:
Der Patient stellte sich zur Kontrolluntersuchung vor. Die Blutzuckereinstellung
ist akzeptabel, jedoch besteht Optimierungsbedarf. Der Blutdruck war mit
145/90 mmHg leicht erhöht. Die Parkinson-Symptomatik ist unter Madopar stabil.

Empfehlung:
Fortführung der aktuellen Medikation. Kontrolle in 3 Monaten empfohlen.

Mit freundlichen Grüßen
Dr. med. Weber
Oberarzt
"""

SAMPLE_ARZTBRIEF_LONG = SAMPLE_ARZTBRIEF_MEDIUM + """

Anamnese:
Der 65-jährige Patient berichtet über gelegentliche Hypoglykämien am Vormittag,
insbesondere bei körperlicher Aktivität. Die Compliance bezüglich der Medikamenteneinnahme
ist gut. Der Patient führt regelmäßig Blutzuckerselbstkontrollen durch.

Familienanamnese:
- Mutter: Diabetes mellitus Typ 2, verstorben mit 78 Jahren an Herzinfarkt
- Vater: Arterielle Hypertonie, Schlaganfall mit 72 Jahren
- Geschwister: Bruder (68) - Diabetes mellitus Typ 2

Sozialanamnese:
- Berentet seit 2023
- Ehemals Bürokaufmann
- Verheiratet, 2 erwachsene Kinder
- Nichtraucher seit 10 Jahren (zuvor 20 pack years)
- Gelegentlicher Alkoholkonsum (1-2 Gläser Wein/Woche)

Körperliche Untersuchung:
- Größe: 175 cm, Gewicht: 85 kg, BMI: 27.8 kg/m²
- RR: 145/90 mmHg, Puls: 72/min, regelmäßig
- Herz: Reine Herztöne, keine pathologischen Geräusche
- Lunge: Vesikuläratmen beidseits, keine Rasselgeräusche
- Abdomen: Weich, keine Druckdolenz, keine Resistenzen
- Extremitäten: Keine Ödeme, Fußpulse beidseits tastbar

Apparative Diagnostik:
- EKG: Sinusrhythmus, Frequenz 70/min, keine ST-Veränderungen
- Langzeit-EKG (24h): Keine relevanten Rhythmusstörungen
- Echokardiographie: Normale LV-Funktion (EF 60%), keine Klappenvitien
- Duplexsonographie Carotiden: Leichte Plaquebildung beidseits, keine Stenosen

Zusätzliche Laborwerte (LOINC-Codes):
- Troponin T (6598-7): < 0.01 ng/ml
- NT-proBNP (30934-4): 125 pg/ml
- CRP (1988-5): 3.2 mg/l
- Ferritin (2500-7): 180 ng/ml
- Vitamin D (1989-3): 22 ng/ml (Insuffizienz)
- Vitamin B12 (2132-9): 450 pg/ml

Procedere:
1. Optimierung der antidiabetischen Therapie: Metformin-Dosis beibehalten,
   zusätzlich Einleitung einer SGLT2-Inhibitor-Therapie (Empagliflozin 10mg)
2. Vitamin D-Substitution: Dekristol 20.000 IE 1x/Woche für 8 Wochen
3. Ernährungsberatung empfohlen
4. Steigerung der körperlichen Aktivität (mind. 150 min/Woche)
5. Kontrolle HbA1c, Nierenfunktion und Elektrolyte in 3 Monaten

Weitere Termine:
- Augenarztliche Kontrolle (Funduskopie) in 6 Monaten
- Diabetologische Fußuntersuchung in 3 Monaten
- Nächster Termin bei uns: 15.04.2024

Kontakt für Rückfragen:
Sekretariat Prof. Dr. Schmidt: +49 89 4400-2345
Email: innere.sekretariat@med.uni-muenchen.de

Mit kollegialen Grüßen

Prof. Dr. med. Schmidt
Klinikdirektor
Facharzt für Innere Medizin
Diabetologie, Endokrinologie
"""

SAMPLE_BEFUNDBERICHT = """
Radiologischer Befundbericht

Patient: Schmidt, Anna
Geb.: 10.08.1972
Untersuchungsdatum: 20.01.2024
Untersuchung: MRT Schädel nativ und mit Kontrastmittel

Fragestellung:
Kopfschmerzen, Ausschluss intrakranieller Pathologie

Technik:
MRT des Schädels in T1-, T2- und FLAIR-Wichtung, DWI, zusätzlich
T1-Wichtung nach Kontrastmittelgabe (Gadovist 15ml i.v.)

Befund:
Normaler intrakranieller Befund. Keine Raumforderung. Keine Diffusionsstörung.
Keine pathologische Kontrastmittelaufnahme. Altersentsprechend unauffällige
Darstellung der basalen Hirngefäße. Nasennebenhöhlen und Mastoidzellen belüftet.

Beurteilung:
Kein Anhalt für intrakranielle Pathologie. Kein Hinweis auf
Raumforderung, Blutung oder Ischämie.

Dr. med. Bauer
Facharzt für Radiologie
"""

SAMPLE_LABORWERTE = """
Laborergebnisse

Patient: Weber, Klaus
Geb.: 05.12.1980
Entnahmedatum: 18.01.2024

Blutbild:
- Leukozyten: 7.2 /nl (Ref: 4.0-10.0)
- Erythrozyten: 4.8 /pl (Ref: 4.5-5.5)
- Hämoglobin: 14.5 g/dl (Ref: 13.0-17.0)
- Hämatokrit: 43% (Ref: 40-52)
- MCV: 89 fl (Ref: 80-96)
- MCH: 30 pg (Ref: 28-33)
- Thrombozyten: 250 /nl (Ref: 150-400)

Klinische Chemie:
- Glucose nüchtern: 95 mg/dl (Ref: 70-100)
- HbA1c: 5.4% (Ref: <5.7)
- Kreatinin: 0.9 mg/dl (Ref: 0.7-1.2)
- eGFR: 95 ml/min (Ref: >90)
- Natrium: 140 mmol/l (Ref: 136-145)
- Kalium: 4.2 mmol/l (Ref: 3.5-5.0)
- Calcium: 2.4 mmol/l (Ref: 2.2-2.6)

Leberwerte:
- GOT (AST): 25 U/l (Ref: <50)
- GPT (ALT): 30 U/l (Ref: <50)
- GGT: 35 U/l (Ref: <60)
- Bilirubin gesamt: 0.8 mg/dl (Ref: <1.2)

Gerinnung:
- Quick: 95% (Ref: 70-130)
- INR: 1.0 (Ref: 0.9-1.2)
- PTT: 32 sec (Ref: 26-40)

Befund:
Alle Parameter im Normbereich. Keine Auffälligkeiten.

Labor Dr. Müller & Partner
"""

SAMPLE_DOCUMENTS = {
    "arztbrief_short": {"text": SAMPLE_ARZTBRIEF_SHORT, "type": "ARZTBRIEF", "size": "short"},
    "arztbrief_medium": {"text": SAMPLE_ARZTBRIEF_MEDIUM, "type": "ARZTBRIEF", "size": "medium"},
    "arztbrief_long": {"text": SAMPLE_ARZTBRIEF_LONG, "type": "ARZTBRIEF", "size": "long"},
    "befundbericht": {"text": SAMPLE_BEFUNDBERICHT, "type": "BEFUNDBERICHT", "size": "medium"},
    "laborwerte": {"text": SAMPLE_LABORWERTE, "type": "LABORWERTE", "size": "medium"},
}


def calculate_percentile(data: list[float], percentile: float) -> float:
    """Calculate the percentile of a list of values."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    index = (len(sorted_data) - 1) * percentile / 100
    lower = int(index)
    upper = lower + 1
    if upper >= len(sorted_data):
        return sorted_data[lower]
    return sorted_data[lower] + (sorted_data[upper] - sorted_data[lower]) * (index - lower)


def benchmark_single_document(
    filter_instance: AdvancedPrivacyFilter,
    text: str,
    iterations: int = 10
) -> dict:
    """Benchmark a single document processing."""
    times = []
    metadata_samples = []

    for _ in range(iterations):
        gc.collect()  # Clean up before each iteration

        start = time.perf_counter()
        _, metadata = filter_instance.remove_pii(text)
        end = time.perf_counter()

        times.append((end - start) * 1000)  # Convert to ms
        metadata_samples.append(metadata)

    return {
        "iterations": iterations,
        "times_ms": {
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "min": min(times),
            "max": max(times),
            "stdev": statistics.stdev(times) if len(times) > 1 else 0,
            "p95": calculate_percentile(times, 95),
            "p99": calculate_percentile(times, 99),
        },
        "char_count": len(text),
        "sample_metadata": metadata_samples[0] if metadata_samples else {},
    }


def benchmark_batch_processing(
    filter_instance: AdvancedPrivacyFilter,
    documents: list[str],
    batch_sizes: list[int] = [1, 8, 16, 32]
) -> dict:
    """Benchmark batch processing throughput."""
    results = {}

    for batch_size in batch_sizes:
        gc.collect()

        start = time.perf_counter()
        _ = filter_instance.remove_pii_batch(documents, batch_size=batch_size)
        end = time.perf_counter()

        total_time_ms = (end - start) * 1000
        docs_per_second = len(documents) / (end - start) if (end - start) > 0 else 0

        results[f"batch_{batch_size}"] = {
            "batch_size": batch_size,
            "total_time_ms": total_time_ms,
            "avg_time_per_doc_ms": total_time_ms / len(documents),
            "throughput_docs_per_second": docs_per_second,
        }

    return results


def profile_memory(filter_instance: AdvancedPrivacyFilter, text: str) -> dict:
    """Profile memory usage during processing."""
    gc.collect()
    tracemalloc.start()

    _, _ = filter_instance.remove_pii(text)

    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "current_bytes": current,
        "peak_bytes": peak,
        "current_mb": round(current / 1024 / 1024, 2),
        "peak_mb": round(peak / 1024 / 1024, 2),
    }


def run_full_benchmark(iterations: int = 20) -> dict:
    """Run the complete benchmark suite."""
    print("=" * 60)
    print("Privacy Filter Performance Benchmark")
    print("=" * 60)
    print(f"Iterations per document: {iterations}")
    print()

    # Initialize filter (time this too)
    print("Initializing AdvancedPrivacyFilter...")
    init_start = time.perf_counter()
    filter_instance = AdvancedPrivacyFilter(load_custom_terms=False)
    init_time = (time.perf_counter() - init_start) * 1000
    print(f"  Initialization time: {init_time:.1f}ms")
    print(f"  NER available: {filter_instance.has_ner}")
    print(f"  Medical terms: {len(filter_instance.medical_terms)}")
    print(f"  Drug database: {len(filter_instance.drug_database)}")
    print()

    results = {
        "timestamp": datetime.now().isoformat(),
        "iterations": iterations,
        "filter_info": {
            "init_time_ms": init_time,
            "has_ner": filter_instance.has_ner,
            "medical_terms_count": len(filter_instance.medical_terms),
            "drug_database_count": len(filter_instance.drug_database),
            "abbreviations_count": len(filter_instance.protected_abbreviations),
        },
        "documents": {},
        "batch_processing": {},
        "memory_profile": {},
        "summary": {},
    }

    # Benchmark individual documents
    print("Benchmarking individual documents...")
    all_times = []

    for doc_name, doc_info in SAMPLE_DOCUMENTS.items():
        print(f"  {doc_name} ({doc_info['size']}, {len(doc_info['text'])} chars)...", end=" ")

        doc_results = benchmark_single_document(
            filter_instance, doc_info["text"], iterations
        )
        doc_results["document_type"] = doc_info["type"]
        doc_results["size_category"] = doc_info["size"]

        results["documents"][doc_name] = doc_results
        all_times.extend([doc_results["times_ms"]["mean"]])

        status = "✓" if doc_results["times_ms"]["mean"] < 100 else "⚠️ SLOW"
        print(f"{doc_results['times_ms']['mean']:.1f}ms {status}")

    # Batch processing benchmark
    print("\nBenchmarking batch processing...")
    batch_docs = [doc["text"] for doc in SAMPLE_DOCUMENTS.values()] * 4  # 20 docs
    results["batch_processing"] = benchmark_batch_processing(filter_instance, batch_docs)

    for batch_name, batch_result in results["batch_processing"].items():
        print(f"  {batch_name}: {batch_result['avg_time_per_doc_ms']:.1f}ms/doc, "
              f"{batch_result['throughput_docs_per_second']:.1f} docs/sec")

    # Memory profiling
    print("\nProfiling memory usage...")
    results["memory_profile"] = profile_memory(
        filter_instance, SAMPLE_ARZTBRIEF_LONG
    )
    print(f"  Peak memory: {results['memory_profile']['peak_mb']} MB")

    # Summary
    overall_avg = statistics.mean(all_times)
    results["summary"] = {
        "overall_avg_ms": overall_avg,
        "target_ms": 100,
        "passes_target": overall_avg < 100,
        "slowest_doc": max(results["documents"].items(),
                          key=lambda x: x[1]["times_ms"]["mean"])[0],
        "fastest_doc": min(results["documents"].items(),
                          key=lambda x: x[1]["times_ms"]["mean"])[0],
    }

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Overall average: {overall_avg:.1f}ms")
    print(f"Target: <100ms")
    print(f"Status: {'✅ PASS' if overall_avg < 100 else '❌ FAIL - REGRESSION DETECTED'}")
    print(f"Slowest: {results['summary']['slowest_doc']}")
    print(f"Fastest: {results['summary']['fastest_doc']}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Privacy Filter Performance Benchmark")
    parser.add_argument(
        "--iterations", "-i", type=int, default=20,
        help="Number of iterations per document (default: 20)"
    )
    parser.add_argument(
        "--output", "-o", type=str, default=None,
        help="Output JSON file path (optional)"
    )
    args = parser.parse_args()

    results = run_full_benchmark(iterations=args.iterations)

    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to: {output_path}")

    # Exit with error code if regression detected
    if not results["summary"]["passes_target"]:
        print("\n⚠️  PERFORMANCE REGRESSION DETECTED!")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
