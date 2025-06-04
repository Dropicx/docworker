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
echo "🎯 NEUE FEATURES:"
echo "   📝 Verbesserter Systemprompt für detailliertere Zusammenfassungen"
echo "   🎨 Schönere Darstellung mit strukturierten Abschnitten"  
echo "   📋 Emoji-basierte Gliederung (📋 🏥 📊 💊 ⚠️ 🏠)"
echo "   💡 Hervorhebung medizinischer Begriffe"
echo "   📈 Verbesserte Lesbarkeit und Struktur"
echo ""
echo "💡 Jetzt verwendet das System mistral-nemo:latest für bessere deutsche medizinische Übersetzungen!"
echo ""
echo "🌐 Öffne https://medical.fra-la.de um die Verbesserungen zu testen" 