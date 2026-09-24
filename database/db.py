"""
Database Access Layer for Production Line Resource Scheduling System
Supports all 8 required tables: users, machines, workers, materials,
jobs, schedules, production_logs, invoices.
"""
import sqlite3
import os
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import config

def get_connection() -> sqlite3.Connection:
    """Create and return a configured sqlite3 connection."""
    os.makedirs(os.path.dirname(config.DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(config.DATABASE_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt."""
    salt = "prod_sched_salt_2026"
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password matches hash."""
    return hmac.compare_digest(hash_password(plain_password), hashed_password)

def init_db(force: bool = False):
    """Initialize database tables from schema.sql."""
    conn = get_connection()
    try:
        with open(config.SCHEMA_PATH, "r") as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()

# ----------------- User Management -----------------

def create_user(username: str, email: str, password: str, role: str = "Operator") -> Optional[int]:
    """Create a new user."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (username.strip(), email.strip().lower(), hash_password(password), role)
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Retrieve user by username."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username.strip(),))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve user by ID."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_all_users() -> List[Dict[str, Any]]:
    """Retrieve all users."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, username, email, role, created_at FROM users ORDER BY id ASC")
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

# ----------------- Machine Management -----------------

def get_machines() -> List[Dict[str, Any]]:
    """List all machines."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM machines ORDER BY id ASC")
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def get_machine_by_id(machine_id: int) -> Optional[Dict[str, Any]]:
    """Get machine by ID."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM machines WHERE id = ?", (machine_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def create_machine(name: str, code: str, machine_type: str, capacity_per_hour: int = 100,
                   hourly_rate: float = 45.0, status: str = "Idle", location: str = "Building A") -> int:
    """Create a machine."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO machines (name, code, machine_type, capacity_per_hour, hourly_rate, status, location)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, code, machine_type, capacity_per_hour, hourly_rate, status, location)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

def update_machine(machine_id: int, name: str, code: str, machine_type: str,
                   capacity_per_hour: int, hourly_rate: float, status: str, location: str) -> bool:
    """Update machine details."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE machines SET name=?, code=?, machine_type=?, capacity_per_hour=?,
               hourly_rate=?, status=?, location=? WHERE id=?""",
            (name, code, machine_type, capacity_per_hour, hourly_rate, status, location, machine_id)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

def update_machine_status(machine_id: int, status: str) -> bool:
    """Quickly update machine operational status."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE machines SET status=? WHERE id=?", (status, machine_id))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

def delete_machine(machine_id: int) -> bool:
    """Delete a machine."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM machines WHERE id=?", (machine_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

# ----------------- Worker Management -----------------

def get_workers() -> List[Dict[str, Any]]:
    """List all workers."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM workers ORDER BY id ASC")
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def get_worker_by_id(worker_id: int) -> Optional[Dict[str, Any]]:
    """Get worker by ID."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM workers WHERE id = ?", (worker_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def create_worker(name: str, employee_code: str, role_title: str, skill_level: str,
                  hourly_wage: float, availability_status: str = "Available", shift: str = "Day Shift") -> int:
    """Create a worker."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO workers (name, employee_code, role_title, skill_level, hourly_wage, availability_status, shift)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, employee_code, role_title, skill_level, hourly_wage, availability_status, shift)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

def update_worker(worker_id: int, name: str, employee_code: str, role_title: str,
                  skill_level: str, hourly_wage: float, availability_status: str, shift: str) -> bool:
    """Update worker information."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE workers SET name=?, employee_code=?, role_title=?, skill_level=?,
               hourly_wage=?, availability_status=?, shift=? WHERE id=?""",
            (name, employee_code, role_title, skill_level, hourly_wage, availability_status, shift, worker_id)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

def update_worker_status(worker_id: int, status: str) -> bool:
    """Update worker availability status."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE workers SET availability_status=? WHERE id=?", (status, worker_id))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

def delete_worker(worker_id: int) -> bool:
    """Delete a worker."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM workers WHERE id=?", (worker_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

# ----------------- Material Management -----------------

def get_materials() -> List[Dict[str, Any]]:
    """List all materials in inventory."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM materials ORDER BY id ASC")
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def get_material_by_id(material_id: int) -> Optional[Dict[str, Any]]:
    """Get material by ID."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM materials WHERE id = ?", (material_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def create_material(material_code: str, name: str, category: str, stock_quantity: float,
                    unit: str, unit_cost: float, minimum_threshold: float, supplier: str) -> int:
    """Create a new material item."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO materials (material_code, name, category, stock_quantity, unit, unit_cost, minimum_threshold, supplier)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (material_code, name, category, stock_quantity, unit, unit_cost, minimum_threshold, supplier)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

def update_material(material_id: int, material_code: str, name: str, category: str,
                    stock_quantity: float, unit: str, unit_cost: float, minimum_threshold: float, supplier: str) -> bool:
    """Update material details."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE materials SET material_code=?, name=?, category=?, stock_quantity=?,
               unit=?, unit_cost=?, minimum_threshold=?, supplier=? WHERE id=?""",
            (material_code, name, category, stock_quantity, unit, unit_cost, minimum_threshold, supplier, material_id)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

def adjust_material_stock(material_id: int, delta: float) -> bool:
    """Adjust material stock quantity by delta (positive or negative)."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE materials SET stock_quantity = stock_quantity + ? WHERE id=?", (delta, material_id))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

def delete_material(material_id: int) -> bool:
    """Delete a material item."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM materials WHERE id=?", (material_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

# ----------------- Job Management -----------------

def get_jobs(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """List jobs with optional status filter, joined with machine, worker, material names."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        query = """
            SELECT j.*, 
                   m.name AS machine_name, m.code AS machine_code,
                   w.name AS worker_name, w.employee_code AS worker_code,
                   mat.name AS material_name, mat.unit AS material_unit, mat.unit_cost AS material_unit_cost
            FROM jobs j
            LEFT JOIN machines m ON j.assigned_machine_id = m.id
            LEFT JOIN workers w ON j.assigned_worker_id = w.id
            LEFT JOIN materials mat ON j.required_material_id = mat.id
        """
        params = []
        if status_filter:
            query += " WHERE j.status = ?"
            params.append(status_filter)
        query += " ORDER BY j.id DESC"
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def get_job_by_id(job_id: int) -> Optional[Dict[str, Any]]:
    """Get single job with resolved relations."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        query = """
            SELECT j.*, 
                   m.name AS machine_name, m.code AS machine_code, m.hourly_rate AS machine_hourly_rate,
                   w.name AS worker_name, w.employee_code AS worker_code, w.hourly_wage AS worker_hourly_wage,
                   mat.name AS material_name, mat.unit AS material_unit, mat.unit_cost AS material_unit_cost, mat.stock_quantity AS material_stock
            FROM jobs j
            LEFT JOIN machines m ON j.assigned_machine_id = m.id
            LEFT JOIN workers w ON j.assigned_worker_id = w.id
            LEFT JOIN materials mat ON j.required_material_id = mat.id
            WHERE j.id = ?
        """
        cur.execute(query, (job_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def create_job(job_number: str, title: str, product_type: str, quantity: int,
               priority: str, processing_time_minutes: int, deadline: str,
               required_machine_type: str, required_skill_level: str = "Mid-Level",
               required_material_id: Optional[int] = None, material_quantity_required: float = 10.0,
               assigned_machine_id: Optional[int] = None, assigned_worker_id: Optional[int] = None) -> int:
    """Create a new job."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO jobs (job_number, title, product_type, quantity, priority,
                                 processing_time_minutes, deadline, required_machine_type,
                                 required_skill_level, required_material_id, material_quantity_required,
                                 assigned_machine_id, assigned_worker_id, status, progress_percentage)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', 0)""",
            (job_number, title, product_type, quantity, priority,
             processing_time_minutes, deadline, required_machine_type,
             required_skill_level, required_material_id, material_quantity_required,
             assigned_machine_id, assigned_worker_id)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

def update_job(job_id: int, title: str, product_type: str, quantity: int,
               priority: str, processing_time_minutes: int, deadline: str,
               required_machine_type: str, required_skill_level: str,
               required_material_id: Optional[int], material_quantity_required: float,
               assigned_machine_id: Optional[int], assigned_worker_id: Optional[int],
               status: str) -> bool:
    """Update job information."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE jobs SET title=?, product_type=?, quantity=?, priority=?,
               processing_time_minutes=?, deadline=?, required_machine_type=?,
               required_skill_level=?, required_material_id=?, material_quantity_required=?,
               assigned_machine_id=?, assigned_worker_id=?, status=?
               WHERE id=?""",
            (title, product_type, quantity, priority, processing_time_minutes,
             deadline, required_machine_type, required_skill_level, required_material_id,
             material_quantity_required, assigned_machine_id, assigned_worker_id, status, job_id)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

def update_job_status(job_id: int, status: str, progress_percentage: Optional[int] = None) -> bool:
    """Update job status and progress."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        if progress_percentage is not None:
            cur.execute("UPDATE jobs SET status=?, progress_percentage=? WHERE id=?",
                        (status, progress_percentage, job_id))
        else:
            cur.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

def update_job_assignment(job_id: int, machine_id: Optional[int], worker_id: Optional[int], status: str = "Scheduled") -> bool:
    """Assign machine and worker to a job."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE jobs SET assigned_machine_id=?, assigned_worker_id=?, status=? WHERE id=?",
            (machine_id, worker_id, status, job_id)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

def delete_job(job_id: int) -> bool:
    """Delete a job."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM jobs WHERE id=?", (job_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

# ----------------- Schedule Management -----------------

def get_schedules() -> List[Dict[str, Any]]:
    """Get all scheduled items joined with job, machine, and worker details."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT s.*, 
                      j.job_number, j.title AS job_title, j.priority AS job_priority,
                      j.processing_time_minutes, j.deadline, j.product_type, j.quantity,
                      m.name AS machine_name, m.code AS machine_code, m.machine_type,
                      w.name AS worker_name, w.employee_code AS worker_code
               FROM schedules s
               JOIN jobs j ON s.job_id = j.id
               JOIN machines m ON s.machine_id = m.id
               JOIN workers w ON s.worker_id = w.id
               ORDER BY s.start_time ASC, s.sequence_order ASC"""
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def get_schedule_by_id(schedule_id: int) -> Optional[Dict[str, Any]]:
    """Get schedule by ID."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM schedules WHERE id=?", (schedule_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def create_schedule(job_id: int, machine_id: int, worker_id: int,
                    start_time: str, end_time: str, sequence_order: int = 1,
                    status: str = "Scheduled", notes: str = "") -> int:
    """Create a new schedule record."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO schedules (job_id, machine_id, worker_id, start_time, end_time, sequence_order, status, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (job_id, machine_id, worker_id, start_time, end_time, sequence_order, status, notes)
        )
        # Update job assigned IDs and status
        cur.execute(
            "UPDATE jobs SET assigned_machine_id=?, assigned_worker_id=?, status='Scheduled' WHERE id=?",
            (machine_id, worker_id, job_id)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

def clear_all_schedules() -> bool:
    """Clear all schedules and reset scheduled jobs back to Pending."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM schedules")
        cur.execute("UPDATE jobs SET status='Pending', assigned_machine_id=NULL, assigned_worker_id=NULL WHERE status='Scheduled'")
        conn.commit()
        return True
    finally:
        conn.close()

def delete_schedule(schedule_id: int) -> bool:
    """Delete a schedule item."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT job_id FROM schedules WHERE id=?", (schedule_id,))
        row = cur.fetchone()
        if row:
            job_id = row["job_id"]
            cur.execute("UPDATE jobs SET status='Pending', assigned_machine_id=NULL, assigned_worker_id=NULL WHERE id=? AND status='Scheduled'", (job_id,))
        cur.execute("DELETE FROM schedules WHERE id=?", (schedule_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()

# ----------------- Production Logs -----------------

def log_production_event(message: str, event_type: str = "INFO", job_id: Optional[int] = None,
                         machine_id: Optional[int] = None, worker_id: Optional[int] = None,
                         thread_id: Optional[str] = None, execution_time_ms: int = 0) -> int:
    """Record an event log from Java or Python processing engines."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO production_logs (job_id, machine_id, worker_id, event_type, message, thread_id, execution_time_ms)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (job_id, machine_id, worker_id, event_type, message, thread_id, execution_time_ms)
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

def get_production_logs(limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieve recent production logs."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT l.*, j.job_number, m.name AS machine_name, w.name AS worker_name
               FROM production_logs l
               LEFT JOIN jobs j ON l.job_id = j.id
               LEFT JOIN machines m ON l.machine_id = m.id
               LEFT JOIN workers w ON l.worker_id = w.id
               ORDER BY l.id DESC LIMIT ?""",
            (limit,)
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def clear_production_logs() -> bool:
    """Clear historical logs."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM production_logs")
        conn.commit()
        return True
    finally:
        conn.close()

# ----------------- Invoice Management -----------------

def get_invoices() -> List[Dict[str, Any]]:
    """Get all generated production invoices."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT i.*, j.job_number, j.title AS job_title, j.product_type, j.quantity
               FROM invoices i
               JOIN jobs j ON i.job_id = j.id
               ORDER BY i.id DESC"""
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

def get_invoice_by_id(invoice_id: int) -> Optional[Dict[str, Any]]:
    """Get full invoice details."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT i.*, j.job_number, j.title AS job_title, j.product_type, j.quantity,
                      j.processing_time_minutes, j.deadline,
                      m.name AS machine_name, m.hourly_rate AS machine_hourly_rate,
                      w.name AS worker_name, w.hourly_wage AS worker_hourly_wage,
                      mat.name AS material_name, mat.unit_cost AS material_unit_cost, j.material_quantity_required
               FROM invoices i
               JOIN jobs j ON i.job_id = j.id
               LEFT JOIN machines m ON j.assigned_machine_id = m.id
               LEFT JOIN workers w ON j.assigned_worker_id = w.id
               LEFT JOIN materials mat ON j.required_material_id = mat.id
               WHERE i.id = ?""",
            (invoice_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def generate_invoice_for_job(job_id: int, client_name: str = "Apex Aerospace Corp", tax_rate: float = 0.08) -> Optional[int]:
    """Calculate costs and create an itemized production invoice for a job."""
    job = get_job_by_id(job_id)
    if not job:
        return None

    # Compute machine cost: (processing_time_minutes / 60) * machine_hourly_rate
    hours = max(0.5, job["processing_time_minutes"] / 60.0)
    machine_rate = job.get("machine_hourly_rate") or 45.0
    machine_cost = round(hours * machine_rate, 2)

    # Compute labor cost: hours * worker_hourly_wage
    labor_rate = job.get("worker_hourly_wage") or 28.0
    labor_cost = round(hours * labor_rate, 2)

    # Compute material cost: required_quantity * unit_cost
    mat_qty = job.get("material_quantity_required") or 10.0
    mat_unit_cost = job.get("material_unit_cost") or 12.0
    material_cost = round(mat_qty * mat_unit_cost, 2)

    subtotal = round(machine_cost + labor_cost + material_cost, 2)
    tax_amount = round(subtotal * tax_rate, 2)
    total_amount = round(subtotal + tax_amount, 2)

    invoice_number = f"INV-{datetime.now().strftime('%Y%m')}-{job_id:04d}"

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO invoices (invoice_number, job_id, client_name, issue_date,
                                    machine_cost, labor_cost, material_cost, subtotal,
                                    tax_amount, total_amount, payment_status, notes)
               VALUES (?, ?, ?, DATE('now'), ?, ?, ?, ?, ?, ?, 'Issued', ?)""",
            (invoice_number, job_id, client_name, machine_cost, labor_cost, material_cost,
             subtotal, tax_amount, total_amount, f"Automated production invoice for Job {job['job_number']}")
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        # Already exists, fetch it
        cur.execute("SELECT id FROM invoices WHERE invoice_number=?", (invoice_number,))
        r = cur.fetchone()
        return r["id"] if r else None
    finally:
        conn.close()

# ----------------- Dashboard & Analytics Aggregations -----------------

def get_dashboard_summary() -> Dict[str, Any]:
    """Aggregate high-level overview metrics."""
    conn = get_connection()
    try:
        cur = conn.cursor()

        # Machine counts
        cur.execute("SELECT COUNT(*) AS total, SUM(CASE WHEN status='Running' THEN 1 ELSE 0 END) AS running, SUM(CASE WHEN status='Idle' THEN 1 ELSE 0 END) AS idle, SUM(CASE WHEN status='Maintenance' THEN 1 ELSE 0 END) AS maintenance, SUM(CASE WHEN status='Error' THEN 1 ELSE 0 END) AS error FROM machines")
        mach_stats = dict(cur.fetchone())

        # Job counts
        cur.execute("SELECT COUNT(*) AS total, SUM(CASE WHEN status='Completed' THEN 1 ELSE 0 END) AS completed, SUM(CASE WHEN status='Processing' THEN 1 ELSE 0 END) AS processing, SUM(CASE WHEN status='Scheduled' THEN 1 ELSE 0 END) AS scheduled, SUM(CASE WHEN status='Pending' THEN 1 ELSE 0 END) AS pending FROM jobs")
        job_stats = dict(cur.fetchone())

        # Worker counts
        cur.execute("SELECT COUNT(*) AS total, SUM(CASE WHEN availability_status='Available' THEN 1 ELSE 0 END) AS available, SUM(CASE WHEN availability_status='Assigned' THEN 1 ELSE 0 END) AS assigned FROM workers")
        worker_stats = dict(cur.fetchone())

        # Material low stock count
        cur.execute("SELECT COUNT(*) AS low_stock FROM materials WHERE stock_quantity <= minimum_threshold")
        mat_stats = dict(cur.fetchone())

        # Total revenue from invoices
        cur.execute("SELECT COALESCE(SUM(total_amount), 0) AS total_revenue FROM invoices")
        rev_stats = dict(cur.fetchone())

        return {
            "machines": mach_stats,
            "jobs": job_stats,
            "workers": worker_stats,
            "materials": mat_stats,
            "revenue": rev_stats["total_revenue"]
        }
    finally:
        conn.close()

def get_system_alerts() -> List[Dict[str, Any]]:
    """Scan database for active critical alerts: material shortages, machine errors, overdue jobs."""
    alerts = []
    conn = get_connection()
    try:
        cur = conn.cursor()

        # 1. Machine errors/maintenance
        cur.execute("SELECT id, name, code, status FROM machines WHERE status IN ('Error', 'Maintenance')")
        for m in cur.fetchall():
            alerts.append({
                "severity": "CRITICAL" if m["status"] == "Error" else "WARNING",
                "category": "MACHINE",
                "title": f"Machine {m['name']} ({m['code']}) is {m['status'].upper()}",
                "message": f"Requires engineering attention before processing scheduled jobs."
            })

        # 2. Material inventory shortages
        cur.execute("SELECT name, material_code, stock_quantity, minimum_threshold, unit FROM materials WHERE stock_quantity <= minimum_threshold")
        for mat in cur.fetchall():
            alerts.append({
                "severity": "WARNING",
                "category": "INVENTORY",
                "title": f"Low Stock: {mat['name']} ({mat['material_code']})",
                "message": f"Current stock is {mat['stock_quantity']} {mat['unit']} (Threshold: {mat['minimum_threshold']} {mat['unit']}). Restocking needed."
            })

        # 3. Impending or breached job deadlines
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            """SELECT job_number, title, deadline, priority, status FROM jobs 
               WHERE status NOT IN ('Completed') AND deadline < ?""",
            (now_str,)
        )
        for j in cur.fetchall():
            alerts.append({
                "severity": "CRITICAL" if j["priority"] in ("Critical", "High") else "WARNING",
                "category": "DEADLINE",
                "title": f"Deadline Breach: Job {j['job_number']} ({j['title']})",
                "message": f"Target deadline was {j['deadline']}. Current state: {j['status']}."
            })

        return alerts
    finally:
        conn.close()
