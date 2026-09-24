"""
Production Analytics & Performance Evaluation Engine
Employs functional programming (map, filter, lambda, comprehensions) for data transformation,
OEE (Overall Equipment Effectiveness) metric calculation, trend predictions, and resource utilization.
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
import database.db as db
from analytics.sympy_optimizer import SymPyProductionOptimizer
from analytics.parallel_worker import ParallelMonteCarloSimulator

class AnalyticsEngine:
    """Core analytics, functional metrics calculation, and predictive analysis."""

    @classmethod
    def get_full_analytics(cls) -> Dict[str, Any]:
        """Aggregates all analytical reports, metrics, SymPy models, and forecasts."""
        machines = db.get_machines()
        jobs = db.get_jobs()
        workers = db.get_workers()
        materials = db.get_materials()
        invoices = db.get_invoices()

        # 1. Functional programming with filter / map / lambda
        completed_jobs = list(filter(lambda j: j.get("status") == "Completed", jobs))
        active_jobs = list(filter(lambda j: j.get("status") in ("Scheduled", "Processing"), jobs))
        critical_jobs = list(filter(lambda j: j.get("priority") == "Critical", jobs))

        # Map processing times and quantities using functional lambdas
        job_durations = list(map(lambda j: j.get("processing_time_minutes", 0), jobs))
        total_planned_minutes = sum(job_durations)
        total_units_in_pipeline = sum(map(lambda j: j.get("quantity", 0), jobs))

        # Dict comprehension for machine load distribution
        machine_load_map = {
            m["name"]: len([j for j in jobs if j.get("assigned_machine_id") == m["id"]])
            for m in machines
        }

        # 2. Resource Utilization Calculation
        running_machines = list(filter(lambda m: m.get("status") == "Running", machines))
        idle_machines = list(filter(lambda m: m.get("status") == "Idle", machines))
        maintenance_machines = list(filter(lambda m: m.get("status") in ("Maintenance", "Error"), machines))

        total_machines_count = max(1, len(machines))
        machine_utilization_rate = round((len(running_machines) / total_machines_count) * 100.0, 1)

        total_workers_count = max(1, len(workers))
        assigned_workers = list(filter(lambda w: w.get("availability_status") == "Assigned", workers))
        worker_utilization_rate = round((len(assigned_workers) / total_workers_count) * 100.0, 1)

        # 3. Overall Equipment Effectiveness (OEE)
        # OEE = Availability Rate * Performance Rate * Quality Rate
        # Availability = (Operational Machines / Total Operable Machines)
        operable_machines = [m for m in machines if m.get("status") != "Error"]
        availability_rate = round((len(operable_machines) / total_machines_count) * 100.0, 1)
        performance_rate = 94.2 # Standard benchmark baseline
        quality_rate = 98.6     # Standard scrap/rework benchmark
        oee_score = round((availability_rate / 100.0) * (performance_rate / 100.0) * (quality_rate / 100.0) * 100.0, 1)

        # 4. Production Trends (Past 7 Days Simulation & 7-Day Forecast)
        today = datetime.now().date()
        daily_trends = []
        for i in range(6, -1, -1):
            day_date = today - timedelta(days=i)
            # Simulated historical daily throughput with realistic curve
            units = int(85 + (i * 7) + (i % 3) * 12)
            daily_trends.append({
                "date": day_date.strftime("%b %d"),
                "units": units,
                "target": 110,
                "efficiency": min(100, int((units / 110.0) * 100))
            })

        # 7-day predictive forecast using simple linear trend extrapolation
        last_units = [d["units"] for d in daily_trends]
        trend_slope = (last_units[-1] - last_units[0]) / max(1, len(last_units))
        predictions = []
        for i in range(1, 8):
            f_date = today + timedelta(days=i)
            f_units = round(last_units[-1] + (trend_slope * i) + ((i % 2) * 5), 1)
            predictions.append({
                "date": f_date.strftime("%b %d"),
                "forecasted_units": max(50.0, f_units),
                "lower_bound": max(40.0, f_units - 12.0),
                "upper_bound": f_units + 14.0
            })

        # 5. SymPy Symbolic Optimizations
        batch_opt = SymPyProductionOptimizer.calculate_optimal_batch_size()
        speed_opt = SymPyProductionOptimizer.calculate_optimal_machine_speed()
        integral_opt = SymPyProductionOptimizer.calculate_cumulative_production_integral()

        # 6. Multiprocessing Monte Carlo Simulation
        monte_carlo = ParallelMonteCarloSimulator.run_parallel_simulation(num_iterations=2000)

        # 7. Material Consumption Value (Comprehension)
        material_inventory_value = sum([m["stock_quantity"] * m["unit_cost"] for m in materials])

        return {
            "overview": {
                "total_jobs": len(jobs),
                "completed_jobs": len(completed_jobs),
                "active_jobs": len(active_jobs),
                "critical_jobs": len(critical_jobs),
                "total_planned_minutes": total_planned_minutes,
                "total_units_in_pipeline": total_units_in_pipeline,
                "machine_utilization_rate": machine_utilization_rate,
                "worker_utilization_rate": worker_utilization_rate,
                "material_inventory_value": round(material_inventory_value, 2),
                "oee_score": oee_score,
                "oee_breakdown": {
                    "availability": availability_rate,
                    "performance": performance_rate,
                    "quality": quality_rate
                }
            },
            "machine_loads": machine_load_map,
            "daily_trends": daily_trends,
            "predictions": predictions,
            "sympy_optimization": {
                "batch_size": batch_opt,
                "machine_speed": speed_opt,
                "cumulative_integral": integral_opt
            },
            "monte_carlo": monte_carlo
        }
