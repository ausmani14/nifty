# MASTER SPECIFICATION: NIFTY AI

**Project Name:** NIFTY AI  
**Document Version:** 1.0.0  
**Status:** Approved Architectural & Methodological Contract  
**Target Asset:** NIFTY 50 Index (NSE: NIFTY_50)  
**Primary Language:** Python 3.13  

---

## 1. Executive Summary & Market Scope

### 1.1 Project Objective
**NIFTY AI** is a professional, research-grade, and production-viable machine learning and paper-trading system. Its core mission is to predict the next trading day's NIFTY 50 directional movement and expected return with rigorous statistical validation, zero data leakage, and automated risk-managed execution in a paper-trading environment.

### 1.2 Market Scope & Version Boundaries
* **Asset Universe (V1):** The **NIFTY 50 Index** benchmark only.
* **Future Expansion:** Individual NIFTY 50 constituent equities, sectoral indices (NIFTY Bank, NIFTY IT), and derivative instruments (options/futures) may be considered in subsequent major versions.
* **Temporal Granularity (V1):** **Daily data only** (End-of-Day and Pre-Market aggregates).
* **Out of Scope (V1):** Intraday high-frequency trading (HFT), order book tick data, real-money execution, and live automated brokerage trading.

---

## 2. Dual Prediction Horizons & Information Cutoffs

Financial markets transition between domestic session finality and overnight global macro information flow. To capture both information sets cleanly without look-ahead bias, NIFTY AI operates on two distinct prediction snapshots for each target trading day \( T \):

```
Trading Day T - 1                                                      Trading Day T
──────────────────────────────────────────────────────────────────────────────────────────
[09:15 - 15:30 IST]           15:40 IST                     08:50 IST            [09:15 IST]
Market Session T-1            Snapshot A                    Snapshot B           Market Open T
                              (Post-Close)                  (Pre-Market)
                              Cutoff: 15:30 IST             Cutoff: 08:50 IST
```

### 2.1 Snapshot A — 3:40 PM IST (Post-Market Close)
* **Execution Timestamp:** 15:40:00 IST on trading day \( T-1 \).
* **Information Cutoff:** Strictly **15:30:00 IST** on trading day \( T-1 \).
* **Target Trading Day:** Day \( T \).
* **Permitted Inputs:**
  * Official closing data for NIFTY 50 on Day \( T-1 \) (cash and settled futures/options).
  * NSE market breadth, advance/decline ratios, sector performance up to 15:30 IST.
  * Domestic institutional flows (FII/DII preliminary estimates if certified published before 15:40 IST; otherwise deferred to Snapshot B).
  * Technical indicators computed strictly on finalized \( T-1 \) daily bars and historical series.
* **Prohibited Inputs:** Any data published or revised after 15:30:00 IST on Day \( T-1 \).

### 2.2 Snapshot B — 8:50 AM IST (Pre-Market Open)
* **Execution Timestamp:** 08:50:00 IST on trading day \( T \).
* **Information Cutoff:** Strictly **08:50:00 IST** on trading day \( T \).
* **Target Trading Day:** Day \( T \).
* **Permitted Inputs:**
  * All inputs from Snapshot A.
  * Overnight global equity closes (US S&P 500, NASDAQ, Dow Jones; European FTSE, DAX; Asian Nikkei, Hang Seng, Shanghai).
  * GIFT Nifty early trading prints prior to 08:50 IST.
  * Global commodities (Crude Oil Brent/WTI, Gold), US Dollar Index (DXY), USD/INR forex movements.
  * Overnight financial news headlines and NLP sentiment published between 15:30:00 IST (Day \( T-1 \)) and 08:50:00 IST (Day \( T \)).
  * Finalized official FII/DII trade statistics released on the evening of Day \( T-1 \).
* **Prohibited Inputs:** Any data, prints, or news published at or after 08:50:00 IST on Day \( T \).

---

## 3. Prediction Outputs & Mathematical Formulations

