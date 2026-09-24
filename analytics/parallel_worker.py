"""
Multiprocessing Parallel Analytics Worker
Executes CPU-intensive Monte Carlo simulations of stochastic production line variability
using Python's multiprocessing Pool / ProcessPoolExecutor.
"""
from concurrent.futures import ProcessPoolExecutor
import random
import time
from typing import Dict, Any, List

def _simulate_batch_chunk(chunk_size: int, base_duration_mins: float, variance_std: float) -> List[float]:
    """Worker function executed across multiple process cores."""
    durations = []
    for _ in range(chunk_size):
        # Gaussian distribution of processing variance
        actual = random.gauss(base_duration_mins, variance_std)
        # Factor in stochastic tool degradation probability
        if random.random() < 0.05:
            actual += random.uniform(5.0, 20.0) # Tool wear delay
        durations.append(max(base_duration_mins * 0.7, actual))
    return durations

class ParallelMonteCarloSimulator:
    """Uses Python multiprocessing to simulate thousands of stochastic schedule outcomes."""

    @classmethod
    def run_parallel_simulation(cls, num_iterations: int = 4000,
                                base_duration_mins: float = 60.0,
                                deadline_mins: float = 75.0,
                                num_workers: int = 4) -> Dict[str, Any]:
        start_time = time.time()
        chunk_size = num_iterations // num_workers

        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(_simulate_batch_chunk, chunk_size, base_duration_mins, 6.5)
                for _ in range(num_workers)
            ]
            all_results = []
            for f in futures:
                all_results.extend(f.result())

        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        # Statistical analysis
        total = len(all_results)
        on_time = sum(1 for d in all_results if d <= deadline_mins)
        on_time_probability = round((on_time / total) * 100.0, 1)

        avg_duration = round(sum(all_results) / total, 1)
        sorted_res = sorted(all_results)
        p50 = round(sorted_res[int(total * 0.50)], 1)
        p95 = round(sorted_res[int(total * 0.95)], 1)
        p99 = round(sorted_res[int(total * 0.99)], 1)

        return {
            "num_iterations": total,
            "cores_utilized": num_workers,
            "multiprocessing_time_ms": elapsed_ms,
            "on_time_probability_percent": on_time_probability,
            "mean_duration_mins": avg_duration,
            "p50_duration_mins": p50,
            "p95_risk_duration_mins": p95,
            "p99_worst_case_mins": p99,
            "deadline_mins": deadline_mins
        }
