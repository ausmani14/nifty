# Phase 9 — Step 4: Incremental News Predictive-Value Evaluation Report

**Document Date**: September 18, 2026  
**Auditor / Senior Quantitative ML Research Engineer**: Senior ML/Quant Software Engineer & Data Provenance Auditor  
**Governing Phase**: Phase 9 — Point-in-Time News Feature Engineering & Incremental Predictive Evaluation  
**Status**: EXPERIMENTAL EVALUATION COMPLETE — FORENSIC AUDIT SUBMITTED  
**Classification Verdict**: **`B) NO ROBUST INCREMENTAL VALUE / C) NEWS DEGRADES PERFORMANCE`**  

---

## 1. Executive Summary & Forensic Verdict

This forensic report delivers the definitive empirical evaluation of whether authentic, point-in-time (PIT) news NLP features provide statistically and economically meaningful incremental out-of-sample predictive value for next-day NIFTY 50 direction and returns beyond the already validated Price + Context baseline.

The experiment was conducted in strict adherence to the pre-registered methodology approved in the **Methodology Reconciliation & Pre-Execution Gate Report**. All model hyperparameters, tree counts ($N^* = 12$ for Classifier, $N^* = 43$ for Regressor), sample partitions, and disjoint feature definitions were frozen prior to running any evaluations. Probability calibrations were fitted strictly within the Development Out-Of-Fold (OOF) framework, and the Terminal Holdout (`2022-01-03` to `2026-09-03`, 1,154 sessions) was subjected to a single, un-tuned forward evaluation pass.

### Primary Forensic Findings:

1. **Central Scientific Comparison ($\text{Model 1} \to \text{Model 2}$)**:
   - **Snapshot A (15:40 IST Cutoff)**:
     - **OOF Validation (`2014–2021`)**: $\Delta \text{LogLoss} = -0.00007$ (Bootstrap 95% CI: `[-0.00150, +0.00171]`, Cohen's d = `+0.002`, **not statistically significant**, spans zero). Diebold-Mariano test on returns: HLN statistic = `-0.215`, $p = 0.8301$ (**not significant**). $\Delta \text{Pearson IC} = -0.00336$ (Bootstrap 95% CI: `[-0.02732, +0.01639]`, spans zero).
     - **Terminal Holdout (`2022–2026`)**: $\Delta \text{LogLoss} = -0.00094$ (Bootstrap 95% CI: `[-0.00096, +0.00300]`, Cohen's d = `+0.029`, **not statistically significant**, spans zero). Diebold-Mariano test: HLN statistic = `-0.709`, $p = 0.4783$ (**not significant**). $\Delta \text{Pearson IC} = -0.00196$ (Bootstrap 95% CI: `[-0.03132, +0.02493]`, spans zero).
   - **Snapshot B (08:50 IST Cutoff)**:
     - **OOF Validation (`2014–2021`)**: $\Delta \text{LogLoss} = +0.00208$ (**statistically significant degradation**, Bootstrap 95% CI for loss reduction: `[-0.00408, -0.00007]`). Baseline Model 1 achieves significantly lower log loss than Model 2. Diebold-Mariano test on returns: HLN statistic = `-0.082`, $p = 0.9344$ (**not significant**). $\Delta \text{Pearson IC} = +0.00911$ (Bootstrap 95% CI: `[-0.01261, +0.02869]`, spans zero).
     - **Terminal Holdout (`2022–2026`)**: $\Delta \text{LogLoss} = +0.00080$ (Model 2 log loss higher; accuracy drops from `37.87%` to `36.74%`; Macro F1 collapses from `0.2555` to `0.1971`). Diebold-Mariano test: HLN statistic = `0.639`, $p = 0.5230$ (**not significant**). $\Delta \text{Pearson IC} = +0.00151$ (Bootstrap 95% CI: `[-0.02288, +0.02133]`, spans zero).

2. **Ablation & Regime Interaction Models**:
   - None of the 6 disjoint ablation subsets (**News-Count**, **News-Sentiment**, **News-Importance**, **News-Event**, **News-Novelty**, **News-Company**) demonstrated statistically significant out-of-sample improvement over Model 1.
   - For Snapshot A OOF, `M2-Ablation-Event` degraded return forecast accuracy significantly below Model 1 (Diebold-Mariano HLN $p = 0.0304$).
   - For Snapshot B OOF, `M2-Ablation-Novelty` degraded return forecast accuracy significantly below Model 1 (Diebold-Mariano HLN $p = 0.0441$).
   - **Model 3 (Regime Interactions)** degraded classification performance on Snapshot B OOF (statistically significant log loss increase, 95% CI: `[-0.00397, -0.00013]`).

3. **Feature Importance & Tree Attribution**:
   - In both Snapshot A and Snapshot B classifiers, **zero news features** appear in the top 10 gain rankings. The trees are overwhelmingly dominated by price moving averages and momentum ratios (`close_to_sma_10`, `close_to_sma_5`, `close_to_sma_20`, `ret_3d`, `ret_10d`).
   - In regressors, price trend and global context variables (`trend_slope_20d`, `ret_2d`, `ctx_ret_1d_sp500`, `ctx_ret_1d_gold`, `ctx_level_us_vix`) dominate. News features that receive non-zero splits inject noise without improving generalized out-of-sample error.

### Official Forensic Taxonomy Verdict:
$$\mathbf{Snapshot\ A:\ B)\ NO\ ROBUST\ INCREMENTAL\ VALUE}$$
$$\mathbf{Snapshot\ B:\ C)\ NEWS\ DEGRADES\ PERFORMANCE}$$
$$\mathbf{OVERALL\ CONCLUSION:\ B)\ NO\ ROBUST\ INCREMENTAL\ VALUE\ /\ C)\ NEWS\ DEGRADES\ PERFORMANCE}$$