For every snapshot (Snapshot A and Snapshot B), the system produces three synchronized outputs:

### 3.1 Outputs
1. **Directional Classification:** A 3-class categorical prediction:
   $$\hat{y}_{\text{dir}} \in \{\text{UP}, \text{DOWN}, \text{SIDEWAYS}\}$$
   accompanied by calibrated class probabilities:
   $$P(\text{UP}), \quad P(\text{DOWN}), \quad P(\text{SIDEWAYS}) \quad \text{where} \quad \sum P = 1.0$$
2. **Expected Return Regression:** Continuous point estimate of expected next-day percentage return:
   $$\hat{r}_{T} \in \mathbb{R}$$
3. **Predicted Closing Price:** A derived reference price level based on the current reference closing price \( C_{\text{ref}} \):
   $$\hat{C}_{T} = C_{\text{ref}} \times (1 + \hat{r}_{T})$$
   * *For Snapshot A:* \( C_{\text{ref}} = C_{T-1} \) (the official close of Day \( T-1 \)).
   * *For Snapshot B:* \( C_{\text{ref}} = C_{T-1} \) (maintaining the daily close-to-close reference baseline).

### 3.2 Model Independence
* Direction classification and return regression are modeled using **separate, dedicated estimators** initially.
* Coupling, joint multi-task learning, or stacking will only be explored in later phases if empirical out-of-sample evidence demonstrates superior calibration.

---

## 4. Machine Learning Model Architecture (V1)

### 4.1 Initial Estimators
* **Direction Classifier:** `xgboost.XGBClassifier`
  * Multi-class objective (`multi:softprob` or `multi:softmax`).
  * Optimized for multi-class log loss and balanced macro F1 score.
* **Return Regressor:** `xgboost.XGBRegressor`
  * Continuous regression objective (`reg:squarederror` or `reg:pseudohubererror` for robustness against extreme outlier sessions).
  * Optimized for Mean Squared Error (MSE) and Mean Absolute Error (MAE).

### 4.2 Architectural Modularity
* High-complexity architectures (e.g., LSTMs, GRUs, Temporal Transformers, TabNet, Deep Reinforcement Learning) are **strictly out of scope for V1**.
* All estimators must implement an abstract base interface (`BaseModel`) defining uniform methods:
  * `fit(X, y)`
  * `predict(X)`
  * `predict_proba(X)`
  * `save(path)`
  * `load(path)`
* Models must remain drop-in replaceable without touching feature extraction, backtesting, or paper-trading execution engines.

---

## 5. Scientific Definition of the SIDEWAYS Regime

### 5.1 Rejection of Arbitrary Hard-Coded Thresholds
* Static arbitrary bounds (such as fixed \(\pm 0.25\%\) or \(\pm 0.50\%\)) are strictly prohibited. Volatility regimes vary dramatically across market cycles (e.g., historical low-volatility consolidations vs. high-volatility election/crisis periods).

### 5.2 Dynamic Volatility-Calibrated Thresholding
The boundary between directional trend and sideways consolidation is determined empirically from the historical training window using a rolling volatility estimator:

$$\theta_{T} = k \times \sigma_{\text{rolling}}(T-1)$$

Where:
* \(\sigma_{\text{rolling}}(T-1)\) is the trailing rolling standard deviation of daily returns (or localized Average True Range percentage \(\text{ATR}\%\)) computed strictly up to Day \( T-1 \).
* \(k\) is a scaling hyperparameter (e.g., \(0.25 \le k \le 0.50\)) tuned via walk-forward cross-validation on training folds.

### 5.3 Formal Target Labeling
The target label \( y_{\text{dir}, T} \) for Day \( T \) with actual close-to-close return \( r_{T} = \frac{C_{T} - C_{T-1}}{C_{T-1}} \) is defined as:

$$y_{\text{dir}, T} = \begin{cases}
\text{UP}, & \text{if } r_{T} > +\theta_{T} \\
\text{DOWN}, & \text{if } r_{T} < -\theta_{T} \\
\text{SIDEWAYS}, & \text{if } -\theta_{T} \le r_{T} \le +\theta_{T}
\end{cases}$$

### 5.4 Leakage Prevention Contract
* \(\theta_{T}\) must **never** incorporate data from Day \( T \) or any point beyond the training partition boundary.
* Threshold statistics computed on a training window must be frozen when evaluating validation or out-of-sample test splits.

---

## 6. Data Architecture & Ingestion Standards

### 6.1 Four Ingestion Pillars
```
┌────────────────────────────────────────────────────────────────────────┐
│                        NIFTY AI Data Layers                            │
├─────────────────┬─────────────────┬──────────────────┬─────────────────┤
│    Pillar A     │    Pillar B     │     Pillar C     │    Pillar D     │
│  NIFTY History  │  Indian Market  │  Global & Macro  │ News Intel/NLP  │
│   & Technicals  │     Context     │     Context      │                 │
├─────────────────┼─────────────────┼──────────────────┼─────────────────┤
│ OHLCV           │ Market Breadth  │ US/EU/Asia Eq    │ Financial News  │
│ Returns         │ Sector Indices  │ GIFT Nifty       │ Event Calendar  │
│ Volatility      │ FII / DII Flows │ Crude Oil, Gold  │ Macro Releases  │
│ Moving Averages │ India VIX       │ DXY, USD/INR     │ Sentiment Index │
└─────────────────┴─────────────────┴──────────────────┴─────────────────┘
```

### 6.2 Provider-Agnostic Abstraction
* Data ingestion must be decoupled through unified repository interfaces (`BaseDataProvider`).
* Free tier, public scraping, and professional vendor APIs must implement standardized adapters.
* Data tiers have clear separation of intent:
  * **Development / Research:** Rapid exploratory analysis, offline fixtures.
  * **Reference / Benchmark:** Official exchange files (NSE bhavcopy, index archives).
  * **Validation:** Audited out-of-sample verification datasets.
  * **Production / Paper-Trading:** Low-latency live feeds.

### 6.3 Mandatory Metadata Schema
Every ingested observation must be persisted with immutable provenance metadata:
* `provider`: Source identifier (e.g., `nse_official`, `yahoo_finance`, `reuters`).
* `event_timestamp`: Timestamp when the market event or bar concluded.
* `publication_timestamp`: Official timestamp when the data was made publicly available.
* `retrieval_timestamp`: System UTC timestamp when NIFTY AI fetched and recorded the record.
* `timezone`: Source timezone (default: `Asia/Kolkata` for domestic; `UTC` for global).
* `data_type`: Indicator of raw format (`ohlcv`, `flow`, `macro_scalar`, `text`).
* `identifier`: Unique entity symbol (e.g., `^NSEI`, `INDIAVIX`, `BRENT_CRUDE`).

---

## 7. News Intelligence & NLP Architecture

### 7.1 Entity & Event Taxonomy
News intelligence must capture structured attributes for every article/headline:
* `headline`: Cleaned text headline.
* `summary` / `body`: Full text or abstract (subject to licensing/availability).
* `source` / `url`: Publication outlet and verifiable origin.
* `publication_timestamp`: Exact point-in-time when news became readable.
* `entities`: Extracted entities (e.g., `RBI`, `Federal Reserve`, `Reliance`, `Government of India`).
* `sector`: Tagged economic sector (e.g., `Banking`, `IT`, `Energy`, `Macro`).
* `sentiment_score`: Point-in-time normalized polarity score \([-1.0, +1.0]\).
* `event_type`: Categorization (e.g., `monetary_policy`, `corporate_earnings`, `geopolitical`, `macro_data`).
* `importance_weight`: Assessed market significance scale \([1, 5]\).
* `novelty_score`: Metric measuring whether news is breaking vs. repetitive commentary.

