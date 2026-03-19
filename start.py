#!/usr/bin/env python
"""
Master startup script for MediAnalyze - Runs all services concurrently
"""
import subprocess
import sys
import os
import signal
import atexit
import time

# Configuration
BACKEND_DIR = os.path.join(os.path.dirname(__file__), 'backend')
MODULES_DIR = os.path.join(os.path.dirname(__file__), 'modules')

# Store process objects
processes = []

def cleanup():
    """Kill all child processes on exit"""
    print("\n🛑 Shutting down all services...")
    for proc in processes:
        if proc.poll() is None:  # If process is still running
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
    print("✅ All services stopped")

# Register cleanup on exit
atexit.register(cleanup)
signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
signal.signal(signal.SIGTERM, lambda sig, frame: sys.exit(0))

def start_service(command, cwd, name):
    """Start a service as a subprocess"""
    print(f"🚀 Starting {name}...")
    proc = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    processes.append(proc)
    return proc

def monitor_output(proc, name):
    """Monitor and print output from a process"""
    for line in iter(proc.stdout.readline, ''):
        print(f"[{name}] {line.strip()}")

print("=" * 60)
print("🚀 STARTING MEDIANALYZE - ALL SERVICES")
print("=" * 60)

# Start Backend (Node.js)
print("\n📦 Starting Node.js Backend...")
backend_proc = start_service(
    ['node', 'server.js'],
    BACKEND_DIR,
    "BACKEND"
)

# Give backend a moment to start
time.sleep(2)

# Start Module 1: Report Analyzer
print("\n📄 Starting Report Analyzer Module...")
report_proc = start_service(
    [sys.executable, 'app.py', '--port=5001'],
    os.path.join(MODULES_DIR, 'report_analyzer'),
    "REPORT"
)

# Start Module 2: Health Chatbot
print("\n🤖 Starting Health Chatbot Module...")
chatbot_proc = start_service(
    [sys.executable, 'app_integrated.py'],
    os.path.join(MODULES_DIR, 'health_chatbot'),
    "CHATBOT"
)

# Start Module 3: Symptom Checker
print("\n🔍 Starting Symptom Checker Module...")
symptom_proc = start_service(
    [sys.executable, 'app.py'],
    os.path.join(MODULES_DIR, 'symptom_checker_ml'),
    "SYMPTOM"
)

# Start Module 4: Drug Interaction
print("\n💊 Starting Drug Interaction Module...")
drug_proc = start_service(
    [sys.executable, 'app.py'],
    os.path.join(MODULES_DIR, 'drug_interaction'),
    "DRUG"
)

print("\n" + "=" * 60)
print("✅ ALL SERVICES STARTED SUCCESSFULLY")
print("📝 Backend: http://localhost:5000")
print("📝 Report Analyzer: http://localhost:5001")
print("📝 Chatbot: http://localhost:5002")
print("📝 Symptom Checker: http://localhost:5003")
print("📝 Drug Interaction: http://localhost:5004")
print("=" * 60 + "\n")

# Monitor all processes
try:
    # Create threads to monitor output
    import threading
    threads = []
    
    for proc, name in [
        (backend_proc, "BACKEND"),
        (report_proc, "REPORT"),
        (chatbot_proc, "CHATBOT"),
        (symptom_proc, "SYMPTOM"),
        (drug_proc, "DRUG")
    ]:
        thread = threading.Thread(target=monitor_output, args=(proc, name), daemon=True)
        thread.start()
        threads.append(thread)
    
    # Wait for any process to exit (shouldn't happen normally)
    for proc in processes:
        proc.wait()
        
except KeyboardInterrupt:
    print("\n\n⚠️ Received shutdown signal")
    sys.exit(0)