"""
Causal Chain-based Risk Probability Calculation (CCRP) algorithm (Stage 4).

Implements the three CCRP steps from Dong et al. (2024):
  Step 1: Expand causal chains (upward and backward to root/evidence/terminal)
  Step 2: Classify chains as UCC, ECC, and HCC (Equation 3)
          and eliminate invalid chains UCC (Equation 4)
  Step 3: Calculate posterior probabilities from retained chains (Equation 5)

References:
  - Dong, Feng, & Shang (2024), Journal of Cloud Computing, 13:24.
  - Section 3 of docs/paper_algorithm_mapping.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence, Union

from .ducag_graph import DUCAGGraph, DUCAGValidationError
from .graph_simplification import list_hypothesis_nodes
from .probability_calculations import (
    ProbabilityCalculationError,
    calculate_ccrp_posterior,
    compute_edge_factor,
    eliminate_ucc_chains,
    evaluate_chain_product,
    sum_all_chains,
    validate_unit_interval,
)

CHAIN_TYPE_UCC = "UCC"  # Unknown Causal Chain (neither evidence nor hypothesis)
CHAIN_TYPE_ECC = "ECC"  # Evidence Causal Chain (includes observed evidence)
CHAIN_TYPE_HCC = "HCC"  # Hypothesis Causal Chain (includes root hypothesis)


class CCRPError(ValueError):
    """Raised when CCRP inputs or chain expansions are invalid."""


@dataclass(frozen=True)
class CausalChain:
    """
    An elementary causal chain associated with a concerned node X_v.

    Attributes
    ----------
    node_id:
        The concerned node X_v being evaluated.
    direction:
        'upstream' (incoming into X_v) or 'downstream' (outgoing from X_v).
    path:
        Ordered tuple of node IDs in the chain.
    chain_type:
        'UCC', 'ECC', or 'HCC' according to Eq. (3).
    terminal_node:
        The boundary node reached (root cause, evidence, or sink).
    associated_hypothesis:
        Root hypothesis ID if this is an HCC, else None.
    associated_evidence:
        Evidence node ID if this is an ECC, else None.
    edge_factors:
        Tuple of weighted transition factors F along the chain hops.
    chain_value:
        Calculated product of starting prior and edge factors.
    """

    node_id: str
    direction: str
    path: tuple[str, ...]
    chain_type: str
    terminal_node: str
    associated_hypothesis: Optional[str]
    associated_evidence: Optional[str]
    edge_factors: tuple[float, ...]
    chain_value: float


@dataclass
class NodeCCRPResult:
    """
    Transparent calculation result for a single node under CCRP reasoning.
    """

    node_id: str
    is_evidence: bool
    is_hypothesis: bool
    all_chains: list[CausalChain] = field(default_factory=list)
    retained_chains: list[CausalChain] = field(default_factory=list)
    discarded_chains: list[CausalChain] = field(default_factory=list)
    distinct_hypotheses: list[str] = field(default_factory=list)
    distinct_evidence: list[str] = field(default_factory=list)
    n_value: int = 0
    retained_sum: float = 0.0
    posterior: float = 0.0
    calculation_log: dict[str, Any] = field(default_factory=dict)


@dataclass
class CCRPResult:
    """
    Complete outcome of CCRP algorithm on a DUCAG graph.
    """

    graph_name: str
    evidence: list[str]
    hypothesis: Optional[str]
    node_results: dict[str, NodeCCRPResult] = field(default_factory=dict)
    posteriors: dict[str, float] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        return {
            "graph_name": self.graph_name,
            "evidence": list(self.evidence),
            "hypothesis": self.hypothesis,
            "posteriors": dict(self.posteriors),
            "node_details": {
                node: {
                    "is_evidence": res.is_evidence,
                    "is_hypothesis": res.is_hypothesis,
                    "n_value": res.n_value,
                    "distinct_hypotheses": res.distinct_hypotheses,
                    "distinct_evidence": res.distinct_evidence,
                    "retained_sum": res.retained_sum,
                    "posterior": res.posterior,
                    "retained_chains": [
                        {
                            "type": c.chain_type,
                            "path": list(c.path),
                            "direction": c.direction,
                            "value": c.chain_value,
                        }
                        for c in res.retained_chains
                    ],
                    "discarded_chains": [
                        {
                            "type": c.chain_type,
                            "path": list(c.path),
                            "direction": c.direction,
                            "value": c.chain_value,
                        }
                        for c in res.discarded_chains
                    ],
                }
                for node, res in self.node_results.items()
            },
        }


def _get_edge_factor(ducag: DUCAGGraph, source: str, target: str) -> float:
    """
    Extract causal transition parameter A along directed edge source -> target.

    In the paper's chain expressions (Table 3, Table 8), chain products are formed
    from edge transition parameters A_{target;source}. Weighting across multiple
    chains is performed via division by N in Equation (5).
    """
    data = ducag.graph.edges[source, target]
    tp = data.get("transition_probability")
    if tp is None:
        raise CCRPError(
            f"Edge {source}->{target} has no scalar transition_probability."
        )
    return validate_unit_interval(
        float(tp), f"transition_probability on {source}->{target}"
    )


def expand_upstream_chains(
    ducag: DUCAGGraph,
    node_id: str,
    evidence_set: set[str],
    hypothesis_set: set[str],
    priors: Mapping[str, float],
) -> list[CausalChain]:
    """
    Expand causal chains upward (incoming into node_id).

    Stopping condition:
      Stops when reaching:
        - a root-cause hypothesis node (B / BX) -> classified as HCC
        - an observed evidence node -> classified as ECC
        - a node with in_degree == 0 (root source) -> classified as UCC
    """
    chains: list[CausalChain] = []
    g = ducag.graph

    def _dfs_upstream(curr: str, path_suffix: list[str]) -> None:
        preds = sorted(g.predecessors(curr))
        for p in preds:
            if p in path_suffix:
                # Cycle prevention
                continue
            full_path = [p] + path_suffix
            is_hyp = p in hypothesis_set
            is_evi = p in evidence_set
            is_root = g.in_degree(p) == 0

            if is_hyp or is_evi or is_root:
                # Terminal boundary reached; compute edge factors
                factors = tuple(
                    _get_edge_factor(ducag, full_path[i], full_path[i + 1])
                    for i in range(len(full_path) - 1)
                )
                if is_evi:
                    chain_type = CHAIN_TYPE_ECC
                    assoc_evi: Optional[str] = p
                    assoc_hyp: Optional[str] = None
                    prior = 1.0
                elif is_hyp:
                    chain_type = CHAIN_TYPE_HCC
                    assoc_evi = None
                    assoc_hyp = p
                    prior = priors.get(p, 1.0)
                else:
                    chain_type = CHAIN_TYPE_UCC
                    assoc_evi = None
                    assoc_hyp = None
                    prior = 1.0

                val = evaluate_chain_product(factors, prior)
                chains.append(
                    CausalChain(
                        node_id=node_id,
                        direction="upstream",
                        path=tuple(full_path),
                        chain_type=chain_type,
                        terminal_node=p,
                        associated_hypothesis=assoc_hyp,
                        associated_evidence=assoc_evi,
                        edge_factors=factors,
                        chain_value=val,
                    )
                )
            else:
                _dfs_upstream(p, full_path)

    _dfs_upstream(node_id, [node_id])
    return chains


def expand_downstream_chains(
    ducag: DUCAGGraph,
    node_id: str,
    evidence_set: set[str],
    hypothesis_set: set[str],
) -> list[CausalChain]:
    """
    Expand causal chains backward/downstream (outgoing from node_id).

    Stopping condition:
      Stops when reaching:
        - an observed evidence node -> classified as ECC
        - a terminal node with out_degree == 0 -> classified as UCC
    """
    chains: list[CausalChain] = []
    g = ducag.graph

    def _dfs_downstream(curr: str, path_prefix: list[str]) -> None:
        succs = sorted(g.successors(curr))
        for c in succs:
            if c in path_prefix:
                # Cycle prevention
                continue
            full_path = path_prefix + [c]
            is_evi = c in evidence_set
            is_sink = g.out_degree(c) == 0

            if is_evi or is_sink:
                factors = tuple(
                    _get_edge_factor(ducag, full_path[i], full_path[i + 1])
                    for i in range(len(full_path) - 1)
                )
                if is_evi:
                    chain_type = CHAIN_TYPE_ECC
                    assoc_evi: Optional[str] = c
                    assoc_hyp: Optional[str] = None
                    # Downstream chain to evidence has terminal evidence state 1.0
                    val = evaluate_chain_product(factors, 1.0)
                else:
                    chain_type = CHAIN_TYPE_UCC
                    assoc_evi = None
                    assoc_hyp = None
                    val = evaluate_chain_product(factors, 1.0)

                chains.append(
                    CausalChain(
                        node_id=node_id,
                        direction="downstream",
                        path=tuple(full_path),
                        chain_type=chain_type,
                        terminal_node=c,
                        associated_hypothesis=assoc_hyp,
                        associated_evidence=assoc_evi,
                        edge_factors=factors,
                        chain_value=val,
                    )
                )
            else:
                _dfs_downstream(c, full_path)

    _dfs_downstream(node_id, [node_id])
    return chains


def expand_causal_chains(
    ducag: DUCAGGraph,
    node_id: str,
    evidence: Sequence[str],
    hypothesis: Optional[str] = None,
    priors: Optional[Mapping[str, float]] = None,
) -> list[CausalChain]:
    """
    Perform Step 1 of CCRP: expand causal chains upward and backward.

    Parameters
    ----------
    ducag:
        The DUCAG graph (original or simplified).
    node_id:
        The concerned node X_v being evaluated.
    evidence:
        List of observed evidence nodes.
    hypothesis:
        Optional root hypothesis ID. If specified, only this hypothesis is
        considered as root hypothesis; otherwise all B/BX nodes are considered.
    priors:
        Optional mapping of hypothesis node priors.

    Returns
    -------
    list[CausalChain]:
        List of all expanded causal chains for node_id.
    """
    if node_id not in ducag.graph:
        raise CCRPError(f"Node {node_id!r} not found in graph.")

    evidence_set = set(evidence)
    all_hyps = list_hypothesis_nodes(ducag)
    if hypothesis is not None:
        if hypothesis not in ducag.graph:
            raise CCRPError(f"Specified hypothesis {hypothesis!r} not in graph.")
        hypothesis_set = {hypothesis}
    else:
        hypothesis_set = set(all_hyps)

    prior_map = dict(priors or {})
    for h in hypothesis_set:
        if h not in prior_map:
            # Use prior stored on node, or default 1.0
            node_prior = ducag.graph.nodes[h].get("prior")
            if isinstance(node_prior, dict) and "attack" in node_prior:
                prior_map[h] = float(node_prior["attack"])
            else:
                prior_map[h] = 1.0

    upstream = expand_upstream_chains(ducag, node_id, evidence_set, hypothesis_set, prior_map)
    downstream = expand_downstream_chains(ducag, node_id, evidence_set, hypothesis_set)
    return upstream + downstream


def calculate_node_ccrp(
    ducag: DUCAGGraph,
    node_id: str,
    evidence: Sequence[str],
    hypothesis: Optional[str] = None,
    priors: Optional[Mapping[str, float]] = None,
) -> NodeCCRPResult:
    """
    Calculate the CCRP posterior probability for a single node X_v.

    Follows the paper's three steps:
      1. Expand causal chains (upward & backward)
      2. Classify (Eq. 3) and eliminate UCC (Eq. 4)
      3. Compute posterior = retained_chain_sum / N (Eq. 5)
    """
    if node_id not in ducag.graph:
        raise CCRPError(f"Node {node_id!r} not in graph.")

    evidence_set = set(evidence)
    all_hyps = list_hypothesis_nodes(ducag)
    hyp_set = {hypothesis} if hypothesis is not None else set(all_hyps)
    prior_map = dict(priors or {})

    is_evidence = node_id in evidence_set
    is_hypothesis = node_id in hyp_set

    # Boundary cases established in paper
    if is_evidence:
        return NodeCCRPResult(
            node_id=node_id,
            is_evidence=True,
            is_hypothesis=is_hypothesis,
            posterior=1.0,
            n_value=1,
            retained_sum=1.0,
            calculation_log={
                "node_id": node_id,
                "rule": "Observed alarm event set to state 1 (Dong et al., Table 3)",
                "posterior": 1.0,
            },
        )

    if is_hypothesis:
        prior_val = prior_map.get(node_id, 1.0)
        return NodeCCRPResult(
            node_id=node_id,
            is_evidence=False,
            is_hypothesis=True,
            posterior=prior_val,
            n_value=1,
            retained_sum=prior_val,
            calculation_log={
                "node_id": node_id,
                "rule": "Hypothesis prior probability (Dong et al., Table 3 / Eq. 2)",
                "prior": prior_val,
                "posterior": prior_val,
            },
        )

    # Step 1: Expand chains
    all_chains = expand_causal_chains(
        ducag, node_id, evidence=evidence, hypothesis=hypothesis, priors=priors
    )

    # Step 2: Classify (Eq. 3) and eliminate UCC (Eq. 4)
    retained_chains: list[CausalChain] = []
    discarded_chains: list[CausalChain] = []
    ecc_values: list[float] = []
    hcc_values: list[float] = []
    ucc_values: list[float] = []

    distinct_hypotheses_set: set[str] = set()
    distinct_evidence_set: set[str] = set()

    for c in all_chains:
        if c.chain_type == CHAIN_TYPE_UCC:
            discarded_chains.append(c)
            ucc_values.append(c.chain_value)
        elif c.chain_type == CHAIN_TYPE_ECC:
            retained_chains.append(c)
            ecc_values.append(c.chain_value)
            if c.associated_evidence:
                distinct_evidence_set.add(c.associated_evidence)
        elif c.chain_type == CHAIN_TYPE_HCC:
            retained_chains.append(c)
            hcc_values.append(c.chain_value)
            if c.associated_hypothesis:
                distinct_hypotheses_set.add(c.associated_hypothesis)

    eq_3_all_sum = sum_all_chains(ucc_values, ecc_values, hcc_values)
    eq_4_retained_sum = eliminate_ucc_chains(ecc_values, hcc_values)

    distinct_hyps = sorted(distinct_hypotheses_set)
    distinct_evis = sorted(distinct_evidence_set)
    n_count = len(distinct_hyps) + len(distinct_evis)

    # Step 3: Compute Eq. (5)
    posterior = calculate_ccrp_posterior(
        eq_4_retained_sum,
        n_count,
        is_evidence=False,
        is_hypothesis=False,
    )

    log: dict[str, Any] = {
        "node_id": node_id,
        "equation_3": {
            "name": "Causal-Chains decomposition (Eq. 3)",
            "ucc_count": len(ucc_values),
            "ucc_values": ucc_values,
            "ecc_count": len(ecc_values),
            "ecc_values": ecc_values,
            "hcc_count": len(hcc_values),
            "hcc_values": hcc_values,
            "total_all_chains": eq_3_all_sum,
        },
        "equation_4": {
            "name": "Eliminate invalid chains UCC (Eq. 4)",
            "retained_chain_count": len(retained_chains),
            "retained_chain_sum": eq_4_retained_sum,
        },
        "equation_5": {
            "name": "CCRP posterior probability (Eq. 5)",
            "distinct_hypotheses": distinct_hyps,
            "distinct_evidence": distinct_evis,
            "N": n_count,
            "formula_substitution": (
                f"{eq_4_retained_sum} / {n_count} = {posterior}"
                if n_count > 0
                else "N=0 -> 0.0"
            ),
            "posterior": posterior,
        },
    }

    return NodeCCRPResult(
        node_id=node_id,
        is_evidence=False,
        is_hypothesis=False,
        all_chains=all_chains,
        retained_chains=retained_chains,
        discarded_chains=discarded_chains,
        distinct_hypotheses=distinct_hyps,
        distinct_evidence=distinct_evis,
        n_value=n_count,
        retained_sum=eq_4_retained_sum,
        posterior=posterior,
        calculation_log=log,
    )


def run_ccrp(
    ducag: DUCAGGraph,
    evidence: Sequence[str],
    hypothesis: Optional[str] = None,
    priors: Optional[Mapping[str, float]] = None,
) -> CCRPResult:
    """
    Execute full CCRP posterior probability calculation on a DUCAG graph.

    Parameters
    ----------
    ducag:
        Input DUCAG graph (should usually be the simplified graph).
    evidence:
        Sequence of observed alarm node IDs.
    hypothesis:
        Optional root hypothesis ID (e.g. "B1").
    priors:
        Optional mapping of hypothesis priors.

    Returns
    -------
    CCRPResult:
        Results containing posteriors and calculation logs for all nodes.
    """
    ducag.validate()
    evidence_list = list(dict.fromkeys(evidence))
    for e in evidence_list:
        if e not in ducag.graph:
            raise CCRPError(f"Evidence node {e!r} not in graph.")

    node_results: dict[str, NodeCCRPResult] = {}
    posteriors: dict[str, float] = {}

    for node_id in ducag.graph.nodes:
        res = calculate_node_ccrp(
            ducag,
            node_id,
            evidence=evidence_list,
            hypothesis=hypothesis,
            priors=priors,
        )
        node_results[node_id] = res
        posteriors[node_id] = res.posterior

    return CCRPResult(
        graph_name=ducag.name,
        evidence=evidence_list,
        hypothesis=hypothesis,
        node_results=node_results,
        posteriors=posteriors,
    )