### 7.2 Strict Snapshot Separation for News
* **Snapshot A (3:40 PM IST):** Considers only news with `publication_timestamp` between 15:30:00 IST of Day \( T-2 \) and 15:30:00 IST of Day \( T-1 \).
* **Snapshot B (8:50 AM IST):** Incorporates news published between 15:30:00 IST of Day \( T-1 \) and 08:50:00 IST of Day \( T \).
* **Zero Look-Ahead Guarantee:** News with a timestamp \(\ge\) cutoff is strictly excluded from that snapshot’s feature vector.

---

## 8. Market Regime Detection Engine

### 8.1 Purpose
Market behavior exhibits distinct structural phases where underlying predictive relationships shift. A dedicated regime detection module classifies the environment prior to signal generation.

### 8.2 Regime Dimensions
The system classifies market state across two orthogonal axes:
1. **Trend Regime:**
   * `BULL`: Persistent upward structure, trading above key trailing moving averages.
   * `BEAR`: Persistent downward structure, trading below key trailing moving averages.
   * `SIDEWAYS`: Range-bound consolidation, lack of directional conviction.
2. **Volatility Regime:**
   * `HIGH_VOLATILITY`: India VIX or historical realization in upper historical quartiles.
   * `LOW_VOLATILITY`: India VIX or historical realization in lower historical quartiles.

### 8.3 Data-Driven Methodology
* Regimes must be classified using unsupervised clustering (e.g., Gaussian Mixture Models, Hidden Markov Models) or rolling parametric estimators (e.g., ADX/Chop Index + VIX percentile rank).
* Arbitrary, non-adaptive rules are prohibited.
* Regime identifiers serve as conditioning features for models, risk filters, and error analysis partitions.

---

## 9. Validation & Temporal Leakage Prevention

### 9.1 Time-Series Validation Contract
* **Prohibition:** Random K-fold cross-validation, shuffling, and retroactive interpolation are strictly banned.
* **Standard:** Only **Chronological Walk-Forward Validation** (rolling or expanding window) is permitted.

```
Split 1: [--- Train 1 ---][ Val 1 ]
Split 2: [----- Train 2 -----][ Val 2 ]
Split 3: [------- Train 3 -------][ Val 3 ]
Final:   [---------------- Train Full ----------------][ Final Test (Frozen) ]
```

### 9.2 Data Partitioning Guidelines
* **Training Period:** Historical historical window used for feature selection, scaling fitting, and parameter estimation.
* **Validation Period:** Rolling out-of-sample segments for hyperparameter tuning and early stopping.
* **Final Test Period (Holdout):** A strictly isolated historical period reserved for the final benchmark verification. It must **never** be used for iterative parameter tweaking.

### 9.3 Zero Leakage Checklist
* All feature scaling (min-max, standard scaling) must be `fit` exclusively on the training slice, then `transform`ed on validation/test slices.
* Target variables must be shifted forward: \( y_{T} \) represents future Day \( T \); feature vector \( X_{T-1} \) contains only information finalized by the cutoff.

---

## 10. Evaluation Framework: ML & Trading Separation

Machine learning accuracy does not guarantee trading profitability. NIFTY AI evaluates model efficacy and financial efficacy as separate, distinct disciplines.

### 10.1 Machine Learning Evaluation Metrics
* **Classification (Direction):**
  * Multi-class Accuracy
  * Precision, Recall, and Macro-averaged F1 Score
  * Multi-class Log Loss
  * One-vs-Rest ROC-AUC
  * Reliability Diagrams / Expected Calibration Error (ECE)
* **Regression (Expected Return):**
  * Root Mean Squared Error (RMSE)
  * Mean Absolute Error (MAE)
  * Mean Directional Accuracy (MDA) — sign agreement between actual and predicted returns
  * \( R^2 \) / Explained Variance score

### 10.2 Trading System Metrics (Paper Trading & Backtesting)
* **Return & Risk-Adjusted Ratios:**
  * Compound Annual Growth Rate (CAGR)
  * Annualized Sharpe Ratio (risk-free rate aligned with RBI 91-day T-Bill yield)
  * Sortino Ratio (downside deviation risk-adjusted return)
  * Profit Factor (gross gains / gross losses)
