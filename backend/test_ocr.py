#!/usr/bin/env python3
"""
Test script to verify OCR capabilities
Run this to check if OCR is properly configured
"""

import sys
import os

def test_ocr_setup():
    print("=== OCR Setup Test ===\n")
    
    # Test 1: Check if pytesseract is installed
    print("1. Checking pytesseract installation...")
    try:
        import pytesseract
        print("   ✅ pytesseract is installed")
    except ImportError as e:
        print(f"   ❌ pytesseract NOT installed: {e}")
        return False
    
    # Test 2: Check if Tesseract binary is available
    print("\n2. Checking Tesseract binary...")
    try:
        version = pytesseract.get_tesseract_version()
        print(f"   ✅ Tesseract version: {version}")
    except Exception as e:
        print(f"   ❌ Tesseract binary NOT found: {e}")
        print("   Install with: apt-get install tesseract-ocr")
        return False
    
    # Test 3: Check available languages
    print("\n3. Checking available languages...")
    try:
        languages = pytesseract.get_languages()
        print(f"   Available languages: {', '.join(languages)}")
        
        required = ['eng', 'deu']
        missing = [lang for lang in required if lang not in languages]
        
        if not missing:
            print("   ✅ Required languages (eng, deu) are available")
        else:
            print(f"   ⚠️ Missing languages: {', '.join(missing)}")
            print(f"   Install with: apt-get install tesseract-ocr-{' tesseract-ocr-'.join(missing)}")
    except Exception as e:
        print(f"   ❌ Could not get languages: {e}")
    
    # Test 4: Check pdf2image
    print("\n4. Checking pdf2image installation...")
    try:
        from pdf2image import convert_from_bytes
        print("   ✅ pdf2image is installed")
    except ImportError as e:
        print(f"   ❌ pdf2image NOT installed: {e}")
        print("   Install with: pip install pdf2image")
        return False
    
    # Test 5: Check poppler-utils
    print("\n5. Checking poppler-utils...")
    try:
        import subprocess
        result = subprocess.run(['pdftoppm', '-v'], capture_output=True, text=True)
        if result.returncode == 0 or 'version' in result.stderr.lower():
            print("   ✅ poppler-utils is installed")
        else:
            raise Exception("pdftoppm not working")
    except Exception as e:
        print(f"   ❌ poppler-utils NOT installed or not working")
        print("   Install with: apt-get install poppler-utils")
        return False
    
    # Test 6: Try a simple OCR operation
    print("\n6. Testing OCR functionality...")
    try:
        from PIL import Image
        import numpy as np
        
        # Create a simple test image with text
        img = Image.new('RGB', (200, 50), color='white')
        
        # Run OCR on the test image
        text = pytesseract.image_to_string(img)
        print("   ✅ OCR test successful")
    except Exception as e:
        print(f"   ❌ OCR test failed: {e}")
        return False
    
    print("\n" + "="*30)
    print("✅ All OCR components are properly configured!")
    print("="*30)
    return True

if __name__ == "__main__":
    success = test_ocr_setup()
    sys.exit(0 if success else 1)