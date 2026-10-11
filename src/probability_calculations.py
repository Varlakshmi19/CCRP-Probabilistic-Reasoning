"""
Probability calculations for DUCAG and CCRP (Stage 4).

Mathematical formulas implemented from Dong et al. (2024):
  - Equation (1): Event-level weighted causal function factor F_{n;i}
  - Equation (3): Causal-Chains decomposition: UCC + ECC + HCC
  - Equation (4): Elimination of invalid causal chains (discarding UCC)
  - Equation (5): CCRP posterior probability from retained chains divided by N
  - Equation (6): Attack-path probability as product of node probabilities
  - Equation (7): Multi-hypothesis attack-path probability aggregation

This module contains pure mathematical calculations and is kept separate
from graph construction and graph representation.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping, Optional, Sequence, Union


class ProbabilityCalculationError(ValueError):
    """Raised when probability calculations receive invalid numerical inputs."""


def validate_unit_interval(value: float, name: str = "probability") -> float:
    """Ensure a numerical value is within the standard probability interval [0, 1]."""
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:
        raise ProbabilityCalculationError(
            f"{name} must be a numeric value, got {value!r}"
        ) from exc
    if not 0.0 <= v <= 1.0:
        raise ProbabilityCalculationError(
            f"{name} must lie in [0.0, 1.0], got {v}"
        )
    return v


def compute_edge_factor(
    r_local: float,
    r_sum: float,
    transition_probability: float,
) -> float:
    """
    Compute weighted function variable factor F_{n;i} (Equation 1).

    Mathematical definition (Dong et al., 2024, Eq. 1):
        F_{n;i} = (r_{n;i} / r_n) * A_{n;i}
    where:
        r_{n;i} > 0 is the causal association degree of parent i on child n
        r_n = sum_p r_{n;p} is the sum of associations from all parents
        A_{n;i} is the transition probability parameter in [0, 1]

    Parameters
    ----------
    r_local:
        Association degree r_{n;i} between parent i and child n. Must be > 0.
    r_sum:
        Total parent association sum r_n for child n. Must be >= r_local > 0.
    transition_probability:
        Parameter A_{n;i} in [0, 1].

    Returns
    -------
    float:
        Weighted edge factor F_{n;i} in [0, 1].
    """
    if r_local <= 0:
        raise ProbabilityCalculationError(f"r_local must be > 0, got {r_local}")
    if r_sum <= 0:
        raise ProbabilityCalculationError(f"r_sum must be > 0, got {r_sum}")
    if r_local > r_sum + 1e-9:
        raise ProbabilityCalculationError(
            f"r_local ({r_local}) cannot exceed r_sum ({r_sum})"
        )
    a = validate_unit_interval(transition_probability, "transition_probability")
    normalized_r = r_local / r_sum
    factor = normalized_r * a
    return float(factor)


def evaluate_chain_product(
    edge_factors: Sequence[float],
    start_prior: float = 1.0,
) -> float:
    """
    Calculate the cumulative probability value along a causal chain.

    The chain value is the product of the starting event prior (hypothesis prior
    or evidence state) and the weighted edge factors F along the chain:
        Value = Prior * prod_{hop} F_{hop}

    Parameters
    ----------
    edge_factors:
        Sequence of F factors along the chain hops.
    start_prior:
        Prior probability of the initial node (defaults to 1.0).

    Returns
    -------
    float:
        Cumulative chain value in [0, 1].
    """
    prior = validate_unit_interval(start_prior, "start_prior")
    product = prior
    for idx, f in enumerate(edge_factors):
        val = validate_unit_interval(f, f"edge_factor[{idx}]")
        product *= val
    return float(product)


def sum_all_chains(
    ucc_values: Sequence[float],
    ecc_values: Sequence[float],
    hcc_values: Sequence[float],
) -> float:
    """
    Sum all causal chain categories according to Equation (3).

    Mathematical definition (Dong et al., 2024, Eq. 3):
        Causal-Chains(X_v) = sum UCC(X_v) + sum ECC(X_v) + sum HCC(X_v)
    where:
        UCC = Unknown Causal Chains (neither evidence nor hypothesis)
        ECC = Evidence Causal Chains (contains observed evidence)
        HCC = Hypothesis Causal Chains (contains root hypothesis)

    Returns
    -------
    float:
        Total sum of all chain values.
    """
    total = sum(ucc_values) + sum(ecc_values) + sum(hcc_values)
    return float(total)


def eliminate_ucc_chains(
    ecc_values: Sequence[float],
    hcc_values: Sequence[float],
) -> float:
    """
    Calculate retained chain sum after eliminating UCC (Equation 4).

    Mathematical definition (Dong et al., 2024, Eq. 4):
        Causal-Chains(X_v)* = sum ECC(X_v) + sum HCC(X_v)
    Invalid chains (UCC) are discarded as redundant for posterior calculation.

    Returns
    -------
    float:
        Sum of retained ECC and HCC values.
    """
    total = sum(ecc_values) + sum(hcc_values)
    return float(total)


def calculate_ccrp_posterior(
    retained_chain_sum: float,
    n: int,
    *,
    is_evidence: bool = False,
    is_hypothesis: bool = False,
    hypothesis_prior: Optional[float] = None,
) -> float:
    """
    Calculate node posterior probability using Equation (5).

    Mathematical definition (Dong et al., 2024, Eq. 5):
        Pr(X_v) = Causal-Chains(X_v)* / N
                = (sum ECC(X_v) + sum HCC(X_v)) / N

    Definition of N (Dong et al., 2024):
        "where N is the sum of all distinct evidence nodes and hypotheses in
        the causal chains associated with the current node."

    Special node rules established in paper (Table 3):
        - Observed evidence alarm nodes have state fixed to 1 -> Pr(E) = 1.0.
        - Root hypothesis nodes retain their prior / evaluated hypothesis state -> Pr(B) = prior.
        - Intermediate nodes divide their retained chain sum by N.
        - When N == 0 (no causal chains retained), posterior is 0.0.

    Parameters
    ----------
    retained_chain_sum:
        Sum of retained ECC and HCC chain values (Causal-Chains(X_v)*).
    n:
        Total count of distinct evidence nodes and hypotheses in retained chains.
    is_evidence:
        Whether the node is an observed evidence node.
    is_hypothesis:
        Whether the node is a root hypothesis node.
    hypothesis_prior:
        Prior probability for hypothesis nodes (defaults to 1.0 if not specified).

    Returns
    -------
    float:
        Calculated posterior probability in [0, 1].
    """
    if is_evidence:
        return 1.0

    if is_hypothesis:
        if hypothesis_prior is not None:
            return validate_unit_interval(hypothesis_prior, "hypothesis_prior")
        return 1.0

    if n < 0:
        raise ProbabilityCalculationError(f"N must be non-negative, got {n}")

    if n == 0:
        # No distinct evidence or hypothesis in chains -> no retained influence
        return 0.0

    if retained_chain_sum < 0:
        raise ProbabilityCalculationError(
            f"retained_chain_sum cannot be negative, got {retained_chain_sum}"
        )

    posterior = retained_chain_sum / float(n)
    # Clamp to [0, 1] against minor floating point overflow
    clamped = max(0.0, min(1.0, posterior))
    return float(clamped)


def calculate_attack_path_probability(
    node_probabilities: Sequence[float],
) -> float:
    """
    Calculate candidate attack-path probability (Equation 6).

    Mathematical definition (Dong et al., 2024, Eq. 6):
        Pr(AttackSeq_i) = Pr(B_i) * Pr(S_1) * Pr(V_1) * ... * Pr(S_k) * Pr(V_k)

    The probability of a candidate attack sequence under hypothesis B_i is
    the product of node probabilities along the path.

    Parameters
    ----------
    node_probabilities:
        Sequence of posterior probabilities of nodes forming the attack path.

    Returns
    -------
    float:
        Path probability product in [0, 1].
    """
    if not node_probabilities:
        raise ProbabilityCalculationError("node_probabilities sequence cannot be empty")

    prod = 1.0
    for idx, p in enumerate(node_probabilities):
        val = validate_unit_interval(p, f"node_probabilities[{idx}]")
        prod *= val
    return float(prod)


def aggregate_hypothesis_path_probabilities(
    path_probabilities: Sequence[float],
) -> float:
    """
    Aggregate attack-path probabilities across hypotheses (Equation 7).

    Mathematical definition (Dong et al., 2024, Eq. 7):
        Pr(AttackSeq_i)* = sum_{hypotheses} Pr(AttackSeq_i under hypothesis)

    When the same path appears under multiple root hypotheses, sum the
    candidate path probabilities before normalization.

    Parameters
    ----------
    path_probabilities:
        Probabilities of the path under each applicable hypothesis.

    Returns
    -------
    float:
        Aggregated unnormalized path probability.
    """
    if not path_probabilities:
        raise ProbabilityCalculationError("path_probabilities cannot be empty")
    for idx, p in enumerate(path_probabilities):
        if p < 0:
            raise ProbabilityCalculationError(
                f"path_probabilities[{idx}] cannot be negative, got {p}"
            )
    return float(sum(path_probabilities))


def normalize_probabilities(
    probabilities: Sequence[float],
) -> list[float]:
    """
    Normalize a list of positive probabilities so they sum to 1.0.

    Mathematical step (Dong et al., 2024, Step 4 / worked example):
        Pr_normalized(i) = Pr(i) / sum_j Pr(j)

    Parameters
    ----------
    probabilities:
        Sequence of non-negative probabilities.

    Returns
    -------
    list[float]:
        Normalized probabilities summing to 1.0.
    """
    if not probabilities:
        raise ProbabilityCalculationError("Cannot normalize an empty list of probabilities")

    for idx, p in enumerate(probabilities):
        if p < 0:
            raise ProbabilityCalculationError(
                f"Cannot normalize negative value at index {idx}: {p}"
            )

    total = sum(probabilities)
    if total <= 0:
        raise ProbabilityCalculationError(
            f"Cannot normalize probabilities with zero sum: {probabilities}"
        )

    return [float(p / total) for p in probabilities]
