"""Stage 3 tests: DUCAG graph simplification."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ducag_graph import DUCAGGraph, load_ducag_from_json
from src.graph_simplification import (
    RULE_DECOMPOSE_HYPOTHESIS,
    RULE_HYPOTHESIS_EXPLAIN,
    RULE_IRRELEVANT_TO_RETAINED,
    RULE_MARK_EVIDENCE,
    RULE_MARK_TARGET,
    SimplificationError,
    decompose_into_sub_ducags,
    hypothesis_descendant_nodes,
    hypothesis_explains_all_evidence,
    list_hypothesis_nodes,
    simplify_ducag,
    verified_rule_catalog,
)

TABLE2_JSON = ROOT / "experiments" / "paper_data" / "table2_fig1_partial.json"


def test_original_graph_is_not_mutated():
    """Simplification must never mutate the original DUCAGGraph."""
    ducag = load_ducag_from_json(TABLE2_JSON)
    num_nodes_before = ducag.graph.number_of_nodes()
    num_edges_before = ducag.graph.number_of_edges()
    node_data_before = {n: dict(d) for n, d in ducag.graph.nodes(data=True)}
    edge_data_before = {(u, v): dict(d) for u, v, d in ducag.graph.edges(data=True)}

    result = simplify_ducag(ducag, evidence=["V4"])

    # Original graph is strictly identical
    assert ducag.graph.number_of_nodes() == num_nodes_before
    assert ducag.graph.number_of_edges() == num_edges_before
    assert {n: dict(d) for n, d in ducag.graph.nodes(data=True)} == node_data_before
    assert {(u, v): dict(d) for u, v, d in ducag.graph.edges(data=True)} == edge_data_before

    # Evidence flag was NOT added to original
    assert "is_evidence" not in ducag.graph.nodes["V4"]


def test_separate_simplified_graph_created():
    """A distinct simplified graph is returned with the original preserved."""
    ducag = load_ducag_from_json(TABLE2_JSON)
    result = simplify_ducag(ducag, evidence=["V4"])

    assert result.original is ducag
    assert result.simplified is not ducag
    assert result.simplified.name == f"{ducag.name}_simplified"


def test_mark_evidence_on_simplified_graph():
    """Evidence nodes must have is_evidence=True on the simplified graph."""
    ducag = load_ducag_from_json(TABLE2_JSON)
    result = simplify_ducag(ducag, evidence=["V4"])

    assert result.simplified.graph.nodes["V4"].get("is_evidence") is True
    # Non-evidence nodes must not be marked as evidence
    assert result.simplified.graph.nodes["V1"].get("is_evidence") is not True
    assert result.simplified.graph.nodes["S2"].get("is_evidence") is not True


def test_mark_target_when_retained():
    """Target node must have is_target=True when retained in the simplified graph."""
    ducag = load_ducag_from_json(TABLE2_JSON)
    result = simplify_ducag(ducag, evidence=["V4"], target="S6")

    assert result.target == "S6"
    assert result.simplified.graph.nodes["S6"].get("is_target") is True


def test_target_outside_retained_subgraph_records_limitation():
    """If target is not inside retained sub-DUCAG, record limitation without error."""
    ducag = load_ducag_from_json(TABLE2_JSON)
    # S7 is in an isolated component not reachable from B1
    result = simplify_ducag(ducag, evidence=["V4"], target="S7")

    assert result.target == "S7"
    assert "S7" not in result.simplified.graph
    assert any("Target 'S7' is not inside" in lim for lim in result.unresolved_limitations)


def test_table2_evidence_v4_simplification():
    """
    On Table 2 graph under evidence V4:
    - B1 can reach V4 (via B1->V1->S2->V4).
    - B2 cannot reach V4 (paths from B2 only lead to V8->S5->V7).
    - B1 is retained, B2 is pruned.
    - S7 and V6 are isolated and irrelevant.
    """
    ducag = load_ducag_from_json(TABLE2_JSON)
    result = simplify_ducag(ducag, evidence=["V4"])

    assert result.retained_hypotheses == ["B1"]
    assert result.pruned_hypotheses == ["B2"]

    expected_kept_nodes = {"B1", "V1", "S2", "V3", "V4", "S5", "S6", "V7"}
    assert set(result.simplified.graph.nodes) == expected_kept_nodes

    expected_removed_nodes = {"B2", "V8", "S7", "V6"}
    actual_removed_nodes = {r.element for r in result.removed_nodes}
    assert actual_removed_nodes == expected_removed_nodes

    expected_removed_edges = {("B2", "V8"), ("V8", "S5"), ("S7", "V6")}
    actual_removed_edges = {tuple(r.element) for r in result.removed_edges}
    assert actual_removed_edges == expected_removed_edges

    # Check reason and rule_id on removed elements
    for r in result.removed_nodes:
        assert r.kind == "node"
        assert len(r.reason) > 0
        assert r.rule_id in {RULE_HYPOTHESIS_EXPLAIN, RULE_IRRELEVANT_TO_RETAINED}

    for r in result.removed_edges:
        assert r.kind == "edge"
        assert len(r.reason) > 0
        assert r.rule_id in {RULE_HYPOTHESIS_EXPLAIN, RULE_IRRELEVANT_TO_RETAINED}


def test_hypothesis_explains_all_evidence_helper():
    ducag = load_ducag_from_json(TABLE2_JSON)
    # B1 can reach V4, S6, V7
    assert hypothesis_explains_all_evidence(ducag, "B1", ["V4"]) is True
    assert hypothesis_explains_all_evidence(ducag, "B1", ["V4", "S6"]) is True
    assert hypothesis_explains_all_evidence(ducag, "B1", ["V8"]) is False

    # B2 cannot reach V4 or S6
    assert hypothesis_explains_all_evidence(ducag, "B2", ["V4"]) is False
    assert hypothesis_explains_all_evidence(ducag, "B2", ["V8"]) is True
    assert hypothesis_explains_all_evidence(ducag, "B2", ["S5"]) is True


def test_hypothesis_descendant_nodes_helper():
    ducag = load_ducag_from_json(TABLE2_JSON)
    desc_b1 = hypothesis_descendant_nodes(ducag, "B1")
    assert desc_b1 == {"B1", "V1", "S2", "V3", "V4", "S5", "S6", "V7"}

    desc_b2 = hypothesis_descendant_nodes(ducag, "B2")
    assert desc_b2 == {"B2", "V8", "S5", "V7"}


def test_decompose_into_sub_ducags():
    """decompose_into_sub_ducags returns one sub-graph per hypothesis."""
    ducag = load_ducag_from_json(TABLE2_JSON)
    subs = decompose_into_sub_ducags(ducag)

    assert set(subs.keys()) == {"B1", "B2"}
    assert set(subs["B1"].graph.nodes) == {"B1", "V1", "S2", "V3", "V4", "S5", "S6", "V7"}
    assert set(subs["B2"].graph.nodes) == {"B2", "V8", "S5", "V7"}

    # Sub-graphs must be valid DUCAGGraphs
    subs["B1"].validate()
    subs["B2"].validate()


def test_decompose_into_sub_ducags_specific_subset():
    ducag = load_ducag_from_json(TABLE2_JSON)
    subs = decompose_into_sub_ducags(ducag, hypotheses=["B1"])
    assert list(subs.keys()) == ["B1"]


def test_concerned_hypotheses_filtering():
    """Restricting concerned_hypotheses prunes unconcerned hypotheses."""
    ducag = load_ducag_from_json(TABLE2_JSON)
    # Both B1 and B2 can reach S5, but caller only focuses on B2
    result = simplify_ducag(ducag, evidence=["S5"], concerned_hypotheses=["B2"])

    assert result.candidate_hypotheses == ["B2"]
    assert result.retained_hypotheses == ["B2"]
    assert result.pruned_hypotheses == []
    assert set(result.simplified.graph.nodes) == {"B2", "V8", "S5", "V7"}

    # B1 should be listed in removed_nodes as irrelevant to B2
    b1_removals = [r for r in result.removed_nodes if r.element == "B1"]
    assert len(b1_removals) == 1
    assert b1_removals[0].rule_id == RULE_IRRELEVANT_TO_RETAINED


def test_no_hypothesis_can_explain_all_evidence():
    """When no hypothesis can explain all evidence, all hypotheses are pruned."""
    ducag = load_ducag_from_json(TABLE2_JSON)
    # B1 cannot reach V8; B2 cannot reach V1
    result = simplify_ducag(ducag, evidence=["V1", "V8"])

    assert result.retained_hypotheses == []
    assert set(result.pruned_hypotheses) == {"B1", "B2"}
    assert result.simplified.graph.number_of_nodes() == 0
    assert result.simplified.graph.number_of_edges() == 0


def test_bx_integrated_hypothesis_type():
    """BX node type is recognized as a valid hypothesis in simplification."""
    g = DUCAGGraph(name="test_bx")
    g.add_node("BX1", "BX")
    g.add_node("V1", "V")
    g.add_node("S1", "S")
    g.add_edge("BX1", "V1", r=1, transition_probability=1.0)
    g.add_edge("V1", "S1", r=1, transition_probability=1.0)

    assert list_hypothesis_nodes(g) == ["BX1"]
    result = simplify_ducag(g, evidence=["S1"])

    assert result.retained_hypotheses == ["BX1"]
    assert result.simplified.graph.number_of_nodes() == 3
    assert result.simplified.graph.nodes["S1"]["is_evidence"] is True


def test_removal_summary_format():
    """removal_summary returns a clean serializable dictionary."""
    ducag = load_ducag_from_json(TABLE2_JSON)
    result = simplify_ducag(ducag, evidence=["V4"])
    summary = result.removal_summary()

    assert "retained_hypotheses" in summary
    assert "pruned_hypotheses" in summary
    assert "removed_nodes" in summary
    assert "removed_edges" in summary
    assert "applied_rules" in summary
    assert "unresolved_limitations" in summary

    assert summary["retained_hypotheses"] == ["B1"]
    assert summary["pruned_hypotheses"] == ["B2"]
    assert any(item["node"] == "B2" for item in summary["removed_nodes"])
    assert any(item["edge"] == ["B2", "V8"] for item in summary["removed_edges"])


def test_unresolved_limitations_documented():
    """Unresolved DUCG rules from [21] must be explicitly documented in results."""
    ducag = load_ducag_from_json(TABLE2_JSON)
    result = simplify_ducag(ducag, evidence=["V4"])

    assert any("[21]" in lim for lim in result.unresolved_limitations)
    assert any("explain" in lim.lower() for lim in result.unresolved_limitations)


def test_verified_rule_catalog():
    """Catalog contains only verified paper-supported simplification rules."""
    catalog = verified_rule_catalog()
    rule_ids = {r["rule_id"] for r in catalog}

    assert RULE_MARK_EVIDENCE in rule_ids
    assert RULE_MARK_TARGET in rule_ids
    assert RULE_DECOMPOSE_HYPOTHESIS in rule_ids
    assert RULE_HYPOTHESIS_EXPLAIN in rule_ids
    assert RULE_IRRELEVANT_TO_RETAINED in rule_ids


def test_reject_empty_evidence():
    ducag = load_ducag_from_json(TABLE2_JSON)
    with pytest.raises(SimplificationError, match="non-empty evidence set"):
        simplify_ducag(ducag, evidence=[])


def test_reject_unknown_evidence_node():
    ducag = load_ducag_from_json(TABLE2_JSON)
    with pytest.raises(SimplificationError, match="Evidence node not in graph"):
        simplify_ducag(ducag, evidence=["V999"])


def test_reject_unknown_target_node():
    ducag = load_ducag_from_json(TABLE2_JSON)
    with pytest.raises(SimplificationError, match="Target node not in graph"):
        simplify_ducag(ducag, evidence=["V4"], target="S999")


def test_reject_unknown_concerned_hypothesis():
    ducag = load_ducag_from_json(TABLE2_JSON)
    with pytest.raises(SimplificationError, match="Concerned hypothesis not in graph"):
        simplify_ducag(ducag, evidence=["V4"], concerned_hypotheses=["B999"])


def test_reject_concerned_hypothesis_not_b_type():
    ducag = load_ducag_from_json(TABLE2_JSON)
    with pytest.raises(SimplificationError, match="not a B/BX hypothesis node"):
        simplify_ducag(ducag, evidence=["V4"], concerned_hypotheses=["V1"])


def test_reject_graph_without_hypotheses():
    g = DUCAGGraph(name="no_hyp")
    g.add_node("V1", "V")
    g.add_node("S1", "S")
    g.add_edge("V1", "S1", r=1, transition_probability=1.0)

    with pytest.raises(SimplificationError, match="No hypothesis nodes"):
        simplify_ducag(g, evidence=["S1"])
