"""
Production Line Resource Scheduling System - Main Flask Application
Complete server implementation with Authentication, Dashboard, Resource Management,
Scheduling Engine, Conflict Hub, Java Thread Monitor, Analytics & Invoices.
"""
import os
import sys
import csv
import io
from functools import wraps
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, Response, send_file
)
import config
import database.db as db
from scheduler.engine import SchedulingEngine, ConflictDetector, PriorityAnalyzer
from scheduler.gantt import get_gantt_data
from scheduler.rescheduling import trigger_auto_reschedule, handle_machine_status_change, handle_job_priority_change
from ipc.java_client import JavaIPCClient
from analytics.engine import AnalyticsEngine
from database.seed_data import seed_database

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Helper: Decorator for login authentication
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to access the Production System.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# Helper: Decorator for role-based authorization
def roles_accepted(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            user_role = session.get("user_role", "Operator")
            if user_role not in roles:
                flash(f"Access denied: {', '.join(roles)} privileges required.", "danger")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.context_processor
def inject_global_data():
    """Injects user session info and critical system alerts across all templates."""
    user = None
    alerts = []
    if "user_id" in session:
        user = {
            "id": session.get("user_id"),
            "username": session.get("username"),
            "role": session.get("user_role")
        }
        alerts = db.get_system_alerts()
    return {
        "current_user": user,
        "active_alerts": alerts,
        "now": datetime.now()
    }

# ----------------- Authentication Routes -----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = db.get_user_by_username(username)
        if user and db.verify_password(password, user["password_hash"]):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["user_role"] = user["role"]
            flash(f"Welcome back, {user['username']}! Logged in as {user['role']}.", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "Operator").strip()

        if not username or not email or not password:
            flash("All registration fields are required.", "danger")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("register.html")

        user_id = db.create_user(username, email, password, role=role)
        if user_id:
            flash("Account successfully created. Please sign in.", "success")
            return redirect(url_for("login"))
        else:
            flash("Username or email already exists. Choose a different one.", "danger")

    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("login"))

# ----------------- Dashboard & Monitoring -----------------

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    summary = db.get_dashboard_summary()
    machines = db.get_machines()
    jobs = db.get_jobs()
    recent_logs = db.get_production_logs(limit=15)
    conflicts = ConflictDetector.detect_all_conflicts()

    return render_template(
        "dashboard.html",
        summary=summary,
        machines=machines,
        jobs=jobs[:10], # Most recent 10 jobs
        recent_logs=recent_logs,
        conflicts=conflicts
    )

# ----------------- Job Management -----------------

@app.route("/jobs")
@login_required
def jobs():
    status_filter = request.args.get("status")
    all_jobs = db.get_jobs(status_filter=status_filter)
    machines = db.get_machines()
    workers = db.get_workers()
    materials = db.get_materials()

    return render_template(
        "jobs.html",
        jobs=all_jobs,
        machines=machines,
        workers=workers,
        materials=materials,
        current_filter=status_filter or "All"
    )

@app.route("/jobs/create", methods=["POST"])
@login_required
@roles_accepted("Admin", "Plant Manager")
def create_job():
    try:
        job_number = request.form.get("job_number", f"JOB-{datetime.now().strftime('%m%d%H%M')}")
        title = request.form.get("title", "").strip()
        product_type = request.form.get("product_type", "").strip()
        quantity = int(request.form.get("quantity", 50))
        priority = request.form.get("priority", "Medium")
        processing_time = int(request.form.get("processing_time_minutes", 60))
        deadline = request.form.get("deadline", "")
        req_machine = request.form.get("required_machine_type", "")
        req_skill = request.form.get("required_skill_level", "Mid-Level")
        req_material_id = request.form.get("required_material_id")
        material_qty = float(request.form.get("material_quantity_required", 10.0))

        if not deadline:
            deadline = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")

        db.create_job(
            job_number=job_number,
            title=title,
            product_type=product_type,
            quantity=quantity,
            priority=priority,
            processing_time_minutes=processing_time,
            deadline=deadline,
            required_machine_type=req_machine,
            required_skill_level=req_skill,
            required_material_id=int(req_material_id) if req_material_id else None,
            material_quantity_required=material_qty
        )

        db.log_production_event(f"New Job {job_number} ('{title}') registered in system.", "INFO")
        flash(f"Job {job_number} created successfully.", "success")

        # If created with Critical priority, auto-reschedule
        if priority == "Critical":
            trigger_auto_reschedule("Critical Job Creation", f"Job {job_number} added with Critical priority.")

    except Exception as e:
        flash(f"Error creating job: {str(e)}", "danger")

    return redirect(url_for("jobs"))