* **Drawdown & Stability:**
  * Maximum Drawdown (MDD %)
  * Maximum Drawdown Duration (recovery days)
  * Calmar Ratio (CAGR / MDD)
* **Execution Realism:**
  * Win Rate (% profitable trades)
  * Average Gain / Average Loss ratio
  * Portfolio Turnover Rate
  * Net returns after deduction of calibrated slippage and statutory transaction costs (STT, exchange turnover charges, GST, stamp duty).

---

## 11. Model Explainability & Error Forensics

### 11.1 Transparency Requirement
Black-box opacity is rejected. Every prediction must output interpretable attribution:
* **Global Explainability:**
  * Tree gain and split importance across the dataset.
  * Summary SHAP (SHapley Additive exPlanations) beeswarm plots for feature importance ranking.
* **Local Explainability (Per Prediction):**
  * Top 5 positive and top 5 negative feature contributions (SHAP waterfall/force vectors) explaining why a specific prediction (UP, DOWN, or SIDEWAYS) was generated.
  * Explicit disclaimer: Feature attribution denotes associative predictive contribution, **not causality**.

### 11.2 Error Forensics
When a prediction fails (e.g., model predicted UP, market plunged DOWN):
* The system automatically logs an error incident record.
* Records the divergence between predicted return \(\hat{r}\) and actual return \(r\).
* Correlates errors with market regimes, high-VIX environments, or unprecedented macro events.

---

## 12. Trading Engine & Decision Logic

### 12.1 End-to-End Operational Pipeline
```
[Market Data Ingestion]
         │
         ▼
[Feature Engineering (Timestamp-Aware)]
         │
         ▼
[ML Inference: Direction & Return Estimators]
         │
         ▼
[Decision Engine: Multi-Factor Rule Evaluation]
         │
         ▼
[Risk Engine: Position Sizing & Stop-Loss Setting]
         │
         ▼
[Paper-Trading Broker Simulator: Virtual Order & Fill]
         │
         ▼
[Portfolio Accounting & Performance Attribution]
```

### 12.2 Action Mapping (V1)
* Initial permissible trading actions:
  * `BUY` (Long position)
  * `HOLD` (Cash / Neutral / Flat position)
  * `SHORT` (Short position, simulated in cash index equivalent / futures equivalent)
* **V1 Decision Rule:**
  * Prediction `UP` with calibrated probability \( P(\text{UP}) > \tau_{\text{confidence}} \) and \(\hat{r} > 0\) \(\implies\) `BUY`
  * Prediction `DOWN` with calibrated probability \( P(\text{DOWN}) > \tau_{\text{confidence}} \) and \(\hat{r} < 0\) \(\implies\) `SHORT`
  * Prediction `SIDEWAYS` \(\implies\) `HOLD` (Close open exposure or remain flat)
* All thresholds (\(\tau_{\text{confidence}}\), return cutoffs) must be configurable and validated against backtest data.

---

## 13. Risk Management & Paper Trading Constraints

### 13.1 Strict Paper Trading Mandate
* NIFTY AI is exclusively a research, simulation, and paper-trading engine.
* No live capital is connected. No direct order routing to real financial exchange accounts is enabled.

### 13.2 Position Sizing & Risk Controls
* **Configurable Capital:** Virtual starting equity parameter (e.g., \(\text{INR } 1,000,000\)).
* **Fixed Fractional Risk:** Maximum account equity risked per single trade is limited to a configurable percentage \( R\% \) (default starting benchmark: \(1.0\%\) of portfolio equity).
* **Volatility-Adjusted Position Sizing:**
  $$\text{Units} = \frac{\text{Portfolio Equity} \times R\%}{|\text{Entry Price} - \text{Stop Loss Price}|}$$
