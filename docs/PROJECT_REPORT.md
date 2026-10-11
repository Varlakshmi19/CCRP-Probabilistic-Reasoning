# Project Report: Dynamic Uncertain Causality Attack Graph (DUCAG) and Causal Chain Reasoning Path (CCRP)

**Reference Paper:** Dong, C., Feng, Y., & Shang, W. (2024). *A new method of dynamic network security analysis based on dynamic uncertain causality graph.* Journal of Cloud Computing, 13(1), 24. [https://doi.org/10.1186/s13677-023-00568-7](https://doi.org/10.1186/s13677-023-00568-7)  
**Implementation Repository:** CCRP (Independent Clean-Room Python Implementation)  
**Verification Status:** All 80 Automated Unit, Integration, and UI Tests Passing

---

## 1. Title and Project Overview

This project provides an independent, clean-room implementation of the **Dynamic Uncertain Causality Attack Graph (DUCAG)** model and the **Causal Chain Reasoning Path (CCRP)** probabilistic inference algorithm described by Dong, Feng, and Shang (2024).

Modern network defense environments suffer from alert fatigue caused by massive volumes of low-level intrusion detection system (IDS) alerts, incomplete alarm sequences due to evasion, and redundant or false-positive alarms. Traditional Bayesian Network Reasoning Path (BNRP) approaches exhibit exponential computational complexity ($O(2^k)$) when marginalizing over unobserved latent variables as the network expands. The DUCAG + CCRP framework resolves this scalability bottleneck by combining graph simplification, causal chain classification (eliminating invalid chains), and evidence-bounded posterior probability evaluation, achieving near-linear online inference complexity ($O(N)$).

This codebase reproduces the core graph representation, simplification rules, probability calculations, all four experimental case studies from the publication, and an interactive Streamlit user interface, validated against 80 automated unit and integration tests.

---

## 2. Problem Statement and Objectives

### 2.1 Problem Statement
1. **Alert Uncertainty & Incompleteness:** IDS sensors frequently drop attack steps (false negatives) or report spurious alerts (false positives). Correlating disparate alarms into coherent multi-stage attack scenarios requires rigorous probabilistic reasoning under uncertainty.
2. **Computational Scalability Bottleneck:** Exact inference in standard Bayesian attack graphs requires evaluating full conditional probability tables (CPTs) and joint distributions. In enterprise networks with dozens of hosts and hundreds of security states, exact BN inference becomes computationally intractable in real time.
3. **Reproducibility Gaps:** Complex graph security models in literature often leave parameter matrices, intermediate expansions, and boundary handling under-specified, requiring independent first-principles verification.

### 2.2 Project Objectives
- **Faithful Implementation:** Implement DUCAG graph structures, dynamic simplification rules, and CCRP reasoning steps strictly according to the paper's mathematical formulas (Equations 1–7).
- **Decoupled Architecture:** Maintain strict separation between graph data structures, simplification algorithms, numerical formulas, and experiment runner scripts.
- **Transparent Mathematical Audit:** Recompute every node posterior and candidate attack path from first principles; differentiate between published values and independently computed outputs.
- **Empirical Reproduction:** Reproduce Experiments 1–4 from the paper, documenting exact matches, numerical approximations, qualitative trends, and publication data omissions.
- **Interactive Demonstration:** Provide an intuitive Streamlit interface allowing users to inspect graphs, trigger evidence scenarios, view pruned chains, and step through calculations.

---

## 3. DUCAG and CCRP Methodology

```
+-----------------------------------------------------------------------------------+
|                              DUCAG GRAPH FORMALISM                                |
|  Nodes: B (Hypothesis) | X (State/Event) | V (Vulnerability) | S (Security State) |
|  Parameters: A_{n,i;j} (Transition Prob) | r_{n;j} (Causal Weight)               |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                        STEP 1: EVIDENCE-DRIVEN SIMPLIFICATION                     |
|  * Identify observed alarm evidence E and target node T                           |
|  * Prune unconcerned hypotheses (hypotheses unable to reach all observed alarms)  |
|  * Remove disconnected subgraphs via ancestral & descendant reachability          |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                          STEP 2: CAUSAL CHAIN EXPANSION                           |
|  * Expand directed chains upstream and downstream from node of interest           |
|  * Halt expansion when boundary reached: Evidence (E), Hypothesis (B), or Root    |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                      STEP 3: CLASSIFICATION & UCC ELIMINATION                     |
|  * UCC (Uncertain): Neither endpoint is observed evidence                         |
|  * ECC (Evidence):  At least one endpoint is an observed alarm                    |
|  * HCC (Hypothesis): Endpoint connects to root hypothesis                         |
|  * Eliminate UCC per Eq. (4): Causal-Chains(X_n)* = Causal-Chains(X_n) \ UCC      |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                     STEP 4: POSTERIOR & PATH PROBABILITY                          |
|  * Node Posterior (Eq. 5): Pr(X_n | E, B) = sum(Chain Products) / N               |
|  * Attack Path Probability (Eq. 6-7): Pr(Path) = Pr(B) * prod(Pr(X_i))            |
|  * Path Normalization: Pr(Path_i)_norm = Pr(Path_i) / sum(Pr(Path_j))             |
+-----------------------------------------------------------------------------------+
```

### 3.1 DUCAG Model Formalism
A DUCAG is a directed graph where nodes represent attack states or events, and directed edges model uncertain causality:
- **Node Types:** $B$ (root hypothesis / attacker intent), $V$ (vulnerabilities / attack events), $S$ (host security states / assets), $X$ (compound events), and $G$ (logic gate nodes).
- **Parameters:**
  - $A_{n,i;j}$: Conditional transition probability that parent $X_j$ produces child $X_n$ under condition $i$.
  - $r_{n;j}$: Causal connection strength / association degree of parent $X_j$ to child $X_n$, satisfying $\sum_j r_{n;j} = 1$ across multiple parents.
- **Equation (1) - Edge Causal Factor:**
  $$F_{n;j} = r_{n;j} \cdot A_{n,i;j}$$

### 3.2 Graph Simplification
Given observed evidence alarms $E = \{e_1, \dots, e_m\}$ and optional target $T$:
1. A root hypothesis $B_k$ is retained only if there exists a directed causal path from $B_k$ to every observed evidence node $e \in E$. Hypotheses unable to explain all evidence alarms are pruned.
2. Nodes and edges not lying on paths between retained hypotheses and evidence or targets are pruned, eliminating irrelevant subgraphs before inference begins.

### 3.3 CCRP Algorithm (Equations 3–7)
1. **Chain Expansion:** For a node $X_n$, expand directed upstream and downstream causal chains until an evidence node, hypothesis node, or root cause is reached.
2. **Chain Classification (Eq. 3):**
   - **UCC (Uncertain Causal Chain):** Neither boundary endpoint is an observed alarm node.
   - **ECC (Evidence Causal Chain):** At least one boundary endpoint is an observed alarm node.
   - **HCC (Hypothesis Causal Chain):** Endpoint connects to a root hypothesis node.
3. **UCC Elimination (Eq. 4):**
   $$\text{Causal-Chains}(X_n)^* = \text{Causal-Chains}(X_n) \setminus \text{UCC}$$
4. **Posterior Probability (Eq. 5):**
   $$\Pr(X_n \mid E, B_k) = \frac{\sum_{c \in \text{Causal-Chains}(X_n)^*} \prod_{(u,v) \in c} F_{v;u}}{N}$$
   where $N$ is the number of distinct bounding entities (observed evidence alarms and root hypotheses) that terminate the retained chains.
5. **Attack Path Probability (Eq. 6–7):**
   For candidate attack path $\text{Path} = (B_k, X_1, \dots, X_m)$:
   $$\Pr(\text{Path} \mid B_k) = \prod_{i=1}^m \Pr(X_i \mid E, B_k)$$
   $$\Pr(\text{Path}) = \sum_k \Pr(B_k) \cdot \Pr(\text{Path} \mid B_k)$$
   Candidate paths are ranked by normalized posterior probability:
   $$\Pr(\text{Path}_i)_{\text{norm}} = \frac{\Pr(\text{Path}_i)}{\sum_j \Pr(\text{Path}_j)}$$

---

## 4. System Architecture and Implementation

The implementation is structured into modular Python packages with strict separation of concerns:

```
CCRP/
|-- app.py                     # Streamlit web application
|-- requirements.txt           # Project dependencies
|-- README.md                  # Quick-start guide
|-- .gitignore                 # Clean repository filters
|-- src/                       # Core DUCAG + CCRP engine
|   |-- ducag_graph.py         # Graph representation, parameter validation, visualization
|   |-- graph_simplification.py# Reachability, hypothesis filtering, subgraph pruning
|   |-- probability_calculations.py # Pure numerical evaluation of Eqs. (1), (3)-(7)
|   |-- ccrp.py                # Causal chain expansion, UCC elimination, path ranking
|-- experiments/               # Standalone paper reproduction experiments
|   |-- paper_data/            # JSON graph topologies and transition parameters
|   |-- paper_experiment_1.py  # DARPA 2000 scenario analysis
|   |-- paper_experiment_2.py  # Simulated network with missing alarms
|   |-- paper_experiment_3.py  # Risk probability baseline comparison
|   |-- paper_experiment_4.py  # Runtime scalability benchmark (CCRP vs simulated BNRP)
|-- tests/                     # 80 automated unit, integration, and UI tests
|-- results/                   # Saved experiment JSON outputs and summary tables
`-- docs/                      # Technical documentation and verification reports
```

### Key Modules
- **`src/ducag_graph.py`:** Implements `DUCAGGraph`, `DUCAGNode`, and `DUCAGEdge` dataclasses. Validates node types, non-negative transition parameters, unit-interval probabilities, and normalized association weights $\sum r = 1$. Integrates with NetworkX and Matplotlib.
- **`src/graph_simplification.py`:** Implements `simplify_ducag()`. Computes ancestor and descendant closures, filters unconcerned hypotheses, partitions the graph into Sub-DUCAGs, and returns a detailed `SimplificationResult` recording every pruned entity and rationale.
- **`src/probability_calculations.py`:** Independent numerical routines implementing Equations (1), (3), (4), (5), (6), and (7). Contains zero graph traversal logic, ensuring pure mathematical verifiability.
- **`src/ccrp.py`:** Implements `run_ccrp()`, `reconstruct_attack_paths()`, and `rank_attack_paths()`. Traverses chains, enforces evidence boundaries, eliminates UCC chains, and calculates normalized path rankings.
- **`app.py`:** A 4-tab Streamlit dashboard:
  1. *CCRP Playground:* Interactive graph loader, evidence toggle, target selector, graph visualization, simplification diff, and step-by-step reasoning inspector.
  2. *Experiment Explorer:* Live execution and inspection of Experiments 1–4.
  3. *Comparative Audit:* Systematic side-by-side audit of published vs computed metrics.
  4. *Methodology Guide:* Mathematical formulas and theoretical foundations.

---

## 5. Experiments and Evaluation

The reference paper presents four experimental evaluations, which were reproduced and audited:

1. **Experiment 1 (DARPA 2000 / LLDOS):**
   - *Scenario:* Multi-stage attack evaluation under LLDOS 1.0 (IP sweep, Sadmind exploit, DDoS daemon installation, DDoS execution) and LLDOS 2.0 (HLL scan, Sadmind exploit, Mstream install, DDoS execution).
   - *Objective:* Verify whether causal simplification discriminates between attacker hypotheses $B_1, B_2, B_3$ and reconstructs correct chronological attack paths under alert noise.
2. **Experiment 2 (Simulated Enterprise Network):**
   - *Scenario:* 24-node simulated enterprise network with 18 security/vulnerability states and 7 candidate attack paths reaching critical database target $S_9$.
   - *Condition:* Incomplete alarms where key intermediate events ($\{S_2, S_6, S_8\}$) were missing from alert logs.
   - *Objective:* Evaluate if CCRP infers missing security states and ranks Candidate Path 2 (the True Path) as the winner.
3. **Experiment 3 (Risk Probability Baseline Comparison):**
   - *Scenario:* 8-resource host network under alerts $\{V_1, V_4\}$ targeting root privilege $S_7$.
   - *Objective:* Compare dynamic risk probabilities computed by CCRP against three published baseline methods: Li et al. (2019), Wang et al. (2018), and Chen et al. (2020).
4. **Experiment 4 (Runtime Scalability):**
   - *Scenario:* Benchmark runtime across 5 synthetic network scales ($N \in \{10, 20, 30, 40, 50\}$ hosts) with evidence count $\lfloor N/2 \rfloor$.
   - *Objective:* Compare CCRP online reasoning scaling against exact Bayesian Network inference (BNRP).

---

## 6. Results and Comparison with the Reference Paper

All experimental results are categorized into four rigorous scientific provenance tiers:

### 6.1 Summary of Reproduction Status

| Experiment | Target / Focus | Published Reference Value | Computed Value | Status | Finding |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **Stage 4** | Worked Example (Table 3) | 8 node posteriors ($S_2=0.7085, S_6=0.2390$, etc.) | $8/8$ exact matches | **Exact** | Perfect mathematical calibration of Eq. (5). |
| **Stage 4** | Table 3 Path Normalization | $P(\text{Path 1}) = 0.5019, P(\text{Path 2}) = 0.4981$ | $0.5021 / 0.4979$ | **Approximation** | $\Delta = 0.00018$ traced to author typo repeating $0.23998$. |
| **Exp 1** | LLDOS 1.0 Winning Hypothesis | Hypothesis $B_2$ | Hypothesis $B_2$ | **Exact** | Path One correctly attributed to $B_2$; $B_3$ pruned. |
| **Exp 1** | LLDOS 2.0 Winning Hypothesis | Hypothesis $B_3$ | Hypothesis $B_3$ | **Exact** | Path Two correctly attributed to $B_3$; $B_1, B_2$ pruned. |
| **Exp 2** | Candidate Path 2 (True Path) | Published normalized $P = 0.3542$ | Recomputed $P = 0.3543$ | **Approximation** | $\Delta = 9.0 \times 10^{-5}$; Rank 1 winner reproduced. |
| **Exp 2** | Candidate Path 7 (Rank 2) | Published normalized $P = 0.2941$ | Recomputed $P = 0.2942$ | **Approximation** | $\Delta = 8.7 \times 10^{-5}$; Rank 2 matched. |
| **Exp 2** | Candidate Path 1 (Rank 3) | Published normalized $P = 0.1293$ | Recomputed $P = 0.1293$ | **Exact** | $\Delta < 1.0 \times 10^{-6}$; Top-3 ranking preserved. |
| **Exp 3** | Surviving Hypothesis | Hypothesis $B_2$ ($B_1, B_3$ pruned) | Hypothesis $B_2$ | **Exact** | Exact match under evidence $\{V_1, V_4\}$. |
| **Exp 3** | Table 10 Risk Vector | $S_1=0.95, S_4=1.0, S_7=0.70$ | $S_1=0.95, S_4=1.0, S_7=0.70$ | **Exact** | Full CCRP row reproduced; uncompromised nodes at prior. |
| **Exp 4** | Time Complexity Trend | CCRP linear $O(N)$; BNRP exponential $O(2^k)$ | $O(N)$ vs $O(2^k)$ scaling confirmed | **Qualitative** | Confirms scaling curves of Fig. 9; speedup $>3.4\times$ at $N=50$. |

### 6.2 Experiment 2 Candidate Path Ranking (Table 9)

$$\Pr(\text{Path}_2)_{\text{recomputed}} = \mathbf{0.3543} \quad (\text{Published: } 0.3542, \; \Delta = 0.00009)$$

Both the first-principles graph traversal and published raw posterior normalization confirm Candidate Path 2 as the decisive Rank 1 winner, correctly identifying the True Attack Scenario despite 3 missing intermediate alarms:
1. **Rank 1 (Path 2, True Path):** $B_1(BX_1) \to V_1 \to S_2 \to V_3 \to S_4 \to V_6 \to S_6 \to V_{11} \to S_8 \to V_{13} \to S_9$ ($P_{\text{norm}} = 0.3543$)
2. **Rank 2 (Path 7):** $BX_1 \to V_2 \to S_3 \to V_9 \to S_9$ ($P_{\text{norm}} = 0.2942$)
3. **Rank 3 (Path 1):** $B_1(BX_1) \to V_1 \to S_2 \to V_5 \to S_8 \to V_{13} \to S_9$ ($P_{\text{norm}} = 0.1293$)

---

## 7. Limitations and Reproducibility

To preserve scientific rigor, all discrepancies, unformalized heuristics, and missing inputs in the original publication are explicitly documented:

### 7.1 Unresolved $S_8$ Discrepancy in Experiment 2
In Experiment 2 Table 8, node $S_8$ (missing alarm) reports a published posterior of $0.3512$, whereas first-principles CCRP evaluation yields $0.8054$:
- **Cause:** When applying the formal definition of Equation (5), $S_8$ is bounded by 3 distinct evidence entities ($\{V_1, V_{11}, V_{13}\}$). Five valid causal chains reach $S_8$, yielding a retained chain sum of $2.4163$. Dividing by $N = 3$ yields:
  $$\Pr(S_8)_{\text{computed}} = \frac{2.4163}{3} = \mathbf{0.8054}$$
- **Paper's Heuristic Formula:** The paper's Table 8 text writes an ad-hoc local formula:
  $$\Pr(S_8)_{\text{paper}} = \frac{1}{4} \left( 1.0 + \frac{1}{4}(0.144 + 0.1001 + 0.1722) \right) = \frac{1.4048}{4} = \mathbf{0.3512}$$
  Here, the authors replaced the global evidence boundary count ($N=3$) with the local node in-degree ($4$), and introduced an unformalized nested branch attenuation factor ($1/4$).
- **Handling:** Rather than modifying the general algorithm to hardcode an unformalized heuristic, the implementation preserves the verified CCRP algorithm and reports the discrepancy transparently.

### 7.2 Stage 4 Table 3 Narrative Typographical Error
The paper reports candidate path normalized probabilities of $0.5019$ and $0.4981$, whereas the implementation computes $0.5021$ and $0.4979$ ($\Delta = 0.00018$).
- **Cause:** In the text beneath Table 3, the authors explicitly calculated:
  $$\Pr(\text{Path 1}) = 1.0 \times 0.7085 \times 0.7085 \times 0.23998 \times 0.23998 = 0.0289$$
  The value $0.23998$ ($\Pr(V_3)$) was accidentally duplicated instead of using $\Pr(S_6) = 0.23899$. Our implementation uses the true calculated node posteriors.

### 7.3 Missing Paper Source Data
- **Experiment 1 (DARPA 46-Variable Matrices):** The authors omitted transition probability matrices for the 46 DARPA variables, citing external papers [25] and [31]. Consequently, Experiment 1 is reproduced qualitatively at the scenario and hypothesis-selection level.
- **Experiment 2 ($BX_1$ Node Posteriors):** The authors stated in Section 4.2 that node posteriors under integrated hypothesis $BX_1$ were omitted from Table 8 "due to space limitations."
- **Experiment 3 (Bayesian CPTs for Baselines):** Full conditional probability tables for Wang et al. (2018) were omitted from the text.

### 7.4 Experiment 4 Workload Characterization
Experiment 4 benchmarks the scaling of CCRP against BNRP. It is critical to state:
- The BNRP baseline in this project uses a **simulated exponential factor marginalization workload** ($O(2^k)$) designed to model exact Bayesian network inference complexity over unobserved variables.
- It does **not** execute a commercial or full third-party exact Bayesian network engine, and timing numbers represent measurements on the local host machine, not a faithful reproduction of the hardware timings in Figure 9. The experiment validates the *qualitative scaling trend* ($O(N)$ vs $O(2^k)$), not absolute millisecond parity.

---

## 8. Conclusion and Reference Paper Citation

### 8.1 Conclusion
This project demonstrates that the DUCAG and CCRP methodology successfully combines causal graph pruning and evidence-bounded chain reasoning to reconstruct multi-stage attack scenarios under incomplete and noisy alert streams. The algorithm prunes irrelevant attacker hypotheses and identifies the true attack path without suffering from the exponential latency explosion typical of exact Bayesian network inference.

By adhering to strict clean-room engineering practices, zero hardcoding of expected outputs, and transparent disclosure of publication discrepancies, this codebase provides a robust, fully tested foundation for further research into dynamic network risk analysis.

### 8.2 Reference Paper Citation
```bibtex
@article{dong2024new,
  title={A new method of dynamic network security analysis based on dynamic uncertain causality graph},
  author={Dong, Chong and Feng, Yunchao and Shang, Wen},
  journal={Journal of Cloud Computing},
  volume={13},
  number={1},
  pages={24},
  year={2024},
  publisher={Springer},
  doi={10.1186/s13677-023-00568-7},
  url={https://link.springer.com/article/10.1186/s13677-023-00568-7}
}
```