@app.route("/jobs/edit/<int:job_id>", methods=["POST"])
@login_required
@roles_accepted("Admin", "Plant Manager")
def edit_job(job_id):
    try:
        title = request.form.get("title")
        product_type = request.form.get("product_type")
        quantity = int(request.form.get("quantity", 50))
        priority = request.form.get("priority", "Medium")
        processing_time = int(request.form.get("processing_time_minutes", 60))
        deadline = request.form.get("deadline")
        req_machine = request.form.get("required_machine_type")
        req_skill = request.form.get("required_skill_level", "Mid-Level")
        req_mat_id = request.form.get("required_material_id")
        mat_qty = float(request.form.get("material_quantity_required", 10.0))
        assigned_mach = request.form.get("assigned_machine_id")
        assigned_wrk = request.form.get("assigned_worker_id")
        status = request.form.get("status", "Pending")

        db.update_job(
            job_id=job_id,
            title=title,
            product_type=product_type,
            quantity=quantity,
            priority=priority,
            processing_time_minutes=processing_time,
            deadline=deadline,
            required_machine_type=req_machine,
            required_skill_level=req_skill,
            required_material_id=int(req_mat_id) if req_mat_id else None,
            material_quantity_required=mat_qty,
            assigned_machine_id=int(assigned_mach) if assigned_mach else None,
            assigned_worker_id=int(assigned_wrk) if assigned_wrk else None,
            status=status
        )
        flash("Job updated successfully.", "success")
    except Exception as e:
        flash(f"Error updating job: {str(e)}", "danger")
    return redirect(url_for("jobs"))

@app.route("/jobs/delete/<int:job_id>", methods=["POST"])
@login_required
@roles_accepted("Admin")
def delete_job(job_id):
    db.delete_job(job_id)
    flash("Job deleted.", "info")
    return redirect(url_for("jobs"))

# ----------------- Machine Management -----------------

@app.route("/machines")
@login_required
def machines():
    all_machines = db.get_machines()
    return render_template("machines.html", machines=all_machines)

@app.route("/machines/create", methods=["POST"])
@login_required
@roles_accepted("Admin", "Plant Manager")
def create_machine():
    try:
        name = request.form.get("name")
        code = request.form.get("code")
        m_type = request.form.get("machine_type")
        capacity = int(request.form.get("capacity_per_hour", 100))
        rate = float(request.form.get("hourly_rate", 45.0))
        status = request.form.get("status", "Idle")
        loc = request.form.get("location", "Main Plant")

        db.create_machine(name, code, m_type, capacity, rate, status, loc)
        flash(f"Machine {code} added to inventory.", "success")
    except Exception as e:
        flash(f"Error adding machine: {str(e)}", "danger")
    return redirect(url_for("machines"))

@app.route("/machines/status/<int:machine_id>", methods=["POST"])
@login_required
def update_machine_status_route(machine_id):
    new_status = request.form.get("status")
    result = handle_machine_status_change(machine_id, new_status)
    flash(f"Machine status updated to '{new_status}'. Automated conflict re-evaluation triggered.", "info")
    return redirect(url_for("machines"))

@app.route("/machines/delete/<int:machine_id>", methods=["POST"])
@login_required
@roles_accepted("Admin")
def delete_machine(machine_id):
    db.delete_machine(machine_id)
    flash("Machine removed from system.", "info")
    return redirect(url_for("machines"))

# ----------------- Worker Management -----------------

@app.route("/workers")
@login_required
def workers():
    all_workers = db.get_workers()
    return render_template("workers.html", workers=all_workers)

@app.route("/workers/create", methods=["POST"])
@login_required
@roles_accepted("Admin", "Plant Manager")
def create_worker():
    try:
        name = request.form.get("name")
        code = request.form.get("employee_code")
        role_title = request.form.get("role_title", "Operator")
        skill = request.form.get("skill_level", "Mid-Level")
        wage = float(request.form.get("hourly_wage", 28.0))
        shift = request.form.get("shift", "Day Shift")

        db.create_worker(name, code, role_title, skill, wage, "Available", shift)
        flash(f"Worker {name} registered.", "success")
    except Exception as e:
        flash(f"Error registering worker: {str(e)}", "danger")
    return redirect(url_for("workers"))

@app.route("/workers/status/<int:worker_id>", methods=["POST"])
@login_required
def update_worker_status_route(worker_id):
    new_status = request.form.get("status")
    db.update_worker_status(worker_id, new_status)
    if new_status == "On Leave":
        trigger_auto_reschedule("Worker On Leave", f"Worker ID {worker_id} went on leave.")
    flash(f"Worker availability updated to {new_status}.", "info")
    return redirect(url_for("workers"))

