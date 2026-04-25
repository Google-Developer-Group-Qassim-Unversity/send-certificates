import subprocess
import sys


def main():
    cmd = [
        "infisical",
        "run",
        "--path=/emails-backend",
        "--env=dev",
        "--",
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--reload",
    ]
    subprocess.run(cmd)


if __name__ == "__main__":
    main()
