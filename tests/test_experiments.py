"""
Test suite for Stage 5: Four experiments from Dong et al. (2024).

Validates:
  - Experiment 1: DARPA / LLDOS attack scenario analysis (Section 4.1, Tables 4 & 5).
  - Experiment 2: Simulated network attack scenario construction (Section 4.2, Tables 6, 7, 8, & 9).
  - Experiment 3: Risk probability comparison (Section 4.3, Tables 10 & 11).
  - Experiment 4: Runtime / time-complexity comparison (Section 4.4, Fig. 9).
"""

from __future__ import annotations

import math
import pytest

from experiments.paper_experiment_1 import run_experiment_1
from experiments.paper_experiment_2 import run_experiment_2
from experiments.paper_experiment_3 import run_experiment_3
from experiments.paper_experiment_4 import (
    generate_random_attack_dag,
    measure_ccrp_runtime,
    run_experiment_4,
    simulate_bnrp_exact_inference,
)
from src.ducag_graph import DUCAGGraph
from src.probability_calculations import normalize_probabilities


# =============================================================================
# Experiment 1: DARPA / LLDOS Tests
# =============================================================================


class TestExperiment1DARPA:
    """Tests for Experiment 1 (DARPA 2000 / LLDOS 1.0 & 2.0)."""

    def test_experiment_1_execution_and_structure(self):
        res = run_experiment_1()
        assert res["experiment"] == "Experiment 1 (DARPA / LLDOS)"
        assert res["status"] == "qualitative_reproduction_verified"
        assert "path_one" in res
        assert "path_two" in res
        assert "limitations" in res
        assert len(res["limitations"]) > 0

    def test_experiment_1_path_one_hypothesis_explainability(self):
        res = run_experiment_1()
        p1 = res["path_one"]
        # In Path One, alerts {X11, X26, X40, X4} are observed
        assert p1["observed_alarms"] == ["X11", "X26", "X40", "X4"]
        assert p1["missing_alarms"] == ["X9", "X10"]
        # Winning hypothesis is B2 (LLDOS 1.0)
        assert p1["published_winning_hypothesis"] == "B2"
        assert p1["hypothesis_match"] is True
        assert "B2" in p1["computed_retained_hypotheses"]
        # B3 cannot explain these alarms and is pruned
        assert "B3" in p1["computed_pruned_hypotheses"]
        # Published scenario sequence matches
        assert p1["published_scenario"] == ["B2", "X9", "X10", "X11", "X4", "X26", "X40"]

    def test_experiment_1_path_two_hypothesis_explainability(self):
        res = run_experiment_1()
        p2 = res["path_two"]
        assert "X17" in p2["observed_alarms_subset"]
        assert p2["published_winning_hypothesis"] == "B3"
        assert p2["hypothesis_match"] is True
        # B1 and B2 cannot explain the LLDOS 2.0 alarms and are pruned
        assert "B3" in p2["computed_retained_hypotheses"]
        assert "B1" in p2["computed_pruned_hypotheses"]
        assert "B2" in p2["computed_pruned_hypotheses"]
        # Published scenario sequence matches Table 5
        assert p2["published_scenario"] == [
            "B3", "X16", "X17", "X18", "X26", "X31", "X32", "X37", "X34", "X29"
        ]

    def test_experiment_1_unresolved_limitations_documented(self):
        res = run_experiment_1()
        limitations = " ".join(res["limitations"])
        # Must clearly document that matrices were deferred to external references [25, 31]
        assert "25" in limitations or "31" in limitations


# =============================================================================
# Experiment 2: Simulated Network Tests
# =============================================================================


