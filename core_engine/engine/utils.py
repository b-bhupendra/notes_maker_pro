import subprocess
import sys
import os
import logging

logger = logging.getLogger("engine.utils")

def safe_is_cuda_available(timeout=20):  # INCREASED TIMEOUT
    """Checks if CUDA is available by running a small script in a subprocess."""
    code = "import torch; print(torch.cuda.is_available())"
    try:
        # Added creationflags to prevent popup windows on Windows
        flags = 0
        if os.name == 'nt':
            import subprocess
            flags = subprocess.CREATE_NO_WINDOW

        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=os.environ.copy(),
            creationflags=flags
        )
        if result.returncode == 0:
            return result.stdout.strip().lower() == "true"
        return False
    except Exception as e:
        logger.warning(f"CUDA check failed or timed out: {e}")
        return False