@app.route("/workers/delete/<int:worker_id>", methods=["POST"])
@login_required
@roles_accepted("Admin")
def delete_worker(worker_id):
    db.delete_worker(worker_id)
    flash("Worker record deleted.", "info")
    return redirect(url_for("workers"))

# ----------------- Material Inventory -----------------

@app.route("/materials")
@login_required
def materials():
    all_materials = db.get_materials()
    return render_template("materials.html", materials=all_materials)

@app.route("/materials/create", methods=["POST"])
@login_required
@roles_accepted("Admin", "Plant Manager")
def create_material():
    try:
        code = request.form.get("material_code")
        name = request.form.get("name")
        cat = request.form.get("category", "Raw Material")
        stock = float(request.form.get("stock_quantity", 0))
        unit = request.form.get("unit", "kg")
        cost = float(request.form.get("unit_cost", 10.0))
        thresh = float(request.form.get("minimum_threshold", 50.0))
        supplier = request.form.get("supplier", "Industrial Supplies")

        db.create_material(code, name, cat, stock, unit, cost, thresh, supplier)
        flash(f"Material {code} added.", "success")
    except Exception as e:
        flash(f"Error adding material: {str(e)}", "danger")
    return redirect(url_for("materials"))

@app.route("/materials/restock/<int:material_id>", methods=["POST"])
@login_required
def restock_material(material_id):
    try:
        delta = float(request.form.get("quantity", 50.0))
        db.adjust_material_stock(material_id, delta)
        flash(f"Stock replenished by +{delta} units.", "success")
    except Exception as e:
        flash(f"Error restocking: {str(e)}", "danger")
    return redirect(url_for("materials"))

@app.route("/materials/delete/<int:material_id>", methods=["POST"])
@login_required
@roles_accepted("Admin")
def delete_material(material_id):
    db.delete_material(material_id)
    flash("Material item removed.", "info")
    return redirect(url_for("materials"))

# ----------------- Scheduling & Gantt -----------------

@app.route("/scheduling")
@login_required
def scheduling():
    schedules = db.get_schedules()
    pending_jobs = [j for j in db.get_jobs() if j["status"] in ("Pending", "Scheduled")]
    ranked_jobs = PriorityAnalyzer.rank_jobs(pending_jobs)
    conflicts = ConflictDetector.detect_all_conflicts()

    return render_template(
        "scheduling.html",
        schedules=schedules,
        ranked_jobs=ranked_jobs,
        conflicts=conflicts
    )

@app.route("/scheduling/run", methods=["POST"])
@login_required
@roles_accepted("Admin", "Plant Manager")
def run_scheduling_engine():
    heuristic = request.form.get("heuristic", "BALANCED")
    result = SchedulingEngine.run_scheduler(heuristic=heuristic, auto_clear_existing=True)

    flash(
        f"Scheduler completed using '{heuristic}' optimization. Scheduled {result['scheduled_count']} jobs. Found {len(result['conflicts'])} potential conflicts.",
        "success" if result["scheduled_count"] > 0 else "warning"
    )
    return redirect(url_for("scheduling"))

@app.route("/scheduling/clear", methods=["POST"])
@login_required
@roles_accepted("Admin")
def clear_schedules():
    db.clear_all_schedules()
    flash("All active schedules reset to Pending.", "info")
    return redirect(url_for("scheduling"))

@app.route("/gantt")
@login_required
def gantt_view():
    gantt_data = get_gantt_data()
    return render_template("gantt.html", gantt=gantt_data)

# ----------------- Conflict Hub -----------------

@app.route("/conflicts")
@login_required
def conflicts():
    all_conflicts = ConflictDetector.detect_all_conflicts()
    return render_template("conflicts.html", conflicts=all_conflicts)

@app.route("/conflicts/resolve", methods=["POST"])
@login_required
@roles_accepted("Admin", "Plant Manager")
def resolve_conflicts():
    result = trigger_auto_reschedule("Manual Conflict Resolution Action", "Admin triggered automated re-allocation.")
    flash(f"Automatic Conflict Resolution completed. Re-scheduled {result['scheduled_count']} tasks with zero overlap.", "success")
    return redirect(url_for("conflicts"))

# ----------------- Java Processing Monitor & IPC -----------------

