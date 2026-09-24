# Production Line Resource Scheduling System (CSE Academic Suite)

A complete, production-grade **Production Line Resource Scheduling System** built with **Python 3.x**, **SQLite3**, **SymPy**, and a genuinely integrated **Java Multithreaded Processing Engine**.

Developed strictly according to CSE Academic standards with clear separation of concerns, true inter-process communication (IPC), thread synchronization, mathematical optimization, and industrial database architecture.

---

## Architecture Overview

```
                          ┌───────────────────────────┐
                          │   Browser Web Interface   │
                          │  (HTML5 / CSS3 / Vanilla) │
                          └─────────────┬─────────────┘
                                        │ HTTP (Port 3000)
                                        ▼
                          ┌───────────────────────────┐
                          │   Python 3 Flask Server   │
                          │ (Auth, RBAC, CRUD, Views) │
                          └──────┬─────────────┬──────┘
                                 │             │
                ┌────────────────┴───┐     ┌───┴────────────────┐
                │   SQLite Database  │     │   SymPy Analytics  │
                │ (8 Relational DDL) │     │ (Lot Size, Speeds) │
                └────────────────────┘     └────────────────────┘
                                 │
                                 ▼
                     ┌───────────────────────┐
                     │   Python Scheduling   │
                     │    Engine (Heuristic) │
                     │  - Priority Scoring   │
                     │  - Conflict Detector  │
                     │  - Auto-Rescheduling  │
                     └───────────┬───────────┘
                                 │ JSON / TCP Socket IPC
                                 │ (127.0.0.1:5050)
                                 ▼
         ╔════════════════════════════════════════════════════╗
         ║        JAVA MULTITHREADED PROCESSING ENGINE        ║
         ║  com.production.engine & com.production.sync       ║
         ║  ────────────────────────────────────────────────  ║
         ║  • One Worker Thread per Physical Machine          ║
         ║  • Fair ReentrantLock Machine/Worker Locking       ║
         ║  • PriorityBlockingQueue Task Dispatch             ║
         ║  • Live Socket Event Stream & Progress Updates     ║
         ╚════════════════════════════════════════════════════╝
```

---

## Key Modules & Implementation Details

### 1. User Authentication & Authorization
- **Session-Based Authentication** with secure PBKDF2-SHA256 password hashing.
- **Role-Based Access Control (RBAC)**:
  - `Admin`: Full permissions (Add/edit/delete machines, workers, materials, jobs, clear schedules).
  - `Plant Manager`: Production scheduling, dispatching, job management, invoice generation.
  - `Operator`: Floor-level execution, status toggling, viewing schedules.
- **Default Accounts**:
  - `admin` / `admin123` (Admin)
  - `manager` / `manager123` (Plant Manager)
  - `operator` / `operator123` (Operator)

### 2. Database Layer (SQLite3)
Relational schema (`database/schema.sql`) with foreign keys and cascade rules across 8 tables:
1. `users` - Personnel credentials, roles, email.
2. `machines` - Machine codes, types, capacity per hour, hourly rates, statuses.
3. `workers` - Operator rosters, skill levels (Junior to Master), shifts, availability.
4. `materials` - SKU codes, stock quantities, unit costs, minimum deficit thresholds.
5. `jobs` - Production job specifications, priority (Critical, High, Medium, Low), required tools.
6. `schedules` - Timeline slot allocations (start time, end time, assigned machine/worker).
7. `production_logs` - Structured audit trail of system events, thread starts, lock acquisitions.
8. `invoices` - Itemized manufacturing invoices (machine cost, labor cost, material cost, overhead).

### 3. Python Scheduling Engine (`scheduler/engine.py`)
- **Priority Analysis**: Multi-criteria weighted composite scoring:
  $$\text{Score} = w_{base} \cdot P + w_{urgency} \cdot U(\text{deadline}) + w_{spt} \cdot \left(\frac{100}{\text{duration}}\right)$$
- **Optimization Heuristics**:
  - `BALANCED`: Multi-criteria composite priority + due date + shortest processing time.
  - `PRIORITY_FIRST`: Strict critical job precedence.
  - `EDD`: Earliest Due Date dispatch.
  - `SPT`: Shortest Processing Time first.
- **Conflict Detection (`scheduler/engine.py:ConflictDetector`)**:
  - Detects machine slot overlap conflicts.
  - Detects human operator double-booking.
  - Detects inventory shortages against batch requirements.
  - Detects offline machine assignments.
- **Automatic Rescheduling (`scheduler/rescheduling.py`)**:
  - Triggered dynamically when a machine enters `Maintenance`/`Error`, or when a job is escalated to `Critical`. Re-routes impacted jobs with zero human intervention.

