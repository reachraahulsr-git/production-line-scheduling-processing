"""
Automatic Rescheduling Module
Dynamically re-allocates jobs when machines fail, maintenance is scheduled, or job priorities change.
"""
from typing import Dict, Any, List
import database.db as db
from scheduler.engine import SchedulingEngine, ConflictDetector

def trigger_auto_reschedule(trigger_source: str, details: str = "") -> Dict[str, Any]:
    """
    Executes an intelligent automated rescheduling pass:
    - Scans for any active conflicts caused by resource changes
    - Re-allocates scheduled jobs to prevent idle bottlenecks and missed deadlines
    - Writes an audit log record
    """
    db.log_production_event(
        f"Dynamic Rescheduling Triggered: {trigger_source}. Details: {details}",
        event_type="WARNING"
    )

    # Re-run scheduler with BALANCED multi-criteria optimization
    result = SchedulingEngine.run_scheduler(heuristic="BALANCED", auto_clear_existing=True)

    db.log_production_event(
        f"Dynamic Rescheduling Completed. {result['scheduled_count']} jobs re-routed successfully.",
        event_type="INFO"
    )

    return result

def handle_machine_status_change(machine_id: int, new_status: str) -> Dict[str, Any]:
    """Called when machine transitions to Maintenance, Error, or Idle."""
    db.update_machine_status(machine_id, new_status)
    mach = db.get_machine_by_id(machine_id)
    mach_name = mach["name"] if mach else f"ID {machine_id}"

    # If machine is taken offline, trigger auto-reschedule
    if new_status in ("Maintenance", "Error"):
        return trigger_auto_reschedule(
            trigger_source=f"Machine Offline ({new_status})",
            details=f"Machine {mach_name} status switched to '{new_status}'."
        )
    return {"success": True, "message": f"Machine status updated to {new_status}."}

def handle_job_priority_change(job_id: int, new_priority: str) -> Dict[str, Any]:
    """Called when job priority is escalated to Critical/High."""
    job = db.get_job_by_id(job_id)
    if not job:
        return {"success": False, "message": "Job not found"}

    db.update_job(
        job_id=job_id,
        title=job["title"],
        product_type=job["product_type"],
        quantity=job["quantity"],
        priority=new_priority,
        processing_time_minutes=job["processing_time_minutes"],
        deadline=job["deadline"],
        required_machine_type=job["required_machine_type"],
        required_skill_level=job["required_skill_level"],
        required_material_id=job["required_material_id"],
        material_quantity_required=job["material_quantity_required"],
        assigned_machine_id=job["assigned_machine_id"],
        assigned_worker_id=job["assigned_worker_id"],
        status=job["status"]
    )

    if new_priority in ("Critical", "High"):
        return trigger_auto_reschedule(
            trigger_source=f"Priority Escalation ({new_priority})",
            details=f"Job {job['job_number']} priority increased to {new_priority}."
        )
    return {"success": True, "message": f"Priority updated to {new_priority}."}
