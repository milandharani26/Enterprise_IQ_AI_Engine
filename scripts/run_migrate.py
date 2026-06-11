import subprocess
import sys

def main():
    print("Running database migrations...")
    subprocess.run([sys.executable, "-m", "poetry", "run", "alembic", "upgrade", "head"])

if __name__ == "__main__":
    main()
