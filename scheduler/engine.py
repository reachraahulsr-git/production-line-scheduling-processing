"""
Production Line Resource Scheduling Engine
Implements:
- Priority Analysis (Multi-factor weighting: Priority, Deadline Urgency, SPT)
- Resource Allocation (Machine matching, Worker qualification, Material validation)
- Resource Availability Checking (Timeline slot collision analysis)
- Conflict Detection (Machine overlap, Worker double-booking, Material shortage, Deadline breaches)
- Schedule Optimization (Makespan minimization, heuristics)
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
import database.db as db

class PriorityAnalyzer:
    """Computes comprehensive multi-criteria priority rankings for production jobs."""

    PRIORITY_WEIGHTS = {
        "Critical": 100.0,
        "High": 75.0,
        "Medium": 50.0,
        "Low": 25.0
    }

    @classmethod
    def calculate_priority_score(cls, job: Dict[str, Any], reference_time: Optional[datetime] = None) -> float:
        if reference_time is None:
            reference_time = datetime.now()

        # 1. Base Priority Weight (50% weight)
        base_weight = cls.PRIORITY_WEIGHTS.get(job.get("priority", "Medium"), 50.0)

        # 2. Deadline Urgency (35% weight)
        deadline_str = job.get("deadline")
        urgency_score = 50.0
        if deadline_str:
            try:
                deadline_dt = datetime.strptime(deadline_str[:19], "%Y-%m-%d %H:%M:%S")
                hours_left = (deadline_dt - reference_time).total_seconds() / 3600.0
                if hours_left <= 0:
                    urgency_score = 100.0  # Already overdue!
                elif hours_left < 12:
                    urgency_score = 95.0
                elif hours_left < 24:
                    urgency_score = 85.0
                elif hours_left < 48:
                    urgency_score = 70.0
                elif hours_left < 96:
                    urgency_score = 50.0
                else:
                    urgency_score = max(10.0, 100.0 - (hours_left / 2.0))
            except ValueError:
                pass

        # 3. Shortest Processing Time (SPT) Bonus (15% weight)
        proc_time = float(job.get("processing_time_minutes", 60))
        # Jobs under 60 mins receive higher SPT bonus to quickly free up resources
        spt_score = max(10.0, min(100.0, 120.0 - (proc_time / 3.0)))

        composite_score = (0.50 * base_weight) + (0.35 * urgency_score) + (0.15 * spt_score)
        return round(composite_score, 2)

    @classmethod
    def rank_jobs(cls, jobs: List[Dict[str, Any]], heuristic: str = "BALANCED") -> List[Dict[str, Any]]:
        """Sort jobs according to selected heuristic: BALANCED, EDD, SPT, or PRIORITY_FIRST."""
        now = datetime.now()
        annotated = []
        for j in jobs:
            item = dict(j)
            item["priority_score"] = cls.calculate_priority_score(j, now)
            annotated.append(item)

        if heuristic == "EDD": # Earliest Due Date
            return sorted(annotated, key=lambda x: str(x.get("deadline", "9999")))
        elif heuristic == "SPT": # Shortest Processing Time
            return sorted(annotated, key=lambda x: x.get("processing_time_minutes", 9999))
        elif heuristic == "PRIORITY_FIRST":
            return sorted(annotated, key=lambda x: (cls.PRIORITY_WEIGHTS.get(x.get("priority"), 0)), reverse=True)
        else: # BALANCED heuristic
            return sorted(annotated, key=lambda x: x["priority_score"], reverse=True)

class ConflictDetector:
    """Detects resource bottlenecks, schedule overlaps, and inventory shortages."""

    @classmethod
    def detect_all_conflicts(cls) -> List[Dict[str, Any]]:
        conflicts = []
        now = datetime.now()

        # Fetch current system state
        schedules = db.get_schedules()
        machines = {m["id"]: m for m in db.get_machines()}
        workers = {w["id"]: w for w in db.get_workers()}
        materials = {m["id"]: m for m in db.get_materials()}
        jobs = {j["id"]: j for j in db.get_jobs()}

        # 1. Machine Overlap Conflicts (Two schedules on the same machine with overlapping intervals)
        for i in range(len(schedules)):
            s1 = schedules[i]
            if s1["status"] in ("Completed", "Cancelled"):
                continue
            start1 = datetime.strptime(s1["start_time"][:19], "%Y-%m-%d %H:%M:%S")
            end1 = datetime.strptime(s1["end_time"][:19], "%Y-%m-%d %H:%M:%S")

            for j in range(i + 1, len(schedules)):
                s2 = schedules[j]
                if s2["status"] in ("Completed", "Cancelled"):
                    continue
                if s1["machine_id"] == s2["machine_id"]:
                    start2 = datetime.strptime(s2["start_time"][:19], "%Y-%m-%d %H:%M:%S")
                    end2 = datetime.strptime(s2["end_time"][:19], "%Y-%m-%d %H:%M:%S")

                    # Check overlap: (start1 < end2) and (end1 > start2)
                    if (start1 < end2) and (end1 > start2):
                        mach_name = s1.get("machine_name", f"Machine {s1['machine_id']}")
                        conflicts.append({
                            "type": "MACHINE_OVERLAP",
                            "severity": "CRITICAL",
                            "title": f"Machine Double-Booking on {mach_name}",
                            "description": f"Job {s1['job_number']} and Job {s2['job_number']} are both scheduled on {mach_name} during overlapping times ({s1['start_time']} - {s1['end_time']} vs {s2['start_time']} - {s2['end_time']}).",
                            "affected_entity": mach_name,
                            "job_ids": [s1["job_id"], s2["job_id"]],
                            "recommendation": "Reschedule the lower-priority job to an alternative idle machine or sequence after completion."
                        })

                # 2. Worker Overlap Conflicts
                if s1["worker_id"] == s2["worker_id"]:
                    start2 = datetime.strptime(s2["start_time"][:19], "%Y-%m-%d %H:%M:%S")
                    end2 = datetime.strptime(s2["end_time"][:19], "%Y-%m-%d %H:%M:%S")
                    if (start1 < end2) and (end1 > start2):
                        worker_name = s1.get("worker_name", f"Worker {s1['worker_id']}")
                        conflicts.append({
                            "type": "WORKER_OVERLAP",
                            "severity": "HIGH",
                            "title": f"Worker Double-Allocation for {worker_name}",
                            "description": f"{worker_name} is assigned to simultaneous jobs: {s1['job_number']} and {s2['job_number']}.",
                            "affected_entity": worker_name,
                            "job_ids": [s1["job_id"], s2["job_id"]],
                            "recommendation": "Reassign one of the tasks to another qualified operator with matching skill level."
                        })

        # 3. Machine Inoperability Conflicts (Scheduled job on broken or maintenance machine)
        for s in schedules:
            if s["status"] in ("Completed", "Cancelled"):
                continue
            m = machines.get(s["machine_id"])
            if m and m["status"] in ("Maintenance", "Error"):
                conflicts.append({
                    "type": "MACHINE_UNAVAILABLE",
                    "severity": "CRITICAL",
                    "title": f"Machine {m['name']} Inoperable",
                    "description": f"Job {s['job_number']} is assigned to {m['name']}, which is currently marked '{m['status']}'.",
                    "affected_entity": m["name"],
                    "job_ids": [s["job_id"]],
                    "recommendation": "Shift scheduled job to an alternate operational workstation or wait for maintenance completion."
                })

        # 4. Material Shortage Conflicts (Total demand across scheduled/processing jobs vs inventory)
        material_demand = {}
        for j in jobs.values():
            if j["status"] in ("Pending", "Scheduled", "Processing") and j.get("required_material_id"):
                mat_id = j["required_material_id"]
                req_qty = float(j.get("material_quantity_required", 0))
                material_demand[mat_id] = material_demand.get(mat_id, 0.0) + req_qty

        for mat_id, total_needed in material_demand.items():
            mat = materials.get(mat_id)
            if mat:
                avail_stock = float(mat["stock_quantity"])
                if avail_stock < total_needed:
                    shortage = round(total_needed - avail_stock, 2)
                    conflicts.append({
                        "type": "MATERIAL_SHORTAGE",
                        "severity": "HIGH",
                        "title": f"Material Shortage: {mat['name']}",
                        "description": f"Total active demand requires {total_needed} {mat['unit']}, but available inventory is only {avail_stock} {mat['unit']} (Deficit: {shortage} {mat['unit']}).",
                        "affected_entity": mat["name"],
                        "job_ids": [j["id"] for j in jobs.values() if j.get("required_material_id") == mat_id and j["status"] in ("Pending", "Scheduled")],
                        "recommendation": "Place emergency replenishment order or prioritize jobs with smaller batch sizes."
                    })

        # 5. Deadline Breaches (Scheduled finish time > Job deadline)
        for s in schedules:
            if s["status"] in ("Completed", "Cancelled"):
                continue
            job = jobs.get(s["job_id"])
            if job and job.get("deadline"):
                try:
                    sched_end = datetime.strptime(s["end_time"][:19], "%Y-%m-%d %H:%M:%S")
                    deadline = datetime.strptime(job["deadline"][:19], "%Y-%m-%d %H:%M:%S")
                    if sched_end > deadline:
                        delay_hours = round((sched_end - deadline).total_seconds() / 3600.0, 1)
                        conflicts.append({
                            "type": "DEADLINE_BREACH",
                            "severity": "CRITICAL" if job["priority"] in ("Critical", "High") else "MEDIUM",
                            "title": f"Deadline Exceeded: {job['job_number']}",
                            "description": f"Scheduled completion at {s['end_time']} exceeds agreed deadline {job['deadline']} by {delay_hours} hours.",
                            "affected_entity": job["job_number"],
                            "job_ids": [job["id"]],
                            "recommendation": "Elevate job priority or assign to higher-speed machine cell to compress processing cycle."
                        })
                except ValueError:
                    pass

        return conflicts

class SchedulingEngine:
    """Core resource scheduling and timeline allocation algorithm."""

    SKILL_HIERARCHY = {
        "Junior": 1,
        "Mid-Level": 2,
        "Senior": 3,
        "Master": 4
    }

    @classmethod
    def can_worker_operate(cls, worker_skill: str, required_skill: str) -> bool:
        """Verify worker qualification meets or exceeds minimum required skill."""
        return cls.SKILL_HIERARCHY.get(worker_skill, 1) >= cls.SKILL_HIERARCHY.get(required_skill, 1)

    @classmethod
    def run_scheduler(cls, heuristic: str = "BALANCED", auto_clear_existing: bool = True) -> Dict[str, Any]:
        """
        Executes complete scheduling pass:
        1. Retrieves uncompleted jobs and system resources
        2. Ranks jobs via PriorityAnalyzer
        3. Allocates earliest non-overlapping time slots across machines & workers
        4. Writes schedule records into SQLite
        5. Logs audit events
        """
        if auto_clear_existing:
            db.clear_all_schedules()

        jobs = db.get_jobs()
        # Filter jobs needing scheduling: Pending or Scheduled
        target_jobs = [j for j in jobs if j["status"] in ("Pending", "Scheduled")]
        ranked_jobs = PriorityAnalyzer.rank_jobs(target_jobs, heuristic=heuristic)

        machines = db.get_machines()
        workers = db.get_workers()
        materials = {m["id"]: m for m in db.get_materials()}

        # Filter operable machines (exclude Maintenance and Error)
        active_machines = [m for m in machines if m["status"] not in ("Maintenance", "Error")]

        # Filter available workers
        active_workers = [w for w in workers if w["availability_status"] != "On Leave"]

        # Track timeline reservations per machine and per worker: list of (start_dt, end_dt, job_id)
        machine_timeline: Dict[int, List[Tuple[datetime, datetime, int]]] = {m["id"]: [] }
        for m in machines:
            machine_timeline[m["id"]] = []

        worker_timeline: Dict[int, List[Tuple[datetime, datetime, int]]] = {w["id"]: []}
        for w in workers:
            worker_timeline[w["id"]] = []

        # If we didn't clear existing, populate timelines from active schedules
        if not auto_clear_existing:
            for s in db.get_schedules():
                if s["status"] not in ("Completed", "Cancelled"):
                    s_dt = datetime.strptime(s["start_time"][:19], "%Y-%m-%d %H:%M:%S")
                    e_dt = datetime.strptime(s["end_time"][:19], "%Y-%m-%d %H:%M:%S")
                    machine_timeline.setdefault(s["machine_id"], []).append((s_dt, e_dt, s["job_id"]))
                    worker_timeline.setdefault(s["worker_id"], []).append((s_dt, e_dt, s["job_id"]))

        scheduled_count = 0
        skipped_jobs = []
        base_time = datetime.now() + timedelta(minutes=5) # Schedule starting 5 minutes from now

        for job in ranked_jobs:
            req_type = job["required_machine_type"]
            req_skill = job.get("required_skill_level", "Mid-Level")
            duration_mins = job["processing_time_minutes"]

            # 1. Find eligible machines
            matching_machines = [m for m in active_machines if m["machine_type"] == req_type]
            if not matching_machines:
                # Fallback to any active machine if specialized type not found
                matching_machines = active_machines

            if not matching_machines:
                skipped_jobs.append({"job": job["job_number"], "reason": "No operable machines available"})
                continue

            # 2. Find eligible workers
            matching_workers = [w for w in active_workers if cls.can_worker_operate(w["skill_level"], req_skill)]
            if not matching_workers:
                matching_workers = active_workers

            if not matching_workers:
                skipped_jobs.append({"job": job["job_number"], "reason": "No qualified workers available"})
                continue

            # 3. Find earliest combined slot where machine AND worker are free for duration_mins
            best_slot = None
            best_machine = None
            best_worker = None

            # Test candidate slot start times starting from base_time in 15-minute increments
            # Scan next 7 days (672 steps)
            found = False
            for step in range(0, 300):
                candidate_start = base_time + timedelta(minutes=step * 15)
                candidate_end = candidate_start + timedelta(minutes=duration_mins)

                for mach in matching_machines:
                    # Check machine availability
                    m_busy = any(
                        (candidate_start < e and candidate_end > s)
                        for s, e, _ in machine_timeline[mach["id"]]
                    )
                    if m_busy:
                        continue

                    for wrk in matching_workers:
                        # Check worker availability
                        w_busy = any(
                            (candidate_start < e and candidate_end > s)
                            for s, e, _ in worker_timeline[wrk["id"]]
                        )
                        if w_busy:
                            continue

                        # Both are free!
                        best_slot = (candidate_start, candidate_end)
                        best_machine = mach
                        best_worker = wrk
                        found = True
                        break
                    if found:
                        break
                if found:
                    break

            if best_slot and best_machine and best_worker:
                start_dt, end_dt = best_slot
                # Commit to local timelines
                machine_timeline[best_machine["id"]].append((start_dt, end_dt, job["id"]))
                worker_timeline[best_worker["id"]].append((start_dt, end_dt, job["id"]))

                start_str = start_dt.strftime("%Y-%m-%d %H:%M:%S")
                end_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")

                db.create_schedule(
                    job_id=job["id"],
                    machine_id=best_machine["id"],
                    worker_id=best_worker["id"],
                    start_time=start_str,
                    end_time=end_str,
                    sequence_order=scheduled_count + 1,
                    status="Scheduled",
                    notes=f"Auto-scheduled via {heuristic} heuristic."
                )
                scheduled_count += 1
            else:
                skipped_jobs.append({"job": job["job_number"], "reason": "Could not find non-overlapping slot"})

        db.log_production_event(
            f"Scheduling pass complete using '{heuristic}' heuristic. Scheduled: {scheduled_count} jobs. Unscheduled: {len(skipped_jobs)}.",
            event_type="INFO"
        )

        return {
            "success": True,
            "heuristic": heuristic,
            "scheduled_count": scheduled_count,
            "skipped_count": len(skipped_jobs),
            "skipped_jobs": skipped_jobs,
            "conflicts": ConflictDetector.detect_all_conflicts()
        }
