import subprocess
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def main():
    print("Starting backend...")
    backend = subprocess.Popen(
        [sys.executable, "-m", "poetry", "run", "uvicorn", "main:app", "--reload"],
        cwd=ROOT,
    )
    
    print("Starting frontend...")
    frontend = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=ROOT / "cpanel",
    )
    
    try:
        backend.wait()
        frontend.wait()
    except KeyboardInterrupt:
        backend.terminate()
        frontend.terminate()

if __name__ == "__main__":
    main()
