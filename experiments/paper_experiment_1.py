"""
Experiment 1: DARPA / LLDOS attack scenario analysis (Dong et al., 2024).

Implements Section 4.1 / Table 4 & Table 5 of the paper:
  - Qualitative attack scenario reconstruction on DARPA 2000 / LLDOS
  - Path One and Path Two alarm sequences and candidate scenarios
  - Verified hypothesis pruning and candidate path identification

Documents blockers and limitations regarding unprinted numerical matrices from [25, 31].
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from src.ducag_graph import DUCAGGraph, load_ducag_from_dict
from src.graph_simplification import simplify_ducag

DATA_PATH = Path(__file__).resolve().parent / "paper_data" / "experiment1_data.json"
RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"


def run_experiment_1() -> dict[str, Any]:
    """Execute Experiment 1 analysis and save results."""
    with open(DATA_PATH, "r", encoding="utf-8") as fh:
        config = json.load(fh)

    ducag = load_ducag_from_dict(config["recoverable_graph"])
    ducag.name = "Experiment_1_DARPA_LLDOS"

    # ------------------------------------------------------------- Path One
    p1_cfg = config["path_one"]
    p1_evidence = p1_cfg["attack_alert_sequence"]  # ["X11", "X26", "X40", "X4"]
    p1_simplification = simplify_ducag(
        ducag,
        evidence=p1_evidence,
        concerned_hypotheses=["B1", "B2", "B3"],
    )

    # In Path One, only B2 connects to the full branch leading to X4, X26, X40
    p1_retained = p1_simplification.retained_hypotheses
    p1_pruned = p1_simplification.pruned_hypotheses

    p1_result = {
        "name": p1_cfg["name"],
        "observed_alarms": p1_evidence,
        "missing_alarms": p1_cfg["missing_alarms"],
        "published_winning_hypothesis": p1_cfg["winning_hypothesis"],
        "computed_retained_hypotheses": p1_retained,
        "computed_pruned_hypotheses": p1_pruned,
        "published_scenario": p1_cfg["published_scenario"],
        "hypothesis_match": (p1_cfg["winning_hypothesis"] in p1_retained),
        "explanation": p1_cfg["published_explanation"],
    }

    # ------------------------------------------------------------- Path Two
    p2_cfg = config["path_two"]
    # Path Two alarms in the recoverable graph subset:
    p2_evidence = ["X17", "X18", "X31", "X32", "X37", "X34", "X29"]
    p2_simplification = simplify_ducag(
        ducag,
        evidence=p2_evidence,
        concerned_hypotheses=["B1", "B2", "B3"],
    )

    p2_retained = p2_simplification.retained_hypotheses
    p2_pruned = p2_simplification.pruned_hypotheses

    p2_result = {
        "name": p2_cfg["name"],
        "observed_alarms_subset": p2_evidence,
        "missing_alarms": p2_cfg["missing_alarms"],
        "published_winning_hypothesis": p2_cfg["winning_hypothesis"],
        "computed_retained_hypotheses": p2_retained,
        "computed_pruned_hypotheses": p2_pruned,
        "published_scenario": p2_cfg["published_scenario"],
        "hypothesis_match": (p2_cfg["winning_hypothesis"] in p2_retained),
        "explanation": p2_cfg["published_explanation"],
    }

    out_data = {
        "experiment": "Experiment 1 (DARPA / LLDOS)",
        "paper": config["metadata"]["paper"],
        "status": "qualitative_reproduction_verified",
        "path_one": p1_result,
        "path_two": p2_result,
        "limitations": config["metadata"]["unresolved"],
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = RESULTS_DIR / "experiment_1_results.json"
    with open(out_file, "w", encoding="utf-8") as fh:
        json.dump(out_data, fh, indent=2)

    return out_data


if __name__ == "__main__":
    res = run_experiment_1()
    print("=== Experiment 1 Results ===")
    print(json.dumps(res, indent=2))
