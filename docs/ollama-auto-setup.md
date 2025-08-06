# Ollama Automatic Model Loading

## Overview
The Ollama service in the doctranslator application now automatically loads all required models at startup, ensuring that the application always has the necessary language models available.

## How It Works

### 1. Startup Script
The `ollama/ollama-startup.sh` script is executed when the Ollama container starts. It:
- Waits for the Ollama service to be ready
- Checks which models are already available
- Automatically pulls any missing models
- Starts the Ollama server to handle requests

### 2. Model Priority
The application uses the following models in priority order:
1. **mistral-nemo:latest** - Primary model for medical translations
2. **llama3.2:latest** - First fallback option
3. **llama3.1** - Secondary fallback
4. **mistral:7b** - Additional fallback
5. **deepseek-r1:7b** - Alternative model
6. **gemma3:27b** - Final fallback option

### 3. Docker Compose Configuration
The `docker-compose.yml` has been updated to:
- Mount the startup script as `/startup.sh` in the container
- Execute the script as the container's command
- Ensure models are loaded before the service accepts requests

## Usage

### Starting the Service
```bash
docker-compose up -d ollama
```

The service will:
1. Start the container
2. Run the startup script
3. Check and pull missing models
4. Start serving requests

### Monitoring Progress
To see the model loading progress:
```bash
docker-compose logs -f ollama
```

### Manual Model Management
If you need to manually manage models:

```bash
# List available models
docker-compose exec ollama ollama list

# Pull a specific model
docker-compose exec ollama ollama pull mistral-nemo:latest

# Remove a model
docker-compose exec ollama ollama rm model-name
```

## Benefits

1. **Zero Manual Setup**: No need to manually pull models after deployment
2. **Automatic Recovery**: If models are accidentally deleted, they're restored on restart
3. **Fallback Support**: Multiple models ensure service availability
4. **Consistent Environment**: All deployments have the same models available

## Troubleshooting

### Models Not Loading
If models fail to load:
1. Check container logs: `docker-compose logs ollama`
2. Verify internet connection for model downloads
3. Ensure sufficient disk space in `./ollama/ollama` directory
4. Check GPU availability if using GPU-accelerated models

### Primary Model Failure
If the primary model (mistral-nemo:latest) fails to load:
- The container will exit with error code 1
- Check logs for specific error messages
- Verify model availability at https://ollama.ai/library

### Performance Considerations
- Initial startup may take longer due to model downloads
- Models are cached locally after first download
- Subsequent restarts will be much faster

## Maintenance

### Updating Models
To update to newer model versions:
1. Update the model list in `ollama/ollama-startup.sh`
2. Restart the container: `docker-compose restart ollama`
3. Old models can be removed manually if needed

### Disk Space
Models can be large (several GB each). Monitor disk usage:
```bash
du -sh ./ollama/ollama
```

### Model Selection
The application automatically selects the best available model. To change the priority:
1. Edit `backend/app/services/ollama_client.py`
2. Update the `fallback_models` list in the order of preference
3. Restart the backend service