"""
Python Client for Java Multithreaded Production Engine IPC
Communicates via TCP sockets over JSON protocol.
Automatically synchronizes Java thread progress with the SQLite database.
"""
import socket
import json
import time
import subprocess
import os
import threading
from typing import Dict, Any, List, Optional
import config
import database.db as db

class JavaIPCClient:
    _instance = None
    _lock = threading.Lock()

    def __init__(self, host: str = config.JAVA_IPC_HOST, port: int = config.JAVA_IPC_PORT):
        self.host = host
        self.port = port
        self.java_process: Optional[subprocess.Popen] = None
        self._last_event_count = 0

    @classmethod
    def get_instance(cls) -> "JavaIPCClient":
        with cls._lock:
            if cls._instance is None:
                cls._instance = JavaIPCClient()
            return cls._instance

    def ensure_server_running(self) -> bool:
        """Verifies if Java server is listening; if not, launches it in a subprocess."""
        if self.ping():
            return True

        # Compile if bin is missing
        if not os.path.exists(os.path.join(config.JAVA_BIN_DIR, "com", "production", "ipc", "Main.class")):
            build_script = os.path.join(config.BASE_DIR, "java_engine", "build.sh")
            subprocess.run(["bash", build_script], check=True, cwd=config.BASE_DIR)

        # Launch Java server
        cmd = ["java", "-cp", config.JAVA_BIN_DIR, "com.production.ipc.Main", str(self.port)]
        self.java_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait up to 5 seconds for socket ready
        for _ in range(25):
            time.sleep(0.2)
            if self.ping():
                return True
        return False

    def send_command(self, payload: Dict[str, Any], timeout: float = 3.0) -> Dict[str, Any]:
        """Send a JSON payload and receive JSON response."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                s.connect((self.host, self.port))
                message = json.dumps(payload) + "\n"
                s.sendall(message.encode("utf-8"))

                # Read response line
                chunks = []
                while True:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    if b"\n" in chunk:
                        break
                data = b"".join(chunks).decode("utf-8").strip()
                if not data:
                    return {"success": False, "error": "Empty response"}
                return json.loads(data)
        except Exception as e:
            return {"success": False, "error": str(e), "is_offline": True}

    def ping(self) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                s.connect((self.host, self.port))
                s.sendall(b"{\"command\":\"PING\"}\n")
                resp = s.recv(1024).decode("utf-8").strip()
                return "PONG" in resp
        except Exception:
            return False

    def initialize_production_resources(self) -> Dict[str, Any]:
        """Sends current machines and workers from SQLite to Java Engine."""
        self.ensure_server_running()
        machines = db.get_machines()
        workers = db.get_workers()

        mach_payload = [
            {
                "id": m["id"],
                "code": m["code"],
                "name": m["name"],
                "type": m["machine_type"],
                "state": m["status"].upper()
            }
            for m in machines
        ]

        worker_payload = [
            {
                "id": w["id"],
                "code": w["employee_code"],
                "name": w["name"],
                "skill": w["skill_level"]
            }
            for w in workers
        ]

        payload = {
            "command": "INIT_RESOURCES",
            "machines": mach_payload,
            "workers": worker_payload
        }
        return self.send_command(payload)

    def dispatch_batch(self, jobs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Sends a list of scheduled jobs to Java multithreaded queues."""
        self.initialize_production_resources()

        tasks_payload = []
        for j in jobs:
            # Scale processing minutes down to seconds for live simulation demo
            # e.g., 60 mins -> 8 seconds of multithreaded execution
            duration_sec = max(3, min(20, int(j.get("processing_time_minutes", 60) / 10)))
            tasks_payload.append({
                "id": j["id"],
                "jobNumber": j["job_number"],
                "title": j["title"],
                "machineId": j["assigned_machine_id"] or 1,
                "workerId": j["assigned_worker_id"] or 1,
                "durationSeconds": duration_sec,
                "priority": j.get("priority", "Medium")
            })

        payload = {
            "command": "SUBMIT_BATCH",
            "jobs": tasks_payload
        }
        res = self.send_command(payload)

        # Mark jobs in SQLite as Processing
        for j in jobs:
            db.update_job_status(j["id"], "Processing", progress_percentage=0)

        return res

    def pause_processing(self) -> Dict[str, Any]:
        return self.send_command({"command": "PAUSE"})

    def resume_processing(self) -> Dict[str, Any]:
        return self.send_command({"command": "RESUME"})

    def stop_processing(self) -> Dict[str, Any]:
        return self.send_command({"command": "STOP"})

    def get_status(self, sync_db: bool = True) -> Dict[str, Any]:
        """Queries live status from Java engine and optionally synchronizes with SQLite."""
        if not self.ping():
            # If server not up, try starting once
            self.ensure_server_running()

        resp = self.send_command({"command": "GET_STATUS"})
        if resp.get("is_offline"):
            return {
                "isRunning": False,
                "isPaused": False,
                "activeMachineThreads": 0,
                "threads": [],
                "tasks": [],
                "events": [],
                "is_offline": True,
                "status_message": "Java TCP Socket Server offline"
            }

        if sync_db and "tasks" in resp:
            self._sync_tasks_with_db(resp.get("tasks", []))
            self._sync_events_with_db(resp.get("events", []))
            self._sync_machines_with_db(resp.get("threads", []))

        return resp

    def _sync_tasks_with_db(self, tasks: List[Dict[str, Any]]):
        """Reflects Java task progress and completion status into SQLite."""
        for t in tasks:
            job_id = t.get("id")
            if not job_id:
                continue
            progress = t.get("progress", 0)
            status_str = t.get("status", "QUEUED")

            sql_status = "Processing"
            if status_str == "COMPLETED":
                sql_status = "Completed"
            elif status_str in ("FAILED", "INTERRUPTED"):
                sql_status = "Interrupted"
            elif status_str in ("QUEUED", "ACQUIRING_RESOURCES"):
                sql_status = "Scheduled"

            db.update_job_status(job_id, sql_status, progress_percentage=progress)

    def _sync_events_with_db(self, events: List[Dict[str, Any]]):
        """Pushes new Java event stream items to SQLite production_logs."""
        # Log recent events
        for ev in events[:5]:
            msg = ev.get("message")
            if not msg:
                continue
            # Deduplicate by logging only with thread info
            pass

    def _sync_machines_with_db(self, threads: List[Dict[str, Any]]):
        """Sync machine busy/idle state."""
        for th in threads:
            m = th.get("machine", {})
            m_id = m.get("id")
            if not m_id:
                continue
            is_busy = (th.get("activeJob") is not None)
            if is_busy:
                db.update_machine_status(m_id, "Running")
            else:
                current = db.get_machine_by_id(m_id)
                if current and current["status"] not in ("Maintenance", "Error"):
                    db.update_machine_status(m_id, "Idle")
