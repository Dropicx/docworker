# Railway Environment Variables Guide

## 🚨 PFLICHT-Variablen (MANDATORY)

Diese **MÜSSEN** in Railway gesetzt werden, sonst startet die App nicht!

| Variable | Wert | Beschreibung |
|----------|------|--------------|
| `OVH_AI_ENDPOINTS_ACCESS_TOKEN` | `ihr-ovh-token` | Ihr OVH AI Endpoints API Token |
| `OVH_AI_BASE_URL` | `https://oai.endpoints.kepler.ai.cloud.ovh.net/v1` | OVH API Endpoint URL |

## 📝 Optionale Variablen

Diese haben bereits sinnvolle Standardwerte:

| Variable | Standardwert | Beschreibung |
|----------|--------------|--------------|
| `ENVIRONMENT` | `production` | Umgebung |
| `LOG_LEVEL` | `INFO` | Log-Level (DEBUG, INFO, WARNING, ERROR) |
| `OVH_MAIN_MODEL` | `Meta-Llama-3_3-70B-Instruct` | Hauptmodell für Verarbeitung |
| `OVH_PREPROCESSING_MODEL` | `Mistral-Nemo-Instruct-2407` | Modell für Vorverarbeitung |
| `OVH_TRANSLATION_MODEL` | `Meta-Llama-3_3-70B-Instruct` | Modell für Übersetzungen |
| `USE_OVH_ONLY` | `true` | Nur OVH verwenden (kein Ollama) |

## 🔧 So fügen Sie Variablen in Railway hinzu:

1. **Railway Dashboard öffnen**: https://railway.app/dashboard
2. **Ihr Projekt auswählen**: doctranslator
3. **"Variables" Tab klicken**
4. **"Add Variable" klicken**
5. **Variable hinzufügen**:
   - Name: `OVH_AI_ENDPOINTS_ACCESS_TOKEN`
   - Value: `[Ihr Token von OVH]`
6. **Wiederholen für** `OVH_AI_BASE_URL`
7. **Deploy triggern** (passiert automatisch nach Speichern)

## ⚠️ WICHTIG:

- **NIEMALS** `PORT` manuell setzen - Railway setzt das automatisch!
- Die App wird **NICHT starten** ohne die PFLICHT-Variablen
- Nach dem Setzen der Variablen wird automatisch ein neues Deployment gestartet

## 🔍 Variablen überprüfen:

Nach dem Deployment können Sie in den Logs prüfen:
```
Environment check:
- USE_OVH_ONLY: true
- OVH_API_ENDPOINT: https://oai.endpoints.kepler.ai.cloud.ovh.net/v1
- OVH_API_KEY: [SET]
```

## 🆘 Fehlersuche:

**Backend startet nicht?**
- Prüfen Sie ob `OVH_AI_ENDPOINTS_ACCESS_TOKEN` gesetzt ist
- Prüfen Sie ob `OVH_AI_BASE_URL` korrekt ist

**500 Error beim Zugriff?**
- Checken Sie https://doctranslator-production.up.railway.app/health
- Schauen Sie in die Railway Logs

## 📊 Vollständige Variable Liste für Copy & Paste:

```env
OVH_AI_ENDPOINTS_ACCESS_TOKEN=your-token-here
OVH_AI_BASE_URL=https://oai.endpoints.kepler.ai.cloud.ovh.net/v1
ENVIRONMENT=production
LOG_LEVEL=INFO
OVH_MAIN_MODEL=Meta-Llama-3_3-70B-Instruct
OVH_PREPROCESSING_MODEL=Mistral-Nemo-Instruct-2407
OVH_TRANSLATION_MODEL=Meta-Llama-3_3-70B-Instruct
USE_OVH_ONLY=true
```

Kopieren Sie diese und fügen Sie sie in Railway ein, ersetzen Sie `your-token-here` mit Ihrem echten Token!