* **Stop-Loss and Target Rules:**
  * Dynamic stop-loss derived from trailing Average True Range (\(\text{ATR}\)) or model-predicted volatility.
  * Hard risk limits: Maximum daily loss limit (circuit breaker halting new trades for the day).

---

## 14. Realistic Backtesting Protocol

### 14.1 Friction Modeling
Backtesting must reflect realistic institutional friction:
* **Slippage Modeling:** Modeled as a percentage of entry/exit price or fixed basis points (e.g., 2 to 5 bps) reflecting index execution spreads.
* **Transaction Cost Schedule:** Modeled Indian exchange cost structure:
  * Securities Transaction Tax (STT)
  * Exchange Transaction Charges
  * SEBI Turnover Charges
  * Integrated Goods & Services Tax (GST)
  * Stamp Duty
* **Execution Timing:** Trades execute at the next eligible bar open or designated reference print following snapshot generation.

### 14.2 Bias Avoidance
* **Look-Ahead Bias:** Strict temporal indexing preventing future bar data leakage.
* **Survivorship Bias:** Benchmark index constituent changes tracked point-in-time when stock-level features are introduced.

---

## 15. Semi-Autonomous Model Improvement Architecture

### 15.1 Feedback & Refinement Loop
```
Daily Prediction ──► Actual Market Outcome ──► Error Logging & Drift Check
                                                        │
                                                        ▼
Candidate Rollback ◄── Reject ◄── Out-of-Sample ◄── Automated Candidate
   (Safe State)                    Validation         Model Training
                                        │
                                        ▼ (Passes Strict Criteria)
                                 Promote to Production (Version Bump)
```

### 15.2 Promotion & Rollback Safety Rules
* **No Spurious Retraining:** The production model is **never** altered automatically due to a single-day prediction error.
* **Controlled Evaluation Gate:** A candidate model generated via updated data or hyperparameter tuning must:
  1. Undergo walk-forward historical backtesting across the complete evaluation window.
  2. Demonstrate statistically significant improvement in out-of-sample log loss or Sharpe ratio over the existing production baseline.
  3. Show no regression in maximum drawdown constraints.
* **Immutable Versioning & Rollback:** Every deployed model artifact is tagged with an immutable semantic version. In the event of performance degradation in paper trading, one-command instantaneous rollback to the preceding verified model is guaranteed.

---

## 16. Modular System Architecture & Codebase Contracts

### 16.1 Package Architecture
The codebase adheres strictly to the `src/nifty_ai/` package layout:

```text
src/nifty_ai/
├── config/           # App configuration, settings, environment loading
├── data/             # Ingestion, validation, storage, provider abstractions
├── features/         # Point-in-time indicators, transforms, macro/sentiment alignment
├── models/           # Estimator interfaces, XGBoost implementations, candidate registry
├── evaluation/       # Walk-forward splits, ML metrics, statistical calibration
├── backtesting/      # Simulation engine, cost modeling, portfolio state machine
├── trading/          # Paper-trading execution, risk management, order book state
├── explainability/   # SHAP attribution, feature importance, forensic logging
├── news/             # News fetchers, entity extractors, sentiment pipelines
└── utils/            # Timezone utilities, logging, I/O formatting
```

### 16.2 Architectural Decoupling Contract
* The **data layer** knows nothing about models or trading strategies.
* The **feature layer** receives raw dataframes and produces immutable feature matrices.
* The **model layer** receives numerical arrays/dataframes and outputs predictions/probabilities.
* The **trading layer** receives predictions and makes portfolio decisions based on risk rules.
* Any layer can be refactored or replaced independently without triggering breaking changes in adjacent layers.

---

## 17. Reproducibility & Secrets Governance

### 17.1 Determinism & Tracking
* **Random Seeds:** All stochastic operations (train-test splits, XGBoost seeds, sampling) must accept an explicit `random_state` parameter.
* **Experiment Artifacts:** Training runs must log configuration YAMLs, data snapshot hashes, hyperparameter dictionaries, and validation metrics.
* **Data Versioning:** Feature matrices must store checksums / schema fingerprints.

