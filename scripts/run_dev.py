import subprocess
import os
import sys

def main():
    print("Starting backend...")
    backend = subprocess.Popen([sys.executable, "-m", "poetry", "run", "uvicorn", "main:app", "--reload"])
    
    print("Starting frontend...")
    os.chdir("cpanel")
    frontend = subprocess.Popen(["npm", "run", "dev"], shell=True)
    
    try:
        backend.wait()
        frontend.wait()
    except KeyboardInterrupt:
        backend.terminate()
        frontend.terminate()

if __name__ == "__main__":
    main()
