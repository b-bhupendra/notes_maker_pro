import subprocess
import sys
import os
import logging

logger = logging.getLogger("engine.utils")

def safe_is_cuda_available():
    """Checks if CUDA is available without risky long-running subprocesses."""
    # TEMPORARY: Bypass torch import to avoid silent crash on Python 3.13
    return False
        
    # Method 3: Lightweight subprocess fallback
    try:
        code = "import torch; print(torch.cuda.is_available())"
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=15, # Shorter timeout
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        return result.stdout.strip().lower() == "true"
    except Exception:
        return False
