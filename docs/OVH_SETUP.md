# OVH API Setup for DocTranslator

## Overview
DocTranslator now uses OVH AI Endpoints exclusively for all AI processing, eliminating the need for local Ollama instances.

## Configuration

### Models Used
- **Preprocessing**: `Mistral-Nemo-Instruct-2407` - Removes personal data while preserving medical information
- **Main Processing**: `Meta-Llama-3.3-70B-Instruct` - Translates medical text to patient-friendly language
- **Language Translation**: `Meta-Llama-3.3-70B-Instruct` - Translates to different languages

### Environment Variables
Add these to your `.env` file:

```env
# OVH AI Endpoints Configuration
OVH_AI_ENDPOINTS_ACCESS_TOKEN=your-ovh-access-token-here
OVH_AI_BASE_URL=https://oai.endpoints.kepler.ai.cloud.ovh.net/v1

# OVH Model Configuration
OVH_MAIN_MODEL=Meta-Llama-3_3-70B-Instruct
OVH_PREPROCESSING_MODEL=Mistral-Nemo-Instruct-2407
OVH_TRANSLATION_MODEL=Meta-Llama-3_3-70B-Instruct

# Use OVH for all processing (no local Ollama needed)
USE_OVH_ONLY=true
```

## Getting Started

### 1. Get OVH API Token
1. Sign up at [OVH AI Endpoints](https://endpoints.ai.cloud.ovh.net/)
2. Create a new API token
3. Add it to your `.env` file

### 2. Start the Application
```bash
# No need to start Ollama anymore!
docker-compose up -d
```

### 3. Test the Configuration
```bash
# Run from the backend directory
cd backend
python tests/test_ovh_integration.py
```

## Benefits of OVH-Only Setup

✅ **No GPU Required**: Works on any server without GPU hardware
✅ **No Local Models**: No need to download or manage large model files
✅ **Better Performance**: Access to high-performance models like Llama 3.3 70B
✅ **Simplified Deployment**: Fewer containers and dependencies
✅ **Cost Effective**: Pay only for what you use

## Processing Pipeline

1. **Document Upload**: User uploads medical document
2. **Preprocessing** (Mistral-Nemo): Removes personal data, keeps medical content
3. **Main Processing** (Llama 3.3 70B): Translates to patient-friendly German
4. **Language Translation** (Llama 3.3 70B): Optional translation to other languages

## Fallback to Local Ollama

If you need to switch back to local Ollama:

1. Set `USE_OVH_ONLY=false` in `.env`
2. Uncomment the `ollama-gpu` service in `docker-compose.yml`
3. Start Ollama and pull required models:
   ```bash
   docker-compose up -d ollama-gpu
   docker exec -it ollama-gpu ollama pull gpt-oss:20b
   docker exec -it ollama-gpu ollama pull zongwei/gemma3-translator:4b
   ```

## Troubleshooting

### OVH Connection Failed
- Check your API token is correct
- Verify network connectivity to OVH endpoints
- Ensure token has necessary permissions

### Wrong Language in Response
- OVH models respect the input language
- All prompts are configured in German
- Models are instructed to respond in the same language as input

### Cache Issues
If you see old content:
```bash
# Clear the processing cache
docker-compose restart backend
```

## API Rate Limits
- Check OVH documentation for rate limits
- Implement retry logic for production use
- Consider caching for frequently processed documents