"""
Advanced Privacy Filter Service mit spaCy NER
Entfernt sensible Daten aus medizinischen Dokumenten mit KI-basierter Namenerkennung
"""

import re
import logging
from typing import List, Set, Tuple, Optional

# Try to import spaCy, but make it optional
try:
    import spacy
    from spacy.language import Language
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    spacy = None
    Language = None

logger = logging.getLogger(__name__)

class AdvancedPrivacyFilter:
    """
    Privacy Filter mit spaCy NER.
    Entfernt: Namen, Adressen, Geburtsdaten, Telefon, E-Mail, Versicherungsnummern, Anreden.
    ERHÄLT: Alle medizinischen Informationen, Laborwerte, Diagnosen, Behandlungen.
    """
    
    def __init__(self):
        """Initialisiert den Filter mit spaCy NER Model"""
        self.nlp = None
        self._initialize_spacy()
        
        logger.info("🎯 Privacy Filter: Entfernt persönliche Daten, erhält medizinische Informationen")
        
        # Medizinische Begriffe, die NICHT als Namen erkannt werden sollen
        self.medical_terms = {
            # Körperteile und Organe
            'herz', 'lunge', 'leber', 'niere', 'magen', 'darm', 'kopf', 'hals',
            'brust', 'bauch', 'rücken', 'schulter', 'knie', 'hüfte', 'hand', 'fuß',
            'hirn', 'gehirn', 'muskel', 'knochen', 'gelenk', 'sehne', 'nerv',
            'gefäß', 'arterie', 'vene', 'lymphe', 'milz', 'pankreas', 'schilddrüse',
            
            # Medizinische Fachbegriffe
            'patient', 'patientin', 'diagnose', 'befund', 'therapie', 'behandlung',
            'untersuchung', 'operation', 'medikament', 'dosierung', 'anamnese',
            'kardial', 'kardiale', 'pulmonal', 'hepatisch', 'renal', 'gastral',
            'neural', 'muskulär', 'vaskulär', 'arterial', 'venös', 'symptom',
            'syndrom', 'erkrankung', 'krankheit', 'störung', 'insuffizienz',
            'stenose', 'thrombose', 'embolie', 'infarkt', 'ischämie', 'nekrose',
            'inflammation', 'infektion', 'sepsis', 'abszeß', 'tumor', 'karzinom',
            
            # Häufige medizinische Adjektive
            'akut', 'akute', 'akuter', 'akutes', 'chronisch', 'chronische',
            'primär', 'sekundär', 'maligne', 'benigne', 'bilateral', 'unilateral',
            'proximal', 'distal', 'lateral', 'medial', 'anterior', 'posterior',
            'superior', 'inferior', 'links', 'rechts', 'beidseits', 'normal',
            'pathologisch', 'physiologisch', 'regelrecht', 'unauffällig',
            
            # Medikamente und Substanzen (häufige)
            'aspirin', 'insulin', 'cortison', 'antibiotika', 'penicillin',
            'morphin', 'ibuprofen', 'paracetamol', 'metformin', 'simvastatin',
            
            # Untersuchungen
            'mrt', 'ct', 'röntgen', 'ultraschall', 'ekg', 'echo', 'szintigraphie',
            'biopsie', 'punktion', 'endoskopie', 'koloskopie', 'gastroskopie',
            
            # Wichtige Wörter
            'aktuell', 'aktuelle', 'aktueller', 'aktuelles', 'vorhanden',
            'unauffällig', 'regelrecht', 'normal', 'pathologisch',
            
            # Abteilungen
            'innere', 'medizin', 'chirurgie', 'neurologie', 'kardiologie',
            'gastroenterologie', 'pneumologie', 'nephrologie', 'onkologie',
            
            # Vitamine und Nährstoffe (auch Kleinschreibung)
            'vitamin', 'vitamine', 'd3', 'b12', 'b6', 'b1', 'b2', 'b9', 'k2', 'k1',
            'folsäure', 'folat', 'cobalamin', 'thiamin', 'riboflavin', 'niacin',
            'pantothensäure', 'pyridoxin', 'biotin', 'ascorbinsäure', 'tocopherol',
            'retinol', 'calciferol', 'cholecalciferol', 'ergocalciferol',
            'calcium', 'magnesium', 'kalium', 'natrium', 'phosphor', 'eisen',
            'zink', 'kupfer', 'mangan', 'selen', 'jod', 'fluor', 'chrom',
            
            # Laborwerte und Einheiten
            'wert', 'werte', 'labor', 'laborwert', 'laborwerte', 'blutbild',
            'parameter', 'referenz', 'referenzbereich', 'normbereich', 'normwert',
            'erhöht', 'erniedrigt', 'grenzwertig', 'positiv', 'negativ',
            'mg', 'dl', 'ml', 'mmol', 'µmol', 'nmol', 'pmol', 'ng', 'pg', 'iu',
            'einheit', 'einheiten', 'prozent', 'promille'
        }
        
        # Titel und Anreden, die auf Namen hinweisen
        self.name_indicators = {
            'herr', 'frau', 'dr', 'prof', 'professor', 'med', 'dipl', 'ing',
            'herrn', 'frau', 'familie'
        }
        
        # Medizinische Abkürzungen, die geschützt werden müssen
        self.protected_abbreviations = {
            'BMI', 'EKG', 'MRT', 'CT', 'ICD', 'OPS', 'DRG', 'GOÄ', 'EBM',
            'EF', 'LAD', 'RCA', 'RCX', 'RIVA', 'CK', 'CK-MB', 'HDL', 'LDL',
            'TSH', 'fT3', 'fT4', 'HbA1c', 'INR', 'PTT', 'AT3', 'CRP', 'PCT',
            'AFP', 'CEA', 'CA', 'PSA', 'BNP', 'NT-proBNP',
            # Vitamine und Nährstoffe
            'D3', 'B12', 'B6', 'B1', 'B2', 'B9', 'K2', 'K1', 'E', 'C', 'A',
            '25-OH', '1,25-OH2', 'OH-D3', 'OH-D', 'D2',
            # Weitere Laborwerte
            'GFR', 'eGFR', 'GPT', 'GOT', 'GGT', 'AP', 'LDH', 'MCH', 'MCV', 'MCHC',
            'RDW', 'MPV', 'PDW', 'PLT', 'WBC', 'RBC', 'HGB', 'HCT', 'NEUT', 'LYMPH',
            'MONO', 'EOS', 'BASO', 'IG', 'RETI', 'ESR', 'BSG', 'IL-6', 'TNF',
            'IgG', 'IgM', 'IgA', 'IgE', 'C3', 'C4', 'ANA', 'ANCA', 'RF', 'CCP'
        }
        
        # Compile regex patterns
        self.patterns = self._compile_patterns()
    
    def _initialize_spacy(self):
        """Initialisiert spaCy mit deutschem Modell"""
        if not SPACY_AVAILABLE:
            logger.info("ℹ️ spaCy ist optional - verwende Heuristik-basierte Erkennung")
            self.nlp = None
            self.has_ner = False
            return
            
        try:
            # Versuche das deutsche Modell zu laden
            self.nlp = spacy.load("de_core_news_sm")
            logger.info("✅ spaCy deutsches Modell (de_core_news_sm) geladen")
            self.has_ner = True
        except (OSError, ImportError) as e:
            logger.warning(f"⚠️ spaCy Modell nicht verfügbar - verwende eingeschränkten Heuristik-Modus: {e}")
            logger.info("💡 Für bessere Namenerkennung: python -m spacy download de_core_news_sm")
            try:
                # Fallback: Versuche ein leeres deutsches Modell
                self.nlp = spacy.blank("de")
                logger.info("📦 Verwende spaCy blank model als Fallback (ohne NER)")
                self.has_ner = False
            except Exception as e2:
                logger.warning(f"⚠️ spaCy Initialisierung fehlgeschlagen - verwende reine Heuristik: {e2}")
                self.nlp = None
                self.has_ner = False
    
    def _compile_patterns(self) -> dict:
        """Kompiliert Regex-Patterns für verschiedene PII-Typen"""
        return {
            # Geburtsdaten
            'birthdate': re.compile(
                r'\b(?:geb(?:oren)?\.?\s*(?:am\s*)?|geboren\s+am\s+|geburtsdatum:?\s*)'
                r'(?:\d{1,2}[\.\/-]\d{1,2}[\.\/-]\d{2,4}|\d{4}[\.\/-]\d{1,2}[\.\/-]\d{1,2})',
                re.IGNORECASE
            ),
            
            # Explizite Patienteninfo
            'patient_info': re.compile(
                r'\b(?:patient(?:in)?|name|versicherte[rn]?)[:\s]+([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*)',
                re.IGNORECASE
            ),
            
            # Adressen
            'street_address': re.compile(
                r'\b[A-ZÄÖÜ][a-zäöüß]+(?:straße|str\.?|weg|allee|platz|ring|gasse|damm)\s+\d+[a-z]?\b',
                re.IGNORECASE
            ),
            
            # PLZ + Stadt
            'plz_city': re.compile(
                r'\b\d{5}\s+[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*\b'
            ),
            
            # Telefon
            'phone': re.compile(
                r'\b(?:\+49|0049|0)[\s\-\(\)\/]*(?:\d[\s\-\(\)\/]*){8,15}\b'
            ),
            
            # E-Mail
            'email': re.compile(
                r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
            ),
            
            # Versicherungsnummern
            'insurance': re.compile(
                r'\b(?:versicherungs?|kassen|patient|fall|akte)[\-\s]*(?:nr\.?|nummer)?[:\s]*[\w\-\/]+\b',
                re.IGNORECASE
            ),
            
            # Anreden
            'salutation': re.compile(
                r'^(?:sehr\s+geehrte[rns]?\s+.*?[,!]|'
                r'(?:mit\s+)?(?:freundlichen|besten|herzlichen)\s+grüßen.*?$|'
                r'hochachtungsvoll.*?$)',
                re.IGNORECASE | re.MULTILINE
            )
        }
    
    def remove_pii(self, text: str) -> str:
        """
        PII-Entfernung: Namen, Adressen, Geburtsdaten, Kontaktdaten, Versicherungsnummern
        
        Args:
            text: Der zu bereinigende Text
            
        Returns:
            Bereinigter Text ohne persönliche Daten, aber mit allen medizinischen Informationen
        """
        if not text:
            return text
        
        logger.info("🔍 Entferne persönliche Daten, behalte medizinische Informationen")
        
        # Schütze medizinische Begriffe vor Entfernung
        text = self._protect_medical_terms(text)
        
        # 1. Entferne alle persönlichen Daten (außer medizinische)
        text = self._remove_personal_data(text)
        
        # 2. Entferne Namen mit spaCy
        if self.nlp and self.has_ner:
            text = self._remove_names_with_ner(text)
        else:
            # Fallback: Heuristische Namenerkennung
            text = self._remove_names_heuristic(text)
        
        # 3. Stelle medizinische Begriffe wieder her
        text = self._restore_medical_terms(text)
        
        # 4. Formatierung bereinigen
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        logger.info("✅ Persönliche Daten entfernt - medizinische Informationen erhalten")
        return text.strip()
    
    def _protect_medical_terms(self, text: str) -> str:
        """Schützt medizinische Begriffe vor Entfernung"""
        import re
        
        # Schütze Vitamin-Kombinationen (z.B. "Vitamin D3", "Vitamin B12")
        vitamin_pattern = r'\b(Vitamin|Vit\.?)\s*([A-Z][0-9]*|[0-9]+[-,]?[0-9]*[-]?OH[-]?[A-Z]?[0-9]*)\b'
        text = re.sub(vitamin_pattern, r'§VITAMIN_\2§', text, flags=re.IGNORECASE)
        
        # Schütze Laborwert-Kombinationen mit Zahlen (z.B. "25-OH-D3", "1,25-OH2-D3")
        lab_pattern = r'\b([0-9]+[,.]?[0-9]*[-]?OH[0-9]*[-]?[A-Z]?[0-9]*)\b'
        text = re.sub(lab_pattern, r'§LAB_\1§', text, flags=re.IGNORECASE)
        
        # Ersetze medizinische Abkürzungen temporär
        for abbr in self.protected_abbreviations:
            # Case-insensitive replacement mit Wortgrenzen
            pattern = r'\b' + re.escape(abbr) + r'\b'
            text = re.sub(pattern, f"§{abbr}§", text, flags=re.IGNORECASE)
        
        return text
    
    def _restore_medical_terms(self, text: str) -> str:
        """Stellt geschützte medizinische Begriffe wieder her"""
        import re
        
        # Stelle Vitamin-Kombinationen wieder her
        text = re.sub(r'§VITAMIN_([^§]+)§', r'Vitamin \1', text)
        
        # Stelle Laborwert-Kombinationen wieder her
        text = re.sub(r'§LAB_([^§]+)§', r'\1', text)
        
        # Stelle normale Abkürzungen wieder her
        for abbr in self.protected_abbreviations:
            text = text.replace(f"§{abbr}§", abbr)
        
        return text
    
    def _remove_personal_data(self, text: str) -> str:
        """Entfernt persönliche Daten aber ERHÄLT medizinische Informationen"""
        
        # Adressen entfernen
        text = self.patterns['street_address'].sub('[ADRESSE ENTFERNT]', text)
        text = self.patterns['plz_city'].sub('[PLZ/ORT ENTFERNT]', text)
        
        # Kontaktdaten entfernen
        text = self.patterns['phone'].sub('[TELEFON ENTFERNT]', text)
        text = self.patterns['email'].sub('[EMAIL ENTFERNT]', text)
        
        # Versicherungsnummern entfernen
        text = self.patterns['insurance'].sub('[NUMMER ENTFERNT]', text)
        
        # Anreden und Grußformeln entfernen
        text = self.patterns['salutation'].sub('', text)
        
        # Geburtsdaten entfernen (aber NICHT aktuelle Untersuchungsdaten!)
        text = self.patterns['birthdate'].sub('[GEBURTSDATUM ENTFERNT]', text)
        
        # Geschlecht entfernen (wenn explizit als "Geschlecht:" angegeben)
        text = re.sub(
            r'\b(?:geschlecht)[:\s]*(?:männlich|weiblich|divers|m|w|d)\b',
            '[GESCHLECHT ENTFERNT]',
            text,
            flags=re.IGNORECASE
        )
        
        return text
    
    def _remove_names_with_ner(self, text: str) -> str:
        """
        Verwendet spaCy NER zur intelligenten Namenerkennung
        Erkennt auch "Name: Nachname, Vorname" Format
        """
        # ZUERST: Entferne explizite "Name:" Patterns
        # Pattern für "Name: Nachname, Vorname" oder "Name: Vorname Nachname"
        name_pattern = re.compile(
            r'\b(?:Name|Patient(?:in)?|Versicherte[rn]?)[:\s]+([A-ZÄÖÜ][a-zäöüß]+(?:\s*,\s*|\s+)[A-ZÄÖÜ][a-zäöüß]+)',
            re.IGNORECASE
        )
        text = name_pattern.sub('[NAME ENTFERNT]', text)
        
        # Verarbeite Text mit spaCy
        doc = self.nlp(text)
        
        # Sammle alle erkannten Personen-Entitäten
        persons_to_remove = set()
        
        for ent in doc.ents:
            # NUR PER = Person, ignoriere ORG, LOC etc.
            if ent.label_ == "PER":
                # Prüfe ob es ein medizinischer Begriff ist
                if ent.text.lower() not in self.medical_terms:
                    # Keine Zahlen im Namen (könnte Laborwert sein)
                    if not any(char.isdigit() for char in ent.text):
                        persons_to_remove.add(ent.text)
                        logger.debug(f"NER erkannt als Person: {ent.text}")
        
        # Zusätzlich: Erkenne Titel+Name Kombinationen
        for i, token in enumerate(doc):
            if token.text.lower() in ['dr.', 'prof.', 'herr', 'frau', 'dr', 'prof']:
                # Sammle die nächsten 1-2 Tokens als Namen
                name_parts = []
                for j in range(1, min(3, len(doc) - i)):
                    next_token = doc[i + j]
                    if (next_token.text[0].isupper() and 
                        len(next_token.text) > 2 and 
                        not any(char.isdigit() for char in next_token.text) and
                        next_token.text.lower() not in self.medical_terms):
                        name_parts.append(next_token.text)
                
                if name_parts:
                    full_name = ' '.join(name_parts)
                    persons_to_remove.add(full_name)
                    logger.debug(f"Titel+Name erkannt: {token.text} {full_name}")
        
        # Entferne nur die sicher erkannten Namen
        result = text
        for person in persons_to_remove:
            # Ersetze den Namen überall im Text
            result = re.sub(r'\b' + re.escape(person) + r'\b', '[NAME ENTFERNT]', result, flags=re.IGNORECASE)
        
        # Entferne Titel die alleine stehen (aber nur am Zeilenanfang)
        result = re.sub(r'^(?:Dr\.?|Prof\.?|Herr|Frau)\s*(?:\n|$)', '', result, flags=re.IGNORECASE | re.MULTILINE)
        
        return result
    
    def _remove_names_heuristic(self, text: str) -> str:
        """
        Heuristische Namenerkennung als Fallback
        Erkennt Namen basierend auf Mustern und Kontext
        """
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Entferne Zeilen mit typischen Namensmustern
            # z.B. "Dr. Hans Müller" oder "Frau Maria Schmidt"
            if re.match(r'^\s*(?:Dr\.?|Prof\.?|Herr|Frau)\s+[A-ZÄÖÜ]', line):
                # Prüfe ob die Zeile medizinische Begriffe enthält
                line_lower = line.lower()
                contains_medical = any(term in line_lower for term in self.medical_terms)
                if not contains_medical:
                    continue  # Skip diese Zeile
            
            # Entferne Namen nach "Patient:", "Name:" etc.
            line = self.patterns['patient_info'].sub('[NAME ENTFERNT]', line)
            
            # Erkenne potenzielle Namen (2-3 aufeinanderfolgende kapitalisierte Wörter)
            # aber nur wenn sie nicht medizinisch sind
            def replace_name(match):
                words = match.group(0).split()
                # Prüfe ob eines der Wörter ein medizinischer Begriff ist
                for word in words:
                    if word.lower() in self.medical_terms or '§' in word:
                        return match.group(0)  # Behalte es
                # Wenn keines medizinisch ist, könnte es ein Name sein
                if len(words) >= 2:
                    return ''
                return match.group(0)
            
            # Pattern für potenzielle Namen (2-3 kapitalisierte Wörter)
            line = re.sub(
                r'\b[A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+){1,2}\b',
                replace_name,
                line
            )
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _remove_dates_and_gender(self, text: str) -> str:
        """Entfernt Datumsangaben die Geburtsdaten sein könnten"""
        # Datumsformat prüfen (könnte Geburtsdatum sein)
        def check_date(match):
            date_str = match.group(0)
            # Extrahiere Jahr wenn möglich
            year_match = re.search(r'(19|20)\d{2}', date_str)
            if year_match:
                year = int(year_match.group(0))
                # Geburtsjahre typischerweise zwischen 1920 und 2010
                if 1920 <= year <= 2010:
                    # Aber behalte aktuelle Daten (Untersuchungsdaten)
                    import datetime
                    current_year = datetime.datetime.now().year
                    if year < current_year - 1:  # Älter als letztes Jahr
                        return '[DATUM ENTFERNT]'
            return date_str
        
        # Prüfe Datumsangaben
        date_pattern = re.compile(r'\b\d{1,2}[\.\/\-]\d{1,2}[\.\/\-](?:19|20)\d{2}\b')
        text = date_pattern.sub(check_date, text)
        
        return text
    
    def validate_medical_content(self, original: str, cleaned: str) -> bool:
        """
        Validiert, dass medizinische Inhalte erhalten geblieben sind
        
        Returns:
            True wenn mindestens 80% der medizinischen Begriffe erhalten sind
        """
        medical_keywords = [
            'diagnose', 'befund', 'labor', 'medikament', 'therapie',
            'mg', 'ml', 'mmol', 'icd', 'ops', 'untersuchung',
            'hämoglobin', 'leukozyten', 'erythrozyten', 'thrombozyten',
            'glucose', 'kreatinin', 'cholesterin'
        ]
        
        original_lower = original.lower()
        cleaned_lower = cleaned.lower()
        
        original_count = sum(1 for kw in medical_keywords if kw in original_lower)
        cleaned_count = sum(1 for kw in medical_keywords if kw in cleaned_lower)
        
        if original_count > 0:
            preservation_rate = cleaned_count / original_count
            return preservation_rate >= 0.8
        
        return True