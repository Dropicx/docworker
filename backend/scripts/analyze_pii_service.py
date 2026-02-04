#!/usr/bin/env python3
"""
PII Service Analysis Script

Tests the PII service at pii.fra-la.de to identify:
1. False positives (medical terms incorrectly removed)
2. False negatives (PII not removed)

Usage:
    PII_API_KEY=your-key python scripts/analyze_pii_service.py
"""

import os
import re
import requests
from collections import defaultdict

# PII Service configuration
PII_URL = "https://pii.fra-la.de/remove-pii"
PII_API_KEY = os.getenv(
    "PII_API_KEY", "2070e777e9e423da7328bba459f4e23db36049a33b364b4b65aadef47a756f20"
)

# Test cases with expected behavior
TEST_CASES = [
    # === FALSE NEGATIVE TESTS (PII that should be removed) ===
    {
        "name": "Patient name after PLZ",
        "input": "[PLZ_CITY], Fritz, , Status M\nPatient-Nr: 12345",
        "should_remove": ["Fritz"],  # First name should be removed
        "should_preserve": ["Status", "Patient-Nr"],
    },
    {
        "name": "Patient name in comma format",
        "input": "Patient: Müller, Hans\ngeb. 15.03.1980",
        "should_remove": ["Müller", "Hans", "15.03.1980"],
        "should_preserve": ["Patient", "geb."],
    },
    {
        "name": "German first names standalone",
        "input": "Befund für Maria, geboren am 01.01.1990, wohnhaft in Berlin",
        "should_remove": ["Maria", "01.01.1990", "Berlin"],
        "should_preserve": ["Befund", "geboren", "wohnhaft"],
    },
    {
        "name": "Hospital names should be removed",
        "input": "Terminvereinbarung mit Dr. Schmidt, Maria Hilf Kliniken Mönchengladbach",
        "should_remove": ["Dr. Schmidt", "Maria Hilf Kliniken", "Mönchengladbach"],
        "should_preserve": ["Terminvereinbarung"],
    },
    # === FALSE POSITIVE TESTS (Medical terms that should be preserved) ===
    {
        "name": "Child-Pugh Score",
        "input": "Leberzirrhose Child B (9 Punkte), MELD-Score 10",
        "should_remove": [],
        "should_preserve": ["Child B", "MELD-Score", "Leberzirrhose"],
    },
    {
        "name": "Medical abbreviations",
        "input": "Z. n. TIPS-Anlage, ÖGD unauffällig, ERCP geplant",
        "should_remove": [],
        "should_preserve": ["Z. n.", "TIPS", "ÖGD", "ERCP"],
    },
    {
        "name": "Lab values with units",
        "input": "LDH 994 U/l, CK 4688 U/l, Kreatinin 1,5 mg/dl",
        "should_remove": [],
        "should_preserve": ["U/l", "mg/dl", "LDH", "CK", "Kreatinin"],
    },
    {
        "name": "Vitamins",
        "input": "Vitamin D Mangel, Substitution mit Vit. B12",
        "should_remove": [],
        "should_preserve": ["Vitamin D", "Vit. B12"],
    },
    {
        "name": "Anatomical terms",
        "input": "Pfortader offen, Lebervenen durchgängig, Milzvene thrombosiert",
        "should_remove": [],
        "should_preserve": ["Pfortader", "Lebervenen", "Milzvene"],
    },
    {
        "name": "Medical procedures",
        "input": "TIPSS-Erweiterung auf 9mm, Parazentese von 5L Aszites",
        "should_remove": [],
        "should_preserve": ["TIPSS", "Parazentese", "Aszites"],
    },
    {
        "name": "Medical device frequency (4000 Hz)",
        "input": "Audiometrie: Hörschwelle bei 4000 Hz normal",
        "should_remove": [],
        "should_preserve": ["4000 Hz", "Audiometrie", "Hörschwelle"],
    },
    {
        "name": "Medications",
        "input": "Metformin 500mg 1-0-1, Ramipril 2,5mg, ASS 100mg",
        "should_remove": [],
        "should_preserve": ["Metformin", "Ramipril", "ASS"],
    },
    # === COMPLEX DOCUMENT TEST ===
    {
        "name": "Full medical document excerpt",
        "input": """
[HOSPITAL_LETTERHEAD]
Patient: Müller, Hans, geb. 15.03.1980
Musterstr. 15, 12345 Berlin

Diagnosen:
1. Leberzirrhose Child B (9 Punkte), äthyltoxisch
   - MELD-Score 10, Meld Na 24
   - Z. n. TIPS-Anlage 02/2024
   - Pfortader und Lebervenen sonografisch offen

2. Polymyositis
   - LDH 994 U/l, CK 4688 U/l
   - ANA negativ, ENA negativ

Medikation:
- Metformin 500mg 1-0-1
- Vitamin D 20.000 IE 1x/Wo
- Ramipril 2,5mg 1-0-1

Procedere:
Wiedervorstellung in der Abteilung von Dr. Weber, Universitätsklinikum Köln

Mit freundlichen Grüßen,
Dr. med. Schmidt
        """,
        "should_remove": [
            "Müller",
            "Hans",
            "15.03.1980",
            "Musterstr. 15",
            "12345 Berlin",
            "Dr. Weber",
            "Universitätsklinikum Köln",
            "Dr. med. Schmidt",
        ],
        "should_preserve": [
            "Child B",
            "MELD-Score",
            "TIPS",
            "Pfortader",
            "Lebervenen",
            "LDH",
            "CK",
            "U/l",
            "ANA",
            "ENA",
            "Metformin",
            "Vitamin D",
            "Ramipril",
        ],
    },
]