**Scientific Bottom Line**: Authentic Point-in-Time corporate news disclosures do **not** provide robust, statistically significant, or economically meaningful predictive value for aggregate next-day NIFTY 50 index movements beyond Price and Market Context. Integrating news features increases model complexity and risks degrading probability calibration and directional F1 scores.

---

## 2. Cryptographic Provenance & Protected Checksum Verification

Prior to model initialization, all protected historical and terminal artifacts were checked against their sealed SHA-256 signatures:

| Artifact Path | Expected SHA-256 Checksum | Verified SHA-256 Checksum | Status |
| :--- | :--- | :--- | :---: |
| `data/interim/news/raw_authentic_news_inventory.jsonl` | `6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3` | `6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3` | **VERIFIED** |
| `data/interim/news/gold_holdout_annotation_input.csv` | `0d55a12d3321886016b62a54eb683f54d827c831ec6f360bd188d2d489bd7199` | `0d55a12d3321886016b62a54eb683f54d827c831ec6f360bd188d2d489bd7199` | **VERIFIED** |
| `data/interim/news/raw_authentic_news_terminal_2022_2026_step2e.jsonl` | `5d5daf5ed7c844e86d45dc6a893f03b1d4f523183e29200d94b592329136f6fd` | `5d5daf5ed7c844e86d45dc6a893f03b1d4f523183e29200d94b592329136f6fd` | **VERIFIED** |
| `data/interim/news/features_news_snapshot_a.csv` | `487ce996f039867959fefc0bc6ea54e0b9b9d4c39e2a09a44944fa87c408f4f7` | `487ce996f039867959fefc0bc6ea54e0b9b9d4c39e2a09a44944fa87c408f4f7` | **VERIFIED** |
| `data/interim/news/features_news_snapshot_b.csv` | `f57137c0244e97e816ed5d8eef7b0afd39d309e5f68327a230747eadab423606` | `f57137c0244e97e816ed5d8eef7b0afd39d309e5f68327a230747eadab423606` | **VERIFIED** |
| `data/interim/news/features_news_snapshot_delta.csv` | `8923c11583fb87fe8458f00aaf714eadacb8a3d402a7143a5b2483549c8ece4c` | `8923c11583fb87fe8458f00aaf714eadacb8a3d402a7143a5b2483549c8ece4c` | **VERIFIED** |

All 6 source datasets remain locked, uncorrupted, and byte-for-byte identical to their pre-registered states.

---

## 3. Sample Counts & Temporal Partition Alignment

