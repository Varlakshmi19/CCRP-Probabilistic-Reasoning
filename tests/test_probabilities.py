"""Stage 4 unit tests: Probability calculations (Equations 1, 3, 4, 5, 6, 7)."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.probability_calculations import (
    ProbabilityCalculationError,
    aggregate_hypothesis_path_probabilities,
    calculate_attack_path_probability,
    calculate_ccrp_posterior,
    compute_edge_factor,
    eliminate_ucc_chains,
    evaluate_chain_product,
    normalize_probabilities,
    sum_all_chains,
    validate_unit_interval,
)


def test_validate_unit_interval():
    assert validate_unit_interval(0.0) == 0.0
    assert validate_unit_interval(1.0) == 1.0
    assert validate_unit_interval(0.5) == 0.5

    with pytest.raises(ProbabilityCalculationError, match="must lie in \\[0.0, 1.0\\]"):
        validate_unit_interval(-0.01)

    with pytest.raises(ProbabilityCalculationError, match="must lie in \\[0.0, 1.0\\]"):
        validate_unit_interval(1.05)

    with pytest.raises(ProbabilityCalculationError, match="must be a numeric"):
        validate_unit_interval("invalid")


def test_compute_edge_factor_equation_1():
    # Equation 1: F_{n;i} = (r_{n;i} / r_n) * A_{n;i}
    # Single parent: r_local = 1, r_sum = 1, A = 0.845 -> F = 0.845
    assert compute_edge_factor(1.0, 1.0, 0.845) == pytest.approx(0.845)

    # Two parents with r=1 each: r_sum = 2 -> (1/2) * 0.6 = 0.3
    assert compute_edge_factor(1.0, 2.0, 0.6) == pytest.approx(0.3)

    # Rejection of invalid association degrees
    with pytest.raises(ProbabilityCalculationError, match="r_local must be > 0"):
        compute_edge_factor(0.0, 1.0, 0.5)

    with pytest.raises(ProbabilityCalculationError, match="r_sum must be > 0"):
        compute_edge_factor(1.0, 0.0, 0.5)

    with pytest.raises(ProbabilityCalculationError, match="cannot exceed r_sum"):
        compute_edge_factor(2.5, 2.0, 0.5)


def test_evaluate_chain_product():
    # Chain: prior=1.0, hops = [0.845, 1.0, 0.284]
    val = evaluate_chain_product([0.845, 1.0, 0.284], start_prior=1.0)
    assert val == pytest.approx(0.845 * 1.0 * 0.284, rel=1e-5)

    # Chain with custom prior 0.7
    val2 = evaluate_chain_product([0.5, 0.4], start_prior=0.7)
    assert val2 == pytest.approx(0.7 * 0.5 * 0.4, rel=1e-5)

    with pytest.raises(ProbabilityCalculationError):
        evaluate_chain_product([0.5, 1.5])


def test_sum_all_chains_equation_3():
    # Equation 3: Causal-Chains(X_v) = sum UCC + sum ECC + sum HCC
    ucc = [0.284]
    ecc = [0.572]
    hcc = [0.845]
    total = sum_all_chains(ucc, ecc, hcc)
    assert total == pytest.approx(0.284 + 0.572 + 0.845)


def test_eliminate_ucc_chains_equation_4():
    # Equation 4: Causal-Chains(X_v)* = sum ECC + sum HCC
    ecc = [0.572]
    hcc = [0.845]
    retained = eliminate_ucc_chains(ecc, hcc)
    assert retained == pytest.approx(0.572 + 0.845)


def test_calculate_ccrp_posterior_equation_5():
    # Equation 5: Pr(X_v) = (sum ECC + sum HCC) / N
    # V1 in Table 3: ECC=0.572, HCC=0.845, N=2 -> 1.417 / 2 = 0.7085
    retained_sum = 0.845 + 0.572
    n = 2
    post = calculate_ccrp_posterior(retained_sum, n)
    assert post == pytest.approx(0.7085)

    # Evidence node has posterior 1.0
    assert calculate_ccrp_posterior(0.0, 0, is_evidence=True) == 1.0

    # Hypothesis node retains its prior
    assert calculate_ccrp_posterior(0.0, 0, is_hypothesis=True, hypothesis_prior=0.85) == 0.85
    assert calculate_ccrp_posterior(0.0, 0, is_hypothesis=True) == 1.0

    # N = 0 returns 0.0
    assert calculate_ccrp_posterior(0.0, 0) == 0.0

    with pytest.raises(ProbabilityCalculationError, match="N must be non-negative"):
        calculate_ccrp_posterior(1.0, -1)

    with pytest.raises(ProbabilityCalculationError, match="cannot be negative"):
        calculate_ccrp_posterior(-0.5, 2)


def test_calculate_attack_path_probability_equation_6():
    # Equation 6: Pr(AttackSeq) = prod Pr(node)
    nodes = [1.0, 0.7085, 0.7085, 0.23998, 0.23899]
    expected = 1.0 * 0.7085 * 0.7085 * 0.23998 * 0.23899
    computed = calculate_attack_path_probability(nodes)
    assert computed == pytest.approx(expected, rel=1e-5)

    with pytest.raises(ProbabilityCalculationError, match="cannot be empty"):
        calculate_attack_path_probability([])

    with pytest.raises(ProbabilityCalculationError, match="must lie in"):
        calculate_attack_path_probability([0.5, 1.2])


def test_aggregate_hypothesis_path_probabilities_equation_7():
    # Equation 7: sum of path probabilities under multiple hypotheses
    probs = [0.0654, 0.1792]
    total = aggregate_hypothesis_path_probabilities(probs)
    assert total == pytest.approx(0.0654 + 0.1792)

    with pytest.raises(ProbabilityCalculationError, match="cannot be empty"):
        aggregate_hypothesis_path_probabilities([])

    with pytest.raises(ProbabilityCalculationError, match="cannot be negative"):
        aggregate_hypothesis_path_probabilities([0.1, -0.2])


def test_normalize_probabilities():
    # Table 3 normalized path probabilities: 0.5019 and 0.4981
    raw = [0.02878, 0.02856]
    norm = normalize_probabilities(raw)
    assert sum(norm) == pytest.approx(1.0)
    assert norm[0] == pytest.approx(0.5019, abs=1e-4)
    assert norm[1] == pytest.approx(0.4981, abs=1e-4)

    with pytest.raises(ProbabilityCalculationError, match="empty list"):
        normalize_probabilities([])

    with pytest.raises(ProbabilityCalculationError, match="zero sum"):
        normalize_probabilities([0.0, 0.0])
