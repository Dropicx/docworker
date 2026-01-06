vastai/vllm:v0.13.0-cuda-12.9-mvc-cuda-12.0
MODEL_NAME=PaddlePaddle/PaddleOCR-VL
VLLM_ARGS="--max-model-len 16384 --gpu-memory-utilization 0.80 --download-dir /workspace/models --host 127.0.0.1 --port 18000 --trust-remote-code --max-num-batched-tokens 16384"