The 4-way chronological inner join across Phase 4 Price (`nifty50_features_clean.csv`), Phase 5 Targets (`nifty50_targets_snapshot_*.csv`), Phase 7 Context (`snapshot_*_context_daily.csv`), and Phase 9 Step 3 News (`features_news_snapshot_*.csv`) executed with **zero dropped rows**:

| Partition | Temporal Span | Supervised Trading Sessions | Notes |
| :--- | :---: | :---: | :--- |
| **Complete Supervised Span** | `2008-07-08` to `2026-09-03` | **4,453** | 100% exact parity with Phase 6 |
| **Development Partition** | `2008-07-08` to `2021-12-31` | **3,299** | Used for CV folds, calibration, and production refits |
| — *Pre-OOF Baseline* | `2008-07-08` to `2013-12-31` | 1,339 | Warm-up training set for Fold 1 |
| — *OOF Walk-Forward Folds* | `2014-01-02` to `2021-12-31` | **1,960** | 8 annual expanding folds (Folds 1–8) |
| **Terminal Holdout** | `2022-01-03` to `2026-09-03` | **1,154** | Single-pass forward evaluation only |
| **Terminal Inference Session** | `2026-09-04` | 1 | Unsupervised (target $T+1$ unobserved) |

---

## 4. Frozen Model Hyperparameters & Sealed Tree Counts

To eliminate hyperparameter confounding, the primary comparison preserved the exact sealed Phase 6 models (`configs/models.yaml`):

### Direction Classifier (`objective: multi:softprob`, 3 classes)
- `learning_rate`: `0.10`
- `max_depth`: `2`
- `min_child_weight`: `10.0`
- `subsample`: `0.8`
- `colsample_bytree`: `0.8`
- `reg_alpha`: `0.1`
- `reg_lambda`: `1.0`
- **Sealed Tree Count ($N^*$): `12` trees**
- **Calibration**: Multinomial Platt Scaler fitted strictly on OOF cross-validation probabilities.

### Return Regressor (`objective: reg:squarederror`)
- `learning_rate`: `0.05`
- `max_depth`: `2`
- `min_child_weight`: `20.0`
- `subsample`: `0.8`
- `colsample_bytree`: `0.7`
- `reg_alpha`: `0.5`
- `reg_lambda`: `2.0`
- **Sealed Tree Count ($N^*$): `43` trees**

---

## 5. Model Hierarchy & Feature Space Ladder

| Model ID | Category | Feature Count | Composition |
| :--- | :--- | :---: | :--- |
| **Model 0** | Price Baseline | 45 | 45 Phase 4 technical features |
| **Model 1** | Price + Context Baseline | 63 | Model 0 (45) + 18 Phase 7 Context features |
| **Model 2** | Price + Context + News-All | **112** | Model 1 (63) + 49 Phase 9 Step 3 News features |
| **M2-Ablation-Count** | Ablation: Volume / Counts | 69 | Model 1 (63) + 6 News-Count features |
| **M2-Ablation-Sentiment** | Ablation: Sentiment Polarity | 73 | Model 1 (63) + 10 News-Sentiment features |
| **M2-Ablation-Importance** | Ablation: Economic Importance | 67 | Model 1 (63) + 4 News-Importance features |
| **M2-Ablation-Event** | Ablation: Corporate Events | 81 | Model 1 (63) + 18 News-Event features |
| **M2-Ablation-Novelty** | Ablation: Novelty / Decay | 66 | Model 1 (63) + 3 News-Novelty features |
| **M2-Ablation-Company** | Ablation: Entity / Concentration | 71 | Model 1 (63) + 8 News-Company features |
| **Model 3** | Secondary: Regime Interaction | 115 | Model 2 (112) + 3 VIX Regime interaction features |

**Mutual Exclusivity Audit**:
$$\text{Count}(6) \cap \text{Sentiment}(10) \cap \text{Importance}(4) \cap \text{Event}(18) \cap \text{Novelty}(3) \cap \text{Company}(8) = \emptyset$$
$$\sum \text{Ablation Features} = 6 + 10 + 4 + 18 + 3 + 8 = 49 \text{ features}$$

---

