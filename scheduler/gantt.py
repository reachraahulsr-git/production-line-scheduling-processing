"""
Gantt Chart Data Generator
Formats schedules for interactive timeline rendering grouped by Machine or Job.
"""
from datetime import datetime
from typing import List, Dict, Any
import database.db as db

def get_gantt_data() -> Dict[str, Any]:
    """Prepares structured series and intervals for rendering Gantt chart."""
    schedules = db.get_schedules()
    machines = db.get_machines()

    if not schedules:
        return {
            "machines": machines,
            "tasks": [],
            "min_time": datetime.now().isoformat(),
            "max_time": datetime.now().isoformat()
        }

    tasks = []
    all_starts = []
    all_ends = []

    priority_colors = {
        "Critical": "#dc2626", # Red
        "High": "#ea580c",     # Orange
        "Medium": "#0284c7",   # Blue
        "Low": "#16a34a"       # Green
    }

    status_styles = {
        "Scheduled": "border-slate-400 bg-opacity-80",
        "In-Progress": "ring-2 ring-blue-500 animate-pulse",
        "Completed": "opacity-70 bg-emerald-600",
        "Delayed": "border-red-500 ring-2 ring-red-400"
    }

    for s in schedules:
        try:
            s_dt = datetime.strptime(s["start_time"][:19], "%Y-%m-%d %H:%M:%S")
            e_dt = datetime.strptime(s["end_time"][:19], "%Y-%m-%d %H:%M:%S")
            all_starts.append(s_dt)
            all_ends.append(e_dt)

            color = priority_colors.get(s.get("job_priority"), "#0284c7")
            duration_hrs = round((e_dt - s_dt).total_seconds() / 3600.0, 2)

            tasks.append({
                "id": s["id"],
                "job_id": s["job_id"],
                "job_number": s["job_number"],
                "title": s["job_title"],
                "machine_id": s["machine_id"],
                "machine_name": s["machine_name"],
                "machine_code": s["machine_code"],
                "worker_name": s["worker_name"],
                "start": s["start_time"],
                "end": s["end_time"],
                "start_iso": s_dt.isoformat(),
                "end_iso": e_dt.isoformat(),
                "duration_hours": duration_hrs,
                "priority": s.get("job_priority", "Medium"),
                "status": s.get("status", "Scheduled"),
                "color": color,
                "notes": s.get("notes", "")
            })
        except ValueError:
            continue

    min_t = min(all_starts).isoformat() if all_starts else datetime.now().isoformat()
    max_t = max(all_ends).isoformat() if all_ends else datetime.now().isoformat()

    return {
        "machines": machines,
        "tasks": tasks,
        "min_time": min_t,
        "max_time": max_t,
        "total_tasks": len(tasks)
    }
