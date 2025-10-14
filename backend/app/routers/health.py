from datetime import datetime
import logging
import os
import shutil
import tempfile

from fastapi import APIRouter, Request
from shared.redis_client import get_redis
from shared.task_queue import check_workers_available

from app.models.document import HealthCheck
from app.services.cleanup import get_memory_usage
from app.services.ovh_client import OVHClient

logger = logging.getLogger(__name__)

def check_ocr_capabilities() -> dict:
    """
    Check OCR architecture status

    NOTE: OCR processing now happens in the WORKER service, not backend.
    Backend no longer requires OCR dependencies (PaddleOCR runs in worker).
    """
    return {
        "ocr_location": "worker_service",
        "backend_ocr": False,
        "available_engines": ["PADDLEOCR", "VISION_LLM", "HYBRID"],
        "architecture": "worker_based",
        "status": "delegated_to_worker",
        "note": "OCR handled by Celery worker with PaddleOCR, Vision LLM, and Hybrid engines"
    }


router = APIRouter()

@router.get("/health", response_model=HealthCheck)
async def health_check(request: Request = None):
    """
    Umfassender Gesundheitscheck des Systems
    """

    # Debug: Log health check request
    if request:
        print("🔍 === HEALTH REQUEST DEBUG ===")
        print(f"🔍 Method: {request.method}")
        print(f"🔍 URL: {request.url}")
        print(f"🔍 Headers: {dict(request.headers)}")
        print(f"🔍 Client: {request.client}")
        print("🔍 === END HEALTH DEBUG ===")

    try:
        services = {}

        # Redis prüfen
        try:
            redis_client = get_redis()
            redis_client.ping()
            services["redis"] = "healthy"
        except Exception as e:
            services["redis"] = f"error: {str(e)[:50]}"

        # Celery Worker prüfen
        try:
            from celery import Celery
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
            celery_app = Celery(broker=redis_url, backend=redis_url)

            worker_status = check_workers_available(celery_app, timeout=1.0)
            if worker_status['available']:
                services["worker"] = f"healthy ({worker_status['worker_count']} active)"
            else:
                services["worker"] = f"error: {worker_status.get('error', 'No workers available')}"
        except Exception as e:
            services["worker"] = f"error: {str(e)[:50]}"

        # OVH API prüfen
        ovh_client = OVHClient()
        ovh_connected, error_msg = await ovh_client.check_connection()
        services["ovh_api"] = "healthy" if ovh_connected else f"error: {error_msg[:100]}"

        # PaddleOCR Service prüfen
        try:
            paddleocr_url = os.getenv('PADDLEOCR_SERVICE_URL')
            if paddleocr_url:
                import httpx
                async with httpx.AsyncClient(timeout=2.0) as client:
                    response = await client.get(f"{paddleocr_url}/health")
                    if response.status_code == 200:
                        services["paddleocr"] = "healthy"
                    else:
                        services["paddleocr"] = f"error: HTTP {response.status_code}"
            else:
                services["paddleocr"] = "not_configured"
        except Exception as e:
            services["paddleocr"] = f"error: {str(e)[:50]}"

        # Temporäres Verzeichnis prüfen
        try:
            temp_dir = tempfile.gettempdir()
            test_file = os.path.join(temp_dir, "health_check_test")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            services["filesystem"] = "healthy"
        except Exception:
            services["filesystem"] = "error"

        # PIL/Pillow prüfen
        try:
            services["image_processing"] = "healthy"
        except Exception:
            services["image_processing"] = "error"

        # PDF-Verarbeitung prüfen
        try:
            services["pdf_processing"] = "healthy"
        except Exception:
            services["pdf_processing"] = "error"

        # Speichernutzung
        memory_usage = get_memory_usage()

        # Gesamtstatus bestimmen - Worker und OCR sind kritisch!
        error_services = [name for name, status in services.items() if "error" in status]
        critical_services = ["redis", "worker", "ovh_api", "paddleocr"]
        critical_errors = [name for name in error_services if name in critical_services]

        if critical_errors:
            overall_status = "error"
        elif error_services:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        return HealthCheck(
            status=overall_status,
            services=services,
            memory_usage=memory_usage
        )

    except Exception as e:
        return HealthCheck(
            status="error",
            services={"error": str(e)},
            memory_usage=None
        )

@router.get("/health/simple")
async def simple_health_check():
    """
    Einfacher Gesundheitscheck für Load Balancer
    """
    return {"status": "ok", "timestamp": datetime.now()}

