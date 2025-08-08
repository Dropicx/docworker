# External API Configuration - OVH AI Endpoints

## Overview

This branch is configured to use a hybrid approach for medical document translation:

1. **Preprocessing**: Local Ollama with `gpt-oss:20b` model
2. **Main Processing**: OVH AI Endpoints with `Meta-Llama-3.3-70B-Instruct`
3. **Language Translation**: Local Ollama with `gemma3-translator:4b` model

## Architecture

```
┌─────────────────┐
│ Medical Document│
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ Preprocessing (Local)   │
│ Model: gpt-oss:20b      │
│ Purpose: Clean & Extract│
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Main Processing (OVH)   │
│ Model: Llama-3.3-70B    │
│ Purpose: Medical→Simple │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ Translation (Local)     │
│ Model: gemma3-translator│
│ Purpose: Language Trans │
└────────┬────────────────┘
         │
         ▼
┌─────────────────┐
│ Translated Text │
└─────────────────┘
```

## Setup Instructions

### 1. Environment Variables

Add the following to your `.env` file:

```env
# OVH AI Endpoints Configuration
OVH_AI_ENDPOINTS_ACCESS_TOKEN=your-access-token-here
OVH_AI_BASE_URL=https://oai.endpoints.kepler.ai.cloud.ovh.net/v1
OVH_AI_MODEL=Meta-Llama-3_3-70B-Instruct

# Ollama Model Configuration
OLLAMA_PREPROCESSING_MODEL=gpt-oss:20b
OLLAMA_TRANSLATION_MODEL=zongwei/gemma3-translator:4b
```

### 2. Get OVH Access Token

1. Go to [OVH AI Endpoints](https://endpoints.ai.cloud.ovh.net/)
2. Create an account or sign in
3. Navigate to AI Endpoints section
4. Generate an access token
5. Copy the token to your `.env` file

### 3. Install Local Ollama Models

Make sure Ollama is running and install the required models:

```bash
# Install preprocessing model
ollama pull gpt-oss:20b

# Install translation model
ollama pull zongwei/gemma3-translator:4b
```

### 4. Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

## Testing the Configuration

Run the test script to verify everything is working:

```bash
cd backend/tests
python test_ovh_integration.py
```

The test will check:
- ✅ OVH API connection
- ✅ Local Ollama models availability
- ✅ Preprocessing with gpt-oss:20b
- ✅ Main processing with OVH API
- ✅ Language translation with gemma3-translator
- ✅ Complete pipeline integration

## Usage

### API Endpoints

The same API endpoints work as before, but now use the hybrid approach:

```bash
# Upload a document
curl -X POST "http://localhost:9122/api/upload" \
  -F "file=@document.pdf"

# Start processing (with optional language translation)
curl -X POST "http://localhost:9122/api/process/{processing_id}" \
  -H "Content-Type: application/json" \
  -d '{"target_language": "en"}'

# Check status
curl "http://localhost:9122/api/process/{processing_id}/status"

# Get result
curl "http://localhost:9122/api/process/{processing_id}/result"
```

## Model Details

### gpt-oss:20b (Local - Preprocessing)
- **Purpose**: Text cleaning, anonymization, format removal
- **Location**: Local Ollama CPU instance
- **Benefits**: Fast preprocessing, data privacy

### Meta-Llama-3.3-70B-Instruct (OVH API - Main)
- **Purpose**: Medical text simplification
- **Location**: OVH Cloud
- **Benefits**: High quality, large model capacity
- **Latency**: ~2-5 seconds per request

### gemma3-translator:4b (Local - Translation)
- **Purpose**: Multi-language translation
- **Location**: Local Ollama GPU instance
- **Benefits**: Fast translation, supports 30+ languages

## Fallback Behavior

If OVH API is unavailable, the system automatically falls back to local models:

1. **Primary**: OVH Meta-Llama-3.3-70B
2. **Fallback 1**: Local gpt-oss:20b
3. **Fallback 2**: Local mistral-nemo:latest
4. **Fallback 3**: Any available local model

## Performance Considerations

- **Preprocessing**: ~1-2 seconds (local)
- **Main Processing**: ~3-5 seconds (OVH API)
- **Translation**: ~1-2 seconds (local)
- **Total Pipeline**: ~5-9 seconds

## Cost Optimization

The OVH API is only used for the main medical text processing, while preprocessing and translation use local models to minimize API costs.

## Security

- Patient data is anonymized locally before sending to OVH
- OVH API uses secure HTTPS connections
- Access token is stored in environment variables only
- No patient data is stored on OVH servers

## Troubleshooting

### OVH API Connection Failed
- Check your access token is correct
- Verify network connectivity
- Ensure token has not expired

### Local Models Not Found
- Run `ollama list` to check installed models
- Pull missing models with `ollama pull <model-name>`
- Ensure Ollama service is running

### High Latency
- Check network connection to OVH
- Consider increasing timeout values
- Monitor OVH service status

## Support

For issues or questions:
- Check OVH status: https://status.ovhcloud.com/
- Ollama documentation: https://ollama.ai/
- Project issues: [GitHub Issues]