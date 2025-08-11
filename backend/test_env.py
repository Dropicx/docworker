#!/usr/bin/env python3
"""
Test script to verify OVH environment variables
Run this locally or on Railway to debug configuration
"""

import os
import sys

def check_env():
    """Check if all required environment variables are set"""
    
    print("=" * 60)
    print("OVH AI ENDPOINTS ENVIRONMENT CHECK")
    print("=" * 60)
    
    required_vars = {
        "OVH_AI_ENDPOINTS_ACCESS_TOKEN": "Your OVH API access token",
        "OVH_AI_BASE_URL": "OVH API endpoint URL (default: https://oai.endpoints.kepler.ai.cloud.ovh.net/v1)",
        "USE_OVH_ONLY": "Should be 'true' for Railway deployment"
    }
    
    optional_vars = {
        "OVH_MAIN_MODEL": "Main model (default: Meta-Llama-3_3-70B-Instruct)",
        "OVH_PREPROCESSING_MODEL": "Preprocessing model (default: Mistral-Nemo-Instruct-2407)",
        "OVH_TRANSLATION_MODEL": "Translation model (default: Meta-Llama-3_3-70B-Instruct)"
    }
    
    print("\n📋 REQUIRED Variables:")
    print("-" * 40)
    
    all_ok = True
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            if var == "OVH_AI_ENDPOINTS_ACCESS_TOKEN":
                # Mask the token for security
                display_value = f"***{value[-8:]}" if len(value) > 8 else "***"
                print(f"✅ {var}: {display_value} ({len(value)} chars)")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: NOT SET - {description}")
            all_ok = False
    
    print("\n📋 OPTIONAL Variables:")
    print("-" * 40)
    
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value}")
        else:
            print(f"ℹ️  {var}: Using default - {description}")
    
    print("\n📋 Railway Variables:")
    print("-" * 40)
    
    railway_vars = ["RAILWAY_ENVIRONMENT", "PORT", "RAILWAY_PROJECT_ID", "RAILWAY_SERVICE_ID"]
    for var in railway_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value}")
        else:
            print(f"ℹ️  {var}: Not set (normal if running locally)")
    
    print("\n" + "=" * 60)
    if all_ok:
        print("✅ All required variables are set!")
        print("Your application should be able to connect to OVH AI Endpoints.")
    else:
        print("❌ Some required variables are missing!")
        print("\nTo fix this in Railway:")
        print("1. Go to your Railway project dashboard")
        print("2. Click on your service")
        print("3. Go to 'Variables' tab")
        print("4. Add the missing variables")
        print("\nExample values:")
        print("  OVH_AI_ENDPOINTS_ACCESS_TOKEN=your-token-here")
        print("  OVH_AI_BASE_URL=https://oai.endpoints.kepler.ai.cloud.ovh.net/v1")
        print("  USE_OVH_ONLY=true")
    print("=" * 60)
    
    return all_ok

if __name__ == "__main__":
    success = check_env()
    sys.exit(0 if success else 1)