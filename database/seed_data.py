"""
Realistic Seed Data for Production Line Resource Scheduling System
Pre-populates users, machines, workers, materials, jobs, schedules, logs, and invoices.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timedelta
import database.db as db

def seed_database():
    """Populate database with sample manufacturing records."""
    db.init_db()

    # 1. Users
    if not db.get_user_by_username("admin"):
        db.create_user("admin", "admin@production.internal", "admin123", role="Admin")
    if not db.get_user_by_username("manager"):
        db.create_user("manager", "manager@production.internal", "manager123", role="Plant Manager")
    if not db.get_user_by_username("operator"):
        db.create_user("operator", "operator@production.internal", "operator123", role="Operator")

    # 2. Machines
    machines_data = [
        ("5-Axis CNC Milling Center", "CNC-01", "CNC Milling", 120, 65.0, "Idle", "Bay 1 - Precision Line"),
        ("Industrial Robotic Welder", "WLD-02", "Robotic Welding", 85, 55.0, "Running", "Bay 2 - Fabrication"),
        ("High-Precision Laser Cutter", "LSR-03", "Laser Cutting", 150, 75.0, "Idle", "Bay 1 - Cutting Cell"),
        ("Hydraulic Injection Molder", "INJ-04", "Injection Molding", 200, 48.0, "Maintenance", "Bay 3 - Plastics"),
        ("Automated Assembly Station", "ASM-05", "Assembly", 180, 40.0, "Idle", "Bay 4 - Final Integration"),
        ("Electrochemical Surface Finisher", "FIN-06", "Finishing", 110, 50.0, "Idle", "Bay 5 - Chemical Cell")
    ]
    for m in machines_data:
        existing = db.get_machines()
        if not any(x["code"] == m[1] for x in existing):
            db.create_machine(m[0], m[1], m[2], m[3], m[4], m[5], m[6])

    # 3. Workers
    workers_data = [
        ("Marcus Vance", "EMP-101", "Lead CNC Programmer", "Master", 42.0, "Available", "Morning (07:00 - 15:30)"),
        ("Elena Rostova", "EMP-102", "Robotics Automation Eng", "Senior", 36.5, "Assigned", "Morning (07:00 - 15:30)"),
        ("Tyler Chen", "EMP-103", "Laser Optics Specialist", "Senior", 34.0, "Available", "Day Shift (08:00 - 16:30)"),
        ("Sarah Jenkins", "EMP-104", "Production Assembly Lead", "Mid-Level", 27.5, "Available", "Evening (15:00 - 23:30)"),
        ("David Kim", "EMP-105", "Junior Quality Technician", "Junior", 22.0, "Available", "Day Shift (08:00 - 16:30)"),
        ("Aisha Morales", "EMP-106", "Surface Treatment Specialist", "Senior", 35.0, "Available", "Day Shift (08:00 - 16:30)")
    ]
    for w in workers_data:
        existing = db.get_workers()
        if not any(x["employee_code"] == w[1] for x in existing):
            db.create_worker(w[0], w[1], w[2], w[3], w[4], w[5], w[6])

    # 4. Materials
    materials_data = [
        ("MAT-AL6061", "Aerospace Aluminum 6061-T6 Billet", "Metals", 145.0, "kg", 18.5, 50.0, "Alcoa Precision Metals"),
        ("MAT-SS304", "Stainless Steel 304 Plate (3mm)", "Metals", 32.0, "sheets", 45.0, 40.0, "ThyssenKrupp Steel"), # Low stock trigger!
        ("MAT-TI64", "Titanium Grade 5 Ti-6Al-4V Bar", "Alloys", 28.5, "kg", 88.0, 15.0, "Dynamet Aerospace"),
        ("MAT-PC01", "Polycarbonate High-Impact Granules", "Polymers", 210.0, "kg", 8.2, 60.0, "Sabic Polymers"),
        ("MAT-EPOXY", "Aerospace Structural Epoxy Compound", "Chemicals", 12.0, "liters", 65.0, 20.0, "Henkel Adhesives"), # Low stock trigger!
        ("MAT-FAST", "Titanium Fasteners & Hardware Set", "Hardware", 450.0, "sets", 4.5, 100.0, "SPS Technologies")
    ]
    for mat in materials_data:
        existing = db.get_materials()
        if not any(x["material_code"] == mat[0] for x in existing):
            db.create_material(mat[0], mat[1], mat[2], mat[3], mat[4], mat[5], mat[6], mat[7])

    # 5. Jobs
    existing_jobs = db.get_jobs()
    if not existing_jobs:
        now = datetime.now()
        materials = {m["material_code"]: m["id"] for m in db.get_materials()}
        machines = {m["code"]: m["id"] for m in db.get_machines()}
        workers = {w["employee_code"]: w["id"] for w in db.get_workers()}

        sample_jobs = [
            ("JOB-2026-001", "Aerospace Turbine Impeller", "Turbine Blades", 25, "Critical", 120,
             (now + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"), "CNC Milling", "Master",
             materials.get("MAT-TI64"), 12.0, machines.get("CNC-01"), workers.get("EMP-101")),

            ("JOB-2026-002", "Robotic Arm Linkage Joint", "Robotic Subassembly", 60, "High", 90,
             (now + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S"), "Robotic Welding", "Senior",
             materials.get("MAT-AL6061"), 20.0, machines.get("WLD-02"), workers.get("EMP-102")),

            ("JOB-2026-003", "Precision Chassis Plate", "Enclosures", 120, "Medium", 45,
             (now + timedelta(days=4)).strftime("%Y-%m-%d %H:%M:%S"), "Laser Cutting", "Senior",
             materials.get("MAT-SS304"), 15.0, None, None),

            ("JOB-2026-004", "Avionics Instrument Bezel", "Optical Bezel", 250, "Medium", 75,
             (now + timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S"), "Injection Molding", "Mid-Level",
             materials.get("MAT-PC01"), 30.0, None, None),

            ("JOB-2026-005", "Medical Sensor Housing", "Bio-Sensors", 40, "High", 60,
             (now + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"), "Assembly", "Mid-Level",
             materials.get("MAT-FAST"), 40.0, None, None),

            ("JOB-2026-006", "Thermal Heat Exchanger Core", "Heat Exchanger", 15, "Critical", 150,
             (now + timedelta(hours=18)).strftime("%Y-%m-%d %H:%M:%S"), "Surface Finishing", "Senior",
             materials.get("MAT-AL6061"), 18.0, None, None)
        ]

        for j in sample_jobs:
            job_id = db.create_job(
                job_number=j[0], title=j[1], product_type=j[2], quantity=j[3], priority=j[4],
                processing_time_minutes=j[5], deadline=j[6], required_machine_type=j[7],
                required_skill_level=j[8], required_material_id=j[9], material_quantity_required=j[10],
                assigned_machine_id=j[11], assigned_worker_id=j[12]
            )

            # Mark JOB-002 as Processing
            if j[0] == "JOB-2026-002":
                db.update_job_status(job_id, "Processing", 45)

        # 6. Initial Schedules
        all_jobs = db.get_jobs()
        job1 = next((j for j in all_jobs if j["job_number"] == "JOB-2026-001"), None)
        job2 = next((j for j in all_jobs if j["job_number"] == "JOB-2026-002"), None)

        if job1 and job1["assigned_machine_id"] and job1["assigned_worker_id"]:
            start_t = now + timedelta(hours=1)
            end_t = start_t + timedelta(minutes=job1["processing_time_minutes"])
            db.create_schedule(
                job_id=job1["id"],
                machine_id=job1["assigned_machine_id"],
                worker_id=job1["assigned_worker_id"],
                start_time=start_t.strftime("%Y-%m-%d %H:%M:%S"),
                end_time=end_t.strftime("%Y-%m-%d %H:%M:%S"),
                sequence_order=1,
                status="Scheduled",
                notes="Initial priority dispatch for Turbine Impeller"
            )

        if job2 and job2["assigned_machine_id"] and job2["assigned_worker_id"]:
            start_t = now - timedelta(minutes=40)
            end_t = start_t + timedelta(minutes=job2["processing_time_minutes"])
            db.create_schedule(
                job_id=job2["id"],
                machine_id=job2["assigned_machine_id"],
                worker_id=job2["assigned_worker_id"],
                start_time=start_t.strftime("%Y-%m-%d %H:%M:%S"),
                end_time=end_t.strftime("%Y-%m-%d %H:%M:%S"),
                sequence_order=1,
                status="In-Progress",
                notes="Active multithreaded simulation processing"
            )

        # 7. Initial production logs
        db.log_production_event("System initialized and production schedule synchronized.", "INFO")
        if job2:
            db.log_production_event(f"Machine WLD-02 thread started processing {job2['job_number']}.", "START",
                                    job_id=job2["id"], machine_id=job2["assigned_machine_id"], thread_id="MachineThread-WLD-02")
            db.log_production_event(f"Resource lock acquired on Machine WLD-02 and Worker EMP-102.", "LOCK_ACQUIRED",
                                    job_id=job2["id"], machine_id=job2["assigned_machine_id"], thread_id="MachineThread-WLD-02")

        # 8. Initial sample invoice
        if job1:
            db.generate_invoice_for_job(job1["id"], client_name="Apex Aerospace Propulsion Ltd")

if __name__ == "__main__":
    seed_database()
    print("Database successfully initialized and seeded with sample data.")