@app.route("/java-monitor")
@login_required
def java_monitor():
    ipc_client = JavaIPCClient.get_instance()
    status = ipc_client.get_status(sync_db=True)
    scheduled_jobs = [j for j in db.get_jobs() if j["status"] in ("Scheduled", "Processing")]
    logs = db.get_production_logs(limit=40)

    return render_template(
        "java_monitor.html",
        status=status,
        scheduled_jobs=scheduled_jobs,
        logs=logs
    )

@app.route("/api/java/status")
@login_required
def api_java_status():
    """AJAX endpoint for real-time thread visualization."""
    ipc_client = JavaIPCClient.get_instance()
    status = ipc_client.get_status(sync_db=True)
    return jsonify(status)

@app.route("/api/java/dispatch", methods=["POST"])
@login_required
@roles_accepted("Admin", "Plant Manager", "Operator")
def api_java_dispatch():
    """Dispatch scheduled jobs to Java worker threads."""
    ipc_client = JavaIPCClient.get_instance()
    jobs = [j for j in db.get_jobs() if j["status"] in ("Scheduled", "Pending")]
    if not jobs:
        return jsonify({"success": False, "message": "No scheduled or pending jobs to process."})

    res = ipc_client.dispatch_batch(jobs)
    return jsonify(res)

@app.route("/api/java/pause", methods=["POST"])
@login_required
def api_java_pause():
    ipc_client = JavaIPCClient.get_instance()
    return jsonify(ipc_client.pause_processing())

@app.route("/api/java/resume", methods=["POST"])
@login_required
def api_java_resume():
    ipc_client = JavaIPCClient.get_instance()
    return jsonify(ipc_client.resume_processing())

@app.route("/api/java/stop", methods=["POST"])
@login_required
def api_java_stop():
    ipc_client = JavaIPCClient.get_instance()
    return jsonify(ipc_client.stop_processing())

# ----------------- Analytics Module -----------------

@app.route("/analytics")
@login_required
def analytics():
    analytics_data = AnalyticsEngine.get_full_analytics()
    return render_template("analytics.html", data=analytics_data)

# ----------------- Reports & Invoices -----------------

@app.route("/reports")
@login_required
def reports():
    jobs = db.get_jobs()
    machines = db.get_machines()
    workers = db.get_workers()
    analytics_data = AnalyticsEngine.get_full_analytics()

    return render_template(
        "reports.html",
        jobs=jobs,
        machines=machines,
        workers=workers,
        analytics=analytics_data
    )

@app.route("/reports/export-csv")
@login_required
def export_csv():
    """Downloadable production report as CSV."""
    jobs = db.get_jobs()
    si = io.StringIO()
    writer = csv.writer(si)

    writer.writerow([
        "Job Number", "Title", "Product Type", "Quantity", "Priority",
        "Duration (Mins)", "Deadline", "Machine", "Worker", "Status", "Progress %"
    ])
    for j in jobs:
        writer.writerow([
            j["job_number"], j["title"], j["product_type"], j["quantity"], j["priority"],
            j["processing_time_minutes"], j["deadline"],
            j.get("machine_name", "Unassigned"),
            j.get("worker_name", "Unassigned"),
            j["status"], j["progress_percentage"]
        ])

    output = io.BytesIO()
    output.write(si.getvalue().encode("utf-8"))
    output.seek(0)
    return send_file(
        output,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"production_report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    )

@app.route("/invoices")
@login_required
def invoices():
    all_invoices = db.get_invoices()
    completed_jobs = [j for j in db.get_jobs() if j["status"] in ("Completed", "Processing")]
    return render_template("invoices.html", invoices=all_invoices, jobs=completed_jobs)

@app.route("/invoices/generate/<int:job_id>", methods=["POST"])
@login_required
@roles_accepted("Admin", "Plant Manager")
def generate_invoice(job_id):
    client_name = request.form.get("client_name", "Apex Engineering Corp")
    inv_id = db.generate_invoice_for_job(job_id, client_name=client_name)
    if inv_id:
        flash("Production invoice generated successfully.", "success")
        return redirect(url_for("view_invoice", invoice_id=inv_id))
    else:
        flash("Could not generate invoice. Ensure job exists.", "danger")
        return redirect(url_for("invoices"))

@app.route("/invoices/<int:invoice_id>")
@login_required
def view_invoice(invoice_id):
    invoice = db.get_invoice_by_id(invoice_id)
    if not invoice:
        flash("Invoice not found.", "danger")
        return redirect(url_for("invoices"))
    return render_template("invoice_detail.html", invoice=invoice)

# ----------------- Application Entry -----------------

if __name__ == "__main__":
    seed_database()
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port, debug=config.DEBUG)
