"""
DUCAG + CCRP Dynamic Network Security Analysis - Streamlit Application.

Interactive user interface for:
  - DUCAG Graph loading and visualization
  - Causal graph simplification under evidence alarms
  - CCRP causal chain expansion and posterior risk probability calculation
  - Attack scenario path reconstruction and most likely path identification
  - Paper experiments reproduction (Dong et al., 2024, Experiments 1-4)
  - Scientific limitations, provenance auditing, and discrepancy explanations
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional, Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import streamlit as st

from src.ccrp import (
    CHAIN_TYPE_ECC,
    CHAIN_TYPE_HCC,
    CHAIN_TYPE_UCC,
    CausalChain,
    NodeCCRPResult,
    calculate_node_ccrp,
    run_ccrp,
)
from src.ducag_graph import DUCAGGraph, load_ducag_from_dict, load_ducag_from_json
from src.graph_simplification import list_hypothesis_nodes, simplify_ducag
from src.probability_calculations import (
    aggregate_hypothesis_path_probabilities,
    calculate_attack_path_probability,
    normalize_probabilities,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "experiments" / "paper_data"
RESULTS_DIR = BASE_DIR / "results"

PRESET_CONFIGS = {
    "Toy Example (Fig. 1 / Table 2 + narrative)": {
        "file": DATA_DIR / "table2_fig1_partial.json",
        "default_evidence": ["V4"],
        "default_target": "S6",
        "description": "8-node canonical worked example from Section 3.7. Alarm V4 observed; target S6.",
        "candidate_paths": [
            {"id": "Path 1", "nodes": ["B1", "V1", "S2", "V3", "S6"]},
            {"id": "Path 2", "nodes": ["B1", "V1", "S2", "V4", "S5", "V7", "S6"]},
        ],
    },
    "Experiment 1: DARPA / LLDOS Recoverable Graph": {
        "file": DATA_DIR / "experiment1_data.json",
        "graph_key": "recoverable_graph",
        "default_evidence": ["X11", "X26", "X40", "X4"],
        "default_target": "X40",
        "description": "DARPA 2000 multi-stage attack scenario (Path One = LLDOS 1.0; Path Two = LLDOS 2.0).",
        "candidate_paths": [
            {"id": "Path One Scenario", "nodes": ["B2", "X9", "X10", "X11", "X4", "X26", "X40"]},
        ],
    },
    "Experiment 2: Simulated Network (24 nodes, Table 6)": {
        "file": DATA_DIR / "experiment2_data.json",
        "graph_key": "graph",
        "default_evidence": ["V1", "V3", "S4", "V6", "V11", "V13", "S9"],
        "default_target": "S9",
        "description": "24-node complex enterprise network (Section 4.2). Incomplete alarms missing S2, S6, S8.",
        "candidate_paths": [
            {
                "id": "Candidate 1",
                "nodes": ["V1", "S2", "V5", "S8", "V13", "S9"],
                "hypotheses": ["B1", "BX1"],
            },
            {
                "id": "Candidate 2 (True Path)",
                "nodes": ["V1", "S2", "V3", "S4", "V6", "S6", "V11", "S8", "V13", "S9"],
                "hypotheses": ["B1", "BX1"],
                "is_true_path": True,
            },
            {
                "id": "Candidate 3",
                "nodes": ["V1", "S2", "V4", "S5", "V7", "S6", "V11", "S8", "V13", "S9"],
                "hypotheses": ["B1", "BX1"],
            },
            {
                "id": "Candidate 6",
                "nodes": ["V1", "S2", "V4", "S5", "V9", "S9"],
                "hypotheses": ["BX1"],
            },
            {
                "id": "Candidate 7",
                "nodes": ["V2", "S3", "V9", "S9"],
                "hypotheses": ["BX1"],
            },
        ],
    },
    "Experiment 3: Risk Comparison Winning Path Graph": {
        "file": DATA_DIR / "experiment3_data.json",
        "graph_key": "winning_path_graph",
        "default_evidence": ["V1", "V4"],
        "default_target": "S7",
        "description": "Risk probability comparison against baseline methods (Section 4.3). Target S7 (root access).",
        "candidate_paths": [
            {"id": "Winning Attack Path", "nodes": ["B2", "V1", "S1", "V4", "S4", "V8", "S7"]},
        ],
    },
}


def load_preset_ducag(preset_name: str) -> tuple[DUCAGGraph, dict[str, Any]]:
    """Load DUCAG graph from a preset configuration."""
    cfg = PRESET_CONFIGS[preset_name]
    file_path = cfg["file"]

    with open(file_path, "r", encoding="utf-8") as fh:
        raw_data = json.load(fh)

    graph_dict = raw_data.get(cfg.get("graph_key", ""), raw_data)
    ducag = load_ducag_from_dict(graph_dict)
    ducag.name = preset_name.split(":")[0]
    return ducag, cfg


def render_graph_plot(ducag: DUCAGGraph, title: str = "DUCAG Graph") -> plt.Figure:
    """Render matplotlib visual plot of a DUCAG graph."""
    fig, ax = plt.subplots(figsize=(10, 6), dpi=120)
    pos = nx.spring_layout(ducag.graph, seed=42, k=1.2)

    color_map = {
        "B": "#d9534f",
        "BX": "#f0ad4e",
        "V": "#337ab7",
        "S": "#5cb85c",
        "G": "#9b59b6",
    }
    node_colors = [
        color_map.get(ducag.graph.nodes[n].get("node_type", ""), "#cccccc")
        for n in ducag.graph.nodes
    ]

    nx.draw_networkx_nodes(
        ducag.graph, pos, node_color=node_colors, node_size=650, ax=ax
    )
    nx.draw_networkx_labels(
        ducag.graph, pos, font_size=8, font_color="white", font_weight="bold", ax=ax
    )
    nx.draw_networkx_edges(
        ducag.graph,
        pos,
        arrows=True,
        arrowstyle="-|>",
        arrowsize=14,
        edge_color="#555555",
        width=1.2,
        connectionstyle="arc3,rad=0.08",
        ax=ax,
    )

    edge_labels = {}
    for u, v, d in ducag.graph.edges(data=True):
        tp = d.get("transition_probability")
        if tp is not None:
            edge_labels[(u, v)] = f"{tp:g}"
        elif d.get("r") is not None:
            edge_labels[(u, v)] = f"r={d.get('r'):g}"

    nx.draw_networkx_edge_labels(
        ducag.graph, pos, edge_labels=edge_labels, font_size=7, ax=ax
    )
    ax.set_title(title, fontsize=12, fontweight="bold", pad=12)
    ax.axis("off")
    fig.tight_layout()
    return fig


# =============================================================================
# STREAMLIT UI SETUP
# =============================================================================

st.set_page_config(
    page_title="DUCAG + CCRP Dynamic Security Analysis",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🛡️ Dynamic Uncertain Causal Attack Graph (DUCAG) & CCRP Engine")
st.caption(
    "Interactive Implementation & Verification of Dong, Feng, & Shang (2024), "
    "Journal of Cloud Computing, 13:24. DOI: 10.1186/s13677-023-00568-7"
)

# Sidebar Navigation
sidebar_nav = st.sidebar.radio(
    "Navigation",
    [
        "🔍 Interactive Inference Engine",
        "📊 Paper Experiments (1–4)",
        "⚖️ Provenance & Results Audit",
        "⚠️ Limitations & Discrepancies",
    ],
    index=0,
)

# =============================================================================
# TAB 1: INTERACTIVE INFERENCE ENGINE
# =============================================================================
if sidebar_nav == "🔍 Interactive Inference Engine":
    st.markdown("### 1. Graph Selection & Evidence Configuration")

    col_load_left, col_load_right = st.columns([2, 1])

    with col_load_left:
        selected_preset = st.selectbox(
            "Select Example DUCAG Graph:",
            list(PRESET_CONFIGS.keys()),
            index=0,
            help="Choose from the reference paper's worked examples and experimental topologies.",
        )
        ducag, preset_info = load_preset_ducag(selected_preset)
        st.info(f"**Description:** {preset_info['description']}")

    with col_load_right:
        st.markdown("**Node Type Legend:**")
        st.markdown(
            "- 🔴 **B**: Root Cause Hypothesis\n"
            "- 🟠 **BX**: Integrated Hypothesis\n"
            "- 🔵 **V**: Vulnerability / Alarm Event\n"
            "- 🟢 **S**: Security / Resource State\n"
            "- 🟣 **G**: Logic Gate (AND / OR)"
        )

    # Graph Inspection & Metrics
    all_nodes = list(ducag.graph.nodes)
    hypothesis_nodes = list_hypothesis_nodes(ducag)
    non_hyp_nodes = [n for n in all_nodes if n not in hypothesis_nodes]

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("Total Nodes", len(all_nodes))
    col_m2.metric("Total Directed Edges", len(ducag.graph.edges))
    col_m3.metric("Hypotheses (B / BX)", len(hypothesis_nodes))
    col_m4.metric("Events / States (V / S)", len(non_hyp_nodes))

    # Evidence & Target Selection
    st.markdown("---")
    st.markdown("### 2. Evidence Alarms & Hypothesis Settings")

    col_sel1, col_sel2, col_sel3 = st.columns([2, 1, 1])

    with col_sel1:
        default_evi = [e for e in preset_info.get("default_evidence", []) if e in all_nodes]
        selected_evidence = st.multiselect(
            "Observed Evidence Alarms (Events observed in intrusion detection):",
            options=non_hyp_nodes,
            default=default_evi,
            help="Select alarm events observed in IDS logs (state fixed to 1.0).",
        )

    with col_sel2:
        default_tgt = preset_info.get("default_target", None)
        target_options = ["None"] + non_hyp_nodes
        tgt_idx = (
            target_options.index(default_tgt)
            if default_tgt in target_options
            else 0
        )
        selected_target = st.selectbox(
            "Target Node (Optional):",
            options=target_options,
            index=tgt_idx,
            help="The high-value asset or final state targeted by the attacker.",
        )
        target_node = None if selected_target == "None" else selected_target

    with col_sel3:
        selected_hyp = st.selectbox(
            "Root Hypothesis to Evaluate:",
            options=hypothesis_nodes if hypothesis_nodes else ["None"],
            index=0,
            help="Primary root attacker strategy for causal chain expansion.",
        )

    # Preset Quick Load buttons
    if selected_preset == "Experiment 2: Simulated Network (24 nodes, Table 6)":
        st.markdown("**Quick Preset Evidence Loaders for Experiment 2:**")
        b_c1, b_c2, b_c3 = st.columns(3)
        if b_c1.button("Load Path 1 Evidence (Incomplete: V1, V3, S4, V6, V11, V13, S9)"):
            st.session_state["override_evi"] = ["V1", "V3", "S4", "V6", "V11", "V13", "S9"]
            st.rerun()
        if b_c2.button("Load Path 2 Evidence (Redundant alarms)"):
            st.session_state["override_evi"] = ["V1", "V2", "V3", "S4", "V6", "V11", "V13", "S9"]
            st.rerun()
        if b_c3.button("Load Path 3 Evidence (Redundant + Missing)"):
            st.session_state["override_evi"] = ["V1", "V3", "S4", "V6", "V9", "S9"]
            st.rerun()

    # Visual Graph Rendering
    with st.expander("👁️ View Input DUCAG Topology & Edge Parameters", expanded=False):
        fig_graph = render_graph_plot(ducag, title=f"Input Topology: {ducag.name}")
        st.pyplot(fig_graph)
        plt.close(fig_graph)

        edge_df = pd.DataFrame([
            {
                "Source": u,
                "Target": v,
                "Source Type": ducag.graph.nodes[u].get("node_type", ""),
                "Target Type": ducag.graph.nodes[v].get("node_type", ""),
                "Causal Strength r": d.get("r", 1.0),
                "Transition Prob A": d.get("transition_probability", 1.0),
            }
            for u, v, d in ducag.graph.edges(data=True)
        ])
        st.dataframe(edge_df, use_container_width=True)

    # Run Execution Button
    st.markdown("---")
    run_btn = st.button("🚀 Run Causality Simplification & CCRP Inference", type="primary")

    if run_btn:
        if not selected_evidence:
            st.error("Please select at least one observed evidence alarm node.")
        else:
            with st.spinner("Executing DUCAG Simplification & CCRP Reasoning..."):
                try:
                    # 1. Simplification
                    simp_result = simplify_ducag(
                        ducag,
                        evidence=selected_evidence,
                        target=target_node,
                    )

                    # 2. CCRP
                    chosen_hyp = None if selected_hyp == "None" else selected_hyp
                    ccrp_result = run_ccrp(
                        simp_result.simplified,
                        evidence=selected_evidence,
                        hypothesis=chosen_hyp,
                    )

                    st.success("✅ CCRP Inference Completed Successfully!")

                    # Results Layout
                    tab_simp, tab_post, tab_chains, tab_path = st.tabs([
                        "1️⃣ Simplification Results",
                        "2️⃣ Node Posteriors Pr(X)",
                        "3️⃣ Causal Chain Inspector",
                        "4️⃣ Attack Path Reconstruction",
                    ])

                    # TAB 1: SIMPLIFICATION
                    with tab_simp:
                        st.subheader("Causality Simplification Outcome")
                        st.markdown(
                            "According to the DUCAG simplification method, hypotheses that cannot "
                            "explain all observed evidence alarms are pruned from the reasoning graph."
                        )

                        col_s1, col_s2 = st.columns(2)
                        with col_s1:
                            st.markdown("#### Retained Hypotheses")
                            if simp_result.retained_hypotheses:
                                for h in simp_result.retained_hypotheses:
                                    st.success(f"🟢 **{h}** (Explains observed evidence)")
                            else:
                                st.warning("No hypothesis could explain all observed evidence!")

                        with col_s2:
                            st.markdown("#### Pruned Hypotheses")
                            if simp_result.pruned_hypotheses:
                                for h in simp_result.pruned_hypotheses:
                                    st.error(f"🔴 **{h}** (Pruned: cannot explain all alarms)")
                            else:
                                st.info("No hypotheses pruned.")

                        st.markdown(f"**Simplified Graph Nodes:** {len(simp_result.simplified.graph.nodes)} | "
                                    f"**Edges:** {len(simp_result.simplified.graph.edges)}")

                        # Render simplified graph
                        if len(simp_result.simplified.graph.nodes) > 0:
                            fig_simp = render_graph_plot(
                                simp_result.simplified,
                                title=f"Simplified DUCAG ({simp_result.simplified.name})",
                            )
                            st.pyplot(fig_simp)
                            plt.close(fig_simp)

                    # TAB 2: POSTERIOR PROBABILITIES
                    with tab_post:
                        st.subheader("Calculated Node Posterior Probabilities Pr(X)")
                        st.markdown(
                            "Posterior probabilities computed via **Equation (5)**: "
                            r"$\Pr(X_v) = \frac{\sum \text{ECC}(X_v) + \sum \text{HCC}(X_v)}{N}$"
                        )

                        post_records = []
                        for n, p_val in sorted(ccrp_result.posteriors.items()):
                            node_data = simp_result.simplified.graph.nodes.get(n, {})
                            is_evi = n in selected_evidence
                            is_hyp = n in hypothesis_nodes
                            post_records.append({
                                "Node ID": n,
                                "Node Type": node_data.get("node_type", ""),
                                "Description": node_data.get("description", ""),
                                "Evidence State": "Observed (Alarm)" if is_evi else ("Hypothesis" if is_hyp else "Latent"),
                                "Posterior Probability Pr(X)": round(p_val, 5),
                            })

                        df_post = pd.DataFrame(post_records)
                        st.dataframe(df_post, use_container_width=True)

                        # Bar chart
                        chart_df = df_post.set_index("Node ID")[["Posterior Probability Pr(X)"]]
                        st.bar_chart(chart_df)

                    # TAB 3: CAUSAL CHAIN INSPECTOR
                    with tab_chains:
                        st.subheader("Causal Chain Decomposition & Elimination (Eq. 3 & Eq. 4)")
                        st.markdown(
                            "CCRP expands elementary causal chains upstream to root causes and downstream "
                            "to evidence or sinks, classifying them into **UCC** (unknown), **ECC** (evidence), and **HCC** (hypothesis)."
                        )

                        inspect_node = st.selectbox(
                            "Select Node to Inspect Chains:",
                            options=sorted(list(simp_result.simplified.graph.nodes)),
                            index=0,
                        )

                        node_ccrp = ccrp_result.node_results.get(inspect_node)
                        if node_ccrp:
                            col_c1, col_c2, col_c3 = st.columns(3)
                            col_c1.metric("Retained Chains (ECC+HCC)", len(node_ccrp.retained_chains))
                            col_c2.metric("Discarded Chains (UCC)", len(node_ccrp.discarded_chains))
                            col_c3.metric("Entity Count N", node_ccrp.n_value)

                            st.markdown(f"#### Calculation for Node **{inspect_node}**:")
                            st.latex(
                                rf"\Pr({inspect_node}) = \frac{{{node_ccrp.retained_sum:.4f}}}{{{node_ccrp.n_value}}} = {node_ccrp.posterior:.4f}"
                            )

                            chain_records = []
                            for c in node_ccrp.all_chains:
                                is_retained = c in node_ccrp.retained_chains
                                chain_records.append({
                                    "Direction": c.direction.capitalize(),
                                    "Causal Path": " → ".join(c.path),
                                    "Chain Type (Eq. 3)": c.chain_type,
                                    "Status (Eq. 4)": "✅ Retained" if is_retained else "❌ Discarded (UCC)",
                                    "Hop Factors": " × ".join([f"{f:.3g}" for f in c.edge_factors]),
                                    "Chain Product": round(c.chain_value, 5),
                                    "Terminal Boundary": c.terminal_node,
                                })

                            df_chains = pd.DataFrame(chain_records)
                            st.dataframe(df_chains, use_container_width=True)

                    # TAB 4: ATTACK PATH RECONSTRUCTION
                    with tab_path:
                        st.subheader("Attack Scenario Path Reconstruction (Eq. 6 & Eq. 7)")
                        st.markdown(
                            "Attack path likelihood evaluates the product of posteriors along candidate sequences: "
                            r"$\Pr(AttackSeq_i) = \prod_{X \in path} \Pr(X_v)$."
                        )

                        candidates = preset_info.get("candidate_paths", [])
                        if candidates:
                            path_eval_records = []
                            raw_probs = []

                            for cand in candidates:
                                c_nodes = cand["nodes"]
                                # Check if nodes exist in posteriors
                                valid = all(n in ccrp_result.posteriors for n in c_nodes)
                                if valid:
                                    p_seq = [ccrp_result.posteriors[n] for n in c_nodes]
                                    path_prob = calculate_attack_path_probability(p_seq)
                                    raw_probs.append(path_prob)
                                    path_eval_records.append({
                                        "Candidate Name": cand["id"],
                                        "Path Sequence": " → ".join(c_nodes),
                                        "True Path?": cand.get("is_true_path", False),
                                        "Raw Probability": path_prob,
                                        "Calculation Trace": " × ".join([f"{ccrp_result.posteriors[n]:.3f}" for n in c_nodes]),
                                    })
                                else:
                                    raw_probs.append(0.0)
                                    path_eval_records.append({
                                        "Candidate Name": cand["id"],
                                        "Path Sequence": " → ".join(c_nodes),
                                        "True Path?": cand.get("is_true_path", False),
                                        "Raw Probability": 0.0,
                                        "Calculation Trace": "Some nodes pruned by simplification",
                                    })

                            norm_probs = normalize_probabilities(raw_probs)
                            for idx, rec in enumerate(path_eval_records):
                                rec["Normalized Probability"] = norm_probs[idx]

                            df_paths = pd.DataFrame(path_eval_records).sort_values(
                                by="Normalized Probability", ascending=False
                            )
                            st.dataframe(df_paths, use_container_width=True)

                            # Display Winner
                            winner = df_paths.iloc[0]
                            st.success(
                                f"🏆 **Most Likely Attack Scenario:** `{winner['Candidate Name']}`\n\n"
                                f"**Path Sequence:** {winner['Path Sequence']}\n\n"
                                f"**Normalized Probability:** `{winner['Normalized Probability']:.4f}`\n\n"
                                f"**Mathematical Trace:** {winner['Calculation Trace']} = `{winner['Raw Probability']:.6f}`"
                            )
                        else:
                            st.info("No predefined candidate paths specified for this graph preset.")

                except Exception as exc:
                    st.error(f"Inference error: {exc}")

# =============================================================================
# TAB 2: PAPER EXPERIMENTAL RESULTS (1–4)
# =============================================================================
elif sidebar_nav == "📊 Paper Experiments (1–4)":
    st.header("📊 Published Experiments Reproduction (Dong et al., 2024)")
    st.markdown(
        "Directly reads and displays machine-readable results from [`results/`](file:///c:/Users/VARALAKSHMI/CCRP/results/). "
        "Separates implementation-computed results from published values copied from the paper."
    )

    exp_tabs = st.tabs([
        "Exp 1: DARPA / LLDOS",
        "Exp 2: Simulated Network",
        "Exp 3: Risk Comparison",
        "Exp 4: Runtime Benchmark",
    ])

    # EXP 1
    with exp_tabs[0]:
        st.subheader("Experiment 1: DARPA 2000 / LLDOS Scenario Analysis")
        p1_file = RESULTS_DIR / "experiment_1_results.json"
        if p1_file.exists():
            with open(p1_file, "r", encoding="utf-8") as fh:
                e1 = json.load(fh)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Path One (LLDOS 1.0)")
                po = e1["path_one"]
                st.write(f"**Observed Alarms:** `{po['observed_alarms']}`")
                st.write(f"**Missing Alarms:** `{po['missing_alarms']}`")
                st.write(f"**Computed Retained Hypotheses:** `{po['computed_retained_hypotheses']}`")
                st.write(f"**Computed Pruned Hypotheses:** `{po['computed_pruned_hypotheses']}`")
                st.success(f"**Published Winner:** {po['published_winning_hypothesis']} (Verified Match: {po['hypothesis_match']})")
                st.info(f"**Published Scenario:** {' → '.join(po['published_scenario'])}")

            with col2:
                st.markdown("#### Path Two (LLDOS 2.0)")
                pt = e1["path_two"]
                st.write(f"**Observed Alarms Subset:** `{pt['observed_alarms_subset']}`")
                st.write(f"**Missing Alarms:** `{pt['missing_alarms']}`")
                st.write(f"**Computed Retained Hypotheses:** `{pt['computed_retained_hypotheses']}`")
                st.write(f"**Computed Pruned Hypotheses:** `{pt['computed_pruned_hypotheses']}`")
                st.success(f"**Published Winner:** {pt['published_winning_hypothesis']} (Verified Match: {pt['hypothesis_match']})")
                st.info(f"**Published Scenario:** {' → '.join(pt['published_scenario'])}")

            st.warning("⚠️ **Documented Limitation:** Exact 46-variable transition matrices were deferred by the paper to external references [25, 31].")
        else:
            st.error("Missing results/experiment_1_results.json")

    # EXP 2
    with exp_tabs[1]:
        st.subheader("Experiment 2: Simulated Enterprise Network (Table 8 & Table 9)")
        p2_file = RESULTS_DIR / "experiment_2_results.json"
        if p2_file.exists():
            with open(p2_file, "r", encoding="utf-8") as fh:
                e2 = json.load(fh)

            p1_scen = e2["primary_scenario"]
            st.markdown(f"**Observed Alarms:** `{p1_scen['observed_evidence']}` | **Missing Alarms:** `{p1_scen['missing_alarms']}`")

            st.markdown("#### Table 9 Candidate Attack Paths Reproduction")
            t9_data = p1_scen["table_9_published_reproduction"]["all_7_candidates"]
            df_t9 = pd.DataFrame(t9_data)
            st.dataframe(df_t9, use_container_width=True)

            winner = p1_scen["table_9_published_reproduction"]["winner"]
            st.success(f"🏆 **True Path Winner Verified:** `{winner}` (Rank 1, Published Normalized Prob: 0.3542)")

            with st.expander("🔍 View Table 8 Node Posteriors Comparison (Under Hypothesis B1)"):
                t8_data = [
                    {
                        "Node": k,
                        "Published Posterior": v["published"],
                        "CCRP Computed": round(v["computed"], 4) if v["computed"] is not None else None,
                        "Difference Δ": round(v["diff"], 4) if v["diff"] is not None else None,
                    }
                    for k, v in p1_scen["table_8_node_posteriors_comparison"].items()
                ]
                st.dataframe(pd.DataFrame(t8_data), use_container_width=True)

    # EXP 3
    with exp_tabs[2]:
        st.subheader("Experiment 3: Risk Probability Comparison Across Baselines")
        p3_file = RESULTS_DIR / "experiment_3_results.json"
        if p3_file.exists():
            with open(p3_file, "r", encoding="utf-8") as fh:
                e3 = json.load(fh)

            st.write(f"**Target Node:** `{e3['target']}` ({e3['target_description']})")
            st.write(f"**Evidence Alarms:** `{e3['evidence_alarms']}`")
            st.success(f"**Simplification Outcome:** Strictly hypothesis `{e3['simplification_surviving_hypotheses']}` survives.")
            st.info(f"**Winning Attack Path:** {' → '.join(e3['winning_attack_path'])}")

            st.markdown("#### Table 10 Node Risk Comparison Across Methods")
            t10_df = pd.DataFrame(e3["table_10_comparison"])
            t10_df.columns = ["Node", "Prior", "Li et al. [32]", "Wang et al. [35]", "Chen et al. [36]", "CCRP (Dong et al.)"]
            st.dataframe(t10_df, use_container_width=True)

            chart_t10 = t10_df.set_index("Node")[["Prior", "Li et al. [32]", "Wang et al. [35]", "Chen et al. [36]", "CCRP (Dong et al.)"]]
            st.line_chart(chart_t10)

    # EXP 4
    with exp_tabs[3]:
        st.subheader("Experiment 4: Runtime / Time-Complexity Benchmark (CCRP vs BNRP)")
        p4_file = RESULTS_DIR / "experiment_4_results.json"
        if p4_file.exists():
            with open(p4_file, "r", encoding="utf-8") as fh:
                e4 = json.load(fh)

            st.caption("Benchmark executed on random DAGs; evidence count = hosts / 2.")
            df_e4 = pd.DataFrame(e4["results_by_scale"])
            st.dataframe(df_e4, use_container_width=True)

            col_c1, col_c2 = st.columns(2)
            with col_c1:
                st.markdown("#### Elapsed Time (ms)")
                st.line_chart(df_e4.set_index("num_hosts")[["ccrp_time_ms", "bnrp_time_ms"]])
            with col_c2:
                st.markdown("#### Natural Log Runtime ln(ms) - Fig. 9(b) Trend")
                st.line_chart(df_e4.set_index("num_hosts")[["ln_ccrp", "ln_bnrp"]])

            st.info(f"**Qualitative Match:** {e4['trend_verification']['growth_trend']}")
            st.warning(
                "⚠️ **Disclaimer:** BNRP timings reflect a synthetic benchmark of exponential factor marginalization. "
                "Absolute millisecond values reflect modern execution host performance."
            )

# =============================================================================
# TAB 3: PROVENANCE & RESULTS AUDIT
# =============================================================================
elif sidebar_nav == "⚖️ Provenance & Results Audit":
    st.header("⚖️ Provenance Classification & Verification Audit")
    st.markdown(
        "To preserve scientific fidelity, this section explicitly categorizes every result in Experiments 2 and 3 into "
        "one of four scientific provenance classes."
    )

    col_p1, col_p2 = st.columns(2)

    with col_p1:
        st.markdown("### Experiment 2 Provenance Classification")
        st.markdown(
            r"1. **Independently Computed by Implementation:**" "\n"
            r"   - Graph simplification under incomplete alarms `{V1, V3, S4, V6, V11, V13, S9}`." "\n"
            r"   - Causal chain expansions (UCC, ECC, HCC) and UCC elimination for all 18 nodes." "\n"
            r"   - First-principles node posteriors under $B_1$ and $BX_1$ via Equation (5)." "\n"
            r"   - Candidate path rankings and True Path winner identification." "\n\n"
            r"2. **Calculated Using Paper-Provided Inputs:**" "\n"
            r"   - Re-normalization of published Table 9 candidate raw posteriors reproducing True Path ($0.3543$ vs $0.3542$, $\Delta < 10^{-4}$)." "\n\n"
            r"3. **Copied from Paper / Reference for Comparison:**" "\n"
            r"   - Table 6 transition parameters $A$ and association strengths $r$." "\n"
            r"   - Table 7 alarm sequences and missing alarm definitions (`{S2, S6, S8}`)." "\n"
            r"   - Table 8 published node posteriors under $B_1$." "\n"
            r"   - Table 9 published candidate path posteriors." "\n\n"
            r"4. **Not Independently Reproducible (Data Missing):**" "\n"
            r"   - Complete node posterior table under integrated hypothesis $BX_1$ (omitted by authors in Section 4.2 'due to space limitations')."
        )

    with col_p2:
        st.markdown("### Experiment 3 Provenance Classification")
        st.markdown(
            r"1. **Independently Computed by Implementation:**" "\n"
            r"   - Graph simplification under evidence `{V1, V4}` targeting $S_7$ (strictly $B_2$ survives; $B_1, B_3$ pruned)." "\n"
            r"   - Winning attack path sequence ($B_2 \to V_1 \to S_1 \to V_4 \to S_4 \to V_8 \to S_7$) and path probability product." "\n\n"
            r"2. **Calculated Using Paper-Provided Inputs:**" "\n"
            r"   - Inactive resource node posteriors ($S_2, S_3, S_5, S_6, S_8$) remaining at prior probabilities." "\n\n"
            r"3. **Copied from Paper / Reference for Comparison:**" "\n"
            r"   - Table 10 prior probabilities for resource nodes." "\n"
            r"   - Literature baseline probabilities for Li [32], Wang [35], and Chen [36]." "\n"
            r"   - Table 11 qualitative feature comparison matrix." "\n\n"
            r"4. **Not Independently Reproducible (Data Missing):**" "\n"
            r"   - Complete Bayesian attack graph CPT matrices for Ref [35] baseline."
        )

# =============================================================================
# TAB 4: SCIENTIFIC LIMITATIONS & DISCREPANCIES
# =============================================================================
elif sidebar_nav == "⚠️ Limitations & Discrepancies":
    st.header("⚠️ Scientific Limitations & Known Discrepancies")
    st.markdown(
        "Per project requirements, our implementation strictly avoids inventing values or forcing artificial "
        "code tweaks. The known differences between the implementation and the paper are documented below."
    )

    with st.expander("1. Experiment 2: Security State S8 Discrepancy (0.8054 vs 0.3512)", expanded=True):
        st.markdown(
            r"**Observation:**" "\n"
            r"- First-principles CCRP computes: **`Pr(S8) = 0.8054`**" "\n"
            r"- Published Table 8 reports: **`Pr(S8) = 0.3512`**" "\n\n"
            r"**Mathematical Explanation:**" "\n"
            r"1. **Equation (5) Traversal:** Incoming edges into $S_8$ are $V_5, V_{10}, V_{11}, V_{12}$, and outgoing is $V_{13}$. "
            r"Both $V_{11}$ and $V_{13}$ are observed evidence alarms ($1.0$). Summing all 5 elementary chains yields $2.4163$. "
            r"Dividing by distinct evidence entities $\{V_1, V_{11}, V_{13}\}$ ($N=3$) yields:" "\n"
            r"$$\Pr(S_8) = \frac{2.4163}{3} = 0.8054$$"
            "\n"
            r"2. **The Paper's Table 8 Heuristic:** In Table 8, the paper writes an analytical formula:" "\n"
            r"$$\Pr(S_8) = \frac{1}{4} \left( A_{13,1;8} + \frac{1}{4}(\dots) \right) = \frac{1}{4}(1.0 + 0.4048) = 0.3512$$"
            r"The authors used the local in-degree ($4$) as the divisor and applied an ad-hoc nested discount of $1/4$ to upstream sub-branches. "
            r"This heuristic was never formalized in the paper's mathematical definitions. Our implementation preserves the general algorithm."
        )

    with st.expander("2. Stage 4 Table 3 Worked Example Normalization (0.5021 vs 0.5019)", expanded=True):
        st.markdown(
            r"**Observation:**" "\n"
            r"- Computed Normalized: **`0.5021 / 0.4979`**" "\n"
            r"- Published Narrative: **`0.5019 / 0.4981`**" "\n\n"
            r"**Mathematical Cause:**" "\n"
            r"In the text below Table 3, the paper contains an explicit author typographical error:" "\n"
            r"$$\Pr(B_1 \to S_2 \to V_3 \to S_6) = 1 \cdot 0.7085 \cdot 0.7085 \cdot 0.23998 \cdot 0.23998 = 0.0289$$"
            r"The author accidentally typed $0.23998$ ($\Pr(V_3)$) twice instead of using $\Pr(S_6) = 0.23899$. "
            r"Our implementation uses the actual node posteriors from Equation (5) without hardcoding the typographical error."
        )

    with st.expander("3. Missing Source Data in Reference Paper", expanded=True):
        st.markdown(
            "- **Experiment 1 (DARPA / LLDOS):** The paper omitted all 46-variable numerical transition matrices and directed readers to Refs [25, 31].\n"
            "- **Experiment 2 (BX1 Posteriors):** The authors explicitly omitted the entire node posterior table under $BX_1$ 'due to space limitations'.\n"
            "- **Experiment 3 (Baseline CPTs):** Ref [35] Bayesian attack graph matrices were not printed in the paper text."
        )
