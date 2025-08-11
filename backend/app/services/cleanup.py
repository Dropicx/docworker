import os
import tempfile
import asyncio
import shutil
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
import gc

logger = logging.getLogger(__name__)

# Globaler In-Memory Store für Verarbeitungsdaten
processing_store: Dict[str, Dict[str, Any]] = {}

# Maximale Lebenszeit für temporäre Daten (30 Minuten)
MAX_DATA_AGE = timedelta(minutes=30)

async def cleanup_temp_files():
    """Bereinigt alle temporären Dateien und Daten"""
    try:
        # Cleanup temporäre Dateien im System temp
        files_removed = await cleanup_system_temp_files()
        
        # Cleanup In-Memory Store
        items_removed = await cleanup_memory_store()
        
        # Garbage Collection
        gc.collect()
        
        if files_removed > 0 or items_removed > 0:
            logger.info(f"🧹 Cleanup: {files_removed} files, {items_removed} memory items removed")
        
        return files_removed
        
    except Exception as e:
        logger.error(f"❌ Cleanup-Fehler: {e}")
        return 0

async def cleanup_system_temp_files():
    """Bereinigt temporäre Dateien im Systemverzeichnis"""
    files_removed = 0
    try:
        temp_dir = tempfile.gettempdir()
        current_time = datetime.now()
        
        # Suche nach medizinischen Dokumenten-Dateien
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.startswith(('medical_', 'uploaded_', 'processed_')):
                    file_path = os.path.join(root, file)
                    try:
                        # Datei älter als 1 Stunde?
                        file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                        if current_time - file_time > timedelta(hours=1):
                            os.remove(file_path)
                            files_removed += 1
                            logger.debug(f"🗑️ Temporäre Datei gelöscht: {file}")
                    except (OSError, FileNotFoundError):
                        # Datei bereits gelöscht oder nicht zugreifbar
                        continue
        
        return files_removed
                        
    except Exception as e:
        logger.error(f"❌ System-Temp-Cleanup Fehler: {e}")
        return files_removed

async def cleanup_memory_store():
    """Bereinigt den In-Memory Store von alten Daten"""
    items_removed = 0
    try:
        current_time = datetime.now()
        expired_keys = []
        
        for processing_id, data in processing_store.items():
            created_time = data.get('created_at', current_time)
            
            # Daten älter als MAX_DATA_AGE?
            if current_time - created_time > MAX_DATA_AGE:
                expired_keys.append(processing_id)
        
        # Abgelaufene Daten löschen
        for key in expired_keys:
            del processing_store[key]
            items_removed += 1
            logger.debug(f"🗑️ Abgelaufene Verarbeitungsdaten gelöscht: {key}")
        
        if len(processing_store) > 0:
            logger.debug(f"📊 Aktive Verarbeitungen: {len(processing_store)}")
        
        return items_removed
        
    except Exception as e:
        logger.error(f"❌ Memory-Store-Cleanup Fehler: {e}")
        return items_removed

def add_to_processing_store(processing_id: str, data: Dict[str, Any]):
    """Fügt Daten zum Processing Store hinzu"""
    data['created_at'] = datetime.now()
    processing_store[processing_id] = data

def get_from_processing_store(processing_id: str) -> Dict[str, Any]:
    """Holt Daten aus dem Processing Store"""
    return processing_store.get(processing_id, {})

def update_processing_store(processing_id: str, updates: Dict[str, Any]):
    """Aktualisiert Daten im Processing Store"""
    if processing_id in processing_store:
        processing_store[processing_id].update(updates)

def remove_from_processing_store(processing_id: str):
    """Entfernt Daten aus dem Processing Store"""
    if processing_id in processing_store:
        del processing_store[processing_id]
        logger.debug(f"🗑️ Verarbeitungsdaten manuell gelöscht: {processing_id}")

async def create_secure_temp_file(prefix: str = "medical_", suffix: str = "") -> str:
    """Erstellt eine sichere temporäre Datei"""
    try:
        fd, temp_path = tempfile.mkstemp(prefix=prefix, suffix=suffix)
        os.close(fd)  # Dateideskriptor schließen
        
        # Berechtigungen setzen (nur Besitzer kann lesen/schreiben)
        os.chmod(temp_path, 0o600)
        
        return temp_path
        
    except Exception as e:
        logger.error(f"❌ Temp-Datei-Erstellung Fehler: {e}")
        raise

async def secure_delete_file(file_path: str):
    """Sicheres Löschen einer Datei"""
    try:
        if os.path.exists(file_path):
            # Datei überschreiben vor dem Löschen (einfache Sicherung)
            with open(file_path, "wb") as f:
                f.write(os.urandom(os.path.getsize(file_path)))
            
            # Datei löschen
            os.remove(file_path)
            logger.debug(f"🔒 Datei sicher gelöscht: {os.path.basename(file_path)}")
            
    except Exception as e:
        logger.error(f"❌ Sicheres Löschen fehlgeschlagen: {e}")

def get_memory_usage() -> Dict[str, Any]:
    """Gibt Speichernutzung zurück"""
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            "rss": memory_info.rss,  # Resident Set Size
            "vms": memory_info.vms,  # Virtual Memory Size
            "percent": process.memory_percent(),
            "processing_store_size": len(processing_store)
        }
    except ImportError:
        return {
            "processing_store_size": len(processing_store),
            "note": "psutil nicht verfügbar für detaillierte Speicherinfo"
        }

async def emergency_cleanup():
    """Notfall-Bereinigung bei hoher Speichernutzung"""
    try:
        logger.warning("🚨 Notfall-Bereinigung gestartet...")
        
        # Alle Verarbeitungsdaten löschen
        processing_store.clear()
        
        # Aggressive temp file cleanup
        await cleanup_system_temp_files()
        
        # Force garbage collection
        for _ in range(3):
            gc.collect()
        
        logger.info("✅ Notfall-Bereinigung abgeschlossen")
        
    except Exception as e:
        logger.error(f"❌ Notfall-Bereinigung Fehler: {e}") 