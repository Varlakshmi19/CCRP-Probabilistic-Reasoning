# Stage 4 Mathematical Verification Report: CCRP & Probability Calculations

**Reference Paper:** Dong, C., Feng, Y., & Shang, W. (2024). *A new method of dynamic network security analysis based on dynamic uncertain causality graph.* Journal of Cloud Computing, 13:24.  
**DOI:** [10.1186/s13677-023-00568-7](https://doi.org/10.1186/s13677-023-00568-7)  
**Modules Verified:** `src/ccrp.py`, `src/probability_calculations.py`  
**Test Suites:** `tests/test_probabilities.py` (9 tests), `tests/test_ccrp.py` (9 tests), plus existing `test_graph.py` (18 tests) and `test_simplification.py` (22 tests) — **58 / 58 passing**.

---

## 1. Equations Verified Against the Paper

| Equation | Paper Name / Definition | Mathematical Form | Implementation Function |
|---|---|---|---|
| **Eq. (1)** | Weighted causal function variable factor $F_{n;i}$ | $F_{n;i} = \left(\frac{r_{n;i}}{r_n}\right) A_{n;i}$ | `compute_edge_factor` in `src/probability_calculations.py` |
| **Eq. (3)** | Causal-Chains decomposition | $\text{Causal-Chains}(X_v) = \sum \text{UCC}(X_v) + \sum \text{ECC}(X_v) + \sum \text{HCC}(X_v)$ | `sum_all_chains` in `src/probability_calculations.py` |
| **Eq. (4)** | Invalid chain elimination | $\text{Causal-Chains}(X_v)^* = \sum \text{ECC}(X_v) + \sum \text{HCC}(X_v)$ | `eliminate_ucc_chains` in `src/probability_calculations.py` |
| **Eq. (5)** | CCRP node posterior probability | $\Pr(X_v) = \frac{\text{Causal-Chains}(X_v)^*}{N} = \frac{\sum\text{ECC}(X_v) + \sum\text{HCC}(X_v)}{N}$ | `calculate_ccrp_posterior` in `src/probability_calculations.py` |
| **Eq. (6)** | Attack scenario probability | $\Pr(AttackSeq_i) = \Pr(B_i) \times \Pr(S_1) \times \Pr(V_1) \times \dots \times \Pr(S_k) \times \Pr(V_k)$ | `calculate_attack_path_probability` in `src/probability_calculations.py` |
| **Eq. (7)** | Multi-hypothesis path aggregation | $\Pr(AttackSeq_i)^* = \sum_{k}^{\{B\}} \Pr(AttackSeq_i \mid B_k) \Pr(B_k)$ | `aggregate_hypothesis_path_probabilities` in `src/probability_calculations.py` |
| **Step 4** | Posterior normalization | $\Pr(AttackSeq_i)_{\text{norm}} = \frac{\Pr(AttackSeq_i)^*}{\sum_j \Pr(AttackSeq_j)^*}$ | `normalize_probabilities` in `src/probability_calculations.py` |

---

## 2. Meaning and Distinction of Probability Values

The implementation strictly maintains the separation required by the project specification:

1. **Causal association degrees ($r$):** Positive structural strengths ($r_{n;i} > 0$). In the toy example, $r = 1$ everywhere.
2. **Transition probability parameters ($A$):** Edge conditional parameters $A_{n,k;i,j} \in [0, 1]$ stored on graph edges.
3. **Initial / prior probabilities:**
   - Root hypotheses ($B_i$): Attacker capability / strategy prior $\Pr(B_i)$ (set to $1.0$ in Table 3 calibration).
   - Observed alarms / evidence ($E$): State fixed to $1.0$ per Section 3.7 ("Evidence variable blue; state = 1").
4. **Intermediate chain values:** Products along individual causal paths: $\Pr(\text{start}) \times \prod_{\text{hops}} A_{\text{hop}}$.
5. **Node posterior probabilities ($\Pr(X_v)$):** Obtained via Equation (5) by dividing retained chain sums by $N$.
6. **Attack scenario probabilities ($\Pr(AttackSeq_i)$):** Product of node posteriors along candidate sequences per Equation (6).
7. **Normalized scenario probabilities:** Scaled probabilities across candidate attack paths summing to $1.0$.

---

## 3. Independent Step-by-Step Recomputation (Table 3 Worked Example)

### Graph Parameters (Dong et al., Table 2 + narrative)
- Hypotheses: $B_1$ ($\Pr(B_1)=1.0$)
- Evidence: $V_4$ (alarm state = 1)
- Transitions:
  - $B_1 \to V_1 = 0.845$
  - $V_1 \to S_2 = 1.0$
  - $S_2 \to V_3 = 0.284$
  - $S_2 \to V_4 = 0.572$
  - $V_4 \to S_5 = 1.0$
  - $V_3 \to S_6 = 1.0$
  - $S_5 \to V_7 = 0.238$
  - $V_7 \to S_6 = 1.0$ (narrative edge)
  - Other branches ($B_2 \to V_8$, $S_7 \to V_6$) are pruned by simplification under evidence $V_4$.

### Independent Node Calculations:

#### 1. $B_1$ (Root hypothesis)
- Rule: Root hypothesis prior
- **Posterior:** $\Pr(B_1) = \mathbf{1.0}$
- *Published Table 3:* $1$

#### 2. $V_1$
- Upstream: $B_1 \to V_1$ (reaches hypothesis $B_1 \implies$ **HCC**, value $= 1.0 \times 0.845 = 0.845$)
- Downstream 1: $V_1 \to S_2 \to V_4$ (reaches evidence $V_4 \implies$ **ECC**, value $= 1.0 \times 0.572 = 0.572$)
- Downstream 2: $V_1 \to S_2 \to V_3 \to S_6$ (reaches terminal sink without evidence $\implies$ **UCC**, value $= 0.284$, **discarded**)
- Retained sum: $0.845 + 0.572 = 1.417$
- Distinct hypotheses: $\{B_1\}$ (1), Distinct evidence: $\{V_4\}$ (1) $\implies N = 2$
- **Posterior:** $\Pr(V_1) = \frac{1.417}{2} = \mathbf{0.7085}$
- *Published Table 3:* $\frac{1}{2}(A_{1;1} + A_{2;1} A_{4,1;2}) = \frac{1}{2}(0.845 + 0.572) = \mathbf{0.7085}$

#### 3. $S_2$
- Upstream: $B_1 \to V_1 \to S_2$ (HCC, value $= 0.845 \times 1.0 = 0.845$)
- Downstream 1: $S_2 \to V_4$ (ECC, value $= 0.572$)
- Downstream 2: $S_2 \to V_3 \to S_6$ (UCC, discarded)
- Retained sum: $0.845 + 0.572 = 1.417$
- Distinct entities: $\{B_1, V_4\} \implies N = 2$
- **Posterior:** $\Pr(S_2) = \frac{1.417}{2} = \mathbf{0.7085}$
- *Published Table 3:* $\frac{1}{2}(A_{1;1} A_{2;1} + A_{4,1;2}) = \mathbf{0.7085}$

#### 4. $V_3$
- Upstream: $B_1 \to V_1 \to S_2 \to V_3$ (HCC, value $= 0.845 \times 1.0 \times 0.284 = 0.23998$)
- Downstream: $V_3 \to S_6$ (UCC, discarded)
- Retained sum: $0.23998$
- Distinct entities: $\{B_1\} \implies N = 1$
- **Posterior:** $\Pr(V_3) = \frac{0.23998}{1} = \mathbf{0.23998}$
- *Published Table 3:* $A_{1;1} A_{2;1} A_{3;2} = \mathbf{0.23998}$

#### 5. $V_4$
- Rule: Observed evidence alarm event (blue node)
- **Posterior:** $\Pr(V_4) = \mathbf{1.0}$
- *Published Table 3:* $1$

#### 6. $S_5$
- Upstream: $V_4 \to S_5$ (starts at evidence $V_4 \implies$ **ECC**, value $= 1.0 \times 1.0 = 1.0$)
- Downstream: $S_5 \to V_7 \to S_6$ (UCC, discarded)
- Retained sum: $1.0$
- Distinct entities: $\{V_4\} \implies N = 1$
- **Posterior:** $\Pr(S_5) = \frac{1.0}{1} = \mathbf{1.0}$
- *Published Table 3:* $A_{5;4,1} = \mathbf{1}$

#### 7. $V_7$
- Upstream: $V_4 \to S_5 \to V_7$ (starts at evidence $V_4 \implies$ **ECC**, value $= 1.0 \times 1.0 \times 0.238 = 0.238$)
- Downstream: $V_7 \to S_6$ (UCC, discarded)
- Retained sum: $0.238$
- Distinct entities: $\{V_4\} \implies N = 1$
- **Posterior:** $\Pr(V_7) = \frac{0.238}{1} = \mathbf{0.238}$
- *Published Table 3:* $A_{5;4,1} A_{7;5} = \mathbf{0.238}$

#### 8. $S_6$
- Upstream 1: $B_1 \to V_1 \to S_2 \to V_3 \to S_6$ (HCC from $B_1$, value $= 0.845 \times 1.0 \times 0.284 \times 1.0 = 0.23998$)
- Upstream 2: $V_4 \to S_5 \to V_7 \to S_6$ (ECC from $V_4$, value $= 1.0 \times 1.0 \times 0.238 \times 1.0 = 0.238$)
- Downstream: none (sink)
- Retained sum: $0.23998 + 0.238 = 0.47798$
- Distinct entities: $\{B_1, V_4\} \implies N = 2$
- **Posterior:** $\Pr(S_6) = \frac{0.47798}{2} = \mathbf{0.23899}$
- *Published Table 3:* $\frac{1}{2} A_{1;1} A_{2;1} A_{3;2} A_{6;3} + \frac{1}{2} A_{5;4,1} A_{7;5} A_{6;7} = \mathbf{0.23899}$

---

## 4. Verification Summary Table

| Node | Paper Causal-Chain Expression | Paper Posterior | Independently Computed | Match Status |
|---|---|---|---|---|
| $B_1$ | — | $1$ | $1.00000$ | **Exact** |
| $V_1$ | $\frac{1}{2}(A_{1;1} + A_{2;1} A_{4,1;2})$ | $0.7085$ | $0.70850$ | **Exact** |
| $S_2$ | $\frac{1}{2}(A_{1;1} A_{2;1} + A_{4,1;2})$ | $0.7085$ | $0.70850$ | **Exact** |
| $V_3$ | $A_{1;1} A_{2;1} A_{3;2}$ | $0.23998$ | $0.23998$ | **Exact** |
| $V_4$ | — | $1$ | $1.00000$ | **Exact** |
| $S_5$ | $A_{5;4,1}$ | $1$ | $1.00000$ | **Exact** |
| $V_7$ | $A_{5;4,1} A_{7;5}$ | $0.238$ | $0.23800$ | **Exact** |
| $S_6$ | $\frac{1}{2} A_{1;1} A_{2;1} A_{3;2} A_{6;3} + \frac{1}{2} A_{5;4,1} A_{7;5} A_{6;7}$ | $0.23899$ | $0.23899$ | **Exact** |

---

## 5. Candidate Attack Path Verification (Equation 6 & Normalization)

### Candidate Path 1: $B_1 \to V_1 \to S_2 \to V_3 \to S_6$
- Equation (6) product:
  $$\Pr(\text{Path 1}) = 1.0 \times 0.7085 \times 0.7085 \times 0.23998 \times 0.23899 = \mathbf{0.0287818}$$
- Paper narrative printed value: $0.0289$ (see Discrepancy Note below).

### Candidate Path 2: $B_1 \to V_1 \to S_2 \to V_4 \to S_5 \to V_7 \to S_6$
- Equation (6) product:
  $$\Pr(\text{Path 2}) = 1.0 \times 0.7085 \times 0.7085 \times 1.0 \times 1.0 \times 0.238 \times 0.23899 = \mathbf{0.0285437}$$
- Paper narrative printed value: $0.02867$.

### Normalized Probabilities:
- Sum: $0.0287818 + 0.0285437 = 0.0573255$
- Normalized Path 1: $0.0287818 / 0.0573255 = \mathbf{0.502078}$
- Normalized Path 2: $0.0285437 / 0.0573255 = \mathbf{0.497922}$
- Published normalized probabilities: $\mathbf{0.5019}$ and $\mathbf{0.4981}$
- Absolute difference: $|\Delta| = 0.000178 \ll 10^{-3}$ tolerance.

---

## 6. Discrepancies and Clarifications

### Discrepancy A: Table 2 Missing Edge $V_7 \to S_6$
- **Finding:** Table 2 lists 10 edges, omitting $V_7 \to S_6$. However, the narrative text directly following Table 2 and Table 3 explicitly describes Path 2 as $B_1 \to V_1 \to S_2 \to V_4 \to S_5 \to V_7 \to S_6$ and includes $A_{6;7} = 1.0$ in the formula for $S_6$.
- **Handling in Code:**
  - `experiments/paper_data/table2_fig1_partial.json` strictly preserves the printed Table 2 text without modifying the raw JSON.
  - A calibrated test fixture `table3_calibrated_ducag` in `tests/test_ccrp.py` adds the narrative edge $V_7 \to S_6$ ($r=1.0, p=1.0$) to verify exact reproduction of Table 3.
  - An independent test `test_table2_raw_without_narrative_edge` verifies that running on the unaugmented Table 2 graph correctly produces $\Pr(S_6) = 0.23998$ ($N=1$).

### Discrepancy B: Paper Narrative Hand-Calculation Typo
- **Finding:** In the paragraph below Table 3, the paper prints:
  $$\Pr(B_1 \to S_2 \to V_3 \to S_6) = 1 \cdot 0.7085 \cdot 0.7085 \cdot 0.23998 \cdot 0.23998 = 0.0289$$
  Notice that:
  1. Node $V_1$ was omitted from the path label string (written as $B_1 \to S_2\dots$), but its posterior $0.7085$ was included in the numeric product.
  2. The posterior $0.23998$ (which belongs to $V_3$) was accidentally typed twice instead of using $\Pr(S_6) = 0.23899$.
  3. The resulting rounded numbers ($0.0289$ and $0.02867$) produce $0.0289 / (0.0289 + 0.02867) = 0.501997 \approx 0.5019$.
- **Handling in Code:**
  - The algorithm does NOT hardcode intermediate rounded values or copy the text typo.
  - It multiplies the actual node posteriors from Equation (5), producing $0.02878$ and $0.02854 \implies 0.5021$ ($0.5019 \pm 0.00018$).
  - This matches within the documented $10^{-3}$ tolerance.

---

## 7. Assumptions Identified

1. **Definition of $N$:**  
   $N$ is the count of distinct root hypotheses and distinct evidence nodes appearing in retained chains ($N = |\mathcal{H}(X_v)| + |\mathcal{E}(X_v)|$). This reproduces the $1/2, 1/3, 1/4$ fractional coefficients in Tables 3 and 8 without invention.
2. **Chain Product Parameters:**  
   Along individual causal chain hops, transition probability parameters $A_{n;i}$ are multiplied. Weighting across alternative chains is performed by dividing by $N$ in Equation (5).
3. **Evidence Boundary Condition:**  
   Observed evidence alarm nodes have posterior fixed to $1.0$ (state = 1).
4. **Hypothesis Boundary Condition:**  
   Root hypothesis nodes retain their prior ($\Pr(B_1) = 1.0$).

---

## 8. Final Verification Status

- **Stage 4 CCRP Mathematics:** **VERIFIED**
- **Table 3 Node Posteriors:** **8 / 8 EXACT MATCHES**
- **Attack Scenario Probabilities:** **VERIFIED (within $0.00018 \ll 10^{-3}$)**
- **Test Suite:** **58 / 58 PASSING**
