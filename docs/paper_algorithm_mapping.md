# Paper Algorithm Mapping — DUCAG and CCRP

**Paper:** Dong, C., Feng, Y., & Shang, W. (2024). *A new method of dynamic network security analysis based on dynamic uncertain causality graph.* Journal of Cloud Computing, 13:24.  
**DOI:** [10.1186/s13677-023-00568-7](https://doi.org/10.1186/s13677-023-00568-7)  
**Open access PDF:** https://journalofcloudcomputing.springeropen.com/counter/pdf/10.1186/s13677-023-00568-7.pdf

**Stage:** 1 (paper study only — no implementation)  
**Legend:**
- **[VERIFIED]** — stated explicitly in the reference paper (text, equations, or readable tables).
- **[NEEDS VERIFICATION]** — incomplete, ambiguous, figure-only, OCR-corrupted, or deferred to cited works.
- **[EXTERNAL]** — required detail lives mainly in cited references, not fully reproduced in this paper.

---

## 1. DUCAG construction

### 1.1 Formal definition **[VERIFIED]**

**Definition 1.**  
\[
\text{DUCAG} = (N, E)
\]
where \(N\) is the set of nodes (variables) and \(E\) is the set of directed causal edges (weighted function variables).

### 1.2 Node / variable types **[VERIFIED]** (Table 1)

| Symbol | Role | Notes from paper |
|--------|------|------------------|
| **X** | Observable / causal variable | In attack graphs: **S** = resource/state node; **V** = attack-behavior (atomic attack) node |
| **B** | Root-cause event hypothesis | Attacker strategy / capability assumption; indexed \(B_i\) |
| **G** | Logic gate | Encodes AND / OR / XOR (etc.) among parents and child |
| \(r_{n;i}\) | Causal association degree | Strength of parent \(i\) on child \(n\); \(r_n = \sum_p r_{n;p}\) |
| \(F_{n;i} \equiv (r_{n;i}/r_n) A_{n;i}\) | Weighted function variable (directed edge) | Two usages: state→attack transition; attack→state transition |
| \(A_{n,k;i,j}\) | Uncertain causal mechanism | Parent \(X_i\) in state \(j\) independently causing child \(X_n\) in state \(k\) |
| Transition probability matrices | Numerical parameters of \(A\) | From statistical learning or domain knowledge |

**Integrated hypothesis variable BX** (used in Experiment 2) **[VERIFIED]:**  
\(BX_1\) represents the attacker simultaneously applying both \(v_1\) and \(v_2\) strategies.

### 1.3 State encoding used in Experiment 1 **[VERIFIED]**

| Variable class | States (paper wording) |
|----------------|------------------------|
| Resource (S / part of X) | TRUE = normal; FALSE = abnormal |
| Atomic attack (V / part of X) | FALSE = attack launched; TRUE = attack not launched |
| B-type | At least two states: attack not launched / attack launched |

### 1.4 Graph construction procedure (LLDOS / general) **[VERIFIED]**

Paper steps for building a DUCG/DUCAG causality graph:

1. Determine \(\{X(S,V), B\}\)-type variables.
2. Partition variables into states (binary for S and V in Experiment 1).
3. Assign prior / state probabilities for each B-type variable.
4. For each X-type variable, build a subgraph:
   1. Select an atomic-attack (V) module variable.
   2. Identify parents from already defined \(\{X,B\}\).
   3. Connect parents to child \(X_n\) via action / conditional action variables; optionally introduce G.
   4. Determine association degrees \(r\) and transition probability matrices.
   5. Merge subgraphs into one complete causality graph.

**Parameter source for Experiment 1 matrices:** paper says *Refer to [25, 31]* **[EXTERNAL / NEEDS VERIFICATION]**.

### 1.5 Illustrative toy graph (Fig. 1 + Table 2) **[VERIFIED]**

Evidence example: IDS detects \(V_4\) (blue evidence node, state set to 1).  
Causal effect weights in the worked example are set to \(r = 1\).

**Table 2 — transition probabilities (toy example):**

| Attack path | Transition probability | Attack path | Transition probability |
|-------------|------------------------|-------------|------------------------|
| \(B_1 \to V_1\) | 0.845 | \(S_2 \to V_3\) | 0.284 |
| \(V_1 \to S_2\) | 1 | \(S_2 \to V_4\) | 0.572 |
| \(V_4 \to S_5\) | 1 | \(S_7 \to V_6\) | 1 |
| \(V_3 \to S_6\) | 1 | \(S_5 \to V_7\) | 0.238 |
| \(B_2 \to V_8\) | 0.155 | \(V_8 \to S_5\) | 1 |

---

## 2. Graph simplification algorithms

### 2.1 Stated goal **[VERIFIED]**

Causality simplification eliminates causalities and events that are:

- unconcerned,
- unreasonable, or
- inconsistent with observed evidence,

citing DUCG theory **[21]** (Dong et al., 2018 / related DUCG simplification literature).

### 2.2 Decomposition by hypothesis **[VERIFIED]**

If the graph is large and contains multiple independent root hypotheses, decompose into **multiple sub-DUCAGs**, one per root-event hypothesis \(B_i\) (or \(BX_i\)).

### 2.3 Evidence-driven removal (Fig. 2 narrative) **[VERIFIED]**

1. Start from original DUCAG.
2. Mark observed alarms as evidence (blue nodes) over time \(T_i\).
3. Remove events irrelevant to the observed evidence and the concerned hypothesis → simplified attack causality graph.
4. **Hypothesis pruning example (Fig. 2 note):** at time \(T_3\), hypothesis \(B_1\) can no longer explain all observed alarms → remove \(B_1\) and its simplified graph; retain only \(BX_1\) and its simplified graph.

### 2.4 Exact numbered simplification rule list **[NEEDS VERIFICATION / EXTERNAL]**

The paper **does not enumerate** the full DUCG simplification rule set (commonly ~10–11 rules in DUCG literature). It refers readers to **[21]** (and more generally Zhang/Dong DUCG papers).

**Implementation implication:** Stage 3 must either:

1. reconstruct operational rules from paper figures + experiments, and/or  
2. consult DUCG references [18–21] and document which rules are actually used in the paper’s experiments.

**Do not invent simplification rules.** Anything not shown by the paper or cited DUCG rules must be flagged as unresolved.

### 2.5 Observed simplification outcomes in experiments **[VERIFIED]**

| Experiment | Evidence | Simplification outcome (paper) |
|------------|----------|--------------------------------|
| Exp. 1 Path One | \(X_4, X_{11}, X_{26}, X_{40}\) (among others) | Only \(B_2\) holds; scenario \(B_2 \to X_9 \to X_{10} \to X_{11} \to X_4(X_{26}, X_{40})\) |
| Exp. 1 Path Two | alarm sequence in Table 5 | Max-posterior path \(B_3 \to X_{16} \to \ldots \to X_{29}\) |
| Exp. 2 Path 1 | \(\{V_1,V_3,S_4,V_6,V_{11},V_{13},S_9\}\); missing \(S_2,S_6,S_8\) | Fig. 6 simplified DUCAG (figure-only topology details) |
| Exp. 3 | \(o_1,o_4\) ↔ \(V_1,V_4\); target \(S_7\) | Fig. 8; **only \(B_2\)** explains all evidence |

---

## 3. CCRP algorithm — step-by-step with paper equations

CCRP = **Causal Chain-based Risk Probability Calculation**.  
Posterior of a node is determined by **both** root hypothesis and evidence.

### 3.1 High-level CCRP steps **[VERIFIED]**

1. Expansion of the causal chain of nodes  
2. Elimination of invalid causal chains  
3. Calculation of the posterior probability based on the causal chains  

### 3.2 Prerequisite: hypothesis-state inference (formulas 1–2)

Used when computing \(\Pr(H_{i,j}\mid E)\) via weighted logical inference **[21]**.

#### Formula (1) — event-level expansion of \(X_{n,k}\) **[VERIFIED]**

\[
X_{n,k}
=
\sum_p
\left(
\frac{r_{n;p}}{r_n}
\right)
\sum_q
A_{n,k;p,q}\,\rho_{p,q}
\]

where:

- \(\displaystyle r_n = \sum_p r_{n;p}\)
- \(\rho_{p,q}\): parent \(\rho\) in state \(q\)
- \(A_{n,k;p,q}\): causal function of \(\rho_{p,q}\) causing \(X_{n,k}\)

#### Formula (2) — posterior of hypothesis given evidence **[VERIFIED]**

\[
h_{i.j}^{s}
\equiv
\Pr\{H_{i,j}\mid E\}
=
\frac{\Pr\{H_{i,j}E\}}{\Pr\{E\}}
=
\frac{\Pr\{H_{i,j}\cap X_{p,q}\}}{\Pr\{\cap X_{p,q}\}}
\]

**Probabilistic step:** replace variables by prior numerical values, algebraically evaluate, then **normalize**.

### 3.3 Step A — causal-chain expansion **[VERIFIED]**

Logical reasoning expands expressions of a concerned variable **upward and backward** until a:

- root-cause node, or  
- terminal node, or  
- evidence node  

is reached.

Three chain categories:

| Abbreviation | Name | Meaning |
|--------------|------|---------|
| **UCC** | Unknown Causal Chains | Expansion includes neither evidence nor hypothesis events |
| **ECC** | Evidence Causal Chains | Chain includes evidence events |
| **HCC** | Hypothesis Causal Chains | Chain includes hypothesis events |

#### Formula (3) **[VERIFIED]**

\[
\text{Causal-Chains}(X_v)
=
\sum \text{UCC}(X_v)
+
\sum \text{ECC}(X_v)
+
\sum \text{HCC}(X_v)
\]

Probabilistic reasoning then substitutes prior probabilities into retained chains.

### 3.4 Step B — eliminate invalid chains **[VERIFIED]**

Invalid chains = **UCC** (treated as redundant for attack-event posterior calculation).

#### Formula (4) **[VERIFIED]**

\[
\text{Causal-Chains}(X_v)^{*}
=
\sum \text{ECC}(X_v)
+
\sum \text{HCC}(X_v)
\]

### 3.5 Step C — posterior from retained chains **[VERIFIED]**

#### Formula (5) **[VERIFIED]**

\[
\Pr(X_v)
=
\frac{\text{Causal-Chains}(X_v)^{*}}{N}
=
\frac{\sum\text{ECC}(X_v)+\sum\text{HCC}(X_v)}{N}
\]

**Definition of \(N\) (paper wording):**  
\(N\) is the **sum of all distinct evidence nodes and hypotheses** in the causal chains associated with the current node.

**Weighting interpretation [VERIFIED]:** dividing by \(N\) automatically assigns different weights to chains; more evidence chains raise relative weight; hypothesis-chain weight is reduced when many distinct evidence chains are present.

**Ambiguity [NEEDS VERIFICATION]:**

- Exact counting rule for “distinct” evidence/hypotheses when the same node appears in multiple products.
- Whether chain values are products of transition parameters only, or also include other DUCG logical operators.
- How evidence nodes with posterior fixed to 1 enter both numerator and \(N\).

Worked Tables 3 and 8 are the primary ground truth for resolving this during Stage 4.

### 3.6 Attack scenario reconstruction (formulas 6–7 + Steps 1–4)

#### Formal attack sequence **[VERIFIED]**

\[
Attack = \{B_i \to S_1 \to V_1 \to \ldots \to S_n \to V_n\}
\]

#### Step 1 **[VERIFIED]**  
Use alarm node sequence at \(T_i\) as evidence → simplify graph → run CCRP for each node posterior.

#### Step 2 — path probability **[VERIFIED]** — Formula (6)

\[
\Pr(AttackSeq_i)
=
\Pr(B_i)\times\Pr(S_1)\times\Pr(V_1)\times\ldots\times\Pr(S_k)\times\Pr(V_k)
\]

#### Step 3 — scale when same path appears under multiple hypotheses **[VERIFIED]** — Formula (7)

\[
\Pr(AttackSeq_i)^{*}
=
\sum_{i,k}^{\{B\}}
\Pr(B_i)\times\Pr(S_1)\times\Pr(V_1)\times\ldots\times\Pr(S_k)\times\Pr(V_k)
\]

where \(\{B\}\) is the hypothesis space.

#### Step 4 **[VERIFIED]**  
Normalize path posteriors; select the sequence with **maximum** posterior as the constructed attack scenario.

### 3.7 Worked numerical example (Fig. 1 / Tables 2–3) **[VERIFIED]**

Assumptions stated by paper:

- Evidence variable blue; state = 1  
- Attacker uses \(B_1\) → set \(\Pr(B_1)=1\)  
- \(r=1\)

**Table 3 node posteriors:**

| Node | Causal-chain expression | Posterior |
|------|-------------------------|-----------|
| \(B_1\) | — | 1 |
| \(V_1\) | \(\frac12(A_{1;1}+A_{2;1}A_{4,1;2})\) | \(\frac12(0.845\cdot1+0.572)=0.7085\) |
| \(S_2\) | \(\frac12(A_{1;1}A_{2;1}+A_{4,1;2})\) | \(\frac12(0.845\cdot1+0.572)=0.7085\) |
| \(V_3\) | \(A_{1;1}A_{2;1}A_{3;2}\) | \(0.845\cdot1\cdot0.284=0.23998\) |
| \(V_{4,1}\) | — | 1 |
| \(S_5\) | \(A_{5;4,1}\) | \(1\cdot1=1\) |
| \(S_6\) | \(\frac12 A_{1;1}A_{2;1}A_{3;2}A_{6;3}+\frac12 A_{5;4,1}A_{7;5}A_{6;7}\) | \(\frac12(0.845\cdot1\cdot0.284\cdot1+0.238)=0.23899\) |
| \(V_7\) | \(A_{5;4,1}A_{7;5}\) | \(1\cdot0.238=0.238\) |

Paths from \(B_1\) to \(S_6\) (paper text):

1. \(B_1\to V_1\to S_2\to V_3\to S_6\)  
2. \(B_1\to V_1\to S_2\to V_4\to S_5\to V_7\to S_6\)

Published products (notation in paper is slightly inconsistent with full path labels — see ambiguities):

\[
\Pr(B_1\to S_2\to V_3\to S_6)
=
1\cdot0.7085\cdot0.7085\cdot0.23998\cdot0.23998
=
0.0289
\]

\[
\Pr(B_1\to V_1\to S_2\to V_4\to S_6)
=
1\cdot0.7085\cdot0.7085\cdot1\cdot1\cdot0.238\cdot0.23998
=
0.02867
\]

After normalization:

\[
0.5019,\quad 0.4981
\]

---

## 4. The four experiments — inputs and published results

### 4.1 Experiment 1 — DARPA / LLDOS attack-scenario construction

**Purpose [VERIFIED]:** Qualitative validation on DARPA2000 / LLDOS using causal network from Ref **[25]**; approach aligned with Ref **[33]**.

**Graph:** Fig. 3 LLDOS DUCAG; variables Table 4; logic gates \(G_1=X_3\cup X_{11}\), \(G_2=X_{11}\cup X_{18}\), \(G_3=X_{11}\cup X_{25}\) **[VERIFIED from extracted Table 4 / figure captions]**.

**Process [VERIFIED]:**

1. Initialize simulated attack sequences and alarm sequences  
2. DUCAG reasoning → node posteriors  
3. Highest-posterior node sequence vs simulated attack  

#### Table 5 configuration **[VERIFIED with parsing caveats]**

| Item | Path One | Path Two |
|------|----------|----------|
| Simulate attack sequence | Starts \(B_1,X_9,X_{10},X_{11},X_4,\ldots\) (full list in paper Table 5) | Starts \(B_2\) / related LLDOS2.0 partial alarms (paper Table 5) |
| Attack alert sequence | \(X_{11},X_{26},X_{40},X_4\) with listed missing alarms | \(X_{17},X_{18},X_{31},X_{32},X_{37},X_{34},X_{29},X_{36},X_{39},X_{42},X_{43},X_{46}\) with missing \(X_{16},X_{44},X_{45}\) |
| Candidate / published scenario | \(B_2\to X_9\to X_{10}\to X_{11}\to X_4(X_{26},X_{40})\) | \(B_3\to X_{16}\to X_{17}\to X_{18}\to X_{26}\to X_{31}\to X_{32}\to X_{37}\to X_{34}\to X_{29}\) |

**Published result type:** qualitative path identity (not a numeric probability table for Exp. 1).

**Missing for faithful reproduction [NEEDS VERIFICATION / EXTERNAL]:**

- Exact full edge list of Fig. 3  
- Exact transition matrices (deferred to [25, 31])  
- Numeric posteriors for Path Two (paper asserts max posterior without publishing the full probability vector)

---

### 4.2 Experiment 2 — simulated network attack-scenario construction (PRIMARY incomplete-alarm case)

**Purpose [VERIFIED]:** Reproduce Ref **[25]** small-scale attack–defense causal network as DUCAG; test missing/redundant alarms.

**Graph sources:** Fig. 5 (causal knowledge net → DUCAG); Path 1 simplified Fig. 6.

#### Table 6 transition probabilities **[VERIFIED]**

| Attack path | P | Attack path | P |
|-------------|---|-------------|---|
| \(BX_1\to V_1\) | 1 | \(BX_1\to V_2\) | 1 |
| \(G_1\to BX_1\) | 0.5 | \(B_2\to V_2\) | 0.155 |
| \(B_1\to V_1\) | 0.845 | \(S_2\to V_3\) | 0.284 |
| \(V_2\to S_3\) | 1 | \(S_2\to V_5\) | 0.144 |
| \(V_3\to S_4\) | 1 | \(S_3\to V_9\) | 1 |
| \(V_4\to S_5\) | 1 | \(S_4\to V_6\) | 1 |
| \(V_5\to S_8\) | 1 | \(S_5\to V_7\) | 0.238 |
| \(V_6\to S_6\) | 1 | \(S_5\to V_8\) | 0.301 |
| \(V_7\to S_6\) | 1 | \(S_5\to V_9\) | 0.286 |
| \(V_8\to S_7\) | 1 | \(S_5\to V_{10}\) | 0.175 |
| \(V_9\to S_9\) | 1 | \(S_6\to V_{11}\) | 1 |
| \(V_{10}\to S_8\) | 1 | \(S_7\to V_{12}\) | 1 |
| \(V_{13}\to S_9\) | 1 | \(S_8\to V_{13}\) | 1 |

Logic gate in this experiment: **AND** (attacker takes multiple strategies) **[VERIFIED]**.

**Simulated attack paths [VERIFIED]:**

1. \(B_1\to V_1\to S_2\to V_3\to S_4\to V_6\to S_6\to V_{11}\to S_8\to V_{13}\to S_9\)  
2. \(B_1\to V_1\to S_2\to V_5\to S_8\to V_{13}\to S_9\)  
3. \(B_1\to V_1\to S_2\to V_4\to S_5\to V_8\to S_7\to V_{12}\to S_8\to V_{13}\to S_9\)

#### Path 1 incomplete-alarm case (PROJECT_SPEC required case) **[VERIFIED]**

| Field | Value |
|-------|-------|
| True / simulated path | \(B_1\to V_1\to S_2\to V_3\to S_4\to V_6\to S_6\to V_{11}\to S_8\to V_{13}\to S_9\) |
| Observed evidence | \(\{V_1, V_3, S_4, V_6, V_{11}, V_{13}, S_9\}\) |
| Missing alarms | \(S_2, S_6, S_8\) |
| Target | \(S_9\) |
| Hypotheses considered | \(BX_1, B_1, B_2\) (paper: 7 candidate paths to \(S_9\)) |

**Table 8 — Path 1 node posteriors under hypothesis \(B_1\) [VERIFIED]:**

| Node | Expression (as printed) | Posterior |
|------|-------------------------|-----------|
| \(V_1\) | — | 1 |
| \(S_2\) | \(\frac14(A_{2;1,1}+A_{4,1;2}+A_{3,1;2}+\frac14 A_{5;2}A_{8;5}A_{13,1;5})\) | 0.473 |
| \(V_5\) | \(\frac12(A_{2;1,1}A_{5,2}+\frac14 A_{8;5}A_{13,1;8})\) | 0.197 |
| \(V_3\) | — | 1 |
| \(V_4\) | — | 1 |
| \(S_4\) | — | 1 |
| \(S_5\) | \(\frac13(A_{5;4}+\frac12 A_{7;5}A_{6;7}A_{11,1;6}+\frac14 A_{8;5}A_{7;8}A_{12;7}A_{8;12}A_{13;8}+\frac14 A_{10;5}A_{8;10}A_{13,1;8})\) | 0.4126 |
| \(V_6\) | — | 1 |
| \(V_7\) | \(\frac12(A_{5;4}A_{7;5}+\frac12 A_{11,1;6}A_{6;7})\) | 0.369 |
| \(V_8\) | \(\frac12(A_{5;4}A_{8;5}+\frac14 A_{13,1;8}A_{8;12}A_{12;7}A_{7;8})\) | 0.2755 |
| \(V_{10}\) | \(\frac12(A_{5;4}A_{10;5}+\frac14 A_{8;10}A_{13,1;8})\) | 0.2125 |
| \(S_6\) | \(\frac13(\frac12 A_{5;4}A_{7;5}A_{6;7}+\frac12 A_{6,6}+A_{11,1;6})\) | 0.5396 |
| \(S_7\) | \(\frac12(A_{5;4}A_{8;5}A_{7;8}+\frac14 A_{13,1;8}A_{8;12}A_{12;7})\) | 0.2755 |
| \(V_{11}\) | — | 1 |
| \(V_{12}\) | \(\frac12(A_{5;4}A_{8;5}A_{7;8}A_{12;7}+\frac14 A_{13,1;8}A_{8;12})\) | 0.2755 |
| \(S_8\) | \(\frac14(A_{13,1;8}+\frac14(\ldots))\) | **0.3512** **[NEEDS DIGIT CHECK]** — HTML/PDF text extraction sometimes showed `3512` without leading `0.` |
| \(V_{13}\) | — | 1 |
| \(S_9\) | — | 1 |

\(BX_1\) calculation omitted in paper “due to space” **[NEEDS VERIFICATION]**.

**Table 9 — Path 1 attack-scenario calculation [VERIFIED]:**

| Candidate path | Path posterior | Normalized |
|----------------|----------------|------------|
| \(B_1(BX_1)\to V_1\to S_2\to V_5\to S_8\to V_{13}\to S_9\) | 0.0654 | 0.1293 |
| \(B_1(BX_1)\to V_1\to S_2\to V_3\to S_4\to V_6\to S_6\to V_{11}\to S_8\to V_{13}\to S_9\) | 0.1792 | **0.3542** |
| \(B_1(BX_1)\to V_1\to S_2\to V_4\to S_5\to V_7\to S_6\to V_{11}\to S_8\to V_{13}\to S_9\) | 0.0249 | 0.0492 |
| \(B_1(BX_1)\to V_1\to S_2\to V_4\to S_5\to V_8\to S_7\to V_{12}\to S_8\to V_{13}\to S_9\) | 0.0025 | 0.0049 |
| \(B_1(BX_1)\to V_1\to S_2\to V_3\to S_5\to V_{10}\to S_8\to V_{13}\to S_9\) | 0.0261 | 0.0516 |
| \(BX_1\to V_1\to S_2\to V_4\to S_5\to V_9\to S_9\) | 0.0589 | 0.1164 |
| \(BX_1\to V_2\to S_3\to V_9\to S_9\) | 0.1488 | **0.2941** |

**Top-3 published candidates for Path 1 [VERIFIED]:**

1. \(B_1(BX_1)\to V_1\to S_2\to V_3\to S_4\to V_6\to S_6\to V_{11}\to S_8\to V_{13}\to S_9\) — **0.3542**  
2. \(BX_1\to V_2\to S_3\to V_9\to S_9\) — **0.2941**  
3. \(B_1(BX_1)\to V_1\to S_2\to V_5\to S_8\to V_{13}\to S_9\) — **0.1293**

#### Table 7 — all three simulated paths **[VERIFIED / one digit NEEDS CHECK]**

| Simulation path | Alarm sequence | Best candidates (paper) |
|-----------------|----------------|-------------------------|
| Path 1 | \(V_1\to V_3\to S_4\to V_6\to V_{11}\to V_{13}\to S_9\) (missing \(S_2,S_6,S_8\)) | 0.3542 / 0.2941 / 0.1293 (as above) |
| Path 2 | \(V_1\to S_2\to V_5\to V_3\to S_8\to V_{13}\to S_9\) (redundant \(V_3\)) | \(B_1\to\ldots\to S_9\) **0.8839**; \(BX_1\to V_2\to S_3\to V_9\to S_9\) **0.0622** |
| Path 3 | \(V_1\to S_2\to S_5\to V_9\to V_8\to S_8\to V_{13}\to S_9\) (redundant \(V_9\); missing \(V_4,S_7,V_{12}\)) | Top path printed as **`(1882)`** in several extractions — almost certainly **0.1882** **[NEEDS VERIFICATION against PDF]**; also 0.1207, 0.3449, 0.2409 |

Paper states top Path-1 candidates match Ref **[25]**.

---

### 4.3 Experiment 3 — risk-probability comparison

**Purpose [VERIFIED]:** Compare CCRP node risk probabilities vs Refs **[32], [35], [36]** on network from Ref **[35]**.

**Graph:** Fig. 7(a) Bayesian attack graph → Fig. 7(b) DUCAG; simplified Fig. 8 under evidence.

**Inputs [VERIFIED]:**

| Field | Value |
|-------|-------|
| Target | workstation root permission ↔ \(S_7\) |
| Evidence alarms | \(o_1, o_4\) ↔ nodes \(V_1, V_4\) |
| Surviving hypothesis after simplification | \(B_2\) only |

**Most probable attack path [VERIFIED]:**

\[
B_2 \to V_1 \to S_1 \to V_4 \to S_4 \to V_8 \to S_7
\]

#### Table 10 — published risk probabilities **[VERIFIED]**

| Method | \(S_1\) | \(S_2\) | \(S_3\) | \(S_4\) | \(S_5\) | \(S_6\) | \(S_7\) | \(S_8\) |
|--------|------|------|------|------|------|------|------|------|
| Node prior | 0.650 | 0.900 | 0.500 | 0.846 | 0.630 | 0.485 | 0.593 | 0.466 |
| Ref [32] | 0.928 | 0.900 | 0.500 | 0.939 | 0.630 | 0.485 | 0.657 | 0.466 |
| Ref [35] | 0.970 | 0.900 | 0.500 | 0.979 | 0.630 | 0.485 | 0.685 | 0.466 |
| Ref [36] | 1.000 | 0.900 | 0.500 | 0.900 | 0.630 | 0.485 | 0.630 | 0.466 |
| **CCRP** | **0.950** | **0.900** | **0.500** | **1.000** | **0.630** | **0.485** | **0.700** | **0.466** |

**Table 11 [VERIFIED]:** qualitative feature comparison (shortest route / most possible route / evidence association / dynamic update). CCRP marked yes for all four listed features.

**Missing for faithful reproduction [NEEDS VERIFICATION / EXTERNAL]:**

- Full edge set and transition parameters of Fig. 7(b) / Fig. 8  
- Exact priors for V-nodes and B-hypotheses  
- Intermediate CCRP chain expressions for Exp. 3 (not tabulated like Tables 3/8)

---

### 4.4 Experiment 4 — runtime / time-complexity comparison

**Purpose [VERIFIED]:** Compare CCRP vs Bayesian Network-based Risk Probability (**BNRP**) on random DAGs.

**Environment [VERIFIED]:**

- OS: Windows 11  
- CPU: 12th Gen Intel Core i7-12700 @ 2.10 GHz  
- RAM: 16.00 GB (15.7 GB available)  
- Tools: Python 3.10, PyCharm  

**Setup [VERIFIED]:**

- Random directed **acyclic** networks of different scales  
- Add nodes without forming loops; add directed edges to existing nodes  
- Evidence count = **half the number of hosts**  
- **25** experiment groups  

**Published results [VERIFIED qualitatively; quantitative values figure-only]:**

- Fig. 9(a): CCRP elapsed time lower than BNRP at same host/evidence counts  
- Fig. 9(b): natural-log scale; CCRP described as approximately **linear** growth  
- Claimed online complexity after precomputation: **\(O(N)\)** vertex-set traversal  

**Numeric millisecond tables are not printed in text** **[NEEDS VERIFICATION]** — must digitize Fig. 9 or treat Exp. 4 as trend reproduction, not exact-number match.

---

## 5. Formulas, graphs, parameters, and evidence checklist per experiment

| Experiment | Formulas | Graphs | Parameters | Evidence / targets | Published outputs to match |
|------------|----------|--------|------------|--------------------|----------------------------|
| Toy example (method section) | (1)–(7); Tables 2–3 | Fig. 1 | Table 2; \(r=1\); \(\Pr(B_1)=1\) | \(V_4\) evidence | Node posteriors Table 3; path probs 0.0289/0.02867 → 0.5019/0.4981 |
| Exp. 1 | Simplification + scenario construction; (1)–(7) as applicable | Fig. 3, Fig. 4 | Table 4 vars; matrices from [25,31] | Table 5 alarm sequences | Candidate paths Path One / Path Two |
| Exp. 2 | CCRP (3)–(5); scenario (6)–(7) | Fig. 5, Fig. 6 | Table 6; AND gate \(G_1\) | Paths 1–3; Path 1 evidence set above | Tables 7–9 probabilities |
| Exp. 3 | CCRP (3)–(5); scenario ranking | Fig. 7, Fig. 8 | priors in Table 10; other params from [35] | \(V_1,V_4\); target \(S_7\) | Table 10 CCRP row; path \(B_2\to\ldots\to S_7\) |
| Exp. 4 | Complexity claims | Fig. 9 | Random DAG generator settings | Evidence = hosts/2; 25 groups | Trend: CCRP faster / near-linear vs BNRP |

---

## 6. Missing or ambiguous items in the paper

### 6.1 Critical gaps for implementation **[NEEDS VERIFICATION]**

1. **Full enumerated DUCG simplification rules** — referenced to [21], not listed.  
2. **Exact topology of large figures** (Figs. 3, 5–8) — edges must be recovered from figures or source papers [25], [35].  
3. **Experiment 1 transition matrices** — deferred to [25], [31].  
4. **Experiment 3 full parameter set** beyond Table 10 priors — deferred to [35] / figures.  
5. **Definition of \(N\) in Eq. (5)** — “sum of all distinct evidence nodes and hypotheses”; counting edge cases unclear.  
6. **Upward and backward expansion** — directionality and stopping conditions need precise operationalization from Tables 3/8.  
7. **\(BX_1\) Path-1 posterior table omitted** — needed to regenerate Table 9 from first principles.  
8. **Table 7 Path 3 leading probability** printed as `1882` in text extractions → likely `0.1882`.  
9. **Table 8 \(S_8\)** may be `0.3512` (digit corruption risk).  
10. **Inconsistent path notation** in toy example products vs stated full paths (nodes omitted/inserted).  
11. **Experiment 4 numeric timings** only in Fig. 9 — no table of (hosts, time) pairs.  
12. **BNRP baseline algorithm details** — “fundamental algorithm” of [24], [35]; exact BN inference variant not specified (variable elimination? junction tree?).  
13. **State TRUE/FALSE polarity** for V/S is unusual (attack launched = FALSE); must not silently invert.  
14. **Whether \(r_{n;i}\) defaults to 1** outside the toy example — Exp. 2 expressions suggest fractional weights like \(1/2,1/3,1/4\) come from \(N\) and/or multiple parents, but mapping is not fully spelled out.

### 6.2 What is *not* missing (verified enough to proceed later)

- CCRP’s three-step structure and Eqs. (3)–(5)  
- Attack reconstruction Steps 1–4 and Eqs. (6)–(7)  
- Exp. 2 Path 1 evidence, missing alarms, target, and top-3 probabilities  
- Exp. 3 Table 10 CCRP outputs and winning path  
- Exp. 4 experimental protocol (qualitative)

### 6.3 Explicit non-claims (do not invent)

- Do **not** invent missing transition probabilities.  
- Do **not** invent Fig. 9 millisecond values.  
- Do **not** replace CCRP with shortest-path / naive edge-weight products / generic Bayesian updates.  
- Do **not** hardcode expected finals into the algorithm core (comparison tables are separate).

---

## 7. Source-trace summary

| Content | Status |
|---------|--------|
| DUCAG definition, Table 1 roles | VERIFIED |
| Eqs. (1)–(7) | VERIFIED |
| CCRP UCC/ECC/HCC + invalid=UCC | VERIFIED |
| Tables 2, 3, 6, 9, 10, 11 | VERIFIED (readable) |
| Tables 5, 7, 8 | VERIFIED with noted digit/topology caveats |
| Fig. 3–9 exact edges / plotted points | NEEDS VERIFICATION (figure digitization / cited papers) |
| Full simplification rule catalog | EXTERNAL ([21] / DUCG literature) |
| Exp. 1 & 3 full numeric parameters | EXTERNAL ([25], [31], [35]) |

---

*End of Stage 1 paper mapping. No algorithm code was implemented in this stage.*
