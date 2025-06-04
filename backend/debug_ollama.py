#!/usr/bin/env python3

import asyncio
import httpx
import json
import os

class OllamaDebugger:
    def __init__(self):
        # Verwende die gleiche Logik wie der echte Client
        if os.getenv("ENVIRONMENT") == "production":
            self.base_url = "http://ollama:11434"
        else:
            self.base_url = "http://localhost:11434"
        
        print(f"🔍 Debugging Ollama at: {self.base_url}")
    
    async def test_connection(self):
        """Test basic connection"""
        print("\n=== Connection Test ===")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}")
                print(f"✅ Base URL ({self.base_url}): {response.status_code}")
                if response.status_code == 200:
                    print(f"   Response: {response.text[:100]}")
        except Exception as e:
            print(f"❌ Base URL error: {e}")
    
    async def test_version(self):
        """Test version endpoint"""
        print("\n=== Version Test ===")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/version")
                print(f"✅ Version endpoint: {response.status_code}")
                if response.status_code == 200:
                    print(f"   Version: {response.json()}")
                else:
                    print(f"   Error: {response.text}")
        except Exception as e:
            print(f"❌ Version error: {e}")
    
    async def test_models(self):
        """Test models endpoint"""
        print("\n=== Models Test ===")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                print(f"✅ Models endpoint: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    print(f"   Found {len(models)} models:")
                    for model in models:
                        print(f"   - {model.get('name', 'Unknown')}")
                    return [m.get('name') for m in models]
                else:
                    print(f"   Error: {response.text}")
                    return []
        except Exception as e:
            print(f"❌ Models error: {e}")
            return []
    
    async def test_generate(self, model_name="llama3.1"):
        """Test generate endpoint"""
        print(f"\n=== Generate Test (Model: {model_name}) ===")
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                payload = {
                    "model": model_name,
                    "prompt": "Hallo, das ist ein Test.",
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 50
                    }
                }
                
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                
                print(f"✅ Generate endpoint: {response.status_code}")
                if response.status_code == 200:
                    result = response.json()
                    response_text = result.get("response", "No response")
                    print(f"   Response: {response_text[:100]}...")
                    return True
                else:
                    print(f"   Error: {response.text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Generate error: {e}")
            return False
    
    async def test_all_endpoints(self):
        """Test all endpoints systematically"""
        print("🔍 Ollama Debug Tool")
        print("===================")
        
        # Basic connection
        await self.test_connection()
        
        # Version check
        await self.test_version()
        
        # List models
        models = await self.test_models()
        
        # Test generation with available models
        if models:
            print(f"\n=== Testing Generation with Available Models ===")
            for model in models[:3]:  # Test first 3 models
                success = await self.test_generate(model)
                if success:
                    print(f"✅ Model {model} works!")
                    break
        else:
            # Try default model anyway
            print(f"\n=== Testing with Default Model ===")
            await self.test_generate("llama3.1")
        
        print("\n🏁 Debug completed!")

async def main():
    debugger = OllamaDebugger()
    await debugger.test_all_endpoints()

if __name__ == "__main__":
    asyncio.run(main()) 