import os
import sys
import time
import subprocess
import threading
import signal
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def check_dependencies():
    """Check if all required dependencies are installed."""
    required_packages = [
        ('fastapi', 'fastapi'),
        ('uvicorn', 'uvicorn'),
        ('streamlit', 'streamlit'),
        ('sqlalchemy', 'sqlalchemy'),
        ('dotenv', 'python-dotenv'),
        ('multipart', 'python-multipart'),
        ('google.generativeai', 'google-generativeai')
    ]

    missing_packages = []
    for import_name, package_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)

    if missing_packages:
        print("ERROR: Missing required packages. Please install them:")
        print(f"pip install {' '.join(missing_packages)}")
        return False

    print("SUCCESS: All dependencies are installed")
    return True

# Database setup not needed for MongoDB

def check_environment():
    """Check if .env file exists and has required variables."""
    env_file = current_dir / '.env'
    if not env_file.exists():
        print("WARNING: .env file not found. Creating template...")
        with open(env_file, 'w') as f:
            f.write("# Google Gemini API Key (optional for demo mode)\n")
            f.write("GOOGLE_API_KEY=\n")
        print("SUCCESS: Created .env template. Add your GOOGLE_API_KEY if you have one.")
        return True

    print("SUCCESS: Environment file found")
    return True

def start_backend():
    """Start the FastAPI backend server."""
    print("STARTING: FastAPI backend server...")
    try:
        cmd = [
            sys.executable, "-m", "uvicorn",
            "main:app",
            "--host", "127.0.0.1",
            "--port", "8000",
            "--reload"
        ]

        print(f"Backend URL: http://127.0.0.1:8000")
        print(f"API Docs: http://127.0.0.1:8000/docs")

        process = subprocess.Popen(
            cmd,
            cwd=current_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )

        # Monitor backend output
        for line in iter(process.stdout.readline, ''):
            if line.strip():
                print(f"[BACKEND] {line.strip()}")

        return process

    except Exception as e:
        print(f"ERROR: Failed to start backend: {e}")
        return None

def start_frontend():
    """Start the Streamlit frontend."""
    print("STARTING: Streamlit frontend...")
    try:
        cmd = [
            sys.executable, "-m", "streamlit", "run",
            "streamlit_app.py",
            "--server.port", "8501",
            "--server.address", "127.0.0.1"
        ]

        print(f"Frontend URL: http://127.0.0.1:8501")

        process = subprocess.Popen(
            cmd,
            cwd=current_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )

        # Monitor frontend output
        for line in iter(process.stdout.readline, ''):
            if line.strip():
                print(f"[FRONTEND] {line.strip()}")

        return process

    except Exception as e:
        print(f"ERROR: Failed to start frontend: {e}")
        return None

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print("\nSTOPPING: Shutting down RFP-Optimize AI Portal...")
    sys.exit(0)

def main():
    """Main launcher function."""
    print("RFP-Optimize AI Portal Launcher")
    print("=" * 50)

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Check environment
    if not check_environment():
        sys.exit(1)

    print("\nSTARTING: RFP-Optimize AI Portal...")
    print("Features:")
    print("   - User authentication (register/login)")
    print("   - RFP creation and management")
    print("   - AI-powered RFP analysis with recommendations")
    print("   - Role-based access (client/admin)")
    print("   - Mock AI analysis (no API key required)")
    print()

    # Start servers in separate threads
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    frontend_thread = threading.Thread(target=start_frontend, daemon=True)

    try:
        backend_thread.start()
        time.sleep(2)  # Give backend time to start
        frontend_thread.start()

        print("\nSUCCESS: Portal is running!")
        print("Access the application at: http://127.0.0.1:8501")
        print("API documentation at: http://127.0.0.1:8000/docs")
        print("\nDemo Instructions:")
        print("   1. Register a new account or login")
        print("   2. Create an RFP with detailed description")
        print("   3. Click 'Run AI' to analyze the RFP")
        print("   4. View AI recommendations and suggestions")
        print("\nPress Ctrl+C to stop the portal")

        # Keep main thread alive
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nSTOPPED: Portal stopped by user")
    except Exception as e:
        print(f"\nERROR: Portal startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()