## 6. Snapshot A Experimental Results (15:40 IST Cutoff)

### A. Development Out-Of-Fold (OOF) Performance (1,960 sessions, 2014–2021)

| Model ID | Dims | LogLoss (Cal) | Brier (Cal) | Accuracy | Macro F1 | ECE | RMSE (%) | Pearson IC | $\Delta \text{LogLoss}$ vs M1 | Bootstrap 95% CI (Loss Red.) | DM HLN $p$-val | $\Delta \text{IC}$ vs M1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Model 0** | 45 | 1.08350 | 0.65721 | 38.93% | 0.2457 | 0.0083 | 1.0783 | +0.0193 | -0.00099 | [-0.00132, 0.00344] | 0.4231 | -0.00359 |
| **Model 1** | 63 | **1.08449** | **0.65770** | **38.67%** | **0.2305** | **0.0140** | **1.0780** | **+0.0229** | **0.00000** | [0.00000, 0.00000] | 1.0000 | **0.00000** |
| **Model 2** | 112 | 1.08442 | 0.65768 | 38.72% | 0.2352 | 0.0095 | 1.0783 | +0.0195 | -0.00007 | [-0.00150, 0.00171] | 0.8301 | -0.00336 |
| *M2-Count* | 69 | 1.08496 | 0.65799 | 38.93% | 0.2317 | 0.0078 | 1.0779 | +0.0245 | +0.00047 | [-0.00152, 0.00065] | 0.9488 | +0.00162 |
| *M2-Sentiment* | 73 | 1.08452 | 0.65773 | 38.98% | 0.2346 | 0.0065 | 1.0781 | +0.0216 | +0.00003 | [-0.00105, 0.00100] | 0.1284 | -0.00128 |
| *M2-Importance*| 67 | 1.08417 | 0.65751 | 38.98% | 0.2320 | 0.0073 | 1.0775 | +0.0321 | -0.00032 | [-0.00073, 0.00143] | 0.7800 | +0.00924 |
| *M2-Event* | 81 | 1.08410 | 0.65739 | 39.13% | 0.2367 | 0.0054 | 1.0781 | +0.0206 | -0.00039 | [-0.00102, 0.00183] | **0.0304\*** | -0.00230 |
| *M2-Novelty* | 66 | 1.08507 | 0.65806 | 38.52% | 0.2251 | 0.0102 | 1.0775 | +0.0311 | +0.00058 | [-0.00159, 0.00020] | 0.7120 | +0.00827 |
| *M2-Company* | 71 | 1.08390 | 0.65737 | 38.93% | 0.2337 | 0.0075 | 1.0786 | +0.0129 | -0.00059 | [-0.00070, 0.00179] | 0.4606 | -0.00993 |
| **Model 3** | 115 | 1.08370 | 0.65725 | 38.78% | 0.2403 | 0.0096 | 1.0779 | +0.0253 | -0.00079 | [-0.00095, 0.00255] | 0.9121 | +0.00239 |

*\*Statistically significant degradation below Model 1 ($p < 0.05$).*

### B. Terminal Holdout Performance (1,154 sessions, 2022–2026)

