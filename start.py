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
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(name)s] %(message)s')
logger = logging.getLogger('MAIN')

# Configuration
BACKEND_DIR = os.path.join(os.path.dirname(__file__), 'backend')
MODULES_DIR = os.path.join(os.path.dirname(__file__), 'modules')

# Store process objects
processes = {}
process_lock = threading.Lock()

def cleanup():
    """Kill all child processes on exit"""
    logger.info("🛑 Shutting down all services...")
    with process_lock:
        for name, proc in processes.items():
            if proc and proc.poll() is None:
                logger.info(f"Terminating {name}...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Killing {name}...")
                    proc.kill()
    logger.info("✅ All services stopped")

# Register cleanup on exit
atexit.register(cleanup)
signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
signal.signal(signal.SIGTERM, lambda sig, frame: sys.exit(0))

def start_service(command, cwd, name, port=None):
    """Start a service as a subprocess"""
    logger.info(f"Starting {name}...")
    try:
        # Set environment variables
        env = os.environ.copy()
        if port:
            env['PORT'] = str(port)
        
        proc = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        with process_lock:
            processes[name] = proc
        return proc
    except Exception as e:
        logger.error(f"Failed to start {name}: {e}")
        return None

def monitor_output(proc, name):
    """Monitor and print output from a process"""
    if not proc:
        return
    for line in iter(proc.stdout.readline, ''):
        if line.strip():
            print(f"[{name}] {line.strip()}")

def monitor_process(proc, name, restart_callback):
    """Monitor a process and restart if it crashes"""
    while True:
        if proc:
            return_code = proc.wait()
            if return_code != 0 and return_code is not None:
                logger.warning(f"{name} crashed with code {return_code}, restarting in 5 seconds...")
                time.sleep(5)
                new_proc = restart_callback()
                if new_proc:
                    with process_lock:
                        processes[name] = new_proc
                    proc = new_proc
                else:
                    logger.error(f"Failed to restart {name}")
                    break
            else:
                logger.info(f"{name} stopped normally")
                break

def restart_service(name, command, cwd, port=None):
    """Restart a service"""
    logger.info(f"Restarting {name}...")
    return start_service(command, cwd, name, port)

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

# Start Backend (Node.js) - THIS IS THE MAIN SERVICE
print("\n📦 Starting Node.js Backend...")
backend_proc = start_service(
    ['node', 'server.js'],
    BACKEND_DIR,
    "BACKEND",
    port=10000  # Render's default port
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
    # Create threads to monitor output and process health
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
        # Thread for output monitoring
        output_thread = threading.Thread(target=monitor_output, args=(proc, name), daemon=True)
        output_thread.start()
        threads.append(output_thread)
        
        # Thread for process monitoring
        if name != "BACKEND":  # Don't auto-restart the main backend
            monitor_thread = threading.Thread(
                target=monitor_process,
                args=(proc, name, lambda: restart_service(name, 
                    ['node', 'server.js'] if name == "BACKEND" else [sys.executable, 'app.py'],
                    BACKEND_DIR if name == "BACKEND" else os.path.join(MODULES_DIR, name.lower()),
                    10000 if name == "BACKEND" else None)),
                daemon=True
            )
            monitor_thread.start()
            threads.append(monitor_thread)
    
    # Keep the main thread alive
    while True:
        time.sleep(1)
        # Check if backend is still running
        if backend_proc.poll() is not None:
            logger.error("Backend crashed! Exiting...")
            break
        
except KeyboardInterrupt:
    print("\n\n⚠️ Received shutdown signal")
    sys.exit(0)
except Exception as e:
    logger.error(f"Error: {e}")
    sys.exit(1)