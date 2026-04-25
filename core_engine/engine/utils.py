import subprocess
import sys
import os
import logging

logger = logging.getLogger("engine.utils")

def safe_is_cuda_available(timeout=5):
    """
    Checks if CUDA is available by running a small script in a subprocess.
    This prevents the main process from hanging if the CUDA driver is unstable.
    """
    code = "import torch; print(torch.cuda.is_available())"
    try:
        # Run python with the same executable as current process
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=os.environ.copy()
        )
        if result.returncode == 0:
            return result.stdout.strip().lower() == "true"
        else:
            logger.warning(f"CUDA check subprocess failed with exit code {result.returncode}")
            return False
    except subprocess.TimeoutExpired:
        logger.warning(f"CUDA check subprocess timed out after {timeout}s. Assuming CUDA is unavailable/unstable.")
        return False
    except Exception as e:
        logger.warning(f"CUDA check failed: {e}")
        return False
