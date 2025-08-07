# Package Update Plan - Medical Document Translator

## 📊 Aktuelle Analyse (Stand: Januar 2025)

### Frontend Dependencies

| Package | Aktuell | Neueste | Risiko | Empfehlung |
|---------|---------|---------|--------|------------|
| react | 18.2.0 | 19.1.1 | HOCH | Warten auf v19 Stabilität |
| react-dom | 18.2.0 | 19.1.1 | HOCH | Warten auf v19 Stabilität |
| react-router-dom | 6.20.1 | 7.7.1 | MITTEL | Nach React 19 Update |
| lucide-react | 0.294.0 | 0.537.0 | NIEDRIG | ✅ Sofort updaten |
| axios | 1.6.2 | 1.11.0 | NIEDRIG | ✅ Sofort updaten |
| clsx | 2.0.0 | 2.1.1 | NIEDRIG | ✅ Sofort updaten |
| react-markdown | 9.0.1 | 10.1.0 | MITTEL | Testen erforderlich |
| jspdf | 2.5.1 | 3.0.1 | MITTEL | Testen erforderlich |
| html2canvas | 1.4.1 | 1.4.1 | - | ✅ Aktuell |
| react-dropzone | 14.2.3 | 14.3.8 | NIEDRIG | ✅ Sofort updaten |
| remark-gfm | 4.0.0 | 4.0.1 | NIEDRIG | ✅ Sofort updaten |

### Backend Dependencies

Alle Backend-Packages sind aktuell ✅

## 🚀 Empfohlene Update-Reihenfolge

### Phase 1: Sichere Updates (Sofort möglich)
```bash
# Frontend
npm update axios@latest
npm update clsx@latest
npm update lucide-react@latest
npm update react-dropzone@latest
npm update remark-gfm@latest
```

### Phase 2: Minor Updates mit Testing (1-2 Wochen)
```bash
# Erst testen, dann updaten
npm update react-markdown@10
npm update jspdf@3
```

### Phase 3: Major Updates (Nach gründlichem Testing)
```bash
# React 19 Migration (Q2 2025 empfohlen)
npm update react@19 react-dom@19
npm update @types/react@19 @types/react-dom@19

# Danach React Router v7
npm update react-router-dom@7
```

## ⚠️ Breaking Changes zu beachten

### React 19
- Neue Concurrent Features
- Geänderte Event-Handler
- Strict Mode Änderungen
- Server Components (optional)

### React Router v7
- Neue Data APIs
- Loader/Action Pattern
- Geänderte Route-Konfiguration

### React Markdown v10
- Plugin-System geändert
- Import-Pfade angepasst
- Neue Komponenten-Props

### jsPDF v3
- API-Änderungen bei PDF-Generierung
- Verbesserte TypeScript-Types
- Neue Module-Struktur

## 📝 Migration Guide

### Schritt 1: Backup erstellen
```bash
git checkout -b package-updates
cp package.json package.json.backup
cp package-lock.json package-lock.json.backup
```

### Schritt 2: Sichere Updates
```bash
npm update axios clsx lucide-react react-dropzone remark-gfm
npm run test
npm run build
```

### Schritt 3: Testing der App
- [ ] Upload-Funktion testen
- [ ] PDF-Export testen
- [ ] Markdown-Rendering prüfen
- [ ] Routing testen
- [ ] Mobile Ansicht prüfen

### Schritt 4: Medium-Risk Updates
```bash
# Einzeln updaten und testen
npm update react-markdown@10
# Test PDF-Export speziell
npm update jspdf@3
```

### Schritt 5: Major Updates (später)
- Warten auf React 19 LTS
- Migration-Guide befolgen
- Umfassende Tests durchführen

## 🔍 Spezifische Anpassungen

### Für lucide-react Update
Keine Anpassungen nötig, nur mehr Icons verfügbar.

### Für react-markdown v10
```typescript
// Alt (v9)
import ReactMarkdown from 'react-markdown';

// Neu (v10) - möglicherweise
import { ReactMarkdown } from 'react-markdown';
```

### Für jsPDF v3
```typescript
// Prüfen in utils/pdfExport.ts
// API könnte sich geändert haben
```

## 📊 Risiko-Bewertung

- **Niedriges Risiko**: axios, clsx, lucide-react, dropzone
- **Mittleres Risiko**: react-markdown, jspdf
- **Hohes Risiko**: React 19, React Router 7

## 🎯 Empfehlung

1. **Sofort**: Sichere Updates durchführen (Phase 1)
2. **Diese Woche**: Phase 2 Updates mit Testing
3. **Q2 2025**: React 19 Migration wenn stabil
4. **Continuous**: Regelmäßige Security-Updates

## 🔒 Security Notes

Keine bekannten Sicherheitslücken in aktuellen Versionen.
Regelmäßig `npm audit` ausführen.