"""
Vast.ai PyWorker for PP-StructureV3 OCR Service

Based on the vLLM/OpenAI template pattern.
This worker registers with Vast.ai's serverless autoscaler,
enabling automatic routing via the /route/ endpoint.

Setup:
1. Create a Vast.ai Serverless Endpoint
2. Use your Docker image with PP-StructureV3
3. Set PYWORKER_REPO to your repo containing this file
4. The /route/ endpoint will now work!
"""

from vastai import Worker, WorkerConfig, HandlerConfig, LogActionConfig, BenchmarkConfig

# PP-StructureV3 model configuration
MODEL_SERVER_URL           = 'http://127.0.0.1'
MODEL_SERVER_PORT          = 9123
MODEL_LOG_FILE             = '/var/log/portal/ppstructure.log'
MODEL_HEALTHCHECK_ENDPOINT = "/health"

# PP-StructureV3 log messages for readiness detection
MODEL_LOAD_LOG_MSG = [
    "Application startup complete.",
    "Uvicorn running on",
]

MODEL_ERROR_LOG_MSGS = [
    "RuntimeError:",
    "CUDA out of memory",
    "Traceback (most recent call last):",
    "Error:",
]

MODEL_INFO_LOG_MSGS = [
    "Loading model",
    "Downloading",
]


def extract_benchmark_generator() -> dict:
    """Generate a minimal benchmark payload for OCR."""
    # For OCR we can't easily generate test images,
    # so we use a minimal payload that the /extract endpoint accepts
    return {
        "mode": "structured",
        "benchmark": True
    }


def ocr_workload_calculator(data: dict) -> float:
    """
    Calculate workload for OCR requests.

    OCR workload is roughly flat per request since we process
    one document at a time. Could be refined based on page count.
    """
    # Flat cost per OCR request (GPU-bound operation)
    return 100.0


# Worker configuration following vLLM pattern
worker_config = WorkerConfig(
    model_server_url=MODEL_SERVER_URL,
    model_server_port=MODEL_SERVER_PORT,
    model_log_file=MODEL_LOG_FILE,
    model_healthcheck_url=MODEL_HEALTHCHECK_ENDPOINT,
    handlers=[
        # Main OCR extraction endpoint
        HandlerConfig(
            route="/extract",
            workload_calculator=ocr_workload_calculator,
            allow_parallel_requests=False,  # OCR is GPU-intensive, sequential processing
            max_queue_time=300.0,  # 5 minutes for large documents
            benchmark_config=BenchmarkConfig(
                generator=extract_benchmark_generator,
                concurrency=1,
                runs=1
            )
        ),
        # Health check (lightweight)
        HandlerConfig(
            route="/health",
            workload_calculator=lambda data: 1.0,
            allow_parallel_requests=True,
            max_queue_time=10.0,
        ),
    ],
    log_action_config=LogActionConfig(
        on_load=MODEL_LOAD_LOG_MSG,
        on_error=MODEL_ERROR_LOG_MSGS,
        on_info=MODEL_INFO_LOG_MSGS
    )
)

# Start the PyWorker
if __name__ == "__main__":
    print("Starting PP-StructureV3 PyWorker for Vast.ai Serverless...")
    Worker(worker_config).run()
