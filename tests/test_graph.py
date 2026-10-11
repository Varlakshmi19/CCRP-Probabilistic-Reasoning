"""Stage 2 tests: DUCAG construction and validation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ducag_graph import (
    DUCAGGraph,
    DUCAGValidationError,
    load_ducag_from_dict,
    load_ducag_from_json,
)

TABLE2_JSON = ROOT / "experiments" / "paper_data" / "table2_fig1_partial.json"

# Exact Table 2 values from the paper (also stored in the JSON data file).
TABLE2_EDGES = {
    ("B1", "V1"): 0.845,
    ("V1", "S2"): 1,
    ("S2", "V3"): 0.284,
    ("S2", "V4"): 0.572,
    ("V4", "S5"): 1,
    ("V3", "S6"): 1,
    ("S5", "V7"): 0.238,
    ("B2", "V8"): 0.155,
    ("V8", "S5"): 1,
    ("S7", "V6"): 1,
}


def test_load_table2_partial_graph():
    ducag = load_ducag_from_json(TABLE2_JSON)
    assert ducag.completeness == "partial_demonstration"
    assert ducag.graph.number_of_nodes() == 12
    assert ducag.graph.number_of_edges() == 10
    assert set(ducag.nodes_of_type("B")) == {"B1", "B2"}
    assert "V4" in ducag.nodes_of_type("V")
    assert "S6" in ducag.nodes_of_type("S")


def test_table2_transition_probabilities_match_paper():
    ducag = load_ducag_from_json(TABLE2_JSON)
    for (src, tgt), expected in TABLE2_EDGES.items():
        assert ducag.get_transition_probability(src, tgt) == expected
        assert ducag.graph.edges[src, tgt]["r"] == 1


def test_table2_does_not_invent_v7_to_s6():
    """V7→S6 appears in narrative/Table 3 but not Table 2 — must stay absent."""
    ducag = load_ducag_from_json(TABLE2_JSON)
    assert not ducag.graph.has_edge("V7", "S6")


def test_validate_passes_for_table2():
    ducag = load_ducag_from_json(TABLE2_JSON)
    ducag.validate()  # should not raise


def test_reject_unknown_node_type():
    g = DUCAGGraph()
    with pytest.raises(DUCAGValidationError, match="Unsupported node_type"):
        g.add_node("Z1", "Z")


def test_reject_edge_with_missing_endpoint():
    g = DUCAGGraph()
    g.add_node("B1", "B")
    with pytest.raises(DUCAGValidationError, match="not a node"):
        g.add_edge("B1", "V1", r=1, transition_probability=0.5)


def test_reject_probability_out_of_range():
    g = DUCAGGraph()
    g.add_node("B1", "B")
    g.add_node("V1", "V")
    with pytest.raises(DUCAGValidationError, match="must be in \\[0, 1\\]"):
        g.add_edge("B1", "V1", r=1, transition_probability=1.5)


def test_reject_non_positive_r():
    g = DUCAGGraph()
    g.add_node("B1", "B")
    g.add_node("V1", "V")
    with pytest.raises(DUCAGValidationError, match="must be > 0"):
        g.add_edge("B1", "V1", r=0, transition_probability=0.5)


def test_reject_edge_without_transition_params():
    g = DUCAGGraph()
    g.add_node("B1", "B")
    g.add_node("V1", "V")
    with pytest.raises(DUCAGValidationError, match="transition_probability"):
        g.add_edge("B1", "V1", r=1)


def test_reject_duplicate_node_and_edge():
    g = DUCAGGraph()
    g.add_node("B1", "B")
    with pytest.raises(DUCAGValidationError, match="Duplicate node"):
        g.add_node("B1", "B")
    g.add_node("V1", "V")
    g.add_edge("B1", "V1", r=1, transition_probability=0.5)
    with pytest.raises(DUCAGValidationError, match="Duplicate directed edge"):
        g.add_edge("B1", "V1", r=1, transition_probability=0.5)


def test_reject_self_loop():
    g = DUCAGGraph()
    g.add_node("V1", "V")
    with pytest.raises(DUCAGValidationError, match="Self-loop"):
        g.add_edge("V1", "V1", r=1, transition_probability=1)


def test_reject_prior_not_summing_to_one():
    g = DUCAGGraph()
    with pytest.raises(DUCAGValidationError, match="sum to 1"):
        g.add_node("B1", "B", prior={"launched": 0.7, "not_launched": 0.2})


def test_transition_matrix_validation():
    g = DUCAGGraph()
    g.add_node("B1", "B")
    g.add_node("V1", "V")
    g.add_edge(
        "B1",
        "V1",
        r=1,
        transition_matrix=[[0.2, 0.8], [0.1, 0.9]],
    )
    assert g.graph.edges["B1", "V1"]["transition_matrix"] == [[0.2, 0.8], [0.1, 0.9]]

    g2 = DUCAGGraph()
    g2.add_node("B1", "B")
    g2.add_node("V1", "V")
    with pytest.raises(DUCAGValidationError, match="lie in \\[0, 1\\]"):
        g2.add_edge("B1", "V1", r=1, transition_matrix=[[0.0, 1.2]])


def test_normalized_r_with_two_parents():
    g = DUCAGGraph()
    g.add_node("B1", "B")
    g.add_node("B2", "B")
    g.add_node("V1", "V")
    g.add_edge("B1", "V1", r=1, transition_probability=0.5)
    g.add_edge("B2", "V1", r=1, transition_probability=0.5)
    assert g.parent_association_sum("V1") == 2.0
    assert g.edge_normalized_r("B1", "V1") == 0.5


def test_gate_type_only_on_g_nodes():
    g = DUCAGGraph()
    with pytest.raises(DUCAGValidationError, match="only valid for G-type"):
        g.add_node("V1", "V", gate_type="AND")
    g.add_node("G1", "G", gate_type="AND")
    assert g.graph.nodes["G1"]["gate_type"] == "AND"


def test_load_from_dict_requires_nodes_and_edges():
    with pytest.raises(DUCAGValidationError, match="nodes' and 'edges"):
        load_ducag_from_dict({"name": "x"})


def test_json_data_file_declares_partial_status():
    with TABLE2_JSON.open(encoding="utf-8") as fh:
        raw = json.load(fh)
    assert raw["completeness"] == "partial_demonstration"
    assert "NOT" in raw["metadata"]["demonstration_note"].upper() or "partial" in raw[
        "metadata"
    ]["demonstration_note"].lower()


def test_visualize_writes_image(tmp_path):
    ducag = load_ducag_from_json(TABLE2_JSON)
    out = tmp_path / "demo.png"
    path = ducag.visualize(out, title="test")
    assert path.exists()
    assert path.stat().st_size > 0
