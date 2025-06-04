from datetime import datetime
from fastapi import APIRouter, Request
from app.models.document import HealthCheck
from app.services.cleanup import get_memory_usage
from app.services.ollama_client import OllamaClient
import tempfile
import os
import shutil

router = APIRouter()

@router.get("/health", response_model=HealthCheck)
async def health_check(request: Request = None):
    """
    Umfassender Gesundheitscheck des Systems
    """
    
    # Debug: Log health check request
    if request:
        print(f"🔍 === HEALTH REQUEST DEBUG ===")
        print(f"🔍 Method: {request.method}")
        print(f"🔍 URL: {request.url}")
        print(f"🔍 Headers: {dict(request.headers)}")
        print(f"🔍 Client: {request.client}")
        print(f"🔍 === END HEALTH DEBUG ===")
    
    try:
        services = {}
        
        # Ollama-Service prüfen
        ollama_client = OllamaClient()
        ollama_connected = await ollama_client.check_connection()
        services["ollama"] = "healthy" if ollama_connected else "error"
        
        # Tesseract prüfen
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            services["tesseract"] = "healthy"
        except Exception:
            services["tesseract"] = "error"
        
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
            from PIL import Image
            services["image_processing"] = "healthy"
        except Exception:
            services["image_processing"] = "error"
        
        # PDF-Verarbeitung prüfen
        try:
            import PyPDF2
            import pdfplumber
            services["pdf_processing"] = "healthy"
        except Exception:
            services["pdf_processing"] = "error"
        
        # Speichernutzung
        memory_usage = get_memory_usage()
        
        # Gesamtstatus bestimmen
        error_services = [name for name, status in services.items() if status == "error"]
        overall_status = "healthy" if not error_services else "degraded" if len(error_services) < len(services) / 2 else "error"
        
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
        
        # Zusätzliche Details
        details = {
            "active_processes": len(processing_store),
            "temp_directory": tempfile.gettempdir(),
            "temp_space_available": shutil.disk_usage(tempfile.gettempdir()).free,
            "python_version": os.sys.version,
            "process_id": os.getpid()
        }
        
        # Disk Space Check
        temp_space_gb = details["temp_space_available"] / (1024**3)
        if temp_space_gb < 1:  # Weniger als 1GB frei
            basic_health.services["disk_space"] = "warning"
        else:
            basic_health.services["disk_space"] = "healthy"
        
        # Ollama-Modelle prüfen
        try:
            ollama_client = OllamaClient()
            models = await ollama_client.list_models()
            details["available_models"] = models
            details["model_count"] = len(models)
        except Exception:
            details["available_models"] = []
            details["model_count"] = 0
        
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
    
    # Externe Services
    try:
        ollama_client = OllamaClient()
        ollama_status = await ollama_client.check_connection()
        dependencies["ollama_service"] = "connected" if ollama_status else "disconnected"
    except Exception:
        dependencies["ollama_service"] = "error"
    
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