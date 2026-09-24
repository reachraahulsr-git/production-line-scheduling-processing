"""
SymPy Demand & Processing Optimization Module
Performs symbolic calculus derivations for optimal manufacturing parameters:
1. Optimal Production Lot Size / Batch Optimization (dC/dq = 0)
2. Machine Speed vs Energy & Labor Cost Minimization (dCost/dv = 0)
3. Cumulative Production Throughput Rate Integration (Integral P(t) dt)
"""
import sympy as sp
from typing import Dict, Any

class SymPyProductionOptimizer:
    """Symbolic mathematical optimization using SymPy for manufacturing engineering."""

    @classmethod
    def calculate_optimal_batch_size(cls, annual_demand: float = 12000.0,
                                     setup_cost: float = 450.0,
                                     holding_cost: float = 8.5,
                                     prod_rate: float = 250.0,
                                     demand_rate: float = 50.0) -> Dict[str, Any]:
        """
        Derives the optimal production batch quantity q* using symbolic calculus:
        Cost Function: C(q) = (D/q)*S + (q/2)*H*(1 - d/p)
        First derivative dC/dq = 0 gives the global minimum.
        """
        q = sp.Symbol('q', positive=True, real=True)
        D = sp.Symbol('D', positive=True, real=True)
        S = sp.Symbol('S', positive=True, real=True)
        H = sp.Symbol('H', positive=True, real=True)
        d = sp.Symbol('d', positive=True, real=True)
        p = sp.Symbol('p', positive=True, real=True)

        # Symbolic Cost Equation
        cost_eq = (D / q) * S + (q / 2) * H * (1 - d / p)

        # Differentiate with respect to q
        d_cost = sp.diff(cost_eq, q)

        # Solve d_cost = 0 for q
        solutions = sp.solve(d_cost, q)
        # Select positive real root
        positive_solutions = [s for s in solutions if s.is_positive or not s.is_negative]
        optimal_formula = positive_solutions[0] if positive_solutions else (solutions[0] if solutions else None)

        # Numerical substitution
        subs_dict = {D: annual_demand, S: setup_cost, H: holding_cost, d: demand_rate, p: prod_rate}
        numerical_q = abs(float(optimal_formula.evalf(subs=subs_dict))) if optimal_formula else 0.0
        total_annual_cost = float(cost_eq.evalf(subs={**subs_dict, q: numerical_q}))

        return {
            "formula_latex": sp.latex(optimal_formula),
            "cost_function_latex": sp.latex(cost_eq),
            "derivative_latex": sp.latex(d_cost),
            "optimal_batch_units": round(numerical_q, 1),
            "minimized_annual_cost": round(total_annual_cost, 2),
            "parameters": {
                "annual_demand": annual_demand,
                "setup_cost": setup_cost,
                "holding_cost": holding_cost,
                "production_rate_per_day": prod_rate,
                "demand_rate_per_day": demand_rate
            }
        }

    @classmethod
    def calculate_optimal_machine_speed(cls, units_batch: int = 500,
                                        k1_energy: float = 0.002,
                                        k2_idle: float = 15.0,
                                        energy_price: float = 0.18,
                                        labor_wage: float = 32.0) -> Dict[str, Any]:
        """
        Symbolic minimization of energy + labor cost with respect to machine operating speed v.
        Processing Time: T(v) = N / v
        Energy Cost = price * (k1 * v^3 + k2) * T(v) = price * N * (k1 * v^2 + k2 / v)
        Labor Cost = wage * T(v) = wage * N / v
        Total Cost C(v) = N * [ price * k1 * v^2 + (price * k2 + wage) / v ]
        """
        v = sp.Symbol('v', positive=True, real=True)
        N, k1, k2, ce, W = sp.symbols('N k1 k2 c_e W', positive=True, real=True)

        total_cost = N * (ce * k1 * (v**2) + (ce * k2 + W) / v)
        d_cost_dv = sp.diff(total_cost, v)

        # Solve dC/dv = 0 => 2 * ce * k1 * v - (ce * k2 + W) / v^2 = 0 => v^3 = (ce * k2 + W) / (2 * ce * k1)
        solutions = sp.solve(d_cost_dv, v)
        opt_speed_formula = solutions[0] if solutions else None

        subs_dict = {N: units_batch, k1: k1_energy, k2: k2_idle, ce: energy_price, W: labor_wage}
        opt_v = float(opt_speed_formula.evalf(subs=subs_dict)) if opt_speed_formula else 0.0
        min_cost = float(total_cost.evalf(subs={**subs_dict, v: opt_v}))

        return {
            "speed_formula_latex": sp.latex(opt_speed_formula),
            "derivative_latex": sp.latex(d_cost_dv),
            "optimal_speed_rpm": round(opt_v, 2),
            "minimized_batch_cost": round(min_cost, 2),
            "cycle_time_hours": round(units_batch / opt_v, 2) if opt_v > 0 else 0
        }

    @classmethod
    def calculate_cumulative_production_integral(cls, max_rate: float = 120.0,
                                                learning_k: float = 0.4,
                                                shift_hours: float = 8.0) -> Dict[str, Any]:
        """
        Symbolic definite integration over time-dependent throughput learning curve:
        Rate function: P(t) = P_max * (1 - exp(-k * t))
        Cumulative Output: Q(T) = Integral_0^T P(t) dt = P_max * [ T + (exp(-k * T) - 1)/k ]
        """
        t = sp.Symbol('t', positive=True, real=True)
        P_max, k, T = sp.symbols('P_{max} k T', positive=True, real=True)

        rate_func = P_max * (1 - sp.exp(-k * t))
        integral_func = sp.integrate(rate_func, (t, 0, T))

        subs_dict = {P_max: max_rate, k: learning_k, T: shift_hours}
        cumulative_units = float(integral_func.evalf(subs=subs_dict))

        return {
            "rate_function_latex": sp.latex(rate_func),
            "integral_formula_latex": sp.latex(integral_func),
            "cumulative_units_produced": round(cumulative_units, 1),
            "shift_hours": shift_hours,
            "average_hourly_rate": round(cumulative_units / shift_hours, 1)
        }
