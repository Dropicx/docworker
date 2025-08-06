#!/bin/bash

echo "🔄 Aktualisiere DocTranslator mit verbessertem Systemprompt und Frontend..."
echo ""

# Prüfe ob Docker Compose läuft
if ! docker-compose ps | grep -q "Up"; then
    echo "⚠️ Starte Docker Compose Services..."
    docker-compose up -d
    echo "⏳ Warte 10 Sekunden bis Services bereit sind..."
    sleep 10
fi

# Backend neu starten um Code-Änderungen zu laden
echo "🔄 Starte Backend mit neuen Prompts neu..."
docker-compose restart backend

# Frontend neu bauen und starten
echo "🎨 Aktualisiere Frontend mit neuen Styles..."
docker-compose restart frontend

echo "⏳ Warte 30 Sekunden bis alles bereit ist..."
sleep 30

# Gesundheitscheck
echo ""
echo "🔍 Prüfe System-Status..."
./check.sh

echo ""
echo "✅ System wurde erfolgreich aktualisiert!"
echo ""
echo "🎯 NEUER SPEZIALISIERTER MEDIZINISCHER SYSTEMPROMPT:"
echo "   🔬 Hochspezialisierte medizinische Dokumentenübersetzung"
echo "   ⚕️ Absolute Sicherheitsregeln für medizinische Genauigkeit"
echo "   📋 Strukturiertes Ausgabeformat mit klaren Abschnitten"
echo "   🎯 4-Stufen-Verarbeitungsprozess (Analyse → Extraktion → Übersetzung → Validierung)"
echo "   📚 Umfassende Übersetzungsbeispiele und Fachbegriff-Wörterbuch"
echo "   🏥 Spezialisierte Anweisungen für alle Dokumenttypen:"
echo "      • Arztbriefe mit Therapieempfehlungen"
echo "      • Laborbefunde mit Werteerklärungen"
echo "      • Radiologie-Befunde mit Bildgebungserklärungen"
echo "      • Pathologie-Befunde mit sensitiver Kommunikation"
echo "      • Entlassungsbriefe mit Nachsorgehinweisen"
echo "   🛡️ Erweiterte Sicherheitsmechanismen bei Unsicherheiten"
echo "   💬 Verbesserte sprachliche Richtlinien für Patientenverständlichkeit"
echo "   ⚖️ Rechtlicher Hinweis und Qualitätskontrolle"
echo ""
echo "💡 Das System verwendet jetzt den hochspezialisierten medizinischen Systemprompt!"
echo ""
echo "🌐 Öffne https://medical.fra-la.de um die Verbesserungen zu testen" 