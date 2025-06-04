#!/usr/bin/env python3

import magic
import os
import sys
from app.services.file_validator import FileValidator, ALLOWED_MIME_TYPES, FALLBACK_MIME_TYPES, MAX_FILE_SIZE, MIN_FILE_SIZE

def debug_magic():
    print("=== Magic Library Debug ===")
    try:
        # Test magic library
        test_content = b"PDF test content"
        mime_type = magic.from_buffer(test_content, mime=True)
        print(f"✅ Magic library working. Test content detected as: {mime_type}")
        
        # Check available MIME types
        print(f"📋 Allowed MIME types: {list(ALLOWED_MIME_TYPES.keys())}")
        print(f"🔄 Fallback MIME types: {list(FALLBACK_MIME_TYPES.keys())}")
        print(f"📏 File size limits: {MIN_FILE_SIZE} - {MAX_FILE_SIZE} bytes")
        
    except Exception as e:
        print(f"❌ Magic library error: {e}")
        return False
    
    return True

def test_common_files():
    print("\n=== Common File Types Test ===")
    
    # Test different content types
    test_cases = [
        (b"%PDF-1.4", "PDF header"),
        (b"\xff\xd8\xff", "JPEG header"),
        (b"\x89PNG\r\n\x1a\n", "PNG header"),
        (b"random content", "Random content")
    ]
    
    for content, description in test_cases:
        try:
            mime_type = magic.from_buffer(content, mime=True)
            
            # Check if it would be accepted
            status = "❌"
            if mime_type in ALLOWED_MIME_TYPES:
                status = "✅ DIRECT"
            elif mime_type in FALLBACK_MIME_TYPES:
                status = "⚠️ FALLBACK"
                
            print(f"{status} {description}: {mime_type}")
        except Exception as e:
            print(f"❌ {description} error: {e}")

def check_system_deps():
    print("\n=== System Dependencies ===")
    
    # Check if libmagic is available
    try:
        import ctypes.util
        libmagic_path = ctypes.util.find_library('magic')
        if libmagic_path:
            print(f"✅ libmagic found at: {libmagic_path}")
        else:
            print("❌ libmagic not found!")
            
        # Try to create magic object
        m = magic.Magic(mime=True)
        print("✅ Magic object created successfully")
        
    except Exception as e:
        print(f"❌ System dependency error: {e}")

if __name__ == "__main__":
    print("🔍 Upload Debug Tool")
    print("===================")
    
    magic_ok = debug_magic()
    test_common_files()
    check_system_deps()
    
    if not magic_ok:
        print("\n❌ Magic library has issues - this is likely the cause of upload failures")
        sys.exit(1)
    else:
        print("\n✅ All checks passed - upload should work") 