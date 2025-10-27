"""
Privacy Filter Service - Entfernt sensible Daten aus medizinischen Dokumenten
Verwendet lokale Python-Bibliotheken für PII-Entfernung
"""

import re
import logging
from typing import Set, 
from datetime import datetime

logger = logging.getLogger(__name__)

class PrivacyFilter:
    """
    Entfernt persönlich identifizierbare Informationen (PII) aus medizinischen Texten
    mit regelbasierten Mustern und heuristischen Methoden.
    """

    def __init__(self):
        # Deutsche Vornamen (häufigste) - ohne medizinische Begriffe
        self.common_first_names = {
            'maria', 'anna', 'emma', 'marie', 'sophia', 'laura', 'julia', 'lisa', 'sarah', 'lena',
            'lea', 'hannah', 'mia', 'nina', 'jana', 'katharina', 'claudia', 'sandra', 'andrea', 'petra',
            'max', 'paul', 'leon', 'lukas', 'felix', 'jonas', 'tim', 'jan', 'michael', 'thomas',
            'peter', 'stefan', 'andreas', 'christian', 'daniel', 'markus', 'frank', 'oliver', 'klaus', 'wolfgang'
        }

        # Deutsche Nachnamen (häufigste)
        self.common_last_names = {
            'müller', 'schmidt', 'schneider', 'fischer', 'meyer', 'weber', 'wagner', 'becker', 'schulz', 'hoffmann',
            'schäfer', 'koch', 'bauer', 'richter', 'klein', 'wolf', 'schröder', 'neumann', 'schwarz', 'zimmermann',
            'braun', 'hofmann', 'krüger', 'hartmann', 'lange', 'werner', 'schmitt', 'krause', 'lehmann', 'köhler',
            'mustermann', 'musterfrau'  # Test-Namen hinzugefügt
        }

        # Anreden und Titel
        self.titles = {
            'dr', 'prof', 'professor', 'med', 'dipl', 'ing', 'mag', 'ba', 'ma', 'msc', 'bsc', 'phd'
        }

        # Geschlechtsspezifische Begriffe
        self.gender_terms = {
            'männlich', 'weiblich', 'divers', 'herr', 'frau', 'mann', 'frau',
            'männl', 'weibl', 'm', 'w', 'd', 'geschlecht'
        }

        # Regex-Patterns für verschiedene Datentypen
        self.patterns = self._compile_patterns()

    def _compile_patterns(self) -> dict[str, re.Pattern]:
        """Kompiliert Regex-Patterns für verschiedene PII-Typen"""
        return {
            # Geburtsdaten in verschiedenen Formaten
            'birthdate': re.compile(
                r'\b(?:geb(?:oren)?\.?\s*(?:am\s*)?|geboren\s+am\s+|geburtsdatum:?\s*)'
                r'(?:\d{1,2}[\.\/-]\d{1,2}[\.\/-]\d{2,4}|\d{4}[\.\/-]\d{1,2}[\.\/-]\d{1,2})',
                re.IGNORECASE
            ),

            # Datumsformat (könnte Geburtsdatum sein)
            'date_format': re.compile(
                r'\b\d{1,2}[\.\/\-]\d{1,2}[\.\/\-](?:19|20)\d{2}\b'
            ),

            # Adressen (Straße + Hausnummer)
            'street_address': re.compile(
                r'\b[A-ZÄÖÜ][a-zäöüß]+(?:straße|str\.?|weg|allee|platz|ring|gasse|damm|berg)\s+\d+[a-z]?\b',
                re.IGNORECASE
            ),

            # PLZ + Ort
            'plz_city': re.compile(
                r'\b\d{5}\s+[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*\b'
            ),

            # Telefonnummern
            'phone': re.compile(
                r'\b(?:\+49|0049|0)\s*(?:\d[\s\-\(\)\/]*){9,15}\b'
            ),

            # E-Mail-Adressen
            'email': re.compile(
                r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
            ),

            # Versicherungsnummern
            'insurance_number': re.compile(
                r'\b(?:versicherungsnr|vers\.?\s*nr|patientennr|pat\.?\s*nr|fallnr)[:\.\s]*[\w\-\/]+\b',
                re.IGNORECASE
            ),

            # Anreden und Grußformeln
            'salutation': re.compile(
                r'^(?:sehr\s+geehrte[rns]?\s+(?:frau|herr|damen|herren).*?[,!]|'
                r'(?:mit\s+)?(?:freundlichen|besten|herzlichen)\s+grüßen.*?$|'
                r'hochachtungsvoll.*?$|'
                r'liebe[rns]?\s+(?:frau|herr).*?[,!])',
                re.IGNORECASE | re.MULTILINE
            ),

            # Unterschriften/Signaturen
            'signature': re.compile(
                r'\b(?:unterschrift|i\.\s*a\.|i\.\s*v\.|gez\.|gezeichnet)[:\s]*[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*',
                re.IGNORECASE
            )
        }

    def remove_pii(self, text: str) -> str:
        """
        Hauptfunktion zur Entfernung von PII aus dem Text

        Args:
            text: Der zu bereinigende Text

        Returns:
            Bereinigter Text ohne PII
        """
        if not text:
            return text

        logger.info("Starting PII removal from medical text")

        # Arbeite mit einer Kopie
        cleaned_text = text

        # 1. Entferne Namen (muss vor anderen Schritten erfolgen)
        cleaned_text = self._remove_names(cleaned_text)

        # 2. Entferne Geburtsdaten
        cleaned_text = self._remove_birthdates(cleaned_text)

        # 3. Entferne Adressen
        cleaned_text = self._remove_addresses(cleaned_text)

        # 4. Entferne Kontaktdaten
        cleaned_text = self._remove_contact_info(cleaned_text)

        # 5. Entferne Versicherungsnummern
        cleaned_text = self._remove_insurance_numbers(cleaned_text)

        # 6. Entferne Geschlechtsangaben
        cleaned_text = self._remove_gender_info(cleaned_text)

        # 7. Entferne Anreden und Grußformeln
        cleaned_text = self._remove_salutations(cleaned_text)

        # 8. Bereinige mehrfache Leerzeilen
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
        cleaned_text = re.sub(r'[ \t]+', ' ', cleaned_text)

        logger.info(f"PII removal completed. Original length: {len(text)}, Cleaned length: {len(cleaned_text)}")

        return cleaned_text.strip()

    def _remove_names(self, text: str) -> str:
        """Entfernt Namen aus dem Text"""
        # Schütze medizinische Abkürzungen vor Entfernung
        protected_terms = {
            'BMI': '§BMI§', 'EKG': '§EKG§', 'MRT': '§MRT§', 'CT': '§CT§',
            'ICD': '§ICD§', 'OPS': '§OPS§', 'EF': '§EF§', 'LAD': '§LAD§',
            'RCA': '§RCA§', 'HDL': '§HDL§', 'LDL': '§LDL§', 'CK-MB': '§CKMB§'
        }

        # Ersetze medizinische Begriffe temporär
        for term, placeholder in protected_terms.items():
            text = text.replace(term, placeholder)
            text = text.replace(term.lower(), placeholder)

        # Entferne Dr./Prof. Titel mit Namen
        text = re.sub(
            r'\b(?:dr\.?|prof\.?|professor|dipl\.?|ing\.?)\s+(?:med\.?\s+)?[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*\b',
            '',
            text,
            flags=re.IGNORECASE
        )

        # Entferne Herr/Frau mit Namen
        text = re.sub(
            r'\b(?:herr(?:n)?|frau)\s+(?:dr\.?\s+)?[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*\b',
            '',
            text,
            flags=re.IGNORECASE
        )

        # Entferne spezifische Namens-Patterns
        text = re.sub(
            r'\b(?:patient(?:in)?|name)[:\s]+[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*\b',
            '[NAME ENTFERNT]',
            text,
            flags=re.IGNORECASE
        )

        # Entferne bekannte deutsche Namen
        lines = text.split('\n')
        cleaned_lines = []

        for line in lines:
            words = line.split()
            cleaned_words = []
            skip_next = False

            for i, word in enumerate(words):
                if skip_next:
                    skip_next = False
                    continue

                # Extrahiere das Wort ohne Satzzeichen für Vergleiche
                word_core = re.sub(r'[^\wäöüÄÖÜß§]', '', word)
                word_lower = word_core.lower()

                # Überspringe geschützte Begriffe
                if '§' in word:
                    cleaned_words.append(word)
                    continue

                # Überspringe wichtige Wörter
                if word_lower in ['aktuell', 'aktuelle', 'aktueller', 'aktuelles']:
                    cleaned_words.append(word)
                    continue

                # Entferne Namen
                if word_lower in self.common_first_names:
                    if i + 1 < len(words):
                        next_word_core = re.sub(r'[^\wäöüÄÖÜß]', '', words[i + 1])
                        if next_word_core.lower() in self.common_last_names:
                            skip_next = True
                            continue
                    continue
                elif word_lower in self.common_last_names:
                    continue
                else:
                    cleaned_words.append(word)

            cleaned_lines.append(' '.join(cleaned_words))

        result = '\n'.join(cleaned_lines)

        # Stelle medizinische Begriffe wieder her
        for term, placeholder in protected_terms.items():
            result = result.replace(placeholder, term)

        return result

    def _remove_birthdates(self, text: str) -> str:
        """Entfernt Geburtsdaten"""
        # Entferne explizite Geburtsdaten
        text = self.patterns['birthdate'].sub('[GEBURTSDATUM ENTFERNT]', text)

        # Prüfe Datumsangaben auf mögliche Geburtsdaten (Jahre 1920-2010)
        def check_birthdate(match):
            date_str = match.group(0)
            try:
                # Versuche Jahr zu extrahieren
                year_match = re.search(r'(19|20)\d{2}', date_str)
                if year_match:
                    year = int(year_match.group(0))
                    # Geburtsjahre typischerweise zwischen 1920 und 2010
                    if 1920 <= year <= 2010:
                        return '[DATUM ENTFERNT]'
            except:
                pass
            return date_str

        text = self.patterns['date_format'].sub(check_birthdate, text)

        return text

    def _remove_addresses(self, text: str) -> str:
        """Entfernt Adressen"""
        # Entferne Straßenadressen
        text = self.patterns['street_address'].sub('[ADRESSE ENTFERNT]', text)

        # Entferne PLZ + Stadt
        text = self.patterns['plz_city'].sub('[PLZ/ORT ENTFERNT]', text)

        return text

    def _remove_contact_info(self, text: str) -> str:
        """Entfernt Kontaktinformationen"""
        # Telefonnummern
        text = self.patterns['phone'].sub('[TELEFON ENTFERNT]', text)

        # E-Mail-Adressen
        text = self.patterns['email'].sub('[EMAIL ENTFERNT]', text)

        return text

    def _remove_insurance_numbers(self, text: str) -> str:
        """Entfernt Versicherungs- und Patientennummern"""
        text = self.patterns['insurance_number'].sub('[NUMMER ENTFERNT]', text)

        # Zusätzliche Nummern-Patterns
        text = re.sub(
            r'\b(?:kassen|patient|fall|akte|id)[:\-\s]*(?:nr\.?|nummer)?[:\s]*[\w\-\/]+\b',
            '[ID ENTFERNT]',
            text,
            flags=re.IGNORECASE
        )

        return text

    def _remove_gender_info(self, text: str) -> str:
        """Entfernt Geschlechtsangaben"""
        # Nur explizite Geschlechtsangaben entfernen
        text = re.sub(
            r'\b(?:geschlecht)[:\s]*(?:männlich|weiblich|divers|m|w|d)\b',
            '[GESCHLECHT ENTFERNT]',
            text,
            flags=re.IGNORECASE
        )

        return text

    def _remove_salutations(self, text: str) -> str:
        """Entfernt Anreden und Grußformeln"""
        # Anreden am Anfang
        text = self.patterns['salutation'].sub('', text)

        # Unterschriften
        text = self.patterns['signature'].sub('', text)

        return text

    def validate_medical_content_preserved(self, original: str, cleaned: str) -> bool:
        """
        Überprüft, ob medizinische Inhalte erhalten geblieben sind

        Args:
            original: Originaltext
            cleaned: Bereinigter Text

        Returns:
            True wenn medizinische Inhalte erhalten sind
        """
        # Liste medizinischer Begriffe die erhalten bleiben müssen
        medical_terms = [
            'hämoglobin', 'erythrozyten', 'leukozyten', 'thrombozyten',
            'diagnose', 'befund', 'labor', 'wert', 'mg/dl', 'mmol/l',
            'medikament', 'dosierung', 'therapie', 'behandlung',
            'untersuchung', 'mrt', 'ct', 'röntgen', 'ultraschall',
            'icd', 'ops', 'drg'
        ]

        # Zähle medizinische Begriffe im Original und bereinigten Text
        original_lower = original.lower()
        cleaned_lower = cleaned.lower()

        original_count = sum(1 for term in medical_terms if term in original_lower)
        cleaned_count = sum(1 for term in medical_terms if term in cleaned_lower)

        # Mindestens 80% der medizinischen Begriffe sollten erhalten sein
        if original_count > 0:
            preservation_rate = cleaned_count / original_count
            return preservation_rate >= 0.8

        return True  # Wenn keine medizinischen Begriffe gefunden wurden