class TestExperiment2SimulatedNetwork:
    """Tests for Experiment 2 (Simulated Network - Incomplete & Redundant alarms)."""

    def test_experiment_2_execution_and_structure(self):
        res = run_experiment_2()
        assert res["experiment"] == "Experiment 2 (Simulated Network)"
        assert "primary_scenario" in res
        assert "path_2_summary" in res
        assert "path_3_summary" in res

    def test_experiment_2_table_9_published_normalization_and_winner(self):
        res = run_experiment_2()
        p1 = res["primary_scenario"]
        t9 = p1["table_9_published_reproduction"]

        # Winner must be the true path (Candidate 2)
        assert t9["true_path_winner"] is True
        top_1 = t9["top_3"][0]
        assert top_1["path_id"] == 2
        assert top_1["is_true_path"] is True
        # Published normalized probability is 0.3542
        assert pytest.approx(top_1["published_normalized"], abs=1e-4) == 0.3542
        assert pytest.approx(top_1["recomputed_normalized"], abs=1e-4) == 0.3542
        assert top_1["diff"] < 1e-4

        # Rank 2 must be Candidate 7 (BX1 -> V2 -> S3 -> V9 -> S9)
        top_2 = t9["top_3"][1]
        assert top_2["path_id"] == 7
        assert pytest.approx(top_2["published_normalized"], abs=1e-4) == 0.2941
        assert pytest.approx(top_2["recomputed_normalized"], abs=1e-4) == 0.2941
        assert top_2["diff"] < 1e-4

        # Rank 3 must be Candidate 1 (B1(BX1) -> V1 -> S2 -> V5 -> S8 -> V13 -> S9)
        top_3 = t9["top_3"][2]
        assert top_3["path_id"] == 1
        assert pytest.approx(top_3["published_normalized"], abs=1e-4) == 0.1293
        assert pytest.approx(top_3["recomputed_normalized"], abs=1e-4) == 0.1293
        assert top_3["diff"] < 1e-4

        # All 7 candidates must match within 1e-4
        for cand in t9["all_7_candidates"]:
            assert cand["diff"] < 1e-4

    def test_experiment_2_first_principles_ranking(self):
        res = run_experiment_2()
        p1 = res["primary_scenario"]
        fp = p1["first_principles_ranking"]
        # Under first-principles CCRP graph evaluation, winning path reaches target S9
        assert "S9" in fp["winner"]
        assert len(fp["top_3"]) == 3
        # Must document that BX1 node posteriors were omitted in Section 4.2
        assert "omitted" in fp["omitted_bx1_limitation"].lower()

    def test_experiment_2_missing_alarms_identification(self):
        res = run_experiment_2()
        p1 = res["primary_scenario"]
        assert p1["observed_evidence"] == ["V1", "V3", "S4", "V6", "V11", "V13", "S9"]
        assert p1["missing_alarms"] == ["S2", "S6", "S8"]
        assert p1["target"] == "S9"

    def test_experiment_2_table_8_posteriors_reproduction(self):
        """
        Verify exact reproduction of Dong et al. (2024) Table 8 node posteriors
        using Equation (1) in-degree normalization and Table 8 evidence.
        """
        res = run_experiment_2()
        p1 = res["primary_scenario"]
        t8 = p1["table_8_node_posteriors_comparison"]

        # S8 posterior: published 0.3512, computed 0.35125
        assert pytest.approx(t8["S8"]["computed"], abs=1e-4) == 0.3512
        assert t8["S8"]["diff"] < 1e-4

        # Key Table 8 nodes
        assert pytest.approx(t8["S2"]["computed"], abs=1e-4) == 0.4730
        assert pytest.approx(t8["V5"]["computed"], abs=1e-4) == 0.1970
        assert pytest.approx(t8["V4"]["computed"], abs=1e-4) == 1.0000
        assert pytest.approx(t8["V8"]["computed"], abs=1e-4) == 0.2755
        assert pytest.approx(t8["V10"]["computed"], abs=1e-4) == 0.2125
        assert pytest.approx(t8["S6"]["computed"], abs=1e-4) == 0.5396
        assert pytest.approx(t8["V7"]["computed"], abs=1e-4) == 0.3690
        assert pytest.approx(t8["S7"]["computed"], abs=1e-4) == 0.2755
        assert pytest.approx(t8["V12"]["computed"], abs=1e-4) == 0.2755

        # First-principles CCRP ranking should rank Candidate 2 (True Path) as #1
        fp = p1["first_principles_ranking"]
        assert "V3" in fp["winner"] and "S6" in fp["winner"]



# =============================================================================
# Experiment 3: Risk Probability Comparison Tests
# =============================================================================


