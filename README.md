# DUCAG + CCRP: Dynamic Network Security Analysis

An independent, clean-room Python implementation of the **Dynamic Uncertain Causality Attack Graph (DUCAG)** model and the **Causal Chain Reasoning Path (CCRP)** probabilistic inference algorithm, based on the research paper:

> Dong, C., Feng, Y., & Shang, W. (2024). *A new method of dynamic network security analysis based on dynamic uncertain causality graph.* Journal of Cloud Computing, 13(1), 24. [https://doi.org/10.1186/s13677-023-00568-7](https://doi.org/10.1186/s13677-023-00568-7)

---

## Overview

Modern Security Operations Centers (SOCs) face alert fatigue from massive volumes of noisy, incomplete, or redundant IDS alerts. Traditional Bayesian network approaches incur exponential computational overhead ($O(2^k)$) when reasoning across unobserved latent variables. 

The DUCAG + CCRP framework addresses this challenge through:
1. **Dynamic Graph Simplification:** Pruning unconcerned attacker hypotheses and irrelevant subgraphs using observed evidence alerts.
2. **Causal Chain Classification & Elimination:** Systematically expanding causal chains, classifying them into UCC, ECC, and HCC, and eliminating uncertain causal chains (UCC).
3. **Linear-Time Online Inference:** Evaluating evidence-bounded posterior probabilities and ranking candidate attack paths in near-linear time ($O(N)$).

---

## Main Features

- **DUCAG Graph Construction (`src/ducag_graph.py`):** Represents multi-type nodes ($B, X, V, S, G$) with conditional transition probabilities ($A$) and causal association degrees ($r$). Includes parameter validation, JSON serialization, and Matplotlib visualization.
- **Evidence-Driven Simplification (`src/graph_simplification.py`):** Filters hypotheses and subgraphs based on observed alerts, outputting detailed pruning summaries and Sub-DUCAG decompositions.
- **Mathematical Formulation (`src/probability_calculations.py`):** Decoupled numerical routines for Equations (1) through (7) with strict unit-interval validation.
- **CCRP Reasoning Engine (`src/ccrp.py`):** Causal chain expansion, UCC elimination, posterior calculation, and candidate attack path ranking.
- **Four Paper Experiments (`experiments/`):** Standalone reproducible scripts for DARPA/LLDOS scenario analysis, incomplete alarm reconstruction, risk probability comparisons, and runtime scalability.
- **Interactive Streamlit Web UI (`app.py`):** Visual graph inspector, evidence/target toggles, step-by-step reasoning explanations, and live experiment viewers.
- **Comprehensive Test Suite (`tests/`):** 80 automated unit, integration, and UI tests.

---

## Prerequisites

- **Python:** Version 3.10 or higher (tested on Python 3.10 – 3.14 on Windows).
- **Operating System:** Windows, macOS, or Linux.
- **PowerShell Execution Policy (Windows):** If PowerShell prevents script execution, enable execution for the current user:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

---

## Quick Start (Windows PowerShell)

### 1. Clone Repository & Setup Virtual Environment
Open Windows PowerShell in the project directory:

```powershell
# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1
```

*(For macOS/Linux, activate via `source .venv/bin/activate`)*

### 2. Install Dependencies
```powershell
python -m pip install -r requirements.txt
```

### 3. Run Automated Tests
```powershell
python -m pytest -v
```
*Expected: 80 passed tests across unit, integration, and UI test suites.*

### 4. Launch Streamlit Web UI
```powershell
python -m streamlit run app.py
```
This opens the interactive dashboard in your default browser (typically at `http://localhost:8501`).

---

## Repository Structure

```
CCRP/
|-- app.py                          # Streamlit interactive UI application
|-- requirements.txt                # Python package dependencies
|-- README.md                       # Project overview and setup instructions
|-- .gitignore                      # Git exclusion rules
|-- src/                            # Core DUCAG + CCRP implementation
|   |-- ducag_graph.py              # Graph data structure, validation & plotting
|   |-- graph_simplification.py     # Subgraph reachability & hypothesis pruning
|   |-- probability_calculations.py # Formulas for Equations (1), (3)-(7)
|   |-- ccrp.py                     # Causal chain expansion & path ranking
|-- experiments/                    # Paper experiment reproduction scripts
|   |-- paper_experiment_1.py       # Exp 1: DARPA/LLDOS scenario construction
|   |-- paper_experiment_2.py       # Exp 2: Simulated network (incomplete alarms)
|   |-- paper_experiment_3.py       # Exp 3: Risk probability comparison
|   |-- paper_experiment_4.py       # Exp 4: Runtime scalability benchmark
|   `-- paper_data/                 # Input graph definitions and parameter JSONs
|-- results/                        # Saved experiment outputs and figures
|   |-- experiment_1_results.json
|   |-- experiment_2_results.json
|   |-- experiment_3_results.json
|   |-- experiment_4_results.json
|   `-- experiment_summary_tables.md
|-- tests/                          # 80 automated unit, integration, and UI tests
|   |-- test_graph.py
|   |-- test_simplification.py
|   |-- test_probabilities.py
|   |-- test_ccrp.py
|   |-- test_experiments.py
|   `-- test_ui.py
`-- docs/                           # Documentation and technical reports
    |-- PROJECT_REPORT.md           # Formal project report (2-3 pages)
    |-- final_results_comparison.md # Detailed experimental audit and provenance
    |-- stage4_verification.md      # Mathematical derivation of worked examples
    `-- paper_algorithm_mapping.md  # Section-by-section mapping to paper
```

---

## Comprehensive Project Report

For the formal 2–3 page project report detailing the problem statement, mathematical derivations, architecture, experiment comparisons, and reproduction audit, see:

- **[docs/PROJECT_REPORT.md](docs/PROJECT_REPORT.md)**

Additional technical audits and derivation notes are available in:
- [docs/final_results_comparison.md](docs/final_results_comparison.md) (comprehensive experimental results audit)
- [docs/stage4_verification.md](docs/stage4_verification.md) (Table 3 worked example verification)
- [results/experiment_summary_tables.md](results/experiment_summary_tables.md) (summary tables)

---

## Note on Experiment Limitations & Reproducibility

1. **Unresolved $S_8$ Discrepancy (Exp 2):** Applying the paper's formal Equation (5) yields $\Pr(S_8) = 0.8054$, whereas the paper's Table 8 reports $0.3512$ by substituting an ad-hoc local in-degree divisor ($4$) and nested sub-branch fraction ($1/4$). The general CCRP algorithm was preserved rather than hardcoding unformalized heuristics.
2. **Missing Author Data:** Transition matrices for the 46 DARPA variables (Exp 1), full $BX_1$ posteriors (Exp 2), and exact conditional probability tables for baselines (Exp 3) were omitted from the publication text.
3. **Simulated BNRP Workload (Exp 4):** Experiment 4 uses a simulated exponential factor marginalization workload ($O(2^k)$) to model exact Bayesian network computational scaling against latent variables; it does not execute a commercial Bayesian inference engine, and reported timings reflect local benchmark measurements confirming the qualitative scaling trend of Figure 9.
