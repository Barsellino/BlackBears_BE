#!/usr/bin/env python3
"""
Startup script that runs migrations before starting the server
"""
import subprocess
import sys

def run_migrations():
    """Run Alembic migrations"""
    print("🔄 Running database migrations...")
    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ Migrations completed successfully")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("❌ Migrations failed:")
        print(e.stderr)
        return False

def start_server():
    """Start the FastAPI server"""
    print("🚀 Starting FastAPI server...")
    subprocess.run([
        "uvicorn",
        "main:app",
        "--host", "0.0.0.0",
        "--port", "10000"
    ])

if __name__ == "__main__":
    # Run migrations first
    if not run_migrations():
        print("⚠️ Migrations failed, but starting server anyway...")
    
    # Start the server
    start_server()
