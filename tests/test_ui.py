"""
Test suite for Streamlit UI module and data loading pipeline (app.py).

Verifies:
  - Preset configurations and graph file paths
  - Preset graph loading and validation
  - Graph visualization plot generation
  - End-to-end inference execution on all presets
  - Saved experiment JSON artifacts readability and structure
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pytest

from app import PRESET_CONFIGS, load_preset_ducag, render_graph_plot
from src.ccrp import run_ccrp
from src.ducag_graph import DUCAGGraph
from src.graph_simplification import simplify_ducag
from src.probability_calculations import (
    calculate_attack_path_probability,
    normalize_probabilities,
)


def test_preset_configs_exist_and_valid():
    """Verify that all predefined example graph files exist on disk."""
    assert len(PRESET_CONFIGS) >= 4
    for name, cfg in PRESET_CONFIGS.items():
        assert "file" in cfg
        assert Path(cfg["file"]).exists(), f"Missing graph file for preset {name}: {cfg['file']}"
        assert "description" in cfg
        assert "default_evidence" in cfg


def test_load_all_presets():
    """Verify that each preset loads into a valid DUCAGGraph without errors."""
    for name in PRESET_CONFIGS:
        ducag, cfg = load_preset_ducag(name)
        assert isinstance(ducag, DUCAGGraph)
        assert len(ducag.graph.nodes) > 0
        assert len(ducag.graph.edges) > 0


def test_render_graph_plot():
    """Verify that render_graph_plot produces a valid matplotlib figure."""
    ducag, _ = load_preset_ducag("Toy Example (Fig. 1 / Table 2 + narrative)")
    fig = render_graph_plot(ducag, title="Test Plot")
    assert isinstance(fig, plt.Figure)
    plt.close(fig)


def test_toy_example_preset_pipeline():
    """Verify inference pipeline on Toy Example preset."""
    ducag, cfg = load_preset_ducag("Toy Example (Fig. 1 / Table 2 + narrative)")
    evidence = cfg["default_evidence"]
    target = cfg["default_target"]

    simp = simplify_ducag(ducag, evidence=evidence, target=target)
    assert "B1" in simp.retained_hypotheses

    ccrp = run_ccrp(simp.simplified, evidence=evidence, hypothesis="B1")
    assert "V4" in ccrp.posteriors
    assert ccrp.posteriors["V4"] == 1.0
    assert "V1" in ccrp.posteriors
    assert ccrp.posteriors["V1"] > 0.0


def test_experiment_2_preset_pipeline():
    """Verify inference pipeline on Experiment 2 preset."""
    ducag, cfg = load_preset_ducag("Experiment 2: Simulated Network (24 nodes, Table 6)")
    evidence = cfg["default_evidence"]
    target = cfg["default_target"]

    simp = simplify_ducag(ducag, evidence=evidence, target=target)
    assert len(simp.simplified.graph.nodes) > 0

    ccrp = run_ccrp(simp.simplified, evidence=evidence, hypothesis="B1")
    for e in evidence:
        assert e in ccrp.posteriors
        assert ccrp.posteriors[e] == 1.0


def test_experiment_3_preset_pipeline():
    """Verify inference pipeline on Experiment 3 preset."""
    ducag, cfg = load_preset_ducag("Experiment 3: Risk Comparison Winning Path Graph")
    evidence = cfg["default_evidence"]
    target = cfg["default_target"]

    simp = simplify_ducag(ducag, evidence=evidence, target=target)
    # Strictly B2 survives
    assert simp.retained_hypotheses == ["B2"]

    ccrp = run_ccrp(simp.simplified, evidence=evidence, hypothesis="B2")
    assert ccrp.posteriors["V1"] == 1.0
    assert ccrp.posteriors["V4"] == 1.0


def test_results_json_artifacts_exist_and_readable():
    """Verify that all 4 experiment output JSON files exist and have required top-level keys."""
    results_dir = Path(__file__).resolve().parents[1] / "results"

    e1_path = results_dir / "experiment_1_results.json"
    assert e1_path.exists()
    with open(e1_path, "r", encoding="utf-8") as fh:
        e1 = json.load(fh)
    assert "path_one" in e1
    assert "path_two" in e1

    e2_path = results_dir / "experiment_2_results.json"
    assert e2_path.exists()
    with open(e2_path, "r", encoding="utf-8") as fh:
        e2 = json.load(fh)
    assert "primary_scenario" in e2

    e3_path = results_dir / "experiment_3_results.json"
    assert e3_path.exists()
    with open(e3_path, "r", encoding="utf-8") as fh:
        e3 = json.load(fh)
    assert "table_10_comparison" in e3

    e4_path = results_dir / "experiment_4_results.json"
    assert e4_path.exists()
    with open(e4_path, "r", encoding="utf-8") as fh:
        e4 = json.load(fh)
    assert "results_by_scale" in e4
    assert len(e4["results_by_scale"]) == 5