### 4. Java Multithreaded Processing Module (`java_engine/`)
Java code structured across 5 OOP packages:
- `com.production.interfaces`: `IProcessor`, `ILockableResource`, `IEventListener`.
- `com.production.models`: `JobTask`, `MachineUnit`, `WorkerAssignment`, `ProductionEvent`.
- `com.production.exceptions`: `ResourceConflictException`, `ProductionHaltException`, `InvalidJobStateException`.
- `com.production.sync`:
  - `ResourceLockManager`: Acquires machine and worker locks in deterministic sorted order to mathematically prevent deadlocks.
  - `SafeJobQueue`: Thread-safe priority blocking queue.
- `com.production.engine`:
  - `MachineWorkerThread`: One dedicated thread per machine executing production cycles with synchronized step-by-step progress simulation.
  - `ProductionEngine`: Coordinates thread pool, pause/resume, and event buffering.
- `com.production.ipc`:
  - `ProtocolHandler`: Dispatches JSON commands (`PING`, `INIT_RESOURCES`, `SUBMIT_BATCH`, `PAUSE`, `RESUME`, `GET_STATUS`, `STOP`).
  - `SocketServer`: Multi-threaded TCP socket server listening on `127.0.0.1:5050`.

### 5. Python-Java Socket Communication (`ipc/java_client.py`)
- Communicates via TCP Socket protocol on `127.0.0.1:5050`.
- Automatically starts Java server process if offline.
- Bidirectional synchronization: sends jobs to Java threads and pushes thread progress/completion back into the SQLite database in real time.

### 6. SymPy Analytics & Parallel Processing (`analytics/`)
- **SymPy Symbolic Optimization (`analytics/sympy_optimizer.py`)**:
  - Solves $\frac{dC}{dq} = 0$ for Economic Batch Size.
  - Solves $\frac{dC_{tot}}{dv} = 0$ for Optimal Machine Operating Speed (RPM) balancing power vs labor wages.
  - Evaluates definite integral $\int_0^T P_{max}(1 - e^{-kt}) dt$ for cumulative output.
- **Parallel Monte Carlo Simulation (`analytics/parallel_worker.py`)**:
  - Uses Python `ProcessPoolExecutor` to simulate 4,000 stochastic manufacturing cycles with tool degradation variance to estimate on-time completion probabilities.

---

## How to Run the Project

### Running Everything in One Command
```bash
python3 run.py
```
This automatically:
1. Compiles Java source files with `javac` into `java_engine/bin/`.
2. Initializes and seeds the SQLite database `production.db`.
3. Starts the Java TCP Socket Server on `127.0.0.1:5050`.
4. Starts the Flask Web Server on `http://0.0.0.0:3000`.

### Standalone Java Engine Execution (for CSE Demo/Defense)
To demonstrate the Java module independently:
```bash
# 1. Compile Java codebase
bash java_engine/build.sh

# 2. Run Java TCP Socket Server directly
java -cp java_engine/bin com.production.ipc.Main 5050
```

### Verifying Python-Java Socket Communication
In a Python terminal:
```python
from ipc.java_client import JavaIPCClient
client = JavaIPCClient.get_instance()
print("Connected:", client.ping())
print("Status:", client.get_status())
```

---

## Web Application Pages & Endpoints

| Page | Route | Description |
|---|---|---|
| **Dashboard** | `/dashboard` | Machine status fleet, job pipeline, material deficit alerts, recent logs |
| **Jobs** | `/jobs` | CRUD operations for production jobs, status filters, priority flags |
| **Scheduling** | `/scheduling` | Heuristic engine selection, composite priority scoring breakdown |
| **Gantt Chart** | `/gantt` | Visual interactive timeline with machine tracks and color-coded jobs |
| **Conflict Hub** | `/conflicts` | Bottleneck scanner with 1-click "Auto-Resolve & Re-Schedule All" |
| **Java Monitor** | `/java-monitor` | Live concurrent thread pool dashboard, live console stream, pause/resume |
| **Machines** | `/machines` | Machine fleet management, capacity/hr, operating cost, status triggers |
| **Workers** | `/workers` | Operator roster, skill tiers, wage rates, shift assignments |
| **Materials** | `/materials` | Raw material SKU inventory, minimum thresholds, quick replenishment |
| **Analytics** | `/analytics` | SymPy calculus derivations, parallel Monte Carlo simulations, OEE score |
| **Reports** | `/reports` | Comprehensive production report with CSV download (`/reports/export-csv`) |
| **Invoices** | `/invoices` | Itemized manufacturing invoices with printable view (`/invoices/<id>`) |
