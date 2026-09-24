"""
Unified Startup Script for Production Line Resource Scheduling System
Coordinates:
1. Java compilation (javac)
2. SQLite database verification and seeding
3. Java Multithreaded TCP Socket Server launch (Port 5050)
4. Flask Web Application start (Port 3000)
"""
import os
import sys
import argparse
import subprocess
import time
import atexit
import signal

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import config
from database.seed_data import seed_database
from ipc.java_client import JavaIPCClient

java_proc = None

def cleanup():
    global java_proc
    if java_proc:
        print("\n[SHUTDOWN] Terminating Java Engine subprocess...")
        try:
            java_proc.terminate()
            java_proc.wait(timeout=2)
        except Exception:
            java_proc.kill()

atexit.register(cleanup)

def main():
    parser = argparse.ArgumentParser(description="Run Production Line Scheduling System")
    parser.add_argument("--port", type=int, default=3000, help="Web server port (default: 3000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Web server host (default: 0.0.0.0)")
    parser.add_argument("--no-java", action="store_true", help="Skip Java engine launch")
    args, unknown = parser.parse_known_args()

    print("==================================================================")
    print("  PRODUCTION LINE RESOURCE SCHEDULING SYSTEM (CSE ACADEMIC SUITE) ")
    print("  Python Flask + SQLite + SymPy + Java Multithreaded Engine        ")
    print("==================================================================")

    # 1. Compile Java if needed
    bin_class = os.path.join(config.JAVA_BIN_DIR, "com", "production", "ipc", "Main.class")
    if not os.path.exists(bin_class):
        print("\n[STEP 1/4] Compiling Java Multithreaded Source Files...")
        build_sh = os.path.join(config.BASE_DIR, "java_engine", "build.sh")
        subprocess.run(["bash", build_sh], check=True, cwd=config.BASE_DIR)
    else:
        print("\n[STEP 1/4] Java binaries verified.")

    # 2. Database Initialization
    print("[STEP 2/4] Initializing and Seeding SQLite Database...")
    seed_database()

    # 3. Start Java Socket Server
    if not args.no_java:
        print("[STEP 3/4] Starting Java TCP Socket Server on 127.0.0.1:5050...")
        client = JavaIPCClient.get_instance()
        client.ensure_server_running()
        if client.ping():
            print(" -> Java Socket Server successfully connected and operational!")
            client.initialize_production_resources()
        else:
            print(" -> WARNING: Could not establish immediate socket connection with Java engine.")
    else:
        print("[STEP 3/4] Skipped Java engine (--no-java flag).")

    # 4. Launch Flask Web Application
    print(f"[STEP 4/4] Starting Flask Web Server on http://{args.host}:{args.port}...")
    from app import app
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)

if __name__ == "__main__":
    main()
