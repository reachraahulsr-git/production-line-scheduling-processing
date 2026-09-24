-- Production Line Resource Scheduling System Schema
-- SQLite3 compatible DDL

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'Operator' CHECK (role IN ('Admin', 'Plant Manager', 'Operator')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS machines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    machine_type TEXT NOT NULL,
    capacity_per_hour INTEGER NOT NULL DEFAULT 100,
    hourly_rate REAL NOT NULL DEFAULT 45.0,
    status TEXT NOT NULL DEFAULT 'Idle' CHECK (status IN ('Idle', 'Running', 'Maintenance', 'Error')),
    location TEXT DEFAULT 'Building A - Floor 1',
    last_maintenance DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    employee_code TEXT UNIQUE NOT NULL,
    role_title TEXT NOT NULL DEFAULT 'Machine Operator',
    skill_level TEXT NOT NULL DEFAULT 'Mid-Level' CHECK (skill_level IN ('Junior', 'Mid-Level', 'Senior', 'Master')),
    hourly_wage REAL NOT NULL DEFAULT 28.0,
    availability_status TEXT NOT NULL DEFAULT 'Available' CHECK (availability_status IN ('Available', 'Assigned', 'On Leave')),
    shift TEXT DEFAULT 'Day Shift (08:00 - 16:00)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT DEFAULT 'Raw Material',
    stock_quantity REAL NOT NULL DEFAULT 0.0,
    unit TEXT NOT NULL DEFAULT 'kg',
    unit_cost REAL NOT NULL DEFAULT 10.0,
    minimum_threshold REAL NOT NULL DEFAULT 50.0,
    supplier TEXT DEFAULT 'Industrial Supply Corp',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_number TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    product_type TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 50,
    priority TEXT NOT NULL DEFAULT 'Medium' CHECK (priority IN ('Low', 'Medium', 'High', 'Critical')),
    processing_time_minutes INTEGER NOT NULL DEFAULT 60,
    deadline TIMESTAMP NOT NULL,
    required_machine_type TEXT NOT NULL,
    required_skill_level TEXT NOT NULL DEFAULT 'Mid-Level' CHECK (required_skill_level IN ('Junior', 'Mid-Level', 'Senior', 'Master')),
    required_material_id INTEGER,
    material_quantity_required REAL DEFAULT 10.0,
    status TEXT NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending', 'Scheduled', 'Processing', 'Completed', 'Interrupted')),
    progress_percentage INTEGER DEFAULT 0,
    assigned_machine_id INTEGER,
    assigned_worker_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (required_material_id) REFERENCES materials (id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_machine_id) REFERENCES machines (id) ON DELETE SET NULL,
    FOREIGN KEY (assigned_worker_id) REFERENCES workers (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    machine_id INTEGER NOT NULL,
    worker_id INTEGER NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    sequence_order INTEGER DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'Scheduled' CHECK (status IN ('Scheduled', 'In-Progress', 'Completed', 'Delayed', 'Cancelled')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE,
    FOREIGN KEY (machine_id) REFERENCES machines (id) ON DELETE CASCADE,
    FOREIGN KEY (worker_id) REFERENCES workers (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS production_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER,
    machine_id INTEGER,
    worker_id INTEGER,
    event_type TEXT NOT NULL DEFAULT 'INFO' CHECK (event_type IN ('INFO', 'START', 'PROGRESS', 'COMPLETION', 'LOCK_ACQUIRED', 'RESOURCE_LOCKED', 'WARNING', 'ERROR')),
    message TEXT NOT NULL,
    thread_id TEXT,
    execution_time_ms INTEGER DEFAULT 0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE SET NULL,
    FOREIGN KEY (machine_id) REFERENCES machines (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT UNIQUE NOT NULL,
    job_id INTEGER NOT NULL,
    client_name TEXT NOT NULL,
    issue_date DATE DEFAULT CURRENT_DATE,
    machine_cost REAL NOT NULL DEFAULT 0.0,
    labor_cost REAL NOT NULL DEFAULT 0.0,
    material_cost REAL NOT NULL DEFAULT 0.0,
    subtotal REAL NOT NULL DEFAULT 0.0,
    tax_amount REAL NOT NULL DEFAULT 0.0,
    total_amount REAL NOT NULL DEFAULT 0.0,
    payment_status TEXT NOT NULL DEFAULT 'Issued' CHECK (payment_status IN ('Draft', 'Issued', 'Paid')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_priority ON jobs(priority);
CREATE INDEX IF NOT EXISTS idx_schedules_start ON schedules(start_time);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON production_logs(timestamp);