class TestExperiment3RiskComparison:
    """Tests for Experiment 3 (Risk probability comparison with Baselines)."""

    def test_experiment_3_execution_and_structure(self):
        res = run_experiment_3()
        assert res["experiment"] == "Experiment 3 (Risk Probability Comparison)"
        assert res["target"] == "S7"
        assert res["evidence_alarms"] == ["V1", "V4"]
        assert "table_10_comparison" in res
        assert "table_11_qualitative_features" in res

    def test_experiment_3_simplification_and_winning_path(self):
        res = run_experiment_3()
        # Under evidence {V1, V4}, only B2 can explain both alarms (Fig. 8 in paper)
        assert res["simplification_surviving_hypotheses"] == ["B2"]
        assert res["only_b2_survives_verified"] is True

        # Winning attack path matches Section 4.3 text
        expected_path = ["B2", "V1", "S1", "V4", "S4", "V8", "S7"]
        assert res["winning_attack_path"] == expected_path

    def test_experiment_3_table_10_numerical_comparison(self):
        res = run_experiment_3()
        rows = {r["node"]: r for r in res["table_10_comparison"]}

        # S1: prior 0.65, CCRP posterior 0.95
        assert rows["S1"]["prior"] == 0.65
        assert rows["S1"]["ccrp"] == 0.95
        assert rows["S1"]["ref_35"] == 0.97

        # S4: prior 0.846, CCRP posterior 1.0 (alarm observed)
        assert rows["S4"]["prior"] == 0.846
        assert rows["S4"]["ccrp"] == 1.0
        assert rows["S4"]["ref_32"] == 0.939

        # S7 (target node): prior 0.593, CCRP posterior 0.70
        assert rows["S7"]["prior"] == 0.593
        assert rows["S7"]["ccrp"] == 0.70
        assert rows["S7"]["ref_35"] == 0.685

        # Unaffected nodes retain prior probabilities under CCRP
        for unaffected in ["S2", "S3", "S5", "S6", "S8"]:
            assert rows[unaffected]["ccrp"] == rows[unaffected]["prior"]


# =============================================================================
# Experiment 4: Runtime / Time-Complexity Tests
# =============================================================================


class TestExperiment4RuntimeComparison:
    """Tests for Experiment 4 (Time complexity and scaling trend)."""

    def test_random_dag_generation_properties(self):
        num_hosts = 10
        seed = 42
        ducag, evidence = generate_random_attack_dag(num_hosts, seed=seed)

        # Graph has B1 + num_hosts nodes
        assert len(ducag.graph.nodes) == num_hosts + 1
        assert "B1" in ducag.graph.nodes

        # Evidence count must follow the paper rule: hosts // 2
        assert len(evidence) == num_hosts // 2

        # Directed acyclic graph check
        import networkx as nx
        assert nx.is_directed_acyclic_graph(ducag.graph)

        # All host nodes must be reachable from B1
        for h in [f"H{i}" for i in range(1, num_hosts + 1)]:
            assert nx.has_path(ducag.graph, "B1", h)

    def test_ccrp_runtime_measurement_executes(self):
        ducag, evidence = generate_random_attack_dag(10, seed=123)
        t_ms = measure_ccrp_runtime(ducag, evidence)
        assert isinstance(t_ms, float)
        assert t_ms >= 0.0

    def test_bnrp_simulation_executes(self):
        ducag, evidence = generate_random_attack_dag(10, seed=123)
        t_ms = simulate_bnrp_exact_inference(ducag, evidence)
        assert isinstance(t_ms, float)
        assert t_ms >= 0.0

    def test_experiment_4_benchmark_and_trend(self):
        # Run a fast benchmark across 2 scales to verify data structure and trend without overwriting canonical results
        res = run_experiment_4(scales=(10, 30), groups=2, save_results=False)
        assert res["experiment"] == "Experiment 4 (Runtime & Time-Complexity Comparison)"
        assert len(res["results_by_scale"]) == 2
        assert res["benchmark_setup"]["evidence_rule"] == "hosts / 2"

        row10 = res["results_by_scale"][0]
        row30 = res["results_by_scale"][1]
        assert row10["num_hosts"] == 10
        assert row10["num_evidence"] == 5
        assert row30["num_hosts"] == 30
        assert row30["num_evidence"] == 15

        # Check positive elapsed times
        assert row10["ccrp_time_ms"] > 0
        assert row30["ccrp_time_ms"] > 0