### 17.2 Secrets Security Protocol
* Hard-coding API keys, broker tokens, database passwords, or personal credentials anywhere in the repository is **strictly forbidden**.
* All sensitive credentials must be accessed via `.env` and environment variables.
* The `.env` file is permanently ignored in [`.gitignore`](file:///C:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/.gitignore).
* Only clean, non-sensitive configuration keys are maintained in [`.env.example`](file:///C:/Users/ABEEL%20USMANI/.antigravity/nifty%20ai/.env.example).

---

## 18. Development Philosophy & Phased Execution

### 18.1 Incremental Delivery Rules
Development proceeds strictly in sequential, bite-sized phases. For every phase:
1. Implement exclusively the defined, minimal scope of that phase.
2. Write comprehensive, dedicated unit and integration tests.
3. Execute the full test suite (`pytest`) and ensure all tests pass.
4. Verify code quality, typing, and docstrings.
5. Report detailed summary of modifications, tests executed, and results.
6. Stop and await user review and explicit approval before advancing.

### 18.2 Ambiguity Resolution Contract
* If an implementation detail is ambiguous, it must be documented as an explicit assumption in the project artifacts rather than silently implemented with arbitrary logic.

---

## 19. Complete Roadmap of Development Phases

| Phase | Phase Name | Focus & Deliverables | Status |
| :---: | :--- | :--- | :---: |
| **0** | **Environment & Scaffold** | Python 3.13 venv, package layout, basic deps, test harness, `.gitignore`, `.env.example`. | **Complete** |
| **1** | **Data Source Architecture** | Provider-agnostic interfaces, metadata schema, source purpose definitions. | *Next* |
| **2** | **Historical NIFTY Data Ingestion** | Ingestion of raw daily NIFTY 50 OHLCV data with timestamp validation. | *Pending* |
| **3** | **Data Cleaning & Validation** | Missing value imputation, calendar alignment, split/dividend corporate action checks. | *Pending* |
| **4** | **Feature Engineering** | Technical indicators, momentum, volatility, point-in-time calculation. | *Pending* |
| **5** | **Target Creation & SIDEWAYS Threshold** | Dynamic volatility-calibrated thresholding, leakage-free label creation. | *Pending* |
| **6** | **XGBoost Direction & Return Models** | Modular model interface, XGBoost classifier and regressor implementations. | *Pending* |
| **7** | **Walk-Forward Evaluation** | Rolling/expanding chronological CV, ML metrics, probability calibration. | *Pending* |
| **8** | **Backtesting Engine** | Realistic simulation, transaction costs, slippage, portfolio accounting. | *Pending* |
| **9** | **Indian & Global Market Context** | India VIX, FII/DII flows, US/EU/Asian equity indices, commodities, forex. | *Pending* |
| **10** | **News Intelligence & NLP** | Ingestion, point-in-time filtering, sentiment and entity extraction. | *Pending* |
| **11** | **Market Regime Detection** | Data-driven trend and volatility regime classification. | *Pending* |
| **12** | **Explainability & Error Forensics** | SHAP values, feature importance ranking, error analysis logging. | *Pending* |
| **13** | **Semi-Autonomous Self-Improvement** | Controlled hypothesis generation, out-of-sample gated promotion. | *Pending* |
| **14** | **Paper-Trading Execution Engine** | Virtual order lifecycle, risk controls, daily snapshot execution. | *Pending* |
| **15** | **Dashboard & Application Interface** | Operational dashboard visualizing predictions, SHAP drivers, paper portfolio. | *Pending* |
| **16** | **Advanced Hybrid Architectures** | Ensembles and deep learning models explored only if justified by experiments. | *Pending* |

---

## 20. Specification Governance & Version History

* Any amendment to this specification requires explicit review, documentation of rationale, and a version increment.
* All code developed throughout the project must remain in compliance with this contract.