| Model ID | Dims | LogLoss (Cal) | Brier (Cal) | Accuracy | Macro F1 | ECE | RMSE (%) | Pearson IC | $\Delta \text{LogLoss}$ vs M1 | Bootstrap 95% CI (Loss Red.) | DM HLN $p$-val | $\Delta \text{IC}$ vs M1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Model 0** | 45 | 1.08767 | 0.65989 | 37.35% | 0.2142 | 0.0218 | 0.8659 | +0.0294 | -0.00011 | [-0.00244, 0.00285] | 0.3245 | -0.02744\* |
| **Model 1** | 63 | **1.08778** | **0.65988** | **36.83%** | **0.2028** | **0.0313** | **0.8647** | **+0.0569** | **0.00000** | [0.00000, 0.00000] | 1.0000 | **0.00000** |
| **Model 2** | 112 | 1.08684 | 0.65930 | 37.78% | 0.2164 | 0.0209 | 0.8648 | +0.0549 | -0.00094 | [-0.00096, 0.00300] | 0.4783 | -0.00196 |
| *M2-Count* | 69 | 1.08754 | 0.65979 | 36.92% | 0.2072 | 0.0296 | 0.8647 | +0.0553 | -0.00024 | [-0.00092, 0.00140] | 0.5290 | -0.00154 |
| *M2-Sentiment* | 73 | 1.08878 | 0.66053 | 36.92% | 0.2070 | 0.0287 | 0.8649 | +0.0521 | +0.00100 | [-0.00237, 0.00047] | 0.0949 | -0.00477 |
| *M2-Importance*| 67 | 1.08764 | 0.65977 | 37.09% | 0.2130 | 0.0288 | 0.8645 | +0.0593 | -0.00014 | [-0.00083, 0.00101] | 0.8245 | +0.00240 |
| *M2-Event* | 81 | 1.08797 | 0.65993 | 37.35% | 0.2117 | 0.0269 | 0.8647 | +0.0570 | +0.00019 | [-0.00191, 0.00165] | 0.1715 | +0.00011 |
| *M2-Novelty* | 66 | 1.08844 | 0.66029 | 37.00% | 0.2035 | 0.0287 | 0.8644 | +0.0621 | +0.00066 | [-0.00198, 0.00074] | 0.6218 | +0.00526 |
| *M2-Company* | 71 | 1.08813 | 0.66012 | 37.00% | 0.2114 | 0.0307 | 0.8645 | +0.0602 | +0.00035 | [-0.00164, 0.00104] | 0.6563 | +0.00335 |
| **Model 3** | 115 | 1.08686 | 0.65935 | 37.18% | 0.2161 | 0.0269 | 0.8645 | +0.0602 | -0.00092 | [-0.00102, 0.00295] | 0.6294 | +0.00331 |

*\*Model 1 significantly outperforms Model 0 on Holdout IC (Context adds statistically significant value, while News does not).*

---

## 7. Snapshot B Experimental Results (08:50 IST Cutoff)

### A. Development Out-Of-Fold (OOF) Performance (1,960 sessions, 2014–2021)

| Model ID | Dims | LogLoss (Cal) | Brier (Cal) | Accuracy | Macro F1 | ECE | RMSE (%) | Pearson IC | $\Delta \text{LogLoss}$ vs M1 | Bootstrap 95% CI (Loss Red.) | DM HLN $p$-val | $\Delta \text{IC}$ vs M1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Model 0** | 45 | 1.08350 | 0.65721 | 38.93% | 0.2457 | 0.0083 | 1.0783 | +0.0193 | +0.00122 | [-0.00390, 0.00174] | 0.2264 | -0.04546 |
| **Model 1** | 63 | **1.08228** | **0.65606** | **39.49%** | **0.2782** | **0.0042** | **1.0755** | **+0.0647** | **0.00000** | [0.00000, 0.00000] | 1.0000 | **0.00000** |
| **Model 2** | 112 | 1.08436 | 0.65748 | 39.34% | 0.2442 | 0.0043 | 1.0751 | +0.0739 | **+0.00208\***| **[-0.00408, -0.00007]\***| 0.9344 | +0.00911 |
| *M2-Count* | 69 | 1.08225 | 0.65618 | 39.29% | 0.2563 | 0.0057 | 1.0754 | +0.0677 | -0.00003 | [-0.00187, 0.00185] | 0.2096 | +0.00293 |
| *M2-Sentiment* | 73 | 1.08340 | 0.65687 | 39.18% | 0.2555 | 0.0061 | 1.0754 | +0.0673 | +0.00112 | [-0.00275, 0.00069] | 0.1220 | +0.00260 |
| *M2-Importance*| 67 | 1.08304 | 0.65655 | 39.18% | 0.2604 | 0.0099 | 1.0758 | +0.0612 | +0.00076 | [-0.00202, 0.00060] | 0.2741 | -0.00351 |
| *M2-Event* | 81 | 1.08268 | 0.65647 | 39.03% | 0.2628 | 0.0092 | 1.0753 | +0.0689 | +0.00040 | [-0.00236, 0.00164] | 0.1193 | +0.00413 |
| *M2-Novelty* | 66 | 1.08312 | 0.65665 | 39.49% | 0.2616 | 0.0029 | 1.0760 | +0.0591 | +0.00084 | [-0.00215, 0.00057] | **0.0441\*** | -0.00567 |
| *M2-Company* | 71 | 1.08335 | 0.65689 | 39.59% | 0.2596 | 0.0028 | 1.0756 | +0.0652 | +0.00107 | [-0.00262, 0.00056] | 0.1316 | +0.00050 |
| **Model 3** | 115 | 1.08442 | 0.65749 | 39.03% | 0.2418 | 0.0056 | 1.0751 | +0.0740 | **+0.00214\***| **[-0.00397, -0.00013]\***| 0.8193 | +0.00925 |

