"""
Smart Privacy Filter - Intelligente PII-Entfernung ohne externe Dependencies
Funktioniert komplett ohne spaCy oder andere ML-Bibliotheken
"""

import re
import logging
from typing import Set, 

logger = logging.getLogger(__name__)

class SmartPrivacyFilter:
    """
    Intelligente PII-Entfernung mit erweiterten Heuristiken.
    Erkennt Namen dynamisch ohne ML-Modelle oder statische Listen.
    """

    def __init__(self):
        # Medizinische Fachbegriffe und Eponyme (diese MÜSSEN erhalten bleiben)
        self.medical_eponyms = {
            # Krankheiten mit Personennamen
            'morbus', 'crohn', 'basedow', 'alzheimer', 'parkinson', 'hodgkin',
            'addison', 'cushing', 'graves', 'hashimoto', 'meniere', 'paget',
            'raynaud', 'reiter', 'sjogren', 'wilson', 'huntington', 'marfan',

            # Anatomische Strukturen
            'baker', 'bartholin', 'bowman', 'broca', 'cooper', 'darwin',
            'douglas', 'eustach', 'fallopian', 'graaf', 'henle', 'langerhans',
            'purkinje', 'ranvier', 'schwann', 'wernicke', 'willis',

            # Medizinische Tests und Regeln
            'babinski', 'romberg', 'rinne', 'weber', 'fechner', 'starling',
            'frank', 'valsalva', 'trendelenburg', 'lasegue', 'kernig',

            # Syndrome
            'down', 'turner', 'klinefelter', 'marfan', 'ehlers', 'danlos',
            'gilbert', 'guillain', 'barre', 'kawasaki', 'reye',

            # Medizinische Scores
            'apgar', 'glasgow', 'ranson', 'bishop', 'wells', 'geneva'
        }

        # Medizinische Kontextwörter
        self.medical_context = {
            # Körperteile
            'herz', 'lunge', 'leber', 'niere', 'magen', 'darm', 'gehirn',
            'blut', 'knochen', 'muskel', 'nerv', 'gefäß', 'arterie', 'vene',

            # Adjektive
            'kardial', 'kardiale', 'kardialer', 'kardiales',
            'pulmonal', 'pulmonale', 'pulmonaler', 'pulmonales',
            'hepatisch', 'hepatische', 'hepatischer', 'hepatisches',
            'renal', 'renale', 'renaler', 'renales',
            'neural', 'neurale', 'neuraler', 'neurales',
            'akut', 'akute', 'akuter', 'akutes',
            'chronisch', 'chronische', 'chronischer', 'chronisches',

            # Substantive
            'patient', 'patientin', 'diagnose', 'befund', 'therapie',
            'behandlung', 'untersuchung', 'operation', 'medikament',
            'dosierung', 'symptom', 'syndrom', 'krankheit', 'erkrankung',

            # Richtungsangaben
            'links', 'rechts', 'beidseitig', 'bilateral', 'unilateral',
            'proximal', 'distal', 'lateral', 'medial', 'ventral', 'dorsal',
            'anterior', 'posterior', 'superior', 'inferior',

            # Abteilungen
            'innere', 'medizin', 'chirurgie', 'neurologie', 'kardiologie',
            'gastroenterologie', 'pneumologie', 'nephrologie', 'onkologie',
            'radiologie', 'pathologie', 'anästhesie', 'intensivmedizin'
        }

        # Titel und Anreden die auf Namen hinweisen
        self.name_titles = {
            'herr', 'frau', 'herrn', 'fr', 'hr',
            'dr', 'prof', 'professor', 'pd', 'priv', 'doz',
            'dipl', 'ing', 'med', 'rer', 'nat', 'phil', 'jur',
            'oberarzt', 'oberärztin', 'oa', 'chefarzt', 'chefärztin', 'ca',
            'assistenzarzt', 'assistenzärztin', 'aa', 'stationsarzt'
        }

        # Namens-Suffixe (typisch deutsch)
        self.name_suffixes = {
            'mann', 'meyer', 'meier', 'mayer', 'maier',
            'müller', 'schmidt', 'schneider', 'fischer', 'weber',
            'bauer', 'berg', 'stein', 'wald', 'bach', 'feld',
            'hof', 'hofer', 'berger', 'steiner', 'huber',
            'er', 'ler', 'ner', 'el', 'en', 'sen', 'son'
        }

        # Medizinische Abkürzungen
        self.medical_abbreviations = {
            'BMI', 'EKG', 'MRT', 'CT', 'PET', 'SPECT',
            'ICD', 'OPS', 'DRG', 'GOÄ', 'EBM',
            'CRP', 'BSG', 'PCT', 'TNF', 'IL',
            'TSH', 'fT3', 'fT4', 'TPO', 'TAK', 'TG',
            'HbA1c', 'BZ', 'BE', 'BD', 'HWZ',
            'RR', 'HF', 'AF', 'EF', 'FS', 'SV', 'HZV',
            'pO2', 'pCO2', 'SaO2', 'SpO2', 'FiO2',
            'AP', 'LAP', 'GGT', 'GOT', 'GPT', 'LDH',
            'CK', 'CKMB', 'BNP', 'NT-proBNP',
            'Hb', 'Hkt', 'MCV', 'MCH', 'MCHC',
            'INR', 'PTT', 'PTZ', 'Quick', 'AT3',
            # Vitamine und Nährstoffe
            'D3', 'B12', 'B6', 'B1', 'B2', 'B9', 'K2', 'K1', 'E', 'C', 'A',
            '25-OH', '1,25-OH2', 'OH-D3', 'OH-D', 'D2',
            # Weitere Laborwerte
            'GFR', 'eGFR', 'HDL', 'LDL', 'VLDL',
            'IgG', 'IgM', 'IgA', 'IgE', 'RF', 'CCP', 'ANA', 'ANCA'
        }

        # Vitamine und Nährstoffe als geschützte Begriffe
        self.vitamins_nutrients = {
            'vitamin', 'vitamine', 'd3', 'b12', 'b6', 'b1', 'b2', 'b9', 'k2', 'k1',
            'folsäure', 'folat', 'cobalamin', 'thiamin', 'riboflavin', 'niacin',
            'pantothensäure', 'pyridoxin', 'biotin', 'ascorbinsäure', 'tocopherol',
            'retinol', 'calciferol', 'cholecalciferol', 'ergocalciferol',
            'calcium', 'magnesium', 'kalium', 'natrium', 'phosphor', 'eisen',
            'zink', 'kupfer', 'mangan', 'selen', 'jod', 'fluor', 'chrom'
        }

        self.patterns = self._compile_patterns()

    def _compile_patterns(self) -> dict:
        """Kompiliert Regex-Patterns"""
        return {
            # Geburtsdaten
            'birthdate': re.compile(
                r'\b(?:geb(?:oren)?\.?\s*(?:am\s*)?|geboren\s+am\s+|geburtsdatum:?\s*)'
                r'(?:\d{1,2}[\.\/-]\d{1,2}[\.\/-]\d{2,4}|\d{4}[\.\/-]\d{1,2}[\.\/-]\d{1,2})',
                re.IGNORECASE
            ),

            # Adressen
            'street': re.compile(
                r'\b[A-ZÄÖÜ][a-zäöüß]+(?:straße|str\.?|weg|allee|platz|ring|gasse|damm|chaussee|promenade)\s+\d+[a-z]?\b',
                re.IGNORECASE
            ),

            # PLZ
            'plz': re.compile(r'\b\d{5}\s+[A-ZÄÖÜ][a-zäöüß]+(?:\s+[a-zäöüß]+)*\b'),

            # Telefon
            'phone': re.compile(r'\b(?:\+49|0049|0)[\s\-\(\)\/]*(?:\d[\s\-\(\)\/]*){8,15}\b'),

            # E-Mail
            'email': re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'),

            # Versicherungsnummern
            'insurance': re.compile(
                r'\b(?:versicherungs?|kassen|patient|fall|akte)[\-\s]*(?:nr\.?|nummer)?[:\s]*[\w\-\/]+\b',
                re.IGNORECASE
            ),

            # Anreden und Grußformeln
            'greetings': re.compile(
                r'^(?:sehr\s+geehrte[rns]?\s+.*?[,!]|'
                r'liebe[rns]?\s+.*?[,!]|'
                r'(?:mit\s+)?(?:freundlichen|besten|herzlichen)\s+grüßen.*?$|'
                r'hochachtungsvoll.*?$)',
                re.IGNORECASE | re.MULTILINE
            )
        }

    def remove_pii(self, text: str) -> str:
        """
        Hauptfunktion zur intelligenten PII-Entfernung
        """
        if not text:
            return text

        logger.info("🧠 Starte intelligente PII-Entfernung")

        # Schütze medizinische Abkürzungen
        protected_text = self._protect_medical_terms(text)

        # 1. Entferne explizite Muster
        protected_text = self._remove_explicit_patterns(protected_text)

        # 2. Intelligente Namenerkennung
        protected_text = self._remove_names_smart(protected_text)

        # 3. Stelle medizinische Begriffe wieder her
        result = self._restore_medical_terms(protected_text)

        # 4. Bereinige Formatierung
        result = re.sub(r'\n{3,}', '\n\n', result)
        result = re.sub(r'[ \t]+', ' ', result)

        logger.info("✅ PII-Entfernung abgeschlossen")
        return result.strip()

    def _protect_medical_terms(self, text: str) -> str:
        """Schützt medizinische Begriffe vor Entfernung"""
        # Schütze Vitamin-Kombinationen (z.B. "Vitamin D3", "Vitamin B12")
        vitamin_pattern = r'\b(Vitamin|Vit\.?)\s*([A-Z][0-9]*|[0-9]+[-,]?[0-9]*[-]?OH[-]?[A-Z]?[0-9]*)\b'
        text = re.sub(vitamin_pattern, r'«VITAMIN_\2»', text, flags=re.IGNORECASE)

        # Schütze Laborwert-Kombinationen mit Zahlen (z.B. "25-OH-D3", "1,25-OH2-D3")
        lab_pattern = r'\b([0-9]+[,.]?[0-9]*[-]?OH[0-9]*[-]?[A-Z]?[0-9]*)\b'
        text = re.sub(lab_pattern, r'«LAB_\1»', text, flags=re.IGNORECASE)

        # Schütze Abkürzungen
        for abbr in self.medical_abbreviations:
            # Case-insensitive replacement mit Wortgrenzen
            pattern = r'\b' + re.escape(abbr) + r'\b'
            text = re.sub(pattern, f"«{abbr}»", text, flags=re.IGNORECASE)

        # Schütze medizinische Eponyme im Kontext
        # z.B. "Morbus Crohn" -> "«Morbus_Crohn»"
        for eponym in ['Morbus Crohn', 'Morbus Basedow', 'Morbus Parkinson',
                      'Morbus Alzheimer', 'Morbus Hodgkin', 'Morbus Paget']:
            text = text.replace(eponym, f"«{eponym.replace(' ', '_')}»")
            text = text.replace(eponym.lower(), f"«{eponym.replace(' ', '_')}»")

        # Schütze anatomische Strukturen
        for struct in ['Baker-Zyste', 'Bartholin-Drüse', 'Broca-Areal',
                      'Douglas-Raum', 'Henle-Schleife', 'Langerhans-Inseln']:
            text = text.replace(struct, f"«{struct.replace('-', '_')}»")

        # Schütze medizinische Tests
        for test in ['Babinski-Reflex', 'Romberg-Test', 'Rinne-Test',
                    'Weber-Test', 'Frank-Starling-Kurve', 'Glasgow-Coma-Scale']:
            text = text.replace(test, f"«{test.replace('-', '_').replace(' ', '_')}»")

        return text

    def _restore_medical_terms(self, text: str) -> str:
        """Stellt geschützte Begriffe wieder her"""
        # Stelle Vitamin-Kombinationen wieder her
        text = re.sub(r'«VITAMIN_([^»]+)»', r'Vitamin \1', text)

        # Stelle Laborwert-Kombinationen wieder her
        text = re.sub(r'«LAB_([^»]+)»', r'\1', text)

        # Entferne restliche Schutzzeichen
        text = re.sub(r'«([^»]+)»', lambda m: m.group(1).replace('_', ' '), text)
        return text

    def _remove_explicit_patterns(self, text: str) -> str:
        """Entfernt explizite PII-Muster"""
        # Geburtsdaten
        text = self.patterns['birthdate'].sub('[GEBURTSDATUM ENTFERNT]', text)

        # Adressen
        text = self.patterns['street'].sub('[ADRESSE ENTFERNT]', text)
        text = self.patterns['plz'].sub('[PLZ/ORT ENTFERNT]', text)

        # Kontaktdaten
        text = self.patterns['phone'].sub('[TELEFON ENTFERNT]', text)
        text = self.patterns['email'].sub('[EMAIL ENTFERNT]', text)

        # Versicherungsnummern
        text = self.patterns['insurance'].sub('[NUMMER ENTFERNT]', text)

        # Grußformeln
        text = self.patterns['greetings'].sub('', text)

        # Geschlecht
        text = re.sub(
            r'\b(?:geschlecht)[:\s]*(?:männlich|weiblich|divers|m|w|d)\b',
            '[GESCHLECHT ENTFERNT]',
            text,
            flags=re.IGNORECASE
        )

        return text

    def _remove_names_smart(self, text: str) -> str:
        """
        Intelligente Namenerkennung ohne ML
        Verwendet Kontext und Muster zur Erkennung
        """
        lines = text.split('\n')
        result_lines = []

        for line in lines:
            # Skip leere Zeilen
            if not line.strip():
                result_lines.append(line)
                continue

            # Tokenize (behalte Satzzeichen separat)
            tokens = re.findall(r'\b\w+\b|[^\w\s]', line)
            result_tokens = []
            i = 0

            while i < len(tokens):
                token = tokens[i]
                token_lower = token.lower()

                # Überspringe geschützte Begriffe
                if '«' in token or '»' in token:
                    result_tokens.append(token)
                    i += 1
                    continue

                # Prüfe auf Titel/Anrede
                if token_lower in self.name_titles:
                    # Wahrscheinlich folgt ein Name
                    potential_name_tokens = []
                    j = i + 1

                    # Sammle die nächsten 2-4 Tokens als potenzielle Namen
                    while j < len(tokens) and j < i + 5:
                        next_token = tokens[j]

                        # Stop bei Satzzeichen (außer Bindestrich und Punkt in Abkürzungen)
                        if next_token in [',', ';', ':', '(', ')', '[', ']']:
                            break

                        # Prüfe ob es wie ein Name aussieht
                        if self._looks_like_name(next_token):
                            potential_name_tokens.append(j)
                        elif next_token == '-' or next_token == '.':
                            # Bindestrich oder Punkt könnten Teil des Namens sein
                            pass
                        else:
                            # Wenn es ein medizinischer Begriff ist, stoppe
                            if next_token.lower() in self.medical_context:
                                break
                        j += 1

                    # Wenn wir potenzielle Namen gefunden haben, entferne sie
                    if potential_name_tokens:
                        # Behalte den Titel, aber entferne die Namen
                        result_tokens.append(token)
                        # Überspringe die Namen-Tokens
                        i = max(potential_name_tokens) + 1
                        continue

                # Prüfe auf Namens-Pattern ohne Titel
                elif self._looks_like_name(token) and not self._is_medical_term(token):
                    # Schaue den Kontext an
                    prev_token = tokens[i-1].lower() if i > 0 else ''
                    next_token = tokens[i+1].lower() if i < len(tokens)-1 else ''

                    # Wenn der vorherige Token ein medizinischer Begriff ist, behalte das Wort
                    if prev_token in self.medical_context or prev_token in self.medical_eponyms:
                        result_tokens.append(token)
                    # Wenn der nächste Token ein Namens-Suffix ist, könnte es ein Nachname sein
                    elif any(next_token.endswith(suffix) for suffix in self.name_suffixes):
                        # Entferne beide
                        i += 2
                        continue
                    # Bei Unsicherheit im medizinischen Kontext: behalten
                    elif self._in_medical_context(tokens, i):
                        result_tokens.append(token)
                    else:
                        # Wahrscheinlich ein Name - entfernen
                        i += 1
                        continue
                else:
                    result_tokens.append(token)

                i += 1

            # Rekonstruiere die Zeile
            result_line = self._reconstruct_line(result_tokens)
            result_lines.append(result_line)

        return '\n'.join(result_lines)

    def _looks_like_name(self, token: str) -> bool:
        """Prüft ob ein Token wie ein Name aussieht"""
        # Muss mit Großbuchstaben beginnen
        if not token or not token[0].isupper():
            return False

        # Muss mindestens 2 Zeichen lang sein
        if len(token) < 2:
            return False

        # Darf keine Zahlen enthalten (außer am Ende bei "2." etc.)
        if any(c.isdigit() for c in token[:-1]):
            return False

        # Ist es eine medizinische Abkürzung?
        if token.upper() in self.medical_abbreviations:
            return False

        return True

    def _is_medical_term(self, token: str) -> bool:
        """Prüft ob ein Token ein medizinischer Begriff ist"""
        token_lower = token.lower()

        # Ist es ein medizinisches Eponym?
        if token_lower in self.medical_eponyms:
            return True

        # Ist es ein medizinischer Kontext-Begriff?
        if token_lower in self.medical_context:
            return True

        # Ist es eine medizinische Abkürzung?
        if token.upper() in self.medical_abbreviations:
            return True

        # Ist es ein Vitamin oder Nährstoff?
        if token_lower in self.vitamins_nutrients:
            return True

        # Spezialfall: Vitamin-Kombinationen (z.B. "D3" nach "Vitamin")
        if re.match(r'^[A-Z]\d+$', token) or re.match(r'^\d+[A-Z]+$', token):
            return True  # Könnte ein Vitamin sein

        return False

    def _in_medical_context(self, tokens: list[str], index: int) -> bool:
        """Prüft ob ein Token in medizinischem Kontext steht"""
        # Schaue 2 Tokens vor und nach
        context_range = 2

        for i in range(max(0, index - context_range),
                      min(len(tokens), index + context_range + 1)):
            if i != index:
                token_lower = tokens[i].lower()
                if token_lower in self.medical_context or token_lower in self.medical_eponyms:
                    return True

        return False

    def _reconstruct_line(self, tokens: list[str]) -> str:
        """Rekonstruiert eine Zeile aus Tokens"""
        if not tokens:
            return ''

        result = []
        for i, token in enumerate(tokens):
            # Füge Leerzeichen vor Token hinzu, außer:
            # - Es ist das erste Token
            # - Es ist ein Satzzeichen
            # - Das vorherige Token war eine öffnende Klammer
            if i > 0 and token not in '.,;:!?)' and tokens[i-1] not in '([':
                result.append(' ')
            result.append(token)

        return ''.join(result)