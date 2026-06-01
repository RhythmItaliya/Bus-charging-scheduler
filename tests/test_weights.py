import copy
import pytest
from dataclasses import replace

from scheduler.engine import schedule
from scheduler.loader import load_scenario
from scheduler.model import Weights


class TestWeightSensitivity:

    def _get_scenario4_with_operator_weight(self, operator_weight: float):
        scenario = load_scenario("data/scenarios/scenario_4.json")
        new_weights = Weights(
            individual=scenario.weights.individual,
            operator=operator_weight,
            overall=scenario.weights.overall,
            extra=scenario.weights.extra,
        )
        return replace(scenario, weights=new_weights)

    def test_operator_weight_1_vs_2_produces_different_operator_breakdown(self):
        scenario_w1 = self._get_scenario4_with_operator_weight(1.0)
        scenario_w2 = self._get_scenario4_with_operator_weight(2.0)

        result_w1 = schedule(scenario_w1)
        result_w2 = schedule(scenario_w2)

        op_score_w1 = result_w1.objective_breakdown.get("OperatorRule", 0)
        op_score_w2 = result_w2.objective_breakdown.get("OperatorRule", 0)


        assert op_score_w1 != op_score_w2, (
            f"Operator breakdown did not change: w=1.0 → {op_score_w1}, "
            f"w=2.0 → {op_score_w2}. Weight must influence the schedule."
        )

    def test_operator_weight_1_vs_2_produces_different_objective_score(self):
        scenario_w1 = self._get_scenario4_with_operator_weight(1.0)
        scenario_w2 = self._get_scenario4_with_operator_weight(2.0)

        result_w1 = schedule(scenario_w1)
        result_w2 = schedule(scenario_w2)

        op_score_w1 = result_w1.objective_breakdown.get("OperatorRule", 0)
        op_score_w2 = result_w2.objective_breakdown.get("OperatorRule", 0)
        total_w1 = result_w1.total_objective
        total_w2 = result_w2.total_objective


        assert op_score_w1 != op_score_w2, (
            f"OperatorRule penalty did not change: w=1.0 → {op_score_w1}, "
            f"w=2.0 → {op_score_w2}. The weight multiplier is not being applied."
        )

        assert total_w1 != total_w2, (
            f"Total objective did not change: w=1.0 → {total_w1}, w=2.0 → {total_w2}."
        )


        assert abs(op_score_w2 - 2 * op_score_w1) < 1e-6, (
            f"OperatorRule penalty at w=2.0 ({op_score_w2:.2f}) is not double "
            f"that at w=1.0 ({op_score_w1:.2f}). Expected {2*op_score_w1:.2f}."
        )

    def test_higher_operator_weight_reduces_operator_variance(self):
        scenario_w1 = self._get_scenario4_with_operator_weight(1.0)
        scenario_w2 = self._get_scenario4_with_operator_weight(2.0)

        result_w1 = schedule(scenario_w1)
        result_w2 = schedule(scenario_w2)

        import statistics

        def _fleet_variance(result, scenario):
            op_waits = {}
            for bp in result.bus_plans:
                op_waits.setdefault(bp.operator, []).append(bp.total_wait)
            total_var = sum(
                statistics.variance(ws) if len(ws) > 1 else 0.0
                for ws in op_waits.values()
            )
            return total_var

        var_w1 = _fleet_variance(result_w1, scenario_w1)
        var_w2 = _fleet_variance(result_w2, scenario_w2)


        assert var_w2 <= var_w1 + 1e-6, (
            f"Higher operator weight did not reduce within-fleet variance: "
            f"var@w=1.0={var_w1:.2f}, var@w=2.0={var_w2:.2f}. "
            f"The operator rule may not be steering plan selection correctly."
        )

    def test_individual_weight_change_affects_individual_term(self):
        scenario = load_scenario("data/scenarios/scenario_1.json")
        weights_hi = Weights(individual=3.0, operator=1.0, overall=1.0)
        weights_lo = Weights(individual=1.0, operator=1.0, overall=1.0)
        s_hi = replace(scenario, weights=weights_hi)
        s_lo = replace(scenario, weights=weights_lo)

        r_hi = schedule(s_hi)
        r_lo = schedule(s_lo)

        ind_hi = r_hi.objective_breakdown.get("IndividualWaitRule", 0)
        ind_lo = r_lo.objective_breakdown.get("IndividualWaitRule", 0)


        if ind_lo > 0:
            assert ind_hi != ind_lo, "Individual weight change had no effect"
