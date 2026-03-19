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
import threading

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
        if line.strip():
            print(f"[{name}] {line.strip()}")

print("=" * 60)
print("🚀 STARTING MEDIANALYZE - ALL SERVICES")
print(f"📂 Current directory: {os.getcwd()}")
print(f"📂 Backend directory: {BACKEND_DIR}")
print(f"📂 Modules directory: {MODULES_DIR}")
print("=" * 60)

# Check if files exist
print("\n🔍 Checking file existence...")
print(f"✅ Backend server.js exists: {os.path.exists(os.path.join(BACKEND_DIR, 'server.js'))}")
print(f"✅ index.html exists: {os.path.exists(os.path.join(os.path.dirname(__file__), 'index.html'))}")

# Start Backend (Node.js)
print("\n📦 Starting Node.js Backend...")
backend_proc = start_service(
    ['node', 'server.js'],
    BACKEND_DIR,
    "BACKEND"
)

# Give backend a moment to start
time.sleep(3)

# Start Module 1: Report Analyzer
print("\n📄 Starting Report Analyzer Module...")
if os.path.exists(os.path.join(MODULES_DIR, 'report_analyzer', 'app.py')):
    report_proc = start_service(
        [sys.executable, 'app.py', '--port=5001'],
        os.path.join(MODULES_DIR, 'report_analyzer'),
        "REPORT"
    )
else:
    print("⚠️ Report Analyzer module not found, skipping...")
    report_proc = None

# Start Module 2: Health Chatbot
print("\n🤖 Starting Health Chatbot Module...")
if os.path.exists(os.path.join(MODULES_DIR, 'health_chatbot', 'app_integrated.py')):
    chatbot_proc = start_service(
        [sys.executable, 'app_integrated.py'],
        os.path.join(MODULES_DIR, 'health_chatbot'),
        "CHATBOT"
    )
else:
    print("⚠️ Health Chatbot module not found, skipping...")
    chatbot_proc = None

# Start Module 3: Symptom Checker
print("\n🔍 Starting Symptom Checker Module...")
if os.path.exists(os.path.join(MODULES_DIR, 'symptom_checker_ml', 'app.py')):
    symptom_proc = start_service(
        [sys.executable, 'app.py'],
        os.path.join(MODULES_DIR, 'symptom_checker_ml'),
        "SYMPTOM"
    )
else:
    print("⚠️ Symptom Checker module not found, skipping...")
    symptom_proc = None

# Start Module 4: Drug Interaction
print("\n💊 Starting Drug Interaction Module...")
if os.path.exists(os.path.join(MODULES_DIR, 'drug_interaction', 'app.py')):
    drug_proc = start_service(
        [sys.executable, 'app.py'],
        os.path.join(MODULES_DIR, 'drug_interaction'),
        "DRUG"
    )
else:
    print("⚠️ Drug Interaction module not found, skipping...")
    drug_proc = None

print("\n" + "=" * 60)
print("✅ ALL SERVICES STARTED")
print("🌐 Access your app at: https://medi-analyze.onrender.com")
print("=" * 60 + "\n")

# Monitor all processes
try:
    # Create threads to monitor output
    threads = []
    
    process_list = [
        (backend_proc, "BACKEND"),
    ]
    
    if report_proc:
        process_list.append((report_proc, "REPORT"))
    if chatbot_proc:
        process_list.append((chatbot_proc, "CHATBOT"))
    if symptom_proc:
        process_list.append((symptom_proc, "SYMPTOM"))
    if drug_proc:
        process_list.append((drug_proc, "DRUG"))
    
    for proc, name in process_list:
        thread = threading.Thread(target=monitor_output, args=(proc, name), daemon=True)
        thread.start()
        threads.append(thread)
    
    # Wait for any process to exit (shouldn't happen normally)
    for proc in processes:
        proc.wait()
        
except KeyboardInterrupt:
    print("\n\n⚠️ Received shutdown signal")
    sys.exit(0)
except Exception as e:
    print(f"\n❌ Error: {e}")
    sys.exit(1)