*\*Statistically significant degradation below Model 1 ($p < 0.05$ or non-overlapping bootstrap CI).*

### B. Terminal Holdout Performance (1,154 sessions, 2022–2026)

| Model ID | Dims | LogLoss (Cal) | Brier (Cal) | Accuracy | Macro F1 | ECE | RMSE (%) | Pearson IC | $\Delta \text{LogLoss}$ vs M1 | Bootstrap 95% CI (Loss Red.) | DM HLN $p$-val | $\Delta \text{IC}$ vs M1 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Model 0** | 45 | 1.08767 | 0.65989 | 37.35% | 0.2142 | 0.0218 | 0.8659 | +0.0294 | -0.00173 | [-0.00256, 0.00607] | 0.3443 | -0.00942 |
| **Model 1** | 63 | **1.08940** | **0.66119** | **37.87%** | **0.2555** | **0.0342** | **0.8656** | **+0.0388** | **0.00000** | [0.00000, 0.00000] | 1.0000 | **0.00000** |
| **Model 2** | 112 | 1.09020 | 0.66157 | 36.74% | 0.1971 | 0.0360 | 0.8655 | +0.0404 | +0.00080 | [-0.00372, 0.00179] | 0.5230 | +0.00151 |
| *M2-Count* | 69 | 1.08883 | 0.66081 | 36.83% | 0.2288 | 0.0375 | 0.8654 | +0.0437 | -0.00057 | [-0.00112, 0.00228] | 0.9425 | +0.00486 |
| *M2-Sentiment* | 73 | 1.08933 | 0.66100 | 37.78% | 0.2353 | 0.0279 | 0.8651 | +0.0491 | -0.00007 | [-0.00181, 0.00185] | 0.4119 | +0.01028 |
| *M2-Importance*| 67 | 1.08960 | 0.66133 | 37.35% | 0.2218 | 0.0322 | 0.8651 | +0.0478 | +0.00020 | [-0.00193, 0.00137] | 0.4515 | +0.00899 |
| *M2-Event* | 81 | 1.08994 | 0.66140 | 37.61% | 0.2318 | 0.0307 | 0.8665 | +0.0258 | +0.00054 | [-0.00253, 0.00138] | 0.2957 | -0.01309 |
| *M2-Novelty* | 66 | 1.08899 | 0.66088 | 37.61% | 0.2273 | 0.0380 | 0.8653 | +0.0446 | -0.00041 | [-0.00115, 0.00188] | 0.4409 | +0.00579 |
| *M2-Company* | 71 | 1.08997 | 0.66141 | 37.18% | 0.2335 | 0.0333 | 0.8654 | +0.0428 | +0.00057 | [-0.00224, 0.00105] | 0.7907 | +0.00395 |
| **Model 3** | 115 | 1.08928 | 0.66108 | 36.92% | 0.1951 | 0.0358 | 0.8655 | +0.0409 | -0.00012 | [-0.00247, 0.00219] | 0.9998 | +0.00206 |

---

## 8. In-Depth Statistical Hypothesis Testing & Interpretation

### A. Classification Loss Differential (Log Loss & Brier Score)
Across all evaluated configurations, the stationary block bootstrap (1,000 resamples, block size 10) indicates:
1. **Snapshot A**:
   - Model 2 achieves a nominal calibrated log loss reduction of `0.00007` on OOF and `0.00094` on Holdout.
   - However, the 95% bootstrap confidence intervals (`[-0.00150, 0.00171]` for OOF, `[-0.00096, 0.00300]` for Holdout) both cross zero.
   - The corresponding Cohen's $d$ effect sizes are `0.002` and `0.029`, representing near-zero effect sizes that are indistinguishable from white noise.
