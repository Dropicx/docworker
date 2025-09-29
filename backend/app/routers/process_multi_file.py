"""
Multi-File Processing Router
Handles batch upload and processing of multiple medical document files
"""

import os
import logging
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
import uuid

from app.services.hybrid_text_extractor import HybridTextExtractor
from app.services.ovh_client import OVHClient
from app.services.file_validator import FileValidator
from app.models.document import ProcessingResponse, ProcessingStatus, DocumentType, CustomPrompts

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
hybrid_extractor = HybridTextExtractor()
ovh_client = OVHClient()
file_validator = FileValidator()

# Configuration
MAX_FILES = int(os.getenv("MAX_FILES_PER_BATCH", "10"))
MAX_TOTAL_SIZE = int(os.getenv("MAX_TOTAL_BATCH_SIZE", "50000000"))  # 50MB

@router.post("/process-multi-file", response_model=ProcessingResponse)
async def process_multiple_files(
    files: List[UploadFile] = File(...),
    document_type: str = Form("universal"),
    target_language: Optional[str] = Form(None),
    merge_strategy: str = Form("smart"),
    enable_preprocessing: bool = Form(True),
    custom_prompts: Optional[str] = Form(None)
):
    """
    Process multiple medical document files as a single cohesive document

    Args:
        files: List of files to process (PDFs, images)
        document_type: Type of medical document
        target_language: Optional language for translation
        merge_strategy: How to merge files ("smart", "sequential")
        enable_preprocessing: Whether to apply preprocessing
        custom_prompts: Optional custom processing prompts

    Returns:
        ProcessingResponse with merged results
    """
    session_id = str(uuid.uuid4())
    start_time = datetime.now()

    logger.info("=" * 80)
    logger.info("🚀 MULTI-FILE PROCESSING STARTED")
    logger.info("=" * 80)
    logger.info(f"📋 Session ID: {session_id}")
    logger.info(f"📁 File count: {len(files)}")
    logger.info(f"📄 Document type: {document_type}")
    logger.info(f"🔧 Merge strategy: {merge_strategy}")
    logger.info(f"🌐 Target language: {target_language or 'None'}")

    try:
        # Step 1: Validate request
        await _validate_multi_file_request(files)

        # Step 2: Validate and prepare files
        validated_files = []
        total_size = 0

        for i, file in enumerate(files, 1):
            logger.info(f"📄 Validating file {i}/{len(files)}: {file.filename}")

            # Read file content
            file_content = await file.read()
            file_size = len(file_content)
            total_size += file_size

            # Validate individual file
            is_valid, file_type, error_message = await file_validator.validate_file(
                file_content, file.filename
            )

            if not is_valid:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {i} ({file.filename}) validation failed: {error_message}"
                )

            validated_files.append({
                'content': file_content,
                'filename': file.filename,
                'file_type': file_type,
                'size': file_size
            })

            logger.info(f"✅ File {i} validated: {file_type}, {file_size:,} bytes")

        logger.info(f"📊 Total batch size: {total_size:,} bytes")

        # Step 3: Extract text using hybrid approach
        logger.info("🔍 Starting hybrid text extraction...")

        file_tuples = [
            (f['content'], f['file_type'], f['filename'])
            for f in validated_files
        ]

        extracted_text, extraction_confidence = await hybrid_extractor.extract_from_multiple_files(
            file_tuples, merge_strategy=merge_strategy
        )

        if not extracted_text or extracted_text.startswith("Error"):
            raise HTTPException(
                status_code=500,
                detail=f"Text extraction failed: {extracted_text}"
            )

        logger.info(f"✅ Text extraction successful:")
        logger.info(f"   - Extracted: {len(extracted_text):,} characters")
        logger.info(f"   - Confidence: {extraction_confidence:.1%}")

        # Step 4: Optional preprocessing
        if enable_preprocessing:
            logger.info("🔧 Applying preprocessing...")
            try:
                preprocessed_text = await ovh_client.preprocess_medical_text(
                    extracted_text,
                    temperature=0.3,
                    max_tokens=4000
                )

                if preprocessed_text and not preprocessed_text.startswith("Error"):
                    extracted_text = preprocessed_text
                    logger.info(f"✅ Preprocessing successful: {len(extracted_text):,} characters")
                else:
                    logger.warning("⚠️ Preprocessing failed, using original text")

            except Exception as e:
                logger.warning(f"⚠️ Preprocessing error: {e}, using original text")

        # Step 5: Process medical text
        logger.info("🏥 Processing medical text...")

        # Parse custom prompts if provided
        prompts = None
        if custom_prompts:
            try:
                import json
                prompts = CustomPrompts(**json.loads(custom_prompts))
            except Exception as e:
                logger.warning(f"⚠️ Invalid custom prompts: {e}")

        # Process with OVH
        translated_text, final_doc_type, processing_confidence, cleaned_original = await ovh_client.translate_medical_document(
            text=extracted_text,
            document_type=document_type,
            custom_prompts=prompts
        )

        if not translated_text or translated_text.startswith("Error"):
            raise HTTPException(
                status_code=500,
                detail=f"Medical processing failed: {translated_text}"
            )

        # Step 6: Optional language translation
        final_text = translated_text
        translation_confidence = processing_confidence

        if target_language and target_language.lower() not in ['german', 'deutsch', 'de']:
            logger.info(f"🌐 Translating to {target_language}...")

            try:
                final_text, translation_confidence = await ovh_client.translate_to_language(
                    translated_text,
                    target_language,
                    temperature=0.3,
                    max_tokens=4000
                )

                if final_text and not final_text.startswith("Error"):
                    logger.info(f"✅ Language translation successful: {len(final_text):,} characters")
                else:
                    logger.warning("⚠️ Language translation failed, using original")
                    final_text = translated_text

            except Exception as e:
                logger.warning(f"⚠️ Language translation error: {e}")
                final_text = translated_text

        # Step 7: Calculate processing time and final confidence
        processing_time = (datetime.now() - start_time).total_seconds()

        # Weighted confidence score
        final_confidence = (
            extraction_confidence * 0.4 +
            processing_confidence * 0.4 +
            translation_confidence * 0.2
        )

        # Step 8: Create response
        response = ProcessingResponse(
            success=True,
            processed_text=final_text,
            original_text=cleaned_original,
            document_type=DocumentType(final_doc_type),
            confidence_score=final_confidence,
            processing_time=processing_time,
            extraction_method="hybrid_multi_file",
            preprocessing_applied=enable_preprocessing,
            file_count=len(files),
            total_characters=len(final_text),
            session_id=session_id,
            target_language=target_language,
            merge_strategy=merge_strategy
        )

        logger.info("=" * 80)
        logger.info("🎯 MULTI-FILE PROCESSING COMPLETED")
        logger.info("=" * 80)
        logger.info(f"📊 Results:")
        logger.info(f"   - Files processed: {len(files)}")
        logger.info(f"   - Total time: {processing_time:.1f}s")
        logger.info(f"   - Final confidence: {final_confidence:.1%}")
        logger.info(f"   - Output characters: {len(final_text):,}")
        logger.info(f"   - Session ID: {session_id}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Multi-file processing failed: {e}")
        logger.error("=" * 80)

        return ProcessingResponse(
            success=False,
            processed_text=f"Multi-file processing error: {str(e)}",
            original_text="",
            document_type=DocumentType.universal,
            confidence_score=0.0,
            processing_time=(datetime.now() - start_time).total_seconds(),
            extraction_method="error",
            file_count=len(files),
            session_id=session_id,
            error_details=str(e)
        )

