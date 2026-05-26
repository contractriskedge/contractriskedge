"""Startup script for the ContractRiskEdge platform.

Starts the API server, Celery worker, and Celery beat scheduler.
"""

import os
import subprocess
import sys
import time


def start_celery_worker():
    """Start the Celery worker for background task processing."""
    print("Starting Celery worker...")
    return subprocess.Popen(
        [
            sys.executable, "-m", "celery", "-A", "ingestion.tasks.celery_app",
            "worker", "--loglevel=info", "--concurrency=4",
            "--queues=ingestion,extraction,ocr,evaluation",
            "--hostname=worker1@%h",
        ],
        cwd=os.path.join(os.path.dirname(__file__), "api"),
    )


def start_celery_beat():
    """Start the Celery beat scheduler for periodic tasks."""
    print("Starting Celery beat...")
    return subprocess.Popen(
        [
            sys.executable, "-m", "celery", "-A", "ingestion.tasks.celery_app",
            "beat", "--loglevel=info",
        ],
        cwd=os.path.join(os.path.dirname(__file__), "api"),
    )


def start_api_server():
    """Start the FastAPI server."""
    print("Starting API server...")
    return subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "main:app",
            "--host", "0.0.0.0", "--port", "8000",
            "--reload", "--reload-delay", "5",
        ],
        cwd=os.path.join(os.path.dirname(__file__), "api"),
    )


if __name__ == "__main__":
    processes = []

    try:
        # Start Celery worker
        worker = start_celery_worker()
        processes.append(worker)
        time.sleep(2)

        # Start Celery beat
        beat = start_celery_beat()
        processes.append(beat)
        time.sleep(1)

        # Start API server
        api = start_api_server()
        processes.append(api)

        print("\n✅ All services started:")
        print("   API Server:    http://localhost:8000")
        print("   Celery Worker: processing ingestion tasks")
        print("   Celery Beat:   scheduling periodic tasks")
        print("\nPress Ctrl+C to stop all services.\n")

        # Wait for any process to exit
        for p in processes:
            p.wait()

    except KeyboardInterrupt:
        print("\nShutting down all services...")
    finally:
        for p in processes:
            p.terminate()
            p.wait()
        print("All services stopped.")