def call_pii_service(text: str) -> dict:
    """Call the PII service and return the response."""
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": PII_API_KEY,
    }
    payload = {"text": text, "language": "de", "include_metadata": True}
    response = requests.post(PII_URL, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    return response.json()


def analyze_result(test_case: dict, result: dict) -> dict:
    """Analyze the PII service result against expected behavior."""
    cleaned_text = result.get("cleaned_text", "")
    original_text = test_case["input"]

    analysis = {
        "name": test_case["name"],
        "false_negatives": [],  # PII not removed (should have been)
        "false_positives": [],  # Terms incorrectly removed (should have been preserved)
        "correct_removals": [],
        "correct_preservations": [],
    }

    # Check false negatives (PII that should have been removed but wasn't)
    for term in test_case.get("should_remove", []):
        if term in cleaned_text:
            analysis["false_negatives"].append(term)
        else:
            analysis["correct_removals"].append(term)

    # Check false positives (medical terms that should have been preserved but weren't)
    for term in test_case.get("should_preserve", []):
        if term not in cleaned_text and term in original_text:
            analysis["false_positives"].append(term)
        elif term in cleaned_text:
            analysis["correct_preservations"].append(term)

    return analysis


def generate_report(results: list) -> str:
    """Generate a markdown report of the analysis."""
    report = "# PII Service Analysis Report\n\n"
    report += f"**Service URL:** {PII_URL}\n"
    report += f"**Date:** {__import__('datetime').datetime.now().isoformat()}\n\n"

    # Summary
    total_fn = sum(len(r["false_negatives"]) for r in results)
    total_fp = sum(len(r["false_positives"]) for r in results)
    total_correct = sum(
        len(r["correct_removals"]) + len(r["correct_preservations"]) for r in results
    )

    report += "## Summary\n\n"
    report += f"| Metric | Count |\n"
    report += f"|--------|-------|\n"
    report += f"| Test Cases | {len(results)} |\n"
    report += f"| False Negatives (PII not removed) | {total_fn} |\n"
    report += f"| False Positives (medical terms removed) | {total_fp} |\n"
    report += f"| Correct | {total_correct} |\n\n"

    if total_fn + total_fp == 0:
        report += "**All tests passed!**\n\n"
    else:
        report += f"**Issues found: {total_fn + total_fp}**\n\n"

    # Details
    report += "## Test Case Details\n\n"

    for r in results:
        status = "PASS" if not r["false_negatives"] and not r["false_positives"] else "FAIL"
        report += f"### {r['name']} [{status}]\n\n"

        if r["false_negatives"]:
            report += f"**False Negatives (PII not removed):**\n"
            for term in r["false_negatives"]:
                report += f"- `{term}`\n"
            report += "\n"

        if r["false_positives"]:
            report += f"**False Positives (medical terms incorrectly removed):**\n"
            for term in r["false_positives"]:
                report += f"- `{term}`\n"
            report += "\n"

        if status == "PASS":
            report += "All checks passed.\n\n"

    # Recommendations
    if total_fn > 0 or total_fp > 0:
        report += "## Recommendations\n\n"

        if total_fn > 0:
            fn_terms = set()
            for r in results:
                fn_terms.update(r["false_negatives"])
            report += "### Patterns to Add (False Negatives)\n\n"
            report += "Add patterns to catch these PII terms:\n"
            for term in sorted(fn_terms):
                report += f"- `{term}`\n"
            report += "\n"

        if total_fp > 0:
            fp_terms = set()
            for r in results:
                fp_terms.update(r["false_positives"])
            report += "### Terms to Protect (False Positives)\n\n"
            report += "Add to `medical_terms` set:\n"
            report += "```python\n"
            for term in sorted(fp_terms):
                report += f'"{term.lower()}",\n'
            report += "```\n"

    return report


def main():
    """Run the PII service analysis."""
    print("=" * 70)
    print("PII SERVICE ANALYSIS")
    print("=" * 70)
    print(f"\nService URL: {PII_URL}")
    print(f"Running {len(TEST_CASES)} test cases...\n")

    results = []

    for test in TEST_CASES:
        print(f"Testing: {test['name']}...")
        try:
            response = call_pii_service(test["input"])
            analysis = analyze_result(test, response)
            results.append(analysis)

            status = (
                "PASS"
                if not analysis["false_negatives"] and not analysis["false_positives"]
                else "FAIL"
            )
            print(
                f"  [{status}] FN: {len(analysis['false_negatives'])}, FP: {len(analysis['false_positives'])}"
            )

            if analysis["false_negatives"]:
                print(f"    False negatives: {analysis['false_negatives']}")
            if analysis["false_positives"]:
                print(f"    False positives: {analysis['false_positives']}")

        except Exception as e:
            print(f"  [ERROR] {e}")

    # Generate report
    report = generate_report(results)

    report_path = "/tmp/pii_analysis_report.md"
    with open(report_path, "w") as f:
        f.write(report)
    print(f"\nReport saved to: {report_path}")

    # Print summary
    total_fn = sum(len(r["false_negatives"]) for r in results)
    total_fp = sum(len(r["false_positives"]) for r in results)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"False Negatives (PII not removed): {total_fn}")
    print(f"False Positives (medical terms removed): {total_fp}")

    if total_fn + total_fp == 0:
        print("\nAll tests passed!")
    else:
        print(f"\n{total_fn + total_fp} issues found - see report for details.")


if __name__ == "__main__":
    main()