async def _validate_multi_file_request(files: List[UploadFile]):
    """Validate the multi-file request"""

    if not files:
        raise HTTPException(
            status_code=400,
            detail="No files provided"
        )

    if len(files) > MAX_FILES:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files. Maximum allowed: {MAX_FILES}"
        )

    # Check total size (approximate)
    total_size = 0
    for file in files:
        if hasattr(file, 'size') and file.size:
            total_size += file.size

    if total_size > MAX_TOTAL_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Total file size too large. Maximum allowed: {MAX_TOTAL_SIZE:,} bytes"
        )

    logger.info(f"✅ Multi-file request validation passed:")
    logger.info(f"   - File count: {len(files)}")
    logger.info(f"   - Estimated total size: {total_size:,} bytes")

@router.get("/multi-file/limits")
async def get_multi_file_limits():
    """Get the limits for multi-file uploads"""
    return {
        "max_files": MAX_FILES,
        "max_total_size": MAX_TOTAL_SIZE,
        "supported_formats": ["pdf", "jpg", "jpeg", "png", "tiff", "bmp"],
        "merge_strategies": ["smart", "sequential"],
        "max_file_size": int(os.getenv("MAX_FILE_SIZE", "10000000"))  # Individual file limit
    }

@router.post("/process-multi-file/batch-status")
async def get_batch_processing_status(session_ids: List[str]):
    """Get status for multiple processing sessions (future implementation)"""
    # This would integrate with a job queue system for tracking long-running processes
    return {
        "message": "Batch status tracking not yet implemented",
        "session_ids": session_ids
    }