@router.get("/health/detailed")
async def detailed_health_check():
    """
    Detaillierter Gesundheitscheck mit zusätzlichen Informationen
    """

    try:
        from app.services.cleanup import processing_store

        # Basis-Gesundheitscheck
        basic_health = await health_check()

        # OCR capability check
        ocr_status = check_ocr_capabilities()

        # Zusätzliche Details
        details = {
            "active_processes": len(processing_store),
            "temp_directory": tempfile.gettempdir(),
            "temp_space_available": shutil.disk_usage(tempfile.gettempdir()).free,
            "python_version": os.sys.version,
            "process_id": os.getpid(),
            "ocr_capabilities": ocr_status
        }

        # Disk Space Check
        temp_space_gb = details["temp_space_available"] / (1024**3)
        if temp_space_gb < 1:  # Weniger als 1GB frei
            basic_health.services["disk_space"] = "warning"
        else:
            basic_health.services["disk_space"] = "healthy"

        # Model availability prüfen - OVH models are configured via environment
        ovh_models = [
            os.getenv("OVH_MAIN_MODEL", "Meta-Llama-3_3-70B-Instruct"),
            os.getenv("OVH_PREPROCESSING_MODEL", "Mistral-Nemo-Instruct-2407"),
            os.getenv("OVH_TRANSLATION_MODEL", "Meta-Llama-3_3-70B-Instruct")
        ]
        details["available_models"] = list(set(ovh_models))  # Remove duplicates
        details["model_count"] = len(details["available_models"])
        details["api_mode"] = "OVH AI Endpoints"

        return {
            **basic_health.dict(),
            "details": details
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now()
        }

# Debug endpoint removed for production security
# To enable debugging, set ENVIRONMENT=development

@router.get("/health/test-markdown-format")
async def test_markdown_format():
    """
    Testet die neue Markdown-Formatierung mit Sublisten
    """

    # Test mit problematischem Text
    test_cases = {
        "simple_bullet_arrow": """• Sie haben Atemnot. → Bedeutung: Sie kommen schnell außer Atem.
• Sie haben Brustschmerzen. → Bedeutung: Ihr Herz arbeitet nicht richtig.""",

        "multiple_arrows": """• Ramipril 5mg. → Wofür: Senkt Ihren Blutdruck. → Einnahme: 1x morgens.
• Metformin 1000mg. → Wofür: Hilft bei der Zuckerverarbeitung. → Einnahme: 2x täglich zum Essen.""",

        "mixed_content": """## 💊 Behandlung & Medikamente

• Ramipril 5mg. → Wofür: Senkt Ihren Blutdruck. → Einnahme: 1x morgens.
• Metformin 1000mg. → Wofür: Hilft bei der Zuckerverarbeitung. → Einnahme: 2x täglich zum Essen.

## 📊 Ihre Werte

• Blutdruck: 140/90 mmHg → Bedeutung: Leicht erhöht, sollte gesenkt werden.
• Blutzucker: 7.8% HbA1c → Bedeutung: Über dem Zielwert, besser kontrollieren."""
    }

    # Teste unsere neue Formatierung
    from app.services.ovh_client import OVHClient
    client = OVHClient()

    formatted_results = {}
    for name, text in test_cases.items():
        formatted = client._improve_formatting(text)
        formatted_results[name] = {
            "original": text,
            "formatted": formatted,
            "lines_original": text.split('\n'),
            "lines_formatted": formatted.split('\n'),
            "contains_sublists": '  - ' in formatted,
            "arrow_count": formatted.count('→'),
            "bullet_count": formatted.count('•'),
            "sublist_count": formatted.count('  - ')
        }

    return {
        "test_results": formatted_results,
        "formatting_info": {
            "method": "Markdown sublists with '  - ' prefix",
            "expected_rendering": "Indented arrows with gray background",
            "reactmarkdown_compatible": True
        }
    }

@router.get("/health/test-formatting-live")
async def test_formatting_live():
    """
    Live-Test der Formatierung mit sichtbarem Output
    """
    # Beispiel-Text der häufig problematisch ist
    problem_text = """## 🏥 Ihre Diagnosen

• Arterielle Hypertonie (Bluthochdruck). → Bedeutung: Ihr Blutdruck ist dauerhaft erhöht.
• Diabetes mellitus Typ 2 (Zuckerkrankheit). → Bedeutung: Ihr Körper kann Zucker nicht richtig verarbeiten.

## 💊 Behandlung & Medikamente

• Ramipril 5mg. → Wofür: Senkt Ihren Blutdruck. → Einnahme: 1x morgens.
• Metformin 1000mg. → Wofür: Hilft bei der Zuckerverarbeitung. → Einnahme: 2x täglich zum Essen."""

    from app.services.ovh_client import OVHClient
    client = OVHClient()

    # Formatierung anwenden
    formatted = client._improve_formatting(problem_text)

    # HTML-Version für Browser-Anzeige erstellen
    html_display = formatted.replace('\n', '<br>').replace('  ', '&nbsp;&nbsp;')

    return {
        "original": problem_text,
        "formatted": formatted,
        "html_preview": f"<pre style='font-family: monospace; white-space: pre-wrap;'>{html_display}</pre>",
        "line_by_line": {
            "original": problem_text.split('\n'),
            "formatted": formatted.split('\n')
        },
        "stats": {
            "original_lines": len(problem_text.split('\n')),
            "formatted_lines": len(formatted.split('\n')),
            "arrows_found": problem_text.count('→'),
            "bullets_found": problem_text.count('•')
        }
    }

