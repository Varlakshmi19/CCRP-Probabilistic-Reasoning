"""Stage 4 unit tests: CCRP algorithm and Table 3 calibration."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ccrp import (
    CHAIN_TYPE_ECC,
    CHAIN_TYPE_HCC,
    CHAIN_TYPE_UCC,
    CCRPError,
    calculate_node_ccrp,
    expand_causal_chains,
    run_ccrp,
)
from src.ducag_graph import DUCAGGraph, load_ducag_from_json
from src.graph_simplification import simplify_ducag
from src.probability_calculations import (
    calculate_attack_path_probability,
    normalize_probabilities,
)

TABLE2_JSON = ROOT / "experiments" / "paper_data" / "table2_fig1_partial.json"


@pytest.fixture
def table3_calibrated_ducag() -> DUCAGGraph:
    """
    Build the complete Fig. 1 / Table 3 worked example graph.

    Table 2 prints 10 transitions but omits V7->S6.
    The narrative text and Table 3 path calculations explicitly include V7->S6
    with transition probability 1.0 (A_{6;7} = 1.0).
    We add this narrative edge to test exact Table 3 reproduction.
    """
    raw = load_ducag_from_json(TABLE2_JSON)
    # Add narrative edge V7 -> S6
    raw.add_edge("V7", "S6", r=1.0, transition_probability=1.0, description="Narrative Table 3 edge V7->S6")
    return raw


def test_table3_exact_posteriors_calibration(table3_calibrated_ducag):
    """
    Reproduce Table 3 node posteriors from Dong et al. (2024):
      B1  = 1.0
      V1  = 0.7085
      S2  = 0.7085
      V3  = 0.23998
      V4  = 1.0  (evidence)
      S5  = 1.0
      V7  = 0.238
      S6  = 0.23899
    """
    # Simplify under evidence V4 and concerned hypothesis B1
    simp_res = simplify_ducag(
        table3_calibrated_ducag,
        evidence=["V4"],
        concerned_hypotheses=["B1"],
    )
    simplified_g = simp_res.simplified

    # Run CCRP
    ccrp_res = run_ccrp(simplified_g, evidence=["V4"], hypothesis="B1")
    posteriors = ccrp_res.posteriors

    # Exact calibration check against published Table 3 values
    assert posteriors["B1"] == pytest.approx(1.0)
    assert posteriors["V1"] == pytest.approx(0.7085, abs=1e-4)
    assert posteriors["S2"] == pytest.approx(0.7085, abs=1e-4)
    assert posteriors["V3"] == pytest.approx(0.23998, abs=1e-5)
    assert posteriors["V4"] == pytest.approx(1.0)
    assert posteriors["S5"] == pytest.approx(1.0)
    assert posteriors["V7"] == pytest.approx(0.238, abs=1e-4)
    assert posteriors["S6"] == pytest.approx(0.23899, abs=1e-5)


def test_table3_intermediate_causal_chains(table3_calibrated_ducag):
    """
    Verify intermediate chain values, categories, and N values for Table 3:
      - V1: 1 HCC (B1->V1: 0.845), 1 ECC (V1->S2->V4: 0.572), N=2
      - S2: 1 HCC (B1->V1->S2: 0.845), 1 ECC (S2->V4: 0.572), N=2
      - V3: 1 HCC (B1->V1->S2->V3: 0.23998), no ECC, N=1
      - S5: 1 ECC (V4->S5: 1.0), no HCC, N=1
      - V7: 1 ECC (V4->S5->V7: 0.238), no HCC, N=1
      - S6: 1 HCC (0.23998), 1 ECC (0.238), N=2
    """
    simp_res = simplify_ducag(
        table3_calibrated_ducag,
        evidence=["V4"],
        concerned_hypotheses=["B1"],
    )
    ccrp_res = run_ccrp(simp_res.simplified, evidence=["V4"], hypothesis="B1")
    details = ccrp_res.node_results

    # V1
    v1 = details["V1"]
    assert v1.n_value == 2
    assert v1.distinct_hypotheses == ["B1"]
    assert v1.distinct_evidence == ["V4"]
    assert len(v1.retained_chains) == 2
    hcc_v1 = [c for c in v1.retained_chains if c.chain_type == CHAIN_TYPE_HCC][0]
    ecc_v1 = [c for c in v1.retained_chains if c.chain_type == CHAIN_TYPE_ECC][0]
    assert hcc_v1.chain_value == pytest.approx(0.845)
    assert ecc_v1.chain_value == pytest.approx(0.572)
    assert v1.retained_sum == pytest.approx(0.845 + 0.572)

    # S2
    s2 = details["S2"]
    assert s2.n_value == 2
    assert s2.retained_sum == pytest.approx(0.845 + 0.572)

    # V3
    v3 = details["V3"]
    assert v3.n_value == 1
    assert v3.distinct_hypotheses == ["B1"]
    assert v3.distinct_evidence == []
    assert len(v3.retained_chains) == 1
    assert v3.retained_chains[0].chain_value == pytest.approx(0.23998)

    # S5
    s5 = details["S5"]
    assert s5.n_value == 1
    assert s5.distinct_hypotheses == []
    assert s5.distinct_evidence == ["V4"]
    assert s5.retained_sum == pytest.approx(1.0)

    # V7
    v7 = details["V7"]
    assert v7.n_value == 1
    assert v7.distinct_evidence == ["V4"]
    assert v7.retained_sum == pytest.approx(0.238)

    # S6
    s6 = details["S6"]
    assert s6.n_value == 2
    assert s6.distinct_hypotheses == ["B1"]
    assert s6.distinct_evidence == ["V4"]
    assert len(s6.retained_chains) == 2
    assert s6.retained_sum == pytest.approx(0.23998 + 0.238)


def test_table3_path_probability_and_normalization(table3_calibrated_ducag):
    """
    Verify Equations (6) and (7) reproduction of Table 3 candidate scenarios:
      Path 1: B1 -> V1 -> S2 -> V3 -> S6
      Path 2: B1 -> V1 -> S2 -> V4 -> S5 -> V7 -> S6
      Normalized: 0.5019 / 0.4981
    """
    simp_res = simplify_ducag(
        table3_calibrated_ducag,
        evidence=["V4"],
        concerned_hypotheses=["B1"],
    )
    ccrp_res = run_ccrp(simp_res.simplified, evidence=["V4"], hypothesis="B1")
    p = ccrp_res.posteriors

    path1_nodes = ["B1", "V1", "S2", "V3", "S6"]
    path2_nodes = ["B1", "V1", "S2", "V4", "S5", "V7", "S6"]

    prob_path1 = calculate_attack_path_probability([p[n] for n in path1_nodes])
    prob_path2 = calculate_attack_path_probability([p[n] for n in path2_nodes])

    # Published normalized probabilities in paper Table 3: 0.5019 and 0.4981
    norm = normalize_probabilities([prob_path1, prob_path2])
    assert norm[0] == pytest.approx(0.5019, abs=1e-3)
    assert norm[1] == pytest.approx(0.4981, abs=1e-3)


def test_table2_raw_without_narrative_edge():
    """
    On unaugmented Table 2 graph (where V7->S6 is absent per Table 2 text):
    S6 only has Path 1 upstream (B1->V1->S2->V3->S6).
    Therefore, N=1 and Pr(S6) = 0.23998.
    """
    ducag = load_ducag_from_json(TABLE2_JSON)
    simp_res = simplify_ducag(ducag, evidence=["V4"], concerned_hypotheses=["B1"])
    ccrp_res = run_ccrp(simp_res.simplified, evidence=["V4"], hypothesis="B1")
    p = ccrp_res.posteriors

    assert p["V1"] == pytest.approx(0.7085, abs=1e-4)
    assert p["S2"] == pytest.approx(0.7085, abs=1e-4)
    assert p["V3"] == pytest.approx(0.23998, abs=1e-5)
    # S6 only reached via V3
    assert p["S6"] == pytest.approx(0.23998, abs=1e-5)


def test_ucc_elimination_recording(table3_calibrated_ducag):
    """Verify that UCC chains to sink S6 are eliminated and recorded as discarded."""
    simp_res = simplify_ducag(
        table3_calibrated_ducag,
        evidence=["V4"],
        concerned_hypotheses=["B1"],
    )
    ccrp_res = run_ccrp(simp_res.simplified, evidence=["V4"], hypothesis="B1")

    # V1 has a downstream path to terminal S6 (V1->S2->V3->S6) which contains no evidence
    v1_res = ccrp_res.node_results["V1"]
    assert len(v1_res.discarded_chains) >= 1
    ucc = v1_res.discarded_chains[0]
    assert ucc.chain_type == CHAIN_TYPE_UCC
    assert ucc.terminal_node == "S6"


def test_small_manually_verifiable_linear_chain():
    """
    Test minimal 3-node graph: B1 -> V1 -> S1
      - B1: prior 1.0
      - B1->V1: r=1, p=0.8
      - V1->S1: r=1, p=0.5
      - Evidence: S1
    Calculations:
      - S1: evidence -> Pr(S1) = 1.0
      - B1: hypothesis -> Pr(B1) = 1.0
      - V1:
          Upstream: B1->V1 (HCC, value=0.8, associated_hypothesis=B1)
          Downstream: V1->S1 (ECC, value=0.5, associated_evidence=S1)
          N = 1 + 1 = 2
          Pr(V1) = (0.8 + 0.5) / 2 = 0.65
    """
    g = DUCAGGraph(name="test_linear")
    g.add_node("B1", "B")
    g.add_node("V1", "V")
    g.add_node("S1", "S")
    g.add_edge("B1", "V1", r=1.0, transition_probability=0.8)
    g.add_edge("V1", "S1", r=1.0, transition_probability=0.5)

    res = run_ccrp(g, evidence=["S1"], hypothesis="B1")
    assert res.posteriors["S1"] == 1.0
    assert res.posteriors["B1"] == 1.0
    assert res.posteriors["V1"] == pytest.approx(0.65)


def test_isolated_node_zero_posterior():
    """An isolated node with no incoming/outgoing chains has N=0 and posterior 0.0."""
    g = DUCAGGraph(name="test_isolated")
    g.add_node("B1", "B")
    g.add_node("V1", "V")
    g.add_node("S1", "S")
    g.add_edge("B1", "V1", r=1.0, transition_probability=0.8)

    res = run_ccrp(g, evidence=["V1"], hypothesis="B1")
    # S1 is isolated
    assert res.posteriors["S1"] == 0.0
    assert res.node_results["S1"].n_value == 0


def test_custom_hypothesis_prior():
    """Custom hypothesis prior scales the HCC chain value."""
    g = DUCAGGraph(name="test_custom_prior")
    g.add_node("B1", "B")
    g.add_node("V1", "V")
    g.add_edge("B1", "V1", r=1.0, transition_probability=0.8)

    # With prior 0.5 for B1:
    # V1: HCC = 0.5 * 0.8 = 0.4. N = 1 -> Pr(V1) = 0.4
    res = run_ccrp(g, evidence=["V1"], hypothesis="B1", priors={"B1": 0.5})
    assert res.posteriors["B1"] == 0.5


def test_ccrp_error_handling():
    g = DUCAGGraph(name="err_test")
    g.add_node("B1", "B")
    g.add_node("V1", "V")
    g.add_edge("B1", "V1", r=1.0, transition_probability=0.5)

    with pytest.raises(CCRPError, match="Evidence node 'UNKNOWN' not in graph"):
        run_ccrp(g, evidence=["UNKNOWN"])

    with pytest.raises(CCRPError, match="Specified hypothesis 'UNKNOWN' not in graph"):
        run_ccrp(g, evidence=["V1"], hypothesis="UNKNOWN")

    with pytest.raises(CCRPError, match="Node 'MISSING' not in graph"):
        calculate_node_ccrp(g, "MISSING", evidence=["V1"])
