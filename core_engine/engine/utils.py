import subprocess
import sys
import os
import logging

logger = logging.getLogger("engine.utils")

def safe_is_cuda_available():
    """Checks if CUDA is available without risky long-running subprocesses."""
    # Method 1: Environment variable check (Fastest)
    if os.environ.get('CUDA_VISIBLE_DEVICES') == '-1':
        return False
        
    # Method 2: Simple torch import with timeout
    try:
        import torch
        return torch.cuda.is_available()
    except Exception as e:
        logger.warning(f"Direct CUDA check failed: {e}")
        
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