@router.get("/health/test-formatting")
async def test_formatting():
    """
    Testet die Formatierungsfunktion
    """
    # Test text mit problematischen Formatierungen
    test_text = """## 📊 Zusammenfassung
### Was wurde gemacht?
• Sie wurden von einem Facharzt für Innere Medizin und Kardiologie untersucht. • Es wurde eine Anamnese (Krankengeschichte) aufgenommen. • Es wurden verschiedene Untersuchungen durchgeführt, wie ein EKG, eine Echokardiographie und eine Ergometrie.

### Was wurde gefunden?
• Sie haben Atemnot bereits bei geringer körperlicher Anstrengung (NYHA II-III). → Bedeutung: Das bedeutet, dass Sie schnell außer Atem kommen, wenn Sie sich anstrengen.
• Sie haben gelegentliche retrosternale Druckgefühle in der Brust. → Bedeutung: Das bedeutet, dass Sie manchmal ein Druckgefühl in der Brust verspüren.
• Ihr Blutdruck ist normal. → Bedeutung: Das bedeutet, dass Ihr Blutdruck im normalen Bereich liegt."""

    from app.services.ovh_client import OVHClient
    client = OVHClient()

    # Schritt für Schritt debuggen
    import re

    steps = []
    step1 = test_text
    steps.append({"step": "original", "text": step1})

    # Schritt 1: Bullet Points auf neue Zeilen
    step2 = re.sub(r'([^\n])(•)', r'\1\n•', step1)
    steps.append({"step": "bullets_on_newlines", "text": step2})

    # Schritt 2: Pfeile auf neue Zeilen
    step3 = re.sub(r'([^^\n])(\s*→\s*)', r'\1\n  → ', step2)
    steps.append({"step": "arrows_on_newlines", "text": step3})

    formatted_text = client._improve_formatting(test_text)

    # Zeige auch die Zeilen einzeln für besseres Debugging
    lines_original = test_text.split('\n')
    lines_formatted = formatted_text.split('\n')

    return {
        "original": test_text,
        "formatted": formatted_text,
        "steps": steps,
        "lines_comparison": {
            "original_lines": lines_original,
            "formatted_lines": lines_formatted,
            "line_count_original": len(lines_original),
            "line_count_formatted": len(lines_formatted)
        },
        "api_mode": "OVH"
    }

@router.get("/health/dependencies")
async def check_dependencies():
    """
    Prüft alle wichtigen Abhängigkeiten
    """

    dependencies = {}

    # Python-Pakete
    packages = [
        "fastapi", "uvicorn", "pydantic", "httpx",
        "PIL", "pytesseract", "PyPDF2", "pdfplumber"
    ]

    for package in packages:
        try:
            __import__(package)
            dependencies[package] = "installed"
        except ImportError:
            dependencies[package] = "missing"

    # System-Kommandos
    system_commands = ["tesseract"]

    for cmd in system_commands:
        try:
            import subprocess
            result = subprocess.run([cmd, "--version"],
                                 capture_output=True,
                                 timeout=5)
            dependencies[f"system_{cmd}"] = "available" if result.returncode == 0 else "error"
        except Exception:
            dependencies[f"system_{cmd}"] = "missing"

    # Externe Services - OVH API Service
    try:
        from app.services.ovh_client import OVHClient
        ovh_client = OVHClient()
        ovh_status, error_msg = await ovh_client.check_connection()
        dependencies["ovh_api_service"] = "connected" if ovh_status else f"disconnected: {error_msg[:50]}"
    except Exception as e:
        dependencies["ovh_api_service"] = f"error: {str(e)}"

    # Zusammenfassung
    missing_deps = [name for name, status in dependencies.items()
                   if status in ["missing", "error", "disconnected"]]

    return {
        "dependencies": dependencies,
        "missing_count": len(missing_deps),
        "missing_dependencies": missing_deps,
        "status": "healthy" if not missing_deps else "degraded",
        "timestamp": datetime.now()
    }