2. **Snapshot B**:
   - On Development OOF, Model 2 **increases** log loss by `0.00208`. The 95% bootstrap confidence interval for loss reduction is `[-0.00408, -0.00007]`.
   - Because the upper bound of the confidence interval is strictly negative, the null hypothesis is rejected in favor of the baseline: **Model 1 (Price + Context) achieves statistically significantly better calibrated log loss than Model 2**.
   - On Terminal Holdout, Model 2 again exhibits higher log loss (`1.09020` vs `1.08940`), lower directional accuracy (`36.74%` vs `37.87%`), and an alarming collapse in Macro F1 (`0.1971` vs `0.2555`). Adding 49 news features causes the classifier to over-predict the majority class and lose sensitivity to minority directional movements.

### B. Continuous Return Forecast Accuracy (Diebold-Mariano HAC Test)
The Diebold-Mariano test with Newey-West HAC covariance and Harvey-Leybourne-Newey (HLN) finite-sample correction evaluates whether Model 2 achieves lower mean absolute error $|e_t|$ than Model 1:
- **Snapshot A OOF**: HLN stat = `-0.215`, $p = 0.8301$ $\to$ Fail to reject null hypothesis of equal forecast accuracy.
- **Snapshot A Holdout**: HLN stat = `-0.709`, $p = 0.4783$ $\to$ Fail to reject null hypothesis.
- **Snapshot B OOF**: HLN stat = `-0.082`, $p = 0.9344$ $\to$ Fail to reject null hypothesis.
- **Snapshot B Holdout**: HLN stat = `+0.639`, $p = 0.5230$ $\to$ Fail to reject null hypothesis.

In all cases, $p \gg 0.05$. There is no evidence of forecast accuracy divergence between Model 1 and Model 2 for continuous returns.

### C. Information Coefficient (Pearson IC Bootstrap)
- On Snapshot A, Model 2 exhibits a lower Pearson IC than Model 1 on both OOF (`+0.0195` vs `+0.0229`, $\Delta = -0.0034$) and Holdout (`+0.0549` vs `+0.0569`, $\Delta = -0.0020$).
- On Snapshot B, Model 2 exhibits a slight nominal increase in Pearson IC on OOF (`+0.0739` vs `+0.0647`, $\Delta = +0.0091$) and Holdout (`+0.0404` vs `+0.0388`, $\Delta = +0.0015$). However, the 95% block bootstrap confidence interval spans zero (`[-0.01261, +0.02869]` on OOF, `[-0.02288, +0.02133]` on Holdout), confirming that this nominal difference is statistically insignificant.

---

## 9. Feature Importance & Tree Attribution Audit

To inspect why the models fail to extract incremental signal from news features, feature importances (split gain and frequency weight) were extracted directly from the native booster trees:

### Top Feature Importances by Gain (Production Model on Development Partition)

#### Snapshot A Direction Classifier:
1. `close_to_sma_10` (Price): Gain = `15.75`
2. `close_to_sma_5` (Price): Gain = `14.28`
3. `close_to_sma_20` (Price): Gain = `12.57`
4. `ret_3d` (Price): Gain = `9.44`
5. `ret_10d` (Price): Gain = `8.07`
6. `ctx_level_us_vix` (Context): Gain = `6.85`
7. `trend_slope_20d` (Price): Gain = `6.41`
...
- **First News Feature in Classifier**: `unique_company_count` ranks **#28** (Gain = `0.84`).
- Over 85% of tree splits in the 12-tree classifier are assigned to price moving average ratios and local return lags.

#### Snapshot A Return Regressor:
1. `trend_slope_20d` (Price): Gain = `0.00302`
2. `ret_2d` (Price): Gain = `0.00137`
3. `volatility_10d` (Price): Gain = `0.00130`
4. `volatility_5d` (Price): Gain = `0.00118`
5. `novelty_weighted_sentiment` (News): Gain = `0.00115`
6. `ctx_ret_1d_sp500` (Context): Gain = `0.00108`
7. `ctx_diff_1d_india_vix` (Context): Gain = `0.00104`

