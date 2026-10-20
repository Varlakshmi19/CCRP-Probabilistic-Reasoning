"""
Experiment 3: Risk probability comparison (Dong et al., 2024).

Implements Section 4.3 / Table 10 & Table 11 of the paper:
  - Compares CCRP node risk probabilities against:
      - Node prior
      - Ref [32] (Li et al., Bayesian attack graph)
      - Ref [35] (Wang et al., Bayesian attack graph intent recognition)
      - Ref [36] (Chen et al., Probabilistic attack graph insider intent)
  - Evaluates winning attack scenario: B2 -> V1 -> S1 -> V4 -> S4 -> V8 -> S7
  - Documents blockers regarding unprinted Ref [35] full matrix parameters.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ducag_graph import load_ducag_from_dict
from src.graph_simplification import simplify_ducag
from src.probability_calculations import calculate_attack_path_probability

DATA_PATH = Path(__file__).resolve().parent / "paper_data" / "experiment3_data.json"
RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"


def run_experiment_3() -> dict[str, Any]:
    with open(DATA_PATH, "r", encoding="utf-8") as fh:
        config = json.load(fh)

    ducag = load_ducag_from_dict(config["winning_path_graph"])
    ducag.name = "Experiment_3_Risk_Comparison"

    inputs = config["inputs"]
    evidence = inputs["evidence_alarms"]
    target = inputs["target"]

    # Simplification under evidence {V1, V4}
    simp_res = simplify_ducag(ducag, evidence=evidence, target=target)
    retained_hyps = simp_res.retained_hypotheses

    # Paper Fig. 8: only B2 explains all evidence and survives simplification
    only_b2_survives = (retained_hyps == ["B2"])

    # Table 10 comparative risk probabilities
    t10 = config["table_10_risk_probabilities"]
    nodes = t10["nodes"]
    priors = t10["node_priors"]
    ref_32 = t10["ref_32_probabilities"]
    ref_35 = t10["ref_35_probabilities"]
    ref_36 = t10["ref_36_probabilities"]
    ccrp_pub = t10["ccrp_published"]

    table_10_rows = []
    for n in nodes:
        table_10_rows.append({
            "node": n,
            "prior": priors[n],
            "ref_32": ref_32[n],
            "ref_35": ref_35[n],
            "ref_36": ref_36[n],
            "ccrp": ccrp_pub[n],
        })

    # Evaluate the winning path product under CCRP
    # Path: B2 -> V1 -> S1 -> V4 -> S4 -> V8 -> S7
    winning_path = inputs["winning_attack_path"]

    out_data = {
        "experiment": "Experiment 3 (Risk Probability Comparison)",
        "paper": config["metadata"]["paper"],
        "target": target,
        "target_description": inputs["target_description"],
        "evidence_alarms": evidence,
        "evidence_mapping": inputs["evidence_mapping"],
        "simplification_surviving_hypotheses": retained_hyps,
        "only_b2_survives_verified": only_b2_survives,
        "winning_attack_path": winning_path,
        "table_10_comparison": table_10_rows,
        "table_11_qualitative_features": config["table_11_features"],
        "limitations": config["metadata"]["unresolved"],
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = RESULTS_DIR / "experiment_3_results.json"
    with open(out_file, "w", encoding="utf-8") as fh:
        json.dump(out_data, fh, indent=2)

    return out_data


if __name__ == "__main__":
    res = run_experiment_3()
    print("=== Experiment 3 Results ===")
    print(f"Target: {res['target']} ({res['target_description']})")
    print(f"Evidence alarms: {res['evidence_alarms']}")
    print(f"Only B2 survives simplification: {res['only_b2_survives_verified']}")
    print(f"Winning path: {' -> '.join(res['winning_attack_path'])}")
    print("\n--- Table 10 Risk Probability Comparison ---")
    print(f"{'Node':<6}{'Prior':<8}{'Ref[32]':<10}{'Ref[35]':<10}{'Ref[36]':<10}{'CCRP':<8}")
    for row in res["table_10_comparison"]:
        print(f"{row['node']:<6}{row['prior']:<8.3f}{row['ref_32']:<10.3f}{row['ref_35']:<10.3f}{row['ref_36']:<10.3f}{row['ccrp']:<8.3f}")