@router.post("/analyze-files")
async def analyze_files_strategy(files: List[UploadFile] = File(...)):
    """
    Analyze files to determine optimal processing strategy without processing

    Args:
        files: List of files to analyze

    Returns:
        Analysis results and recommended strategy
    """
    try:
        logger.info(f"🔍 Analyzing {len(files)} files for strategy recommendation")

        if len(files) > MAX_FILES:
            raise HTTPException(
                status_code=400,
                detail=f"Too many files for analysis. Maximum: {MAX_FILES}"
            )

        # Validate and prepare files
        file_tuples = []
        for i, file in enumerate(files, 1):
            file_content = await file.read()

            # Basic validation
            is_valid, file_type, error = await file_validator.validate_file(
                file_content, file.filename
            )

            if not is_valid:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {i} validation failed: {error}"
                )

            file_tuples.append((file_content, file_type, file.filename))

        # Analyze files
        analysis = await hybrid_extractor.quality_detector.analyze_multiple_files(file_tuples)

        logger.info(f"✅ File analysis complete:")
        logger.info(f"   - Recommended strategy: {analysis['recommended_strategy']}")
        logger.info(f"   - Complexity: {analysis['recommended_complexity']}")

        return {
            "success": True,
            "file_count": len(files),
            "analysis": analysis,
            "recommendations": {
                "processing_time_estimate": _estimate_processing_time(analysis),
                "expected_accuracy": _estimate_accuracy(analysis),
                "cost_estimate": _estimate_cost(analysis)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ File analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"File analysis error: {str(e)}"
        )

def _estimate_processing_time(analysis: Dict[str, Any]) -> str:
    """Estimate processing time based on analysis"""
    file_count = analysis.get("file_count", 1)
    strategy = analysis.get("recommended_strategy", "vision_llm")

    if strategy == "local_text":
        base_time = 2  # seconds per file
    elif strategy == "local_ocr":
        base_time = 10  # seconds per file
    elif strategy == "vision_llm":
        base_time = 30  # seconds per file
    else:
        base_time = 20  # hybrid

    total_time = file_count * base_time
    return f"{total_time}-{total_time * 2} seconds"

def _estimate_accuracy(analysis: Dict[str, Any]) -> str:
    """Estimate accuracy based on analysis"""
    strategy = analysis.get("recommended_strategy", "vision_llm")
    complexity = analysis.get("recommended_complexity", "complex")

    if strategy == "local_text":
        return "95-99% (clean embedded text)"
    elif strategy == "vision_llm":
        if complexity == "simple":
            return "90-95% (high quality vision OCR)"
        elif complexity == "complex":
            return "80-90% (complex layout, good context understanding)"
        else:
            return "70-85% (very complex, challenging content)"
    else:
        return "75-90% (mixed approach)"

def _estimate_cost(analysis: Dict[str, Any]) -> str:
    """Estimate processing cost based on analysis"""
    strategy = analysis.get("recommended_strategy", "vision_llm")
    file_count = analysis.get("file_count", 1)

    if strategy == "local_text" or strategy == "local_ocr":
        return "Free (local processing)"
    elif strategy == "vision_llm":
        # Rough estimate based on OVH pricing
        cost_per_file = 0.01  # Rough estimate
        total_cost = file_count * cost_per_file
        return f"~${total_cost:.2f} (vision model usage)"
    else:
        return "Mixed (free + paid components)"