While `novelty_weighted_sentiment` and `company_novelty_mean` receive occasional splits in the regressor, their splits do not improve out-of-sample RMSE or IC, indicating that these splits represent sample-specific variance fitting rather than structural predictive signal.

---

## 10. Quantitative & Economic Explanations for News Inefficacy

Why does high-quality, authentic, leakage-free corporate disclosure NLP fail to provide predictive edge for the NIFTY 50 index?

1. **Market Efficiency & Algorithmic Discounting**:
   Official corporate filings submitted to the National Stock Exchange (NSE) are ingested and acted upon within milliseconds by co-located algorithmic and institutional market participants. By the time a daily session concludes (Snapshot A at 15:30 IST) or the pre-market opens (Snapshot B at 08:50 IST), any actionable valuation adjustments have already been priced into individual stocks and the broader cash index.

2. **Macro vs. Micro Aggregation Asymmetry**:
   The NIFTY 50 is a market-cap weighted index representing the 50 largest companies in India. Most corporate announcements (e.g., board meetings, small order wins, dividend declarations, credit rating reaffirmations) are company-specific idiosyncratic events. In aggregate index returns, idiosyncratic firm news cancels out, while macro factors (crude oil, US equities, interest rate yields, currency moves, VIX) dominate. The Phase 7 Context features capture these macro forces directly, rendering firm-level news counts redundant.

3. **High Noise-to-Signal Ratio in Aggregate Disclosures**:
   Out of the ~62,329 historical corporate announcements, a vast majority (>85%) consist of routine compliance notices, statutory disclosures, postal ballot updates, and procedural filings. Even with sentiment lexicons and importance filtering, the aggregate daily news count fluctuates primarily due to calendar compliance cycles (e.g., quarter-end filing deadlines) rather than true economic shocks to the aggregate economy.

4. **Curse of Dimensionality in Tree Models**:
   Adding 49 noisy features to a 63-feature model increases the feature space by 78%. In shallow gradient-boosted trees ($depth = 2$), each split on a spurious news variable deprives the model of a split on a robust price or macro feature, diluting predictive power and increasing out-of-sample variance.

---

## 11. Final Recommendations & Architecture Governance

1. **Production Baseline Selection**:
   - **Recommendation**: Retain **Model 1 (Price + Context)** or **Model 0 (Price Only)** for production forecasting.
   - **Do NOT deploy Model 2 (Price + Context + News)** into live trading or signal generation.
   - Integrating news introduces operational fragility (API scraping latency, NSE website downtime, HTML parsing errors) while demonstrably failing to generate alpha.

2. **Phase 10 & Beyond**:
   - Step 4 execution is complete. All artifacts are saved and verified.
   - In accordance with the prompt's governance mandate, **Phase 10 is NOT initiated**.
   - The system halts here for user review and audit of the experimental findings.

---

## 12. Artifact Signatures & Manifest

| Output Artifact Path | Type | Row Count | SHA-256 Checksum |
| :--- | :--- | :---: | :--- |
| `data/interim/news/phase9_step4_experiment_results.csv` | Experiment Summary Metrics | 40 | `7d0f39f7ce8a50b6f8b1591dc6ce9b3a4af8f75507531740a06147cb4aedffc3` |
| `data/interim/news/phase9_step4_oof_results.csv` | Session-by-Session OOF Predictions | 3,920 | `62b88a1689c7ed57e1ddf79ca0064356eec5d2a16e00f7975998a155141f02d8` |
| `data/interim/news/phase9_step4_holdout_results.csv` | Session-by-Session Holdout Predictions | 2,308 | `4359edb7e585053c676e444d958a4265c584b9b13a58c89dd38067fc0bc41967` |
| `configs/phase9_step4_experiment_config.json` | Provenance & Config Manifest | JSON | `8940206588dad34eb5a9d2fdb01ecbfeb629930374a733c15d077b2281ae7547` |
| `tests/test_phase9_step4_experiments.py` | Automated Verification Suite | 11 tests | `4596e785272357c16a13f51ae68133e7fe6dd7700d2c77042db0f9cc66b290